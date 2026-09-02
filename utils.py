import json
import sqlite3
# import requests
from requests import Session
import os

# 刮风这天我试过握着你手
# 但偏偏雨渐渐大到我看你不见
# 还要多久我才能在你身边
# 等到放晴的那天也许我会比较好一点

# no result... 2025.08.29

global session
session = Session()

def getAllSchools(province):
    """
    获取到学校列表
    """
    raw = session.get(f"http://wap.xiaoyuananquantong.com/guns-vip-main/wap/select/proCollege?provincesName={province}")
    return raw.text

def getFacultyBySchoolId(id):
    """
    通过学校id获取到学院清单 id: int
    """
    raw = session.post("http://wap.xiaoyuananquantong.com/guns-vip-main/wap/getFaculty",data={"collegeId":id,"notTeacher":10})
    return raw.text

def getClassById(id):
    """
    通过学院id获取到专业清单 id: int
    """
    raw = session.post("http://wap.xiaoyuananquantong.com/guns-vip-main/wap/select/class",{"facultyId":id})

def regMethod(name, collegeId, facultyId, classId, account):
    """
    貌似没啥用，给大佬们自己二次开发吧qwq
    注册学生方法 通过传入姓名-name，学校id-collegeId，学院id-facultyId，专业id-classId，账号（考生号14位）-account以实现注册一个账号
    """
    raw = session.post("http://wap.xiaoyuananquantong.com/guns-vip-main/wap/jsregisterUser", data={"name":name, "password":"", "collegeId":collegeId, "facultyId":facultyId, "classId":classId, "account":account})
    """
    接口返回示例：
    {
        "code":200,
        "data":{
            "phone":"",
            "auth":"1b7d9a*********************ab20e",
            "success":"\u6CE8\u518C\u6210\u529F",
            "userId":"195**************38"
        },
        "message":"\u8BF7\u6C42\u6210\u529F",
        "success":true
    }
    """

def getUserSchool():
    """
    [+] 2026
    通过让用户提供关键词，获取用户的 collegeId 实现登录
    """
    schoolKey = input("请输入学校名称[关键词也可以]：").strip()
    try:
        schoolList = json.loads(getAllSchools("江苏省"))
    except:
        print("错误：网络异常")
        end(1)
    schoolLs = []
    for _ in schoolList['data']:
        if schoolKey in _['name']:
            schoolLs.append(_['name'])
    if schoolLs == []:
        print("未查找到任何学校，请重新输入")
        getUserSchool()
        return
    else:
        if len(schoolLs) == 1:
            # 精准匹配
            for _ in schoolList['data']:
                if _['name'] == schoolLs[0]:
                    print(f"已获取学校id：{_['id']}")
                    return _['id']
        else:
            # 关键词序号匹配
            print("查找到以下学校：")
            i = 0
            for _ in schoolLs:
                print(f"[{i}] {_}")
                i += 1
            try:
                n = int(input("请输入数字序号来选择学校："))
            except:
                print("您的输入有误，请重新输入")
                getUserSchool()
                return
            schoolName = schoolLs[n]
            for _ in schoolList['data']:
                    if _['name'] == schoolName:
                        print(f"已获取学校id：{_['id']}")
                        return _['id']


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

    response = session.post(
        'http://wap.xiaoyuananquantong.com/guns-vip-main/wap/jsUserLogin',
        cookies=cookies,
        headers=headers,
        data=data,
        verify=False,
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

    response = session.get(
        'http://wap.xiaoyuananquantong.com/guns-vip-main/wap/JsUntying',
        params=params,
        cookies=cookies,
        headers=headers,
        verify=False,
    )
    return json.loads(response.text)


def processData():
    """
    自用函数，现在没啥用了
    处理请求数据 -> 提交答案的请求，将其转为json类型
    """
    with open("sample.txt", 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]
        f.close()
    
    with open("out.txt", "w", encoding="utf-8") as f:
        nowLine = 0
        f.write('{"')
        for i in lines:
            if nowLine % 2 == 0:
                print(nowLine)
                # 判断结果是个整数，来确定奇偶，这是个偶数的话那就是key，奇数就是value
                f.write(i+'":"')
                nowLine += 1
            else:
                print(nowLine)
                f.write(i+'","')
                nowLine += 1
        f.write('"}')
        f.close()
    
def creatExam(userId):
    # 创建考试方法:先取当前有效考试 id(旧考试 id 已过期,会抽到 2025 年题库);create 返回 logId + token(提交凭证)
    exam_id = json.loads(session.post(
        "http://wap.xiaoyuananquantong.com/guns-vip-main/wap/test/getTest",
        data={"examType": 2, "examClass": 20, "userId": userId, "ah": ""}).text)["data"]["id"]
    result = session.post("http://wap.xiaoyuananquantong.com/guns-vip-main/wap/test/create",
                          data={"examId": exam_id, "userId": userId}).text
    return json.loads(result)

def createUnitSession(userId, articleId):
    # 签发token
    try:
        result = session.post("http://wap.xiaoyuananquantong.com/guns-vip-main/wap/unitTest/create",
                              data={"userId": userId, "articleId": articleId}).text
        j = json.loads(result)
    except Exception as e:
        print("创建防作弊会话异常:", e)
        return {"logId": "", "token": ""}
    if j.get("code") == 200 and (j.get("data") or {}).get("token"):
        return {"logId": j["data"]["logId"], "token": j["data"]["token"]}
    # print("创建防作弊会话失败:", j)
    return {"logId": "", "token": ""}

def getExam(logId,userId):
    # 获取考题
    result = session.get("http://wap.xiaoyuananquantong.com/guns-vip-main/wap/test/list?logId=%s&page=1&limit=200&ah=&userId=%s" % (logId,userId)).text
    return json.loads(result)

def getAnswerById(id):
    # print(f"查询 {id}")
    # 从数据库获取答案然后组装元组
    conn = sqlite3.connect(os.path.abspath('database.db')) # 2026 修复路径问题，解决找不到tiku的报错
    cursor = conn.cursor()
    
    cursor.execute(f'''
    SELECT questionId, answer, quesType 
    FROM tiku 
    WHERE questionId is %s
    ORDER BY questionId
    '''% id)
    
    records = cursor.fetchall()
    conn.close()
    
    # 没有对应答案
    if not records:
        print("没找到答案")
        return ""
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
    res = session.post("http://wap.xiaoyuananquantong.com/guns-vip-main/wap/test/getTest",data={"examType":2,"examClass":20,"userId":userId,"ah":""})
    jsonData = json.loads(res.text)
    return jsonData

def imitateExam(examId,logId,userId,answers,token=""):
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
        ("token",token),
        ]
    data += answers
    # 构造提交考试请求：examId=1948924196784492546&examType=2&sysSource=20&logId=1956159499542806530&userId=1955967136757313538&ah= &token=...
    result = session.post("http://wap.xiaoyuananquantong.com/guns-vip-main/wap/imitateTest", data=data, headers=headers)
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

    resp = session.post(url, json=payload, timeout=3)
    return resp.json()
    # Example return: 
    # {'status': 'ok', 'message': '记录成功', 'data': {'count': 1, 'score': 100.0, 'runtime_ms': 2369.517}}
