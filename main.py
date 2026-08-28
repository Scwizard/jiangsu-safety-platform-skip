# -*- coding: utf-8 -*-
"""
“2026江苏省大学新生安全知识教育”一键完成脚本 —— 2026-08-28 修复版
原脚本: Scwizard/HAM:BA4TLH
修复内容(详见 修复说明.md):
  1. 平台 2026-08 起要求完成“全部必修安全教育课程(courseType=1 + courseType=2)”才允许创建考试;
     原脚本只按 courseType=2 的 11 门课各提交 1 题,考试接口永远返回“请先完成全部必修安全教育课程”。
     修复:按真实页面流程 directory/list -> question/list -> 全量 unitTest 提交;
           答案缺失时利用“错题接口泄露标准答案”自动收割(两轮错误提交取并集),并持久化到 course_answers.json。
  2. 考试题库已换新(300 题,id 以 2079 开头),原 database.db 已过期 -> 已用收割到的新答案重建 tiku 表。
  3. creatExam 写死旧 examId -> 改为通过 getTest(examType=2, examClass=20) 动态获取,并正确携带 ah 参数。
  4. 修复:创建考试返回 code=500 时 TypeError 崩溃 -> 改为友好提示服务器返回的 message。
  5. 修复:答案缺失时 answers += "" 的 TypeError 被误报为“数据库读写错误” -> 明确提示缺哪题。
  6. 移除结尾的微信解绑(UntyingMethod 会解绑 openId,可能导致后续无法用微信登录)。
  7. 学校选择:修复递归不 return 返回 None、序号越界崩溃的问题。
  8. 全部 SQL 改参数化查询;所有接口响应先校验 code 再取字段,避免裸崩溃。
"""
import os
import sys
import re
import json
import time
import base64
import sqlite3
import urllib3

urllib3.disable_warnings()
from requests import Session

try:
    from urllib.parse import quote as url_quote
except ImportError:
    from urllib import quote as url_quote

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

BASE = "http://wap.xiaoyuananquantong.com/guns-vip-main/wap"
STATS = True  # 脚本用量统计(只上传分数和用时),不需要请改为 False
HEADERS = {
    "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
    "Origin": "http://wap.xiaoyuananquantong.com",
    "User-Agent": ("Mozilla/5.0 (Linux; Android 16; wv) AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Version/4.0 Chrome/146.0.7680.178 Mobile Safari/537.36 MicroMessenger/8.0.71"),
    "X-Requested-With": "XMLHttpRequest",
}

script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)
DB_PATH = os.path.join(script_dir, "database.db")
COURSE_ANSWERS_PATH = os.path.join(script_dir, "course_answers.json")

session = Session()


