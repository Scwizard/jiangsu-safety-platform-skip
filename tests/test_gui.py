# -*- coding: utf-8 -*-
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class GuiImportTest(unittest.TestCase):
    def test_gui_module_imports(self):
        try:
            import gui  # noqa: F401
        except ImportError as e:
            self.skipTest("tkinter 不可用，跳过: %s" % e)
        self.assertTrue(hasattr(gui, "App"))
        self.assertTrue(hasattr(gui, "main"))


class GuiWindowTest(unittest.TestCase):
    """真实创建/销毁窗口的冒烟测试；无显示环境时跳过。"""

    def setUp(self):
        try:
            import gui
        except ImportError as e:  # tkinter 不可用（无 GUI 环境的 CI）
            self.skipTest("tkinter 不可用，跳过: %s" % e)
        self.gui = gui

    def test_window_construct_and_log_roundtrip(self):
        try:
            app = self.gui.App()
        except Exception as e:  # 无桌面环境（如 CI）
            self.skipTest("无法创建 GUI 窗口: %s" % e)
        try:
            app.update_idletasks()
            # 日志写入与清空
            app._append_log("test message\n", "ok")
            app.update_idletasks()
            content = app.log_text.get("1.0", "end")
            self.assertIn("test message", content)
            app._clear_log()
            self.assertEqual(app.log_text.get("1.0", "end").strip(), "")

            # 学校列表填充
            app._fill_schools([{"id": "1", "name": "测试大学"}, {"id": "2", "name": "示例学院"}])
            self.assertEqual(len(app.school_combo["values"]), 2)
            self.assertTrue(app.school_var.get())

            # 模式切换（用几何管理器状态断言，避免依赖窗口映射时序）
            app.mode_var.set("login")
            app._switch_mode()
            self.assertEqual(app.userid_frame.winfo_manager(), "")
            self.assertEqual(app.login_frame.winfo_manager(), "pack")
            app.mode_var.set("userid")
            app._switch_mode()
            self.assertEqual(app.userid_frame.winfo_manager(), "pack")
            self.assertEqual(app.login_frame.winfo_manager(), "")

            # 非法输入拦截（不启动线程）
            app.userid_var.set("not-a-number")
            app.mode_var.set("userid")
            app._start()
            self.assertFalse(app.running)
            self.assertIn("userId 应为纯数字", app.log_text.get("1.0", "end"))

            # 登录模式：未选择学校时拦截
            app.mode_var.set("login")
            app._switch_mode()
            app.username_var.set("user")
            app.password_var.set("pass")
            app.school_var.set("")
            app._start()
            self.assertFalse(app.running)
            self.assertIn("请先查询并选择学校", app.log_text.get("1.0", "end"))
        finally:
            app.destroy()

    def test_mainloop_smoke(self):
        """完整事件循环冒烟：500ms 后自动关闭窗口。"""
        try:
            app = self.gui.App()
        except Exception as e:
            self.skipTest("无法创建 GUI 窗口: %s" % e)
        app.after(500, app.destroy)
        app.mainloop()  # 正常返回即代表事件循环无异常


if __name__ == "__main__":
    unittest.main()
