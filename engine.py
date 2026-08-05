# -*- coding: utf-8 -*-
"""
核心运行逻辑（供 CLI 与 GUI 共用）。

从 main.py / main_login.py 抽取的流程：
  - run_by_userid : userId 版
  - run_by_login  : 登录版（学校 + 账号 + 密码）
与原来两个脚本的差异：
  - 不再使用阻塞式 input() / utils.end()，而是通过 log 回调输出、
    通过 check_cancel 回调支持在步骤之间取消。
"""
import json
import os
import sys
import time

import requests

import utils

# 运行目录：PyInstaller 打包后取解压临时目录（_MEIPASS），否则取脚本目录。
# 保证 database.db 与工作目录始终正确。
_base_dir = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
os.chdir(_base_dir)

# 江苏省新生安全知识教育的固定 collegeId（见 main.py）
COLLEGE_ID = "1224316234189443073"

# 题库模板，与 main.py / main_login.py 保持一致
TIKU_TEMPLATES = [
    {"articleId": "2080135073788600321", "title": "题库学习",  "question": "2080136617019842561-1",   "quesType": "3"},
    {"articleId": "2079132357549375490", "title": "入学安全",  "question": "2079154657984266242-1",   "quesType": "3"},
    {"articleId": "2079133938168643585", "title": "国家安全",  "question": "2079156723934838786-B",   "quesType": "1"},
    {"articleId": "2079139032318623745", "title": "财物安全",  "question": "2079446660177477633-1",   "quesType": "3"},
    {"articleId": "2079140991327027201", "title": "心理健康",  "question": "2079467760328392705-D",   "quesType": "1"},
    {"articleId": "2079142411614830593", "title": "消防安全",  "question": "2079492272201678850-C",   "quesType": "1"},
    {"articleId": "2079143452481699842", "title": "人身安全",  "question": "2079527272678703105-1",   "quesType": "3"},
    {"articleId": "2079144978977669121", "title": "交通安全",  "question": "2079540470853156866-A",   "quesType": "1"},
    {"articleId": "2079146093836255234", "title": "禁毒防艾",  "question": "2079548501443756034-1",   "quesType": "3"},
    {"articleId": "2079146628521934850", "title": "应急救护",  "question": "~2079553855799967746-A~2079553855799967746-B~2079553855799967746-C~2079553855799967746-D", "quesType": "2"},
    {"articleId": "2079147344531570690", "title": "防灾减灾",  "question": "2079558043292418049-D",   "quesType": "1"},
]


class RunCancelled(Exception):
    """用户主动取消运行。"""


class EngineError(Exception):
    """流程中的可预期错误（登录失败、题库错误等）。"""


def _check(check_cancel):
    if check_cancel is not None:
        check_cancel()


def query_schools(keyword):
    """
    按关键词查询江苏省学校列表。
    返回 [{"id": ..., "name": ...}, ...]，匹配失败返回空列表。
    """
    raw = utils.getAllSchools("江苏省")
    data = json.loads(raw)
    schools = [{"id": s["id"], "name": s["name"]} for s in data["data"]]
    return [s for s in schools if keyword in s["name"]]


def login_and_get_user(school_name_or_id, username, password):
    """
    登录并返回 (userId, loginData)。
    登录失败时抛 EngineError。
    """
    # 兼容直接传 collegeId 或学校名称（名称需要先解析）
    college_id = school_name_or_id
    if not str(college_id).isdigit():
        schools = query_schools(college_id)
        if not schools:
            raise EngineError("未找到匹配的学校，请检查学校名称")
        college_id = schools[0]["id"]
    login_result = utils.loginMethod(username, password, college_id)
    if login_result.get("success") is not True:
        raise EngineError("登录失败，请检查账号、密码和学校是否正确")
    data = login_result["data"]
    return data["userId"], data


