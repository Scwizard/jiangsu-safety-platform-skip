import time
import utils
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

# “2026江苏省大学新生安全知识教育”一键完成脚本 (登录版)
# Scwizard/HAM:BA4TLH
# 2025/08/14 (Rebuild at 2026/07/25)

# print("本脚本开源免费，禁止倒卖。") # 卖吧 无所谓了

print("本脚本开源免费，如果您付钱得到了这份脚本，恭喜您被骗了。")
STATS = True # 脚本用量统计，我们只保存您的脚本最终得分和运行时长，不会记录浏览器指纹、IP地址、客户端信息等内容
# 如果您不想开启此功能，请把 True 改成 False
WAIT_SECONDS = 7 # 默认开 7，再更新考虑加个传参（但我很懒 另外我科目二今天又挂了呜呜呜  - 26/09/30

EXAM_WAIT_SECONDS = 255 # 考试最短答题时长:2026-09 平台按题量校验,50 题卷需 250 秒

THREADS = 0

VERSION = [1, 1, 4]

script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)
print("切换到工作目录：", os.getcwd())
# 修一下目录问题
# 2026 的时候回来发现还有一些历史遗留问题，需要解决，比如数据库的路径
print("您正在运行：v1.1.4-source")
session = utils.session # 统一采用 Session 管理会话继承 cookies
collegeId = utils.getUserSchool()
username = str(input("请输入账号：").strip())
password = str(input("请输入密码：").strip())

loginResult = utils.loginMethod(username, password, collegeId)
if loginResult['success'] == False:
    print("登录失败，请检查账号密码和学校是否正确")
    print(loginResult)
    utils.end(1)
openId = loginResult['data']['openId']
userId = loginResult['data']['userId']
print(f"获取到了userId {userId}，开始执行脚本")
start_time = time.time() # 计时器，启动！

res = session.post("http://wap.xiaoyuananquantong.com/guns-vip-main/wap/compulsory/list", data={"userId":userId,"collegeId":collegeId}).text
data = json.loads(res)
print("正在遍历课程列表，查询完成度：")
course = data["data"]
j = 1
unfinished = []
for i in course:
    if i["isFinsh"] == True:
        print(f"第{j}课 {i['name']} 已完成")
    else:
        unfinished.append(i)
        print(f"第{j}课 {i['name']} 未完成")
    j += 1

process = ()
# 保留一个turple 但这个东西不太好搞 且没啥实质影响 就不搞了()
if unfinished == []:
    print("检测到所有课程已经完成，直接进入考试")
else:
    def finish_course(c):
        title = c['name']
        articles = utils.getArticles(userId, collegeId, c['id'])
        print(f"[线程] 正在完成 {title}，共 {len(articles)} 篇课件")
        for articleId in articles:
            rnd = 0
            while rnd < 8:
                rnd += 1
                items = utils.getQuestions(articleId)
                if not items:
                    print(f"[线程] {title} 课件 {articleId} 没有题目，跳过")
                    break
                answers, known = utils.buildUnitAnswers(items)
                utils.markArticleViewed(userId, articleId)
                sess = utils.createUnitSession(userId, articleId)
                form = [("articleId", articleId), ("title", title), ("userId", userId), ("ah", ""),
                        ("logId", sess["logId"]), ("token", sess["token"])] + answers
                need = max(WAIT_SECONDS, 5 * len(items) + 5)
                started = time.time()
                print(f"[线程] {title} 课件 {articleId}:本轮 {len(items)} 题（题库命中 {known}），等待 {need} 秒后提交...")
                res = {}
                for _ in range(8):
                    time.sleep(max(0, need - (time.time() - started)))
                    try:
                        res = json.loads(session.post("http://wap.xiaoyuananquantong.com/guns-vip-main/wap/unitTest",
                                                      data=form).text)
                    except Exception as e:
                        print(f"[线程] {title} 提交连接异常: {e}")
                        time.sleep(2)
                        continue
                    if res.get("code") == 1006:
                        need += 20
                        print(f"[线程] {title} 答题时间过短，再加 20 秒重试...")
                        continue
                    if res.get("code") == 1001:
                        sess = utils.createUnitSession(userId, articleId)
                        form = [("articleId", articleId), ("title", title), ("userId", userId), ("ah", ""),
                                ("logId", sess["logId"]), ("token", sess["token"])] + answers
                        started = time.time()
                        print(f"[线程] {title} 缺凭证，重新签发会话...")
                        continue
                    break
                d = res.get("data") if isinstance(res.get("data"), dict) else {}
                if d.get("isSuccess"):
                    print(f"[线程] {title} 课件 {articleId} 提交完成（{len(items)} 题）")
                    break
                n = utils.saveWrongAnswers(d.get("logId"))
                if not n:
                    print(f"[线程] {title} 课件 {articleId} 第{rnd}轮未通过,且没拿到错题: {json.dumps(res, ensure_ascii=False)[:160]}")
                    break
                print(f"[线程] {title} 课件 {articleId} 第{rnd}轮未过（命中 {known}/{len(items)}），已补 {n} 条进题库，重试...")
            else:
                print(f"[线程] {title} 课件 {articleId} 8 轮仍未通过")
        return c
    with ThreadPoolExecutor(max_workers=THREADS or len(unfinished)) as executor:
        futures = {executor.submit(finish_course, c): c for c in unfinished}
        for future in as_completed(futures):
            c = futures[future]
            try:
                future.result()
            except Exception as e:
                print(f"[线程] {c['name']} 完成时出错: {e}")

    print("课程完成度查询(完成后)：")
    res = session.post("http://wap.xiaoyuananquantong.com/guns-vip-main/wap/compulsory/list",data={"userId":userId,"collegeId":collegeId}).text
    data = json.loads(res)
    course = data["data"]
    j = 1
    for i in course:
        if i["isFinsh"] == True:
            print("第%s课 %s 已完成" % (j, i["name"]))
        else:
            print("第%s课 %s 未完成" % (j, i["name"]))
        j += 1
    print("已完成课程学习")
