import utils
import engine

# "2026江苏省大学新生安全知识教育"一键完成脚本（登录版）
# Scwizard/HAM:BA4TLH
# 2025/08/14 (Rebuild at 2026/07/25)

STATS = True  # 脚本用量统计，我们只保存您的脚本最终得分和运行时长，不会记录浏览器指纹、IP地址、客户端信息等内容
# 如果您不想开启此功能，请把 True 改成 False

print("您正在运行：登录版")
collegeId = utils.getUserSchool()
username = input("请输入账号：").strip()
password = input("请输入密码：").strip()

try:
    result = engine.run_by_login(collegeId, username, password, stats=STATS)
    score = result["score"]
    elapsed_ms = result["elapsed_ms"]
    
    print(f"得分：{score}")
    if int(score) != 100:
        print("没到100分，这是一个历史遗留问题，重刷一次就行了，因为题库录入的时候有一题出错了。")
    else:
        print(f"前往 http://wap.xiaoyuananquantong.com/guns-vip-main/wap/qrCode?userId={result.get('userId', '')} 下载结课证书")
    
    print(f"execute time: {elapsed_ms:.3f} ms.")
    print("脚本作者:南晓 Scwizard b站同名")
except engine.EngineError as e:
    print(f"错误：{e}")
    utils.end(1)

input("程序结束，感谢使用!")