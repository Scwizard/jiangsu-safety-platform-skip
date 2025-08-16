import json
import sqlite3
import requests

# 刮风这天我试过握着你手
# 但偏偏雨渐渐大到我看你不见
# 还要多久我才能在你身边
# 等到放晴的那天也许我会比较好一点

def getAllSchools():
    """
    获取到学校列表
    """
    raw = requests.get("http://wap.xiaoyuananquantong.com/guns-vip-main/wap/select/proCollege?provincesName=江苏省")
    return raw.text

def getFacultyBySchoolId(id):
    """
    通过学校id获取到学院清单 id: int
    """
    raw = requests.post("http://wap.xiaoyuananquantong.com/guns-vip-main/wap/getFaculty",data={"collegeId":id,"notTeacher":10})
    return raw.text

def getClassById(id):
    """
    通过学院id获取到专业清单 id: int
    """
    raw = requests.post("http://wap.xiaoyuananquantong.com/guns-vip-main/wap/select/class",{"facultyId":id})

def regMethod(name, collegeId, facultyId, classId, account):
    """
    貌似没啥用，给大佬们自己二次开发吧qwq
    注册学生方法 通过传入姓名-name，学校id-collegeId，学院id-facultyId，专业id-classId，账号（考生号14位）-account以实现注册一个账号
    """
    raw = requests.post("http://wap.xiaoyuananquantong.com/guns-vip-main/wap/jsregisterUser", data={"name":name, "password":"", "collegeId":collegeId, "facultyId":facultyId, "classId":classId, "account":account})
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
    # 创建考试方法
    result = requests.post("http://wap.xiaoyuananquantong.com/guns-vip-main/wap/test/create",data={"examId":"1948924196784492546","userId":userId}).text
    return json.loads(result)

def getExam(logId,userId):
    # 获取考题
    result = requests.get("http://wap.xiaoyuananquantong.com/guns-vip-main/wap/test/list?logId=%s&page=1&limit=200&ah=&userId=%s" % (logId,userId)).text
    return json.loads(result)

def getAnswerById(id):
    # 从数据库获取答案然后组装元组
    conn = sqlite3.connect('database.db')
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
        return ""
    
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
    res = requests.post("http://wap.xiaoyuananquantong.com/guns-vip-main/wap/test/getTest",data={"examType":2,"examClass":20,"userId":userId,"ah":""})
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
    result = requests.post("http://wap.xiaoyuananquantong.com/guns-vip-main/wap/imitateTest", data=data, headers=headers)
    return result
