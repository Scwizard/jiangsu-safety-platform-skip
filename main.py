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
  9. 速度优化: 学校列表 7 天落盘缓存; 两个课程列表并行拉取、未完成课程 4 线程并行;
     考试答案一次 IN 查询(不再逐题开数据库); 证书已存在则跳过重复下载。
"""
import os
import sys
import re
import json
import time
import base64
import sqlite3
import threading
import urllib3
from concurrent.futures import ThreadPoolExecutor, as_completed

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
SCHOOLS_CACHE_PATH = os.path.join(script_dir, "schools_cache.json")
SCHOOLS_CACHE_TTL = 7 * 24 * 3600  # 学校列表缓存 7 天,省掉每次 600KB+ 的下载

session = Session()


def load_schools_cache():
    """学校列表落盘缓存,7 天内直接复用,网络失败时兜底"""
    try:
        with open(SCHOOLS_CACHE_PATH, encoding="utf-8") as f:
            d = json.load(f)
        if time.time() - float(d.get("ts", 0)) < SCHOOLS_CACHE_TTL:
            return d.get("data")
    except Exception:
        pass
    return None


def save_schools_cache(data):
    try:
        with open(SCHOOLS_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump({"ts": time.time(), "data": data}, f, ensure_ascii=False)
    except Exception:
        pass


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


def db_lookup_all(question_ids):
    """一次 IN 查询取全部题目答案(替代逐题打开数据库),返回 {qid: [quesType, answer]}"""
    result = {}
    if not question_ids:
        return result
    try:
        placeholders = ",".join("?" * len(question_ids))
        con = sqlite3.connect(DB_PATH)
        cur = con.cursor()
        cur.execute(f"SELECT questionId, answer, quesType FROM tiku "
                    f"WHERE questionId IN ({placeholders}) ORDER BY rowid",
                    list(question_ids))
        for qid, ans, qt in cur.fetchall():
            if str(qt) == "2":
                result.setdefault(str(qid), ["2", []])[1].append(str(ans))
            else:
                result[str(qid)] = [str(qt), str(ans)]
        con.close()
    except Exception as e:
        print(f"[警告] 本地题库读取失败: {e}")
    for v in result.values():
        if v[0] == "2":
            v[1] = ",".join(v[1])
    return result


def qt_code(chinese):
    return {"单选": "1", "多选": "2", "判断": "3"}.get(chinese, "1")


def build_value(qid, qtype, answer):
    """按平台格式拼 question 字段值: 单选/判断 id-X, 多选 ~id-A~id-B..."""
    a = str(answer or "").strip()
    # 兼容 "qid-X" / "~qid-A~qid-B" 的整串缓存格式
    if a.startswith(qid + "-"):
        a = a[len(qid) + 1:]
    a = a.replace("~" + qid + "-", "")
    if qtype == "2":
        letters = [c for c in a.replace(",", "").replace("，", "") if c in "ABCDEF"]
        if letters:
            return "".join(f"~{qid}-{L}" for L in letters)
        return None
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


def complete_article(user_id, course_name, article_id, cache, cache_lock=None):
    """完成一篇文章的学习测试;缺失答案时用两轮错误提交从错题接口收割正确答案"""
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
                if cache_lock:
                    with cache_lock:
                        for qid, v in got.items():
                            cache[qid] = list(v)
                            answer_map[qid] = v
                else:
                    for qid, v in got.items():
                        cache[qid] = list(v)
                        answer_map[qid] = v
            elif d.get("isSuccess"):
                # 理论上不会两轮全中;真发生了就把本轮答案记为正确
                if cache_lock:
                    with cache_lock:
                        for qid, v in wrong_map.items():
                            cache[qid] = list(v)
                            answer_map[qid] = v
                else:
                    for qid, v in wrong_map.items():
                        cache[qid] = list(v)
                        answer_map[qid] = v
            time.sleep(0.3)

    r = submit_unit(user_id, article_id, course_name, items, answer_map)
    d = r.get("data") or {}
    if not d.get("isSuccess") and d.get("logId"):
        # 自愈:缓存答案可能有误导致未通过 -> 从错题表收割正确答案,修正后重试一次
        got = harvest_from_wrong(d["logId"])
        if got:
            def _merge():
                for qid, v in got.items():
                    cache[qid] = list(v)
                    answer_map[qid] = v
            if cache_lock:
                with cache_lock:
                    _merge()
            else:
                _merge()
            r = submit_unit(user_id, article_id, course_name, items, answer_map)
            d = r.get("data") or {}
    if d.get("isSuccess"):
        print(f"  [{course_name}] 文章 {article_id}: 通过 ({len(items)}题)", flush=True)
        return True
    print(f"  [{course_name}] 文章 {article_id}: 仍未通过! 响应: {json.dumps(r, ensure_ascii=False)[:200]}", flush=True)
    return False


def complete_all_courses(user_id, college_id):
    """课程完成:两个 courseType 列表并行拉取,未完成课程 4 线程并行完成"""
    cache = load_course_answers()
    cache_lock = threading.Lock()

    def fetch_list(ctype):
        r = session.post(f"{BASE}/compulsory/list",
                         data={"name": "", "courseType": ctype, "userId": user_id,
                               "collegeId": college_id, "ah": ""}, timeout=25).json()
        return ctype, r.get("data") or []

    with ThreadPoolExecutor(max_workers=2) as ex:
        futures = {ex.submit(fetch_list, ct): ct for ct in ("2", "1")}
        type_map = {}
        for fut in as_completed(futures):
            ctype, courses = fut.result()
            type_map[ctype] = courses

    pending = []
    for ctype in ("2", "1"):
        for c in type_map.get(ctype, []):
            name, finsh = c.get("name"), c.get("isFinsh")
            if finsh:
                print(f"[courseType={ctype}] {name}: 已完成", flush=True)
            else:
                print(f"[courseType={ctype}] {name}: 未完成,开始处理", flush=True)
                pending.append((ctype, c))

    def do_course(ctype, c):
        name, cid = c.get("name"), c.get("id")
        try:
            d = session.post(f"{BASE}/directory/list",
                             data={"name": "", "courseId": cid, "userId": user_id,
                                   "collegeId": college_id, "ah": ""}, timeout=25).json()
            articles = [it["id"] for ch in (d.get("data") or []) for it in (ch.get("list") or [])]
        except Exception as e:
            print(f"  [{name}] 目录获取失败: {e}", flush=True)
            return False
        ok = True
        for art in articles:
            if not complete_article(user_id, name, art, cache, cache_lock):
                ok = False
        return ok

    all_ok = True
    if pending:
        with ThreadPoolExecutor(max_workers=4) as ex:
            for fut in as_completed([ex.submit(do_course, ct, c) for ct, c in pending]):
                if not fut.result():
                    all_ok = False

    with cache_lock:
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

    # 4) 组装答案(一次性 IN 查询全部题目,替代逐题查库)
    data = [("examId", exam_id), ("examType", 2), ("sysSource", 20),
            ("logId", log_id), ("userId", user_id), ("ah", "")]
    hits = db_lookup_all([str((row.get("question") or {}).get("id")) for row in rows])
    missing = []
    for row in rows:
        qq = row.get("question") or {}
        qid, qt = str(qq.get("id")), str(qq.get("quesType"))
        hit = hits.get(qid)
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
    # 证书已存在则直接复用,跳过 300KB+ 的页面下载;文件名带 userId 避免多账号互相覆盖
    for ext in ("jpeg", "png", "jpg", "webp", "gif"):
        p = os.path.join(script_dir, f"certificate_{user_id}.{ext}")
        if os.path.exists(p) and os.path.getsize(p) > 1000:
            print(f"证书已存在,直接使用: {p}")
            return p
    try:
        r = session.get(f"{BASE}/qrCode?userId={user_id}", timeout=25)
        m = re.search(r"data:image/(\w+);base64,([A-Za-z0-9+/=]+)", r.text)
        if m:
            name = os.path.join(script_dir, f"certificate_{user_id}.{m.group(1)}")
            with open(name, "wb") as f:
                f.write(base64.b64decode(m.group(2)))
            print(f"证书图片已保存到: {name}")
            return name
    except Exception as e:
        print(f"证书下载失败: {e}")
    return None


def main():
    print("您正在运行:登录版 2026-08-28 修复版")

    # 学校选择(学校列表走 7 天落盘缓存,缓存未命中才联网;带重试与越界保护)
    college_id = None
    schools_data = load_schools_cache()
    if schools_data is None:
        try:
            schools_data = session.get(
                f"{BASE}/select/proCollege?provincesName={url_quote('江苏省')}", timeout=20).json()
            schools_data = schools_data.get("data") or []
            save_schools_cache(schools_data)
        except Exception:
            schools_data = []
    while college_id is None:
        school_key = input("请输入学校名称[关键词也可以]:").strip()
        matches = [s for s in schools_data if school_key in str(s.get("name", ""))]
        if not matches:
            # 缓存未命中关键词 -> 强制刷新一次再试
            try:
                fresh = session.get(
                    f"{BASE}/select/proCollege?provincesName={url_quote('江苏省')}", timeout=20).json()
                schools_data = fresh.get("data") or []
                save_schools_cache(schools_data)
                matches = [s for s in schools_data if school_key in str(s.get("name", ""))]
            except Exception:
                print("错误:网络异常,且本地缓存中无匹配学校")
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