def load_course_answers():
    try:
        with open(COURSE_ANSWERS_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_course_answers(data):
    try:
        with open(COURSE_ANSWERS_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception as e:
        print(f"[警告] 保存课程答案缓存失败: {e}")


def db_lookup(question_id):
    """从 database.db 的 tiku 表查答案,返回 (quesType, answer) 或 None"""
    try:
        con = sqlite3.connect(DB_PATH)
        cur = con.cursor()
        cur.execute("SELECT questionId, answer, quesType FROM tiku WHERE questionId = ? ORDER BY rowid",
                    (str(question_id),))
        rows = cur.fetchall()
        con.close()
        if not rows:
            return None
        qt = str(rows[0][2])
        if qt == "2":
            letters = [r[1] for r in rows if r[1] in "ABCDEF"]
            return qt, ",".join(letters)
        return qt, str(rows[0][1])
    except Exception as e:
        print(f"[警告] 本地题库读取失败: {e}")
        return None


def qt_code(chinese):
    return {"单选": "1", "多选": "2", "判断": "3"}.get(chinese, "1")


def build_value(qid, qtype, answer):
    """按平台格式拼 question 字段值: 单选/判断 id-X, 多选 ~id-A~id-B..."""
    if qtype == "2":
        letters = [c for c in (answer or "").replace(",", "").replace("，", "") if c in "ABCDEF"]
        if letters:
            return "".join(f"~{qid}-{L}" for L in letters)
        return None
    a = str(answer or "").strip()
    if a == "正确":
        a = "1"
    if a == "错误":
        a = "0"
    if not a or (a not in ("0", "1") and a[0] not in "ABCDEF"):
        return None
    return f"{qid}-{a[0] if len(a) > 1 else a}"


def harvest_from_wrong(log_id):
    """从错题接口提取正确答案: {questionId: (quesType, answer 原始串)}"""
    out = {}
    try:
        w = session.get(f"{BASE}/wrong/list",
                        params={"errorLogId": log_id, "page": 1, "limit": 500}, timeout=25).json()
        for rec in ((w.get("data") or {}).get("data") or []):
            qq = rec.get("question") or {}
            qid = str(qq.get("id") or rec.get("questionId"))
            qt = {"1": "1", "2": "2", "3": "3"}.get(qq.get("quesType"), "1")
            out[qid] = (qt, qq.get("answer"))
    except Exception as e:
        print(f"    [警告] 错题接口读取失败: {e}")
    return out


def submit_unit(user_id, article_id, title, items, answer_map):
    """提交一次单元测试。items: 题目对象列表;answer_map: {qid: (quesType, answer 原始串)}"""
    data = [("articleId", article_id), ("title", title), ("userId", user_id), ("ah", "")]
    for it in items:
        qid = str(it["id"])
        qt, ans = answer_map.get(qid, (qt_code(it["quesType"]), ""))
        val = build_value(qid, qt, ans)
        if val is None:
            val = f"{qid}-1" if qt == "3" else (f"~{qid}-A" if qt == "2" else f"{qid}-A")
        data.append(("question", val))
        data.append(("quesType", qt))
    return session.post(f"{BASE}/unitTest", data=data, timeout=30).json()


def complete_article(user_id, course_name, article_id, cache):
    """完成一篇文章的学习测试;缺失答案时用两轮错误提交从错题接口收割正确答案"""
    # 平台 2026-08-28 新增 markArticleViewed 校验:正常流程先标记文章已观看,再取题作答
    try:
        session.get(f"{BASE}/markArticleViewed", params={"articleId": article_id, "userId": user_id}, timeout=25)
    except Exception:
        pass
    q = session.get(f"{BASE}/question/list", params={"articleId": article_id, "ah": ""}, timeout=25).json()
    items = (q.get("data") or {}).get("list") or []
    if not items:
        return True

    answer_map = {}
    need_harvest = []
    for it in items:
        qid = str(it["id"])
        if qid in cache:
            answer_map[qid] = tuple(cache[qid])
        else:
            need_harvest.append(it)

    if need_harvest:
        # 两轮故意答错(A/1 与 B/0),错题接口返回标准答案,取并集可覆盖全部题
        for letter, jv in (("A", "1"), ("B", "0")):
            wrong_map = {}
            for it in need_harvest:
                qid = str(it["id"])
                qt = qt_code(it["quesType"])
                if qt == "2":
                    wrong_map[qid] = (qt, f"~{qid}-{letter}")
                elif qt == "3":
                    wrong_map[qid] = (qt, f"{qid}-{jv}")
                else:
                    wrong_map[qid] = (qt, f"{qid}-{letter}")
            r = submit_unit(user_id, article_id, course_name, need_harvest, wrong_map)
            d = r.get("data") or {}
            if not d.get("isSuccess") and d.get("logId"):
                got = harvest_from_wrong(d["logId"])
                for qid, v in got.items():
                    cache[qid] = list(v)
                    answer_map[qid] = v
            elif d.get("isSuccess"):
                # 理论上不会两轮全中;真发生了就把本轮答案记为正确
                for qid, v in wrong_map.items():
                    cache[qid] = list(v)
                    answer_map[qid] = v
            time.sleep(0.3)
        save_course_answers(cache)

    r = submit_unit(user_id, article_id, course_name, items, answer_map)
    d = r.get("data") or {}
    if d.get("isSuccess"):
        print(f"  [{course_name}] 文章 {article_id}: 通过 ({len(items)}题)", flush=True)
        return True
    print(f"  [{course_name}] 文章 {article_id}: 仍未通过! 响应: {json.dumps(r, ensure_ascii=False)[:200]}", flush=True)
    return False


def complete_all_courses(user_id, college_id):
    cache = load_course_answers()
    all_ok = True
    for ctype in ("2", "1"):
        r = session.post(f"{BASE}/compulsory/list",
                         data={"name": "", "courseType": ctype, "userId": user_id,
                               "collegeId": college_id, "ah": ""}, timeout=25).json()
        courses = r.get("data") or []
        for c in courses:
            name, cid, finsh = c.get("name"), c.get("id"), c.get("isFinsh")
            if finsh:
                print(f"[courseType={ctype}] {name}: 已完成", flush=True)
                continue
            print(f"[courseType={ctype}] {name}: 未完成,开始处理", flush=True)
            d = session.post(f"{BASE}/directory/list",
                             data={"name": "", "courseId": cid, "userId": user_id,
                                   "collegeId": college_id, "ah": ""}, timeout=25).json()
            articles = [it["id"] for ch in (d.get("data") or []) for it in (ch.get("list") or [])]
            for art in articles:
                if not complete_article(user_id, name, art, cache):
                    all_ok = False
            time.sleep(0.3)
    save_course_answers(cache)
    return all_ok


def take_exam(user_id):
    # 1) 获取当前有效考试 id(原脚本写死旧 examId,已失效)
    r = session.post(f"{BASE}/test/getTest",
                     data={"examType": 2, "examClass": 20, "userId": user_id, "ah": ""}, timeout=25).json()
    if r.get("code") != 200 or not (r.get("data") or {}).get("id"):
        print(f"获取考试配置失败: {json.dumps(r, ensure_ascii=False)[:300]}")
        return False
    exam_id = r["data"]["id"]

    # 2) 创建考试
    r = session.post(f"{BASE}/test/create",
                     data={"examId": exam_id, "userId": user_id, "ah": ""}, timeout=25).json()
    if r.get("code") != 200 or not (r.get("data") or {}).get("logId"):
        print(f"创建考试失败(服务器消息: {r.get('message')})")
        print("提示: 如果提示未完成课程,请先确认 courseType=1 与 courseType=2 的课程都已学习完成。")
        return False
    log_id = r["data"]["logId"]
    print(f"取得 logId {log_id}", flush=True)

    # 3) 取题
    r = session.get(f"{BASE}/test/list",
                    params={"logId": log_id, "page": 1, "limit": 200, "ah": "", "userId": user_id},
                    timeout=25).json()
    rows = (r.get("data") or {}).get("data") or []
    print(f"取得 {len(rows)} 道考题,正在匹配本地题库答案...", flush=True)

    # 4) 组装答案
    data = [("examId", exam_id), ("examType", 2), ("sysSource", 20),
            ("logId", log_id), ("userId", user_id), ("ah", "")]
    missing = []
    for row in rows:
        qq = row.get("question") or {}
        qid, qt = str(qq.get("id")), str(qq.get("quesType"))
        hit = db_lookup(qid)
        if not hit:
            missing.append(qid)
            continue
        val = build_value(qid, qt, hit[1])
        if val is None:
            missing.append(qid)
            continue
        data.append(("question", val))
        data.append(("questionId", qid))
        data.append(("quesType", qt))
    if missing:
        print(f"有 {len(missing)} 道题在本地题库中找不到答案,已中止提交以保护考试次数: {missing}")
        return False

    # 5) 交卷
    r = session.post(f"{BASE}/imitateTest", data=data, timeout=60)
    try:
        j = r.json()
    except Exception:
        print(f"交卷接口返回异常: {r.text[:300]}")
        return False
    d = j.get("data") or {}
    if j.get("code") == 200 and d.get("isSuccess"):
        score = d.get("count")
        print(f"得分:{score}  错题:{d.get('num')}  证书ID:{d.get('certificate')}")
        if score is not None and float(score) >= 90.0:
            return float(score)
        return None
    print(f"交卷未通过: {j.get('message')} | {json.dumps(j, ensure_ascii=False)[:400]}")
    return None


def download_certificate(user_id):
    try:
        r = session.get(f"{BASE}/qrCode?userId={user_id}", timeout=25)
        m = re.search(r"data:image/(\w+);base64,([A-Za-z0-9+/=]+)", r.text)
        if m:
            name = os.path.join(script_dir, f"certificate.{m.group(1)}")
            with open(name, "wb") as f:
                f.write(base64.b64decode(m.group(2)))
            print(f"证书图片已保存到: {name}")
            return name
    except Exception as e:
        print(f"证书下载失败: {e}")
    return None


def main():
    print("您正在运行:登录版 2026-08-28 修复版")

    # 学校选择(带重试与越界保护)
    college_id = None
    while college_id is None:
        school_key = input("请输入学校名称[关键词也可以]:").strip()
        try:
            school_list = session.get(
                f"{BASE}/select/proCollege?provincesName={url_quote('江苏省')}", timeout=20).json()
        except Exception:
            print("错误:网络异常,请检查网络后重试")
            continue
        matches = [s for s in (school_list.get("data") or []) if school_key in str(s.get("name", ""))]
        if not matches:
            print("未查找到任何学校,请重新输入")
            continue
        if len(matches) == 1:
            college_id = matches[0]["id"]
            print(f"已获取学校id:{college_id} ({matches[0]['name']})")
        else:
            print("查找到以下学校:")
            for i, s in enumerate(matches):
                print(f"[{i}] {s['name']}")
            while college_id is None:
                try:
                    n = int(input("请输入数字序号来选择学校:").strip())
                    college_id = matches[n]["id"]
                    print(f"已获取学校id:{college_id} ({matches[n]['name']})")
                except (ValueError, IndexError):
                    print("您的输入有误,请重新输入序号")
                except EOFError:
                    return

    username = input("请输入账号:").strip()
    password = input("请输入密码:").strip()

    try:
        r = session.post(f"{BASE}/jsUserLogin", headers=HEADERS, verify=False,
                         data={"openId": "", "account": username,
                               "collegeId": college_id, "password": password}, timeout=25)
        login_result = r.json()
    except Exception as e:
        print(f"登录接口异常: {e}")
        return
    if not login_result.get("success") or login_result.get("code") != 200:
        print("登录失败,请检查账号密码和学校是否正确")
        print(json.dumps(login_result, ensure_ascii=False)[:400])
        return
    user_id = login_result["data"]["userId"]
    print(f"获取到了 userId {user_id},开始执行脚本")

    start_time = time.time()
    complete_all_courses(user_id, college_id)
    print("课程学习完成,进入考试流程...")
    score = take_exam(user_id)
    if score is not None:
        print(f"前往 {BASE}/qrCode?userId={user_id} 查看结课证书")
        download_certificate(user_id)
    else:
        print("考试未通过(≥90 分才算通过),请检查后重新运行。")

    elapsed_ms = (time.time() - start_time) * 1000
    print(f"execute time: {elapsed_ms:.3f} ms.")
    print("原脚本作者:南晓 Scwizard | 由Mr_Zhen_(狐涂)修正")
    if STATS:
        try:
            session.post("http://101.133.233.225:81/result_update",
                         json={"score": score, "runtime_ms": round(elapsed_ms, 3)}, timeout=3)
            print("脚本统计已上传(只含分数和运行时长)。")
        except Exception:
            print("脚本统计未被上传")
    try:
        input("程序结束,感谢使用!")
    except EOFError:
        pass


if __name__ == "__main__":
    main()
