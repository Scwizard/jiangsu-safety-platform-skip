import json
import sqlite3
import sys
import requests
import os

# 运行目录：PyInstaller 打包后取解压临时目录（_MEIPASS），否则取脚本目录。
# database.db 等资源一律用此绝对路径定位，不再依赖 chdir。
BASE_DIR = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))

def getAllSchools(province, timeout=10):
    """
    获取到学校列表
    """
    raw = requests.get(f"http://wap.xiaoyuananquantong.com/guns-vip-main/wap/select/proCollege?provincesName={province}", timeout=timeout)
    return raw.text

def getFacultyBySchoolId(id):
    """
    通过学校id获取到学院清单 id: int
    """
    raw = requests.post("http://wap.xiaoyuananquantong.com/guns-vip-main/wap/getFaculty",data={"collegeId":id,"notTeacher":10},timeout=10)
    return raw.text

def getUserSchool():
    """
    [+] 2026
    通过让用户提供关键词，获取用户的 collegeId 实现登录
    """
    try:
        schoolList = json.loads(getAllSchools("江苏省", timeout=10))
    except Exception:
        print("错误：网络异常")
        end(1)
    idByName = {_['name']: _['id'] for _ in schoolList['data']}
    while True:
        schoolKey = input("请输入学校名称[关键词也可以]：").strip()
        matches = [name for name in idByName if schoolKey in name]
        if not matches:
            print("未查找到任何学校，请重新输入")
            continue
        if len(matches) > 1:
            print("查找到以下学校：")
            for i, name in enumerate(matches):
                print(f"[{i}] {name}")
            try:
                schoolName = matches[int(input("请输入数字序号来选择学校："))]
            except (ValueError, IndexError):
                print("您的输入有误，请重新输入")
                continue
        else:
            schoolName = matches[0]
        print(f"已获取学校id：{idByName[schoolName]}")
        return idByName[schoolName]


def loginMethod(username, password, collegeId):
    """
    [+] 2026
    重写的登陆函数
    返回样例：
        {
        "code":200,
        "data":{
            "account":"******",
            "area":"",
            "auth":"b12f***********************653ba",
            "avatar":"",
            "birthday":"",
            "classId":"*******************",
            "className":"",
            "collegeId":"*******************",
            "collegeName":"",
            "createTime":"2026-07-28 16:23:26",
            "createUser":"*******************",
            "deptId":"*******************",
            "email":"",
            "facultyId":"*******************",
            "ipAddress":"49.**.***.46",
            "loginNum":3,
            "name":"****",
            "openId":"****************************",
            "password":"",
            "phone":"",
            "roleId":"*******************",
            "salt":"9a5sr",
            "sex":"",
            "status":"ENABLE",
            "sysSource":"20",
            "updateTime":"2026-07-29 09:58:58",
            "updateUser":-100,
            "userId":"*******************",
            "version":""
        },
        "message":"\u8BF7\u6C42\u6210\u529F",
        "success":true
    }
    """
    cookies = {}

    headers = {
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
        'Connection': 'keep-alive',
        'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
        'Origin': 'http://wap.xiaoyuananquantong.com',
        'Referer': 'http://wap.xiaoyuananquantong.com/guns-vip-main/wap/jiangsuwxJsback',
        'User-Agent': 'Mozilla/5.0 (Linux; Android 16; MEIZU 20 Pro Build/BQ2A.251110.001-BP2A.250605.031.A3; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/146.0.7680.178 Mobile Safari/537.36 XWEB/1460249 MMWEBSDK/20260202 MMWEBID/3950 REV/6666666666666666666666666666666666666666 MicroMessenger/8.0.71.3080(0x28004750) WeChat/arm64 Weixin NetType/5G Language/zh_CN ABI/arm64',
        'X-Requested-With': 'XMLHttpRequest',
    }

    data = {
        'openId': '',
        'account': f'{username}',
        'collegeId': f'{collegeId}',
        'password': f'{password}',
    }

    response = requests.post(
        'http://wap.xiaoyuananquantong.com/guns-vip-main/wap/jsUserLogin',
        cookies=cookies,
        headers=headers,
        data=data,
        timeout=10,
    )
    return json.loads(response.text)

