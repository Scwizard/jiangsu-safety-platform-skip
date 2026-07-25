import time
import utils
import requests
import json
import os

# “2026江苏省大学新生安全知识教育”一键完成脚本
# Scwizard/HAM:BA4TLH
# 2025/08/14 (Rebuild at 2026/07/25)

# 主页请求要带有账号id和auth 分别为userid和ah
# 很显然 这个平台的变量名的命名规则并不统一 QwQ

# print("本脚本开源免费，禁止倒卖。") # 卖吧 无所谓了

script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)
print("切换到工作目录：", os.getcwd())
# 修一下目录问题

userId = input("请输入userId：")
start_time = time.time()
# 别问为什么是中文 问就是我想不出来什么奇怪的英文变量名了
题库学习 = {"articleId":"2080135073788600321","title":"题库学习","userId":userId,"ah":"","question":"2080136617019842561-1","quesType":"3"}
入学安全 = {"articleId":"2079132357549375490","title":"入学安全","userId":userId,"ah":"","question":"2079154657984266242-1","quesType":"3"}
国家安全 = {"articleId":"2079133938168643585","title":"国家安全","userId":userId,"ah":"","question":"2079156723934838786-B","quesType":"1"}
财物安全 = {"articleId":"2079139032318623745","title":"财物安全","userId":userId,"ah":"","question":"2079446660177477633-1","quesType":"3"}
心理健康 = {"articleId":"2079140991327027201","title":"心理健康","userId":userId,"ah":"","question":"2079467760328392705-D","quesType":"1"}
消防安全 = {"articleId":"2079142411614830593","title":"消防安全","userId":userId,"ah":"","question":"2079492272201678850-C","quesType":"1"}
人身安全 = {"articleId":"2079143452481699842","title":"人身安全","userId":userId,"ah":"","question":"2079527272678703105-1","quesType":"3"}
交通安全 = {"articleId":"2079144978977669121","title":"交通安全","userId":userId,"ah":"","question":"2079540470853156866-A","quesType":"1"}
禁毒防艾 = {"articleId":"2079146093836255234","title":"禁毒防艾","userId":userId,"ah":"","question":"2079548501443756034-1","quesType":"3"}
应急救护 = {"articleId":"2079146628521934850","title":"应急救护","userId":userId,"ah":"","question":"~2079553855799967746-A~2079553855799967746-B~2079553855799967746-C~2079553855799967746-D","quesType":"2"}
防灾减灾 = {"articleId":"2079147344531570690","title":"防灾减灾","userId":userId,"ah":"","question":"2079558043292418049-D","quesType":"1"}

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
requests.post("http://wap.xiaoyuananquantong.com/guns-vip-main/wap/unitTest", data=禁毒防艾).text
print("正在完成禁毒防艾...")
requests.post("http://wap.xiaoyuananquantong.com/guns-vip-main/wap/unitTest", data=应急救护).text
print("正在完成应急救护...")
requests.post("http://wap.xiaoyuananquantong.com/guns-vip-main/wap/unitTest", data=防灾减灾).text
print("正在完成防灾减灾...")
print("课程完成度查询(完成后)：")
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
print("已完成课程学习")
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
print("脚本作者:南晓 Scwizard b站同名")
input("程序结束，感谢使用!")
