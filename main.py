# -*- coding: utf-8 -*-
import time
import utils
import json
import os
import base64
import re as _re
import sys

# “2026江苏省大学新生安全知识教育”一键完成脚本 (登录版)
# Scwizard/HAM:BA4TLH
# 2025/08/14 (Rebuild at 2026/07/25, fixed at 2026/09/30)
#
# 2026-09-30 修复要点（详见 修复说明.md）：
#   1. 课程完成改为平台现行流程：markArticleViewed -> question/list
#      -> unitTest/create 取凭证 -> unitTest 提交作答（平台按 5 秒/题 校验）。
#      旧版写死的题目 ID 早已失效，服务器返回 1011/1010，脚本却把失败当成功，
#      导致课程永远刷不完，考试接口一直返回“请先完成全部必修安全教育课程”。
#   2. 考试题与课程练习题是同一批题，但每份试卷会重新生成题目 ID 并打乱选项顺序，
#      因此改为按【题干 + 选项文本】匹配答案库（题库答案.json）。
#   3. 补上平台新增的提交凭证(token)、完成校验与错误分支处理，
#      并修掉 utils.end() 缺参数等一系列会掩盖真实错误的崩溃点。

print("本脚本开源免费，如果您付钱得到了这份脚本，恭喜您被骗了。")
STATS = True  # 脚本用量统计，我们只保存您的脚本最终得分和运行时长，不会记录浏览器指纹、IP地址、客户端信息等内容
# 如果您不想开启此功能，请把 True 改成 False

WAIT_SECONDS = 7          # 单元测试每题最短作答时长(平台按 5 秒/题 校验，留点余量)
EXAM_WAIT_SECONDS = 255   # 考试最短答题时长:50 题卷需 250 秒
VERSION = [1, 2, 0]

script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)
print("切换到工作目录：", os.getcwd())

print("您正在运行：登录版 (v1.2.0)")
session = utils.session  # 统一采用 Session 管理会话继承 cookies
collegeId = utils.getUserSchool()
username = str(input("请输入账号：").strip())
password = str(input("请输入密码：").strip())

loginResult = utils.loginMethod(username, password, collegeId)
if not loginResult.get('success'):
    print("登录失败，请检查账号密码和学校是否正确")
    print(loginResult)
    utils.end(1)

openId = loginResult['data']['openId']
userId = loginResult['data']['userId']
realCollegeId = loginResult['data'].get('collegeId') or collegeId
print(f"获取到了userId {userId}，开始执行脚本")
start_time = time.time()

QT_CODE = {"单选": "1", "多选": "2", "判断": "3"}


def finishCourse(userId, collegeId):
    """
    按平台现行流程完成必修课程。
    实测：考试只要求 courseType=2 的江苏新生必修课（11 门）全部完成，
          courseType=1 里混着其它学校/年份的课程，不影响本省考试，故不处理。
    返回 True 表示必修课都已标记完成。
    """
    courses = utils.getCourseList(userId, collegeId, "2")
    todo = [c for c in courses if not c.get("isFinsh")]
    print(f"必修课共 {len(courses)} 门，待完成 {len(todo)} 门")
    for course in todo:
        articles = [a for a in utils.getArticleList(userId, collegeId, course["id"])
                    if not a.get("isFinsh")]
        print(f"  《{course['name']}》待完成文章 {len(articles)} 篇")
        for article in articles:
            if not finishArticle(userId, course["name"], article["id"]):
                print(f"    !! 文章 {article['id']} 未能完成")
    # 复查
    left = [c["name"] for c in utils.getCourseList(userId, collegeId, "2")
            if not c.get("isFinsh")]
    if left:
        print("仍有未完成课程：", "、".join(left[:10]), "..." if len(left) > 10 else "")
        return False
    print("全部必修课程已完成")
    return True


def finishArticle(userId, courseName, articleId):
    """
    完成一篇文章：先上报"课件已看"，再取题作答。
    平台规则：只要有一题作答正确(isSuccess=true)，该文章即算完成；
              单题最短作答时长 5 秒，提交凭证(token)一次性。
    """
    utils.markArticleViewedNew(userId, articleId)
    questions = utils.getArticleQuestions(articleId)
    if not questions:
        return True  # 没有题目，视为已通过

    # 优先用判断题（答案只有 1/0，可稳定命中），否则按答案库做选择题
    attempts = []
    for q in [x for x in questions if x.get("quesType") == "判断"][:3]:
        attempts.append((q, ["%s-1" % q["id"], "%s-0" % q["id"]]))

    if not attempts:
        for q in questions:
            qt = QT_CODE.get(q.get("quesType"), "1")
            val = utils.buildAnswerValue(q, q["id"], qt)
            if val:
                attempts.append((q, [val]))
                break

    if not attempts:
        print("    该文章没有判断题，且答案库里没有对应答案，暂时跳过")
        return False

    for q, values in attempts:
        qt = QT_CODE.get(q.get("quesType"), "1")
        for val in values:
            tokenInfo = utils.createUnitSession(userId, articleId)
            if not tokenInfo.get("token"):
                print("    签发提交凭证失败，稍后重试")
                time.sleep(2)
                continue
            time.sleep(WAIT_SECONDS)
            res = utils.submitUnitAnswer(userId, articleId, courseName,
                                         [("question", val), ("quesType", qt)], tokenInfo)
            data = res.get("data") if isinstance(res.get("data"), dict) else {}
            if data.get("isSuccess"):
                return True
            code = res.get("code")
            if code == 1006:            # 答题时间过短，再等一轮重试
                time.sleep(WAIT_SECONDS)
            elif code in (1010, 1011):  # 防作弊服务限流 / 凭证问题
                time.sleep(3)
    return False