print("正在进入考试流程...")
# print()
try:
    res = utils.creatExam(userId)
except:
    print("脚本运行异常，如果没有完成课程学习，请前往github下载新版...")
    utils.end()
logId = res["data"]["logId"]
token = res["data"]["token"]  # 新增:提交凭证(防作弊),create 响应里带
print("取得logId %s" % logId)
try:
    examList = utils.getExam(logId=logId, userId=userId)
except:
    print("脚本运行异常，如果没有完成课程学习，请前往github下载新版...")
    utils.end()
print("取得考题列表，正在从数据库中读取答案然后整合...")
# print(examList)
questions = examList["data"]["data"]
questionList = []
data = utils.getExamId(userId)
if data["code"] == 500:
    print("""出错了！你的账号未完成内容学习，可能由以下几点原因导致
        1.你所在学校不属于江苏省
        2.脚本题库出错
        3.平台更新""")
    print("程序已自动结束，非常抱歉给您带来不便，您可以联系脚本作者！")
    utils.end(1)
examId = data["data"]["id"]
# 考试题目 id 每次组卷随机，按题目文本从 database.db 查答案
answers = ()
miss = 0
for it in questions:
    q = it["question"]
    qid = str(q.get("id") or q.get("questionId"))
    qt = utils.typeCode(q.get("quesType"))
    found = utils.getAnswerByQuestion(q.get("question"))  # 正确选项文本列表
    if not found:
        miss += 1
        print(f"[无答案] {str(q.get('question'))[:40]}")
        found = ["1"] if qt == "3" else []
    if qt == "3":
        val = f"{qid}-{found[0]}"
    else:
        # 按选项文本匹配字母（应对考试选项随机）
        letters = []
        for L in "ABCDEF":
            opt = utils.normText(q.get("option" + L) or "")
            if opt and opt in found:
                letters.append(L)
        if qt == "2":
            val = "".join(f"~{qid}-{x}" for x in letters) or f"~{qid}-A"
        else:
            letter = letters[0] if letters else "A"
            val = f"{qid}-{letter}"
    answers += (("question", val), ("questionId", qid), ("quesType", qt))
print(f"答案已生成（缺失 {miss} 题），正在执行imitateExam提交答案...")
# 平台新增防作弊:token 里带开答时间，不足 = 1006
print(f"等待最短答题时长 {EXAM_WAIT_SECONDS} 秒(防作弊校验)...")
time.sleep(EXAM_WAIT_SECONDS)
res = utils.imitateExam(examId, logId, userId, answers, token)
res = json.loads(res.text)
total_try = 10
for _ in range(total_try):
    if res.get("code") == 1006:  # 答题时间过短
        print(f"[{_}/{total_try}] 等待10秒，若右侧次数满了但不成功请前往github下载新版")
        time.sleep(10)
        res = json.loads(utils.imitateExam(examId, logId, userId, answers, token).text)
        continue
    break
if not isinstance(res.get("data"), dict):
    print("交卷未成功:", json.dumps(res, ensure_ascii=False)[:300])
    utils.end(1)
score = res["data"]["count"]
print(f'得分：{score}')
if int(score) != 100:
    n = utils.saveWrongAnswers(res["data"].get("logId"))
    print("没到100分，这是一个历史遗留问题，重刷一次就行了，因为题库录入的时候有一题出错了。")
    if n:
        print(f"已自动把本次 {n} 条错题答案补进 database.db，直接重跑脚本即可拿满分。")
else:
    print(f"前往 http://wap.xiaoyuananquantong.com/guns-vip-main/wap/qrCode?userId={userId} 下载结课证书")
    # 下载证书(按 userId 命名,多账号互不覆盖;该账号证书已存在则直接复用)
    import base64, re as _re, sys
    save_dir = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else script_dir
    # 修了打包版本下载 frozen 路径
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
        cer = session.get(f"http://wap.xiaoyuananquantong.com/guns-vip-main/wap/qrCode?userId={userId}")
        r = _re.search(r'data:image/(\w+);base64,([A-Za-z0-9+/=]+)', cer.text)
        if r:
            cert_path = os.path.join(save_dir, f"certificate_{userId}.{r.group(1)}")
            with open(cert_path, "wb") as f:
                f.write(base64.b64decode(r.group(2)))
            print(f"证书图片已下载到本地：{os.path.abspath(cert_path)}")
        else:
            print("证书下载失败，请自行前往：首页->电子学档 查看或下载证书")
print("正在解绑openId并退出登录...")
res = utils.UntyingMethod(userId)
print(res)
end_time = time.time()
elapsed_ms = (end_time - start_time) * 1000
print(f"execute time: {elapsed_ms:.3f} ms.")
print("脚本作者:南晓 Scwizard b站同名，欢迎前往github支持作者~")
print("感谢 (排名不分先后) ：ECXiaobai | Leeyus | Mr_Zhen_cn | BaJie041012 | TGap-Ruo 对本项目的贡献")
print("开源地址：https://github.com/Scwizard/jiangsu-safety-platform-skip")
if STATS == True:
    try:
        res = utils.upload_stats(score, round(elapsed_ms, 3))
        print("脚本统计已上传，只记录分数和运行时长，不会保存您的IP地址与设备信息，您可以在脚本开头选择是否开启该功能")
        print(res)
    except:
        print("脚本统计未被上传")
input("程序结束，感谢使用!")