def _run_flow(userId, log, check_cancel, stats, untie=False):
    """userId 版 / 登录版共用的主流程。untie=True 时在结束时解绑 openId。"""
    _check(check_cancel)
    start_time = time.time()

    tiku_list = [dict(t, userId=userId, ah="") for t in TIKU_TEMPLATES]
    table = {i: t for i, t in enumerate(tiku_list)}

    log("正在遍历课程列表，查询完成度：")
    res = requests.post(
        "http://wap.xiaoyuananquantong.com/guns-vip-main/wap/compulsory/list",
        data={"userId": userId, "collegeId": COLLEGE_ID},
    ).text
    course = json.loads(res)["data"]
    unfinished = []
    for i, item in enumerate(course):
        status = "已完成" if item["isFinsh"] else "未完成"
        log("第%d课 %s %s" % (i + 1, item["name"], status))
        if not item["isFinsh"]:
            unfinished.append(i)
    _check(check_cancel)

    if unfinished == []:
        log("检测到所有课程已经完成，直接进入考试")
    else:
        for i in unfinished:
            log("正在完成 %s" % table[i]["title"])
            requests.post(
                "http://wap.xiaoyuananquantong.com/guns-vip-main/wap/unitTest",
                data=table[i],
            ).text
            _check(check_cancel)
        log("课程完成度查询（完成后）：")
        res = requests.post(
            "http://wap.xiaoyuananquantong.com/guns-vip-main/wap/compulsory/list",
            data={"userId": userId, "collegeId": COLLEGE_ID},
        ).text
        course = json.loads(res)["data"]
        for i, item in enumerate(course):
            status = "已完成" if item["isFinsh"] else "未完成"
            log("第%d课 %s %s" % (i + 1, item["name"], status))
        log("已完成课程学习")
    _check(check_cancel)

    log("正在进入考试流程...")
    log_id = utils.creatExam(userId)["data"]["logId"]
    log("取得logId %s" % log_id)
    exam_list = utils.getExam(logId=log_id, userId=userId)
    log("取得考题列表，正在从数据库中读取答案然后整合...")
    questions = exam_list["data"]["data"]
    question_list = [questions[i]["questionId"] for i in range(0, 50)]

    data = utils.getExamId(userId)
    if data.get("code") == 500:
        raise EngineError(
            "出错了！你的账号未完成内容学习，可能由以下几点原因导致：\n"
            "1.你所在学校不属于江苏省\n2.脚本题库出错\n3.平台更新\n"
            "程序已自动结束，非常抱歉给您带来不便，您可以联系脚本作者！"
        )
    exam_id = data["data"]["id"]

    answers = ()
    for qid in question_list:
        try:
            answers += utils.getAnswerById(qid)
        except Exception:
            raise EngineError("err: 数据库读写错误")
        _check(check_cancel)
    log("答案已生成，正在执行imitateExam提交答案...")
    res = utils.imitateExam(exam_id, log_id, userId, answers)
    score = json.loads(res.text)["data"]["count"]
    log("得分：%s" % score)
    if int(score) != 100:
        log("没到100分，这是一个历史遗留问题，重刷一次就行了，因为题库录入的时候有一题出错了。")
    else:
        log("前往 http://wap.xiaoyuananquantong.com/guns-vip-main/wap/qrCode?userId=%s 下载结课证书" % userId)

    if untie:
        log("正在解绑openId并退出登录...")
        try:
            log(str(utils.UntyingMethod(userId)))
        except Exception as e:
            log("解绑失败（不影响结果）：%s" % e)

    elapsed_ms = (time.time() - start_time) * 1000
    log("execute time: %.3f ms." % elapsed_ms)
    if stats:
        try:
            utils.upload_stats(score, round(elapsed_ms, 3))
            log("脚本统计执行成功（只记录分数和运行时长）")
        except Exception:
            log("脚本统计未被上传")
    return {"score": score, "elapsed_ms": elapsed_ms}


def run_by_userid(userId, log=print, check_cancel=None, stats=True):
    """
    userId 版入口。userId 为 19 位左右纯数字字符串。
    返回 {"score": ..., "elapsed_ms": ...}。
    """
    try:
        int(userId)
    except (TypeError, ValueError):
        raise EngineError(
            "err: 你输入了错误的user_id，user_id通常是一个19位长的纯数字，请检查输入是否正确。"
        )
    return _run_flow(userId.strip(), log, check_cancel, stats, untie=False)


def _mask_userid(userId):
    """对 userId 打码展示（如 195***456），避免日志截屏泄露个人标识。"""
    s = str(userId)
    if len(s) <= 6:
        return s[:2] + "***" + s[-1:]
    return s[:3] + "***" + s[-3:]


def run_by_login(school_id, username, password, log=print, check_cancel=None, stats=True):
    """
    登录版入口。school_id 为学校 collegeId（数字字符串）。
    返回 {"score": ..., "elapsed_ms": ...}。
    """
    login_result = utils.loginMethod(username.strip(), password, school_id)
    if login_result.get("success") is not True:
        raise EngineError("登录失败，请检查账号密码和学校是否正确")
    userId = login_result["data"]["userId"]
    log("获取到了userId %s，开始执行脚本" % _mask_userid(userId))
    return _run_flow(userId, log, check_cancel, stats, untie=True)
