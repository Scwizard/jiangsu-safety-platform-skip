import time
import utils
import requests
import json
import os

# “2025江苏省大学新生安全知识教育”一键完成脚本
# Scwizard/HAM:BA4TLH
# 2025/08/14

# 主页请求要带有账号id和auth 分别为userid和ah
# 很显然 这个平台的变量名的命名规则并不统一 QwQ

print("本脚本开源免费，禁止倒卖。")

script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)
print("切换到工作目录：", os.getcwd())
# 修一下目录问题

userId = input("请输入userId：")
start_time = time.time()
# 别问为什么是中文 问就是我想不出来什么奇怪的英文变量名了
题库学习 = {"articleId":"1672768716061863938","title":"题库学习","userId":userId,"ah":"","question":"1677233633049554945-1","quesType":"3"}
入学安全 = {"articleId":"1493130725405294593","title":"入学安全","userId":userId,"ah":"","question":"1677226064641896450-A","quesType":"1"}
国家安全 = {"articleId":"1493144962773041153","title":"国家安全","userId":userId,"ah":"","question":"~1677237820399398914-A~1677237820399398914-B~1677237820399398914-C","quesType":"2"}
财物安全 = {"articleId":"1493144438782836737","title":"财物安全","userId":userId,"ah":"","question":"1677246774982586370-0","quesType":"3"}
心理健康 = {"articleId":"1493144798591205378","title":"心理健康","userId":userId,"ah":"","question":"1677248976384012289-A","quesType":"1"}
消防安全 = {"articleId":"1493144639081824257","title":"消防安全","userId":userId,"ah":"","question":"1677231441840287746-1","quesType":"3"}
人身安全 = {"articleId":"1493144727023796226","title":"人身安全","userId":userId,"ah":"","question":"1677234520794968065-1","quesType":"3"}
交通安全 = {"articleId":"1672797851245158401","title":"交通安全","userId":userId,"ah":"","question":"1677236377873395714-C","quesType":"1"}
应急救护 = {"articleId":"1493144873958653953","title":"应急救护","userId":userId,"ah":"","question":"~1810585965882793986-A~1810585965882793986-B~1810585965882793986-C~1810585965882793986-D","quesType":"2"}
防灾减灾 = {"articleId":"1810496679200198657","title":"防灾减灾","userId":userId,"ah":"","question":"1810587849070764033-A","quesType":"1"}


res = requests.post("http://wap.xiaoyuananquantong.com/guns-vip-main/wap/compulsory/list", data={"userId":userId,"collegeId":"1224316234189443073"}).text
data = json.loads(res)
print("课程完成度查询(开始)：")
course = data["data"]
j = 1
for i in course:
    if i["isFinsh"] == True:
        print("第%s课 %s 已完成" % (j, i["name"]))
    else:
        print("第%s课 %s 未完成" % (j, i["name"]))
    j += 1

process = ()
# 保留一个turple 但这个东西不太好搞 且没啥实质影响 就不搞了()
requests.post("http://wap.xiaoyuananquantong.com/guns-vip-main/wap/unitTest", data=题库学习).text
print("正在完成题库学习...")
requests.post("http://wap.xiaoyuananquantong.com/guns-vip-main/wap/unitTest", data=国家安全).text
print("正在完成国家安全...")
requests.post("http://wap.xiaoyuananquantong.com/guns-vip-main/wap/unitTest", data=入学安全).text
print("正在完成入学安全...")
requests.post("http://wap.xiaoyuananquantong.com/guns-vip-main/wap/unitTest", data=财物安全).text
print("正在完成财物安全...")
requests.post("http://wap.xiaoyuananquantong.com/guns-vip-main/wap/unitTest", data=心理健康).text
print("正在完成心理健康...")
requests.post("http://wap.xiaoyuananquantong.com/guns-vip-main/wap/unitTest", data=人身安全).text
print("正在完成人身安全...")
requests.post("http://wap.xiaoyuananquantong.com/guns-vip-main/wap/unitTest", data=消防安全).text
print("正在完成消防安全...")
requests.post("http://wap.xiaoyuananquantong.com/guns-vip-main/wap/unitTest", data=交通安全).text
print("正在完成交通安全...")
requests.post("http://wap.xiaoyuananquantong.com/guns-vip-main/wap/unitTest", data=应急救护).text
print("正在完成应急救护...")
requests.post("http://wap.xiaoyuananquantong.com/guns-vip-main/wap/unitTest", data=防灾减灾).text
print("正在完成防灾减灾...")
print("课程完成度查询(完成)：")
res = requests.post("http://wap.xiaoyuananquantong.com/guns-vip-main/wap/compulsory/list",data={"userId":userId,"collegeId":"1224316234189443073"}).text
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
logId = utils.creatExam(userId)["data"]["logId"]
print("取得logId %s" % logId)
examList = utils.getExam(logId=logId, userId=userId)
print("取得考题列表，正在从数据库中读取答案然后整合...")
questions = examList["data"]["data"]
questionList = []
data = utils.getExamId(userId)
if data["code"] == 500:
    print("""出错了！你的账号未完成内容学习，可能由以下几点原因导致
        1.你所在学校不属于江苏省
        2.脚本题库出错
        3.平台更新""")
    print("程序已自动结束，非常抱歉给您带来不便，您可以联系脚本作者！")
    exit(1)
examId = data["data"]["id"]
for i in range(0,50):
    questionList.append(questions[i]["questionId"])
answers = ()
for i in questionList:
    answers += utils.getAnswerById(i)
print("答案已生成，正在执行imitateExam提交答案...")
res = utils.imitateExam(examId, logId, userId, answers)
print(res.text)
res = json.loads(res.text)
print("得分：%s" % res["data"]["count"])
end_time = time.time()
elapsed_ms = (end_time - start_time) * 1000
print(f"execute time: {elapsed_ms:.3f} ms.")
print("脚本作者:南晓25届新生Scwizard b站同名")
input("程序结束，感谢使用!")