# ======================= 完成必修课程 =======================
print("正在查询课程完成度：")
finishCourse(userId, realCollegeId)

print("正在进入考试流程...")
try:
    examCfg = utils.getExamConfig(userId)
except Exception as e:
    print("获取考试配置失败：", e)
    utils.end(1)

if examCfg.get("code") != 200 or not isinstance(examCfg.get("data"), dict):
    print("无法进入考试：", examCfg.get("message"))
    print("提示：如果提示未完成课程，请重新运行本脚本把课程刷完。")
    utils.end(1)

examId = examCfg["data"]["id"]
createRes = json.loads(session.post(
    "http://wap.xiaoyuananquantong.com/guns-vip-main/wap/test/create",
    data={"examId": examId, "userId": userId}).text)
if createRes.get("code") != 200 or not isinstance(createRes.get("data"), dict):
    print("创建考试失败：", createRes.get("message"))
    utils.end(1)

logId = createRes["data"]["logId"]
token = createRes["data"].get("token")
print("取得logId %s" % logId)

questions = utils.getExamPaper(logId, userId)
print(f"取得考题 {len(questions)} 道，正在按题干匹配答案库...")

examData = [("examId", examId), ("examType", 2), ("sysSource", 20),
            ("logId", logId), ("userId", userId), ("ah", ""), ("token", token)]
missing = 0
for row in questions:
    q = row.get("question") or {}
    qid = str(q.get("id") or row.get("questionId"))
    qt = str(q.get("quesType") or row.get("questType") or "1")
    val = utils.buildAnswerValue(q, qid, qt)
    if val is None:
        missing += 1
        val = ("%s-1" if qt == "3" else "%s-A") % qid
    examData.append(("question", val))
    examData.append(("questionId", qid))
    examData.append(("quesType", qt))

if missing:
    print(f"注意：有 {missing} 道题不在答案库中，本次仅供参考。")

print(f"等待最短答题时长 {EXAM_WAIT_SECONDS} 秒(防作弊校验)...")
time.sleep(EXAM_WAIT_SECONDS)

res = json.loads(session.post("http://wap.xiaoyuananquantong.com/guns-vip-main/wap/imitateTest",
                              data=examData).text)
for _ in range(10):
    if res.get("code") == 1006:
        print(f"[{_}/10] 答题时间过短，等待10秒后重试")
        time.sleep(10)
        res = json.loads(session.post(
            "http://wap.xiaoyuananquantong.com/guns-vip-main/wap/imitateTest",
            data=examData).text)
        continue
    break

if res.get("code") != 200 or not isinstance(res.get("data"), dict):
    print("交卷未成功:", json.dumps(res, ensure_ascii=False)[:300])
    utils.end(1)

score = res["data"]["count"]
print(f'得分：{score}')

if float(score) < 100:
    print("未到 100 分，重跑一次本脚本即可（每次试卷不同，题目会逐步补全）。")
else:
    print(f"前往 http://wap.xiaoyuananquantong.com/guns-vip-main/wap/qrCode?userId={userId} 下载结课证书")

# 下载证书(按 userId 命名,该账号证书已存在则直接复用)
save_dir = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else script_dir
exist_cert = None
for ext in ("jpeg", "png", "jpg", "webp", "gif"):
    p = os.path.join(save_dir, f"certificate_{userId}.{ext}")
    if os.path.exists(p) and os.path.getsize(p) > 0:
        exist_cert = p
        break
if exist_cert:
    print(f"该账号证书已存在，直接使用：{os.path.abspath(exist_cert)}")
else:
    print("正在下载证书...")
    try:
        cer = session.get(f"http://wap.xiaoyuananquantong.com/guns-vip-main/wap/qrCode?userId={userId}")
        r = _re.search(r'data:image/(\w+);base64,([A-Za-z0-9+/=]+)', cer.text)
        if r:
            cert_path = os.path.join(save_dir, f"certificate_{userId}.{r.group(1)}")
            with open(cert_path, "wb") as f:
                f.write(base64.b64decode(r.group(2)))
            print(f"证书图片已下载到本地：{os.path.abspath(cert_path)}")
        else:
            print("证书下载失败，请自行前往：首页->电子学档 查看或下载证书")
    except Exception as e:
        print("证书下载失败：", e)

print("正在解绑openId并退出登录...")
try:
    print(utils.UntyingMethod(userId))
except Exception:
    pass

end_time = time.time()
elapsed_ms = (end_time - start_time) * 1000
print(f"execute time: {elapsed_ms:.3f} ms.")
print("脚本作者:南晓 Scwizard b站同名，欢迎前往github支持作者~")
print("感谢 (排名不分先后) ：ECXiaobai | Leeyus | Mr_Zhen_cn | BaJie041012 对本项目的贡献")
print("开源地址：https://github.com/Scwizard/jiangsu-safety-platform-skip")
if STATS:
    try:
        res = utils.upload_stats(score, round(elapsed_ms, 3))
        print("脚本统计已上传，只记录分数和运行时长，不会保存您的IP地址与设备信息，您可以在脚本开头选择是否开启该功能")
        print(res)
    except Exception:
        print("脚本统计未被上传")
input("程序结束，感谢使用!")