def UntyingMethod(userid):
    """
    微信解绑，没有鉴权，真搞不明白他设置那个ah的作用是啥
    """
    cookies = {}

    headers = {
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
        'Connection': 'keep-alive',
        'Referer': 'http://wap.xiaoyuananquantong.com/guns-vip-main/wap/jspersonal',
        'User-Agent': 'Mozilla/5.0 (Linux; Android 16; MEIZU 20 Pro Build/BQ2A.251110.001-BP2A.250605.031.A3; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/146.0.7680.178 Mobile Safari/537.36 XWEB/1460249 MMWEBSDK/20260202 MMWEBID/3950 REV/6666666666666666666666666666666666666666 MicroMessenger/8.0.71.3080(0x28004750) WeChat/arm64 Weixin NetType/5G Language/zh_CN ABI/arm64',
        'X-Requested-With': 'XMLHttpRequest',
    }

    params = {
        'userId': f'{userid}',
    }

    response = requests.get(
        'http://wap.xiaoyuananquantong.com/guns-vip-main/wap/JsUntying',
        params=params,
        cookies=cookies,
        headers=headers,
        timeout=10,
    )
    return json.loads(response.text)


def creatExam(userId):
    # 创建考试方法
    result = requests.post("http://wap.xiaoyuananquantong.com/guns-vip-main/wap/test/create",data={"examId":"1948924196784492546","userId":userId},timeout=10).text
    return json.loads(result)

def getExam(logId,userId):
    # 获取考题
    result = requests.get("http://wap.xiaoyuananquantong.com/guns-vip-main/wap/test/list?logId=%s&page=1&limit=200&ah=&userId=%s" % (logId,userId),timeout=10).text
    return json.loads(result)

_db_conn = None


def _get_conn():
    """复用单个 sqlite 连接（一次运行要查 50 道题）。"""
    global _db_conn
    if _db_conn is None:
        _db_conn = sqlite3.connect(os.path.join(BASE_DIR, "database.db"))
    return _db_conn


def getAnswerById(id):
    # 从数据库获取答案然后组装元组
    cursor = _get_conn().cursor()

    cursor.execute('''
    SELECT questionId, answer, quesType 
    FROM tiku 
    WHERE questionId = ?
    ORDER BY questionId
    ''', (str(id),))
    
    records = cursor.fetchall()
    
    # 没有对应答案
    if not records:
        raise LookupError("题库缺少题目 %s 的答案，请联系脚本作者更新题库" % id)
    print(f"从题库查询题目 {id} 类型 {records[0][2]} -> 答案 {records[0][1]}")
    
    quesType = records[0][2]
    if quesType == "2":
        # 多选
        question = ""
        for i in records:
            question += "~%s-%s" % (i[0],i[1])
    elif quesType == "1":
        # 单选
        question = "%s-%s" % (records[0][0],records[0][1])
    else:
        # 判断
        question = "%s-%s" % (records[0][0],records[0][1])
    # 重建原始字符串
    return ("question",question),("questionId",records[0][0]),("quesType",quesType)
    # 保留了另一种构建完整请求体的方法 ↓↓↓
    # return "&question=%s&questionId=%s&quesTpe=%s"%(question,records[0][0],quesType)

def getExamId(userId):
    res = requests.post("http://wap.xiaoyuananquantong.com/guns-vip-main/wap/test/getTest",data={"examType":2,"examClass":20,"userId":userId,"ah":""},timeout=10)
    jsonData = json.loads(res.text)
    return jsonData

def imitateExam(examId,logId,userId,answers):
    headers = {
        "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
        "Referer" : "http://wap.xiaoyuananquantong.com/guns-vip-main/wap/newStudentssimulate?examId=%s&examType=2&userId=%s&ah"% (examId, userId)
        }
    data = [
        ("examId",examId),
        ("examType",2),
        ("sysSource",20),
        ("logId",logId),
        ("userId",userId),
        ("ah",""),
        ]
    data += answers
    # 构造提交考试请求：examId=1948924196784492546&examType=2&sysSource=20&logId=1956159499542806530&userId=1955967136757313538&ah=
    result = requests.post("http://wap.xiaoyuananquantong.com/guns-vip-main/wap/imitateTest", data=data, headers=headers, timeout=10)
    return result

def end(code: int):
    input()
    exit(code)

def upload_stats(score, execute_time):
    """
    脚本用量统计，我们只保存您的脚本最终得分和运行时长，不会记录浏览器指纹、IP地址、客户端信息等内容
    如果您不想开启此功能，请在 main.py 的开始位置把 STATS = True 改成 STATS = False
    """
    url = "http://101.133.233.225:81/result_update"

    payload = {
        "score": score,
        "runtime_ms": execute_time
    }

    resp = requests.post(url, json=payload, timeout=3)
    return resp.json()
    # Example return: 
    # {'status': 'ok', 'message': '记录成功', 'data': {'count': 1, 'score': 100.0, 'runtime_ms': 2369.517}}
