# ”2026江苏省大学新生安全知识教育“一键完成脚本

jiangsu-safety-platform-skip

**🤔 食用指导**

1.安装 Python3 ，并且确保安装了这个额外的库： requests 。

2.程序只有登陆版一个版本，对应仓库内的 main.py ，登陆版需要输入学校名称、账号和密码。

3.针对于平台 2026 年 08 月 28 日的策略进行了略微的调整，采用 session 对全局进行管理，并移除了 userid 版本，回归 main 分支，并将发布版本回退到 v1.0.6 。

⚙ **基本原理**

通过数据包重放的方式完成课程学习，通过将考题对应答案写入 database.db 中来实现答案获取和处理。

✒️ **进阶**

欢迎提交 Issue 来交换您的看法和对脚本的更多建议！

作者：南京晓庄学院 Scwizard

感谢：ECXiaobai | Leeyus | Mr_Zhen_cn (排名不分先后) 对本项目的贡献

👌 **给我捐点**

![donation](https://raw.githubusercontent.com/Scwizard/jiangsu-safety-competition/refs/heads/main/donation.jpg)

📊 **统计数据**

![stats](http://101.133.233.225:81/chart?no-cache=true)
