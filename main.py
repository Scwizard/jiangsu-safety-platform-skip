import os
import time
import utils
import requests
import json
import re

# “2025江苏省大学新生安全知识教育”一键完成脚本
# Scwizard/HAM:BA4TLH
# 2025/08/14

# 主页请求要带有账号id和auth 分别为userid和ah
# 很显然 这个平台的变量名的命名规则并不统一 QwQ

print("本脚本开源免费，禁止倒卖。")

script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)
print("切换到工作目录：", os.getcwd())

userId = input("请输入userId：")
start_time = time.time()

home = requests.get("http://wap.xiaoyuananquantong.com/guns-vip-main/wap/home", params={"userid": userId}).text
pattern = r'<input[^>]*id="collegeId"[^>]*value="([^"]+)"'
match_result = re.search(pattern, home, re.IGNORECASE)
if match_result:
    collegeId = match_result.group(1)
else:
    print("未找到collegeId")
    collegeId = None

compulsory = requests.post("http://wap.xiaoyuananquantong.com/guns-vip-main/wap/compulsory/list", data={"userId": userId, "collegeId": collegeId}).json()
print("课程完成度查询(开始)：")

j = 1
for i in compulsory["data"]:
    if i["isFinsh"]:
        print("第%i课 %s 已完成" % (j, i["name"]))
    else:
        print("第%i课 %s 未完成" % (j, i["name"]))
        directory = requests.post("http://wap.xiaoyuananquantong.com/guns-vip-main/wap/directory/list", data={"courseId": i["id"], "userId": userId, "collegeId": collegeId}).json()
        for k in directory["data"]:
            if not k["isFinsh"]:
                print(f"{k['name']} 未完成")
                for l in k["list"]:
                    print(f"正在完成 {l['course']}...")
                    test = requests.post("http://wap.xiaoyuananquantong.com/guns-vip-main/wap/unitTest", data={"articleId": l["id"], "title": l["course"], "userId": userId, "ah": "", "question": "1677233633049554945-1", "quesType": "3"}).text
    j += 1

print("课程完成度查询(完成)：")
res = requests.post("http://wap.xiaoyuananquantong.com/guns-vip-main/wap/compulsory/list", data={"userId": userId, "collegeId": collegeId}).text
data = json.loads(res)
course = data["data"]
j = 1
for i in course:
    if i["isFinsh"] == True:
        print("第%s课 %s 已完成" % (j, i["name"]))
    else:
        print("第%s课 %s 未完成" % (j, i["name"]))
    j += 1
print("完成课程学习")
print("正在进行考试流程...")
data = utils.getExamId(userId)
examId = data["data"]["id"]
logId = utils.creatExam(examId, userId)["data"]["logId"]
print("取得logId %s" % logId)
examList = utils.getExam(logId=logId, userId=userId)
print("取得考题列表，正在从数据库中读取答案然后整合...")
questions = examList["data"]["data"]
questionList = []
for i in range(0, 50):
    questionList.append(questions[i]["questionId"])
answers = ()
for i in questionList:
    answers += utils.getAnswerById(i)
print("答案已生成，正在执行imitateExam提交答案...")
res = utils.imitateExam(examId, logId, userId, answers)
# 好长一个元组...
print(res.text)
res = json.loads(res.text)
print("得分：%s" % res["data"]["count"])
end_time = time.time()
elapsed_ms = (end_time - start_time) * 1000
print(f"execute time: {elapsed_ms:.3f} ms.")
print("脚本作者:南晓25届新生Scwizard b站同名")
print("程序结束，感谢使用!")
