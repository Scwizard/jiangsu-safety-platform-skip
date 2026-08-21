# -*- coding: utf-8 -*-
"""
“2026江苏省大学新生安全知识教育”一键完成脚本 —— GUI 版

支持两种运行方式：
  1. userId 版：粘贴主页链接中的 userId（纯数字）直接运行
  2. 登录版：输入学校关键词 -> 选择学校 -> 输入账号密码登录运行

运行：python gui.py   （仅依赖标准库 tkinter 与 requests）
"""
import queue
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
import json

import batch_processor
import engine
import userid_validator

APP_TITLE = "2026江苏省大学新生安全知识教育 · 一键完成"
APP_SIZE = "760x600"
CONFIG_FILE = "config.json"


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry(APP_SIZE)
        self.minsize(680, 520)

        self.queue = queue.Queue()
        self.cancel_event = None
        self.running = False
        self.school_map = {}  # 显示名 -> {"id":..., "name":...}
        self.batch_processor = batch_processor.BatchProcessor()
        self.batch_tasks = []
        self.batch_running = False

        self._build_ui()
        self.after(100, self._poll_queue)
        
        # 检查是否首次运行，显示教程
        self._check_first_run()

    def _check_first_run(self):
        """检查是否首次运行，如果是则显示教程"""
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    if config.get('has_shown_tutorial', False):
                        return  # 已经显示过教程，不再显示
        except Exception:
            pass  # 配置文件读取失败，继续显示教程
        
        # 首次运行，显示教程
        self.after(500, self._show_tutorial)
        
        # 标记已显示过教程
        try:
            config = {'has_shown_tutorial': True}
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"配置文件保存失败: {e}")

    def _show_tutorial(self):
        """显示使用教程窗口"""
        tutorial = tk.Toplevel(self)
        tutorial.title("使用教程")
        tutorial.geometry("700x550")
        tutorial.resizable(False, False)
        
        # 设置窗口模态
        tutorial.transient(self)
        tutorial.grab_set()
        
        # 主容器
        main_frame = ttk.Frame(tutorial, padding=20)
        main_frame.pack(fill="both", expand=True)
        
        # 标题
        title = ttk.Label(main_frame, text="📚 使用教程", 
                         font=("Microsoft YaHei UI", 16, "bold"))
        title.pack(pady=(0, 15))
        
        # 教程内容
        tutorial_text = """
欢迎使用"2026江苏省大学新生安全知识教育"一键完成脚本！

【两种运行方式】

1️⃣ userId 版（推荐）
   • 复制主页链接中的 userId（19位纯数字）
   • 粘贴到输入框中
   • 点击"开始运行"即可
   
2️⃣ 登录版
   • 输入学校关键词，点击"查询学校"
   • 从下拉列表中选择您的学校
   • 输入账号和密码
   • 点击"开始运行"

【批量处理功能】
   • 切换到"批量处理"标签页
   • 选择 userId 模式或登录模式
   • 系统会自动下载对应 Excel 模板到桌面
   • 按照模板格式填写账号信息
   • 选择填好的 Excel 文件，点击"开始批量处理"

【注意事项】
   • userId 必须是 19 位左右的纯数字
   • 确保网络连接正常
   • 首次运行可能需要几秒钟完成课程学习
   • 得分 100 分即为完成，可前往平台查询证书

【提示】
   • 本脚本完全免费，仅供学习交流使用
   • 如遇问题，请检查输入是否正确
   • 建议先测试单个账号，确认无误后再批量处理
        """
        
        text_widget = tk.Text(main_frame, height=18, width=70, 
                             wrap="word", font=("Microsoft YaHei UI", 10))
        text_widget.pack(fill="both", expand=True)
        text_widget.insert("1.0", tutorial_text)
        text_widget.configure(state="disabled")
        
        # 滚动条
        scrollbar = ttk.Scrollbar(main_frame, command=text_widget.yview)
        scrollbar.pack(side="right", fill="y")
        text_widget.configure(yscrollcommand=scrollbar.set)
        
        # 底部按钮
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x", pady=(15, 0))
        
        ttk.Button(button_frame, text="我知道了", 
                 command=tutorial.destroy, width=15).pack(side="right")
        
        # 提示信息
        tip_label = ttk.Label(button_frame, 
                            text="下次打开程序将不再显示此教程",
                            foreground="#666", font=("Microsoft YaHei UI", 9))
        tip_label.pack(side="left")

    # ---------------- 界面构建 ----------------
    def _build_ui(self):
        main = ttk.Frame(self, padding=10)
        main.pack(fill="both", expand=True)

        title = ttk.Label(main, text=APP_TITLE, font=("Microsoft YaHei UI", 13, "bold"))
        title.pack(anchor="w")

        # 主标签页
        self.notebook = ttk.Notebook(main)
        self.notebook.pack(fill="both", expand=True, pady=(8, 0))

        # 单账号处理标签页
        self.single_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.single_tab, text="单账号处理")

        # 批量处理标签页
        self.batch_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.batch_tab, text="批量处理")

        # 模式选择（仅用于单账号标签页内的模式切换）
        self.mode_var = tk.StringVar(value="userid")
        self.userid_var = tk.StringVar()
        self.school_keyword_var = tk.StringVar()
        self.school_var = tk.StringVar()
        self.username_var = tk.StringVar()
        self.password_var = tk.StringVar()
        self.stats_var = tk.BooleanVar(value=True)
        self.status_var = tk.StringVar(value="就绪")

        # 构建单账号界面
        self._build_single_ui(self.single_tab)

        # 构建批量处理界面
        self._build_batch_ui(self.batch_tab)

        # 底部声明
        decl_frame = ttk.Frame(main)
        decl_frame.pack(fill="x", pady=(4, 0))
        decl_label = ttk.Label(decl_frame, text="项目在github大佬基础上二改，软件完全免费，此版本最终解释权小喵学长所有",
                               foreground="#999", font=("Microsoft YaHei UI", 8))
        decl_label.pack()

    def _build_single_ui(self, parent):
        """构建单账号处理界面"""
        # 模式选择
        mode_frame = ttk.LabelFrame(parent, text="运行方式", padding=8)
        mode_frame.pack(fill="x", pady=(8, 4))
        ttk.Radiobutton(mode_frame, text="userId 版（复制主页链接中的 userId）",
                        variable=self.mode_var, value="userid",
                        command=self._switch_mode).pack(side="left", padx=(0, 20))
        ttk.Radiobutton(mode_frame, text="登录版（学校 + 账号 + 密码）",
                        variable=self.mode_var, value="login",
                        command=self._switch_mode).pack(side="left")

        # userId 表单
        self.userid_frame = ttk.Frame(parent, padding=(8, 4))
        ttk.Label(self.userid_frame, text="userId：").pack(side="left")
        userid_entry = ttk.Entry(self.userid_frame, textvariable=self.userid_var, width=40)
        userid_entry.pack(side="left", fill="x", expand=True)
        ttk.Label(self.userid_frame, text="（19 位纯数字，不含其他字符）").pack(side="left", padx=6)

        # 登录表单
        self.login_frame = ttk.Frame(parent, padding=(8, 4))

        row1 = ttk.Frame(self.login_frame)
        row1.pack(fill="x", pady=2)
        ttk.Label(row1, text="学校关键词：").pack(side="left")
        ttk.Entry(row1, textvariable=self.school_keyword_var, width=22).pack(side="left")
        self.query_btn = ttk.Button(row1, text="查询学校", command=self._query_schools)
        self.query_btn.pack(side="left", padx=6)

        row2 = ttk.Frame(self.login_frame)
        row2.pack(fill="x", pady=2)
        ttk.Label(row2, text="选择学校：").pack(side="left")
        self.school_combo = ttk.Combobox(row2, textvariable=self.school_var,
                                         state="readonly", width=50)
        self.school_combo.pack(side="left", fill="x", expand=True)

        row3 = ttk.Frame(self.login_frame)
        row3.pack(fill="x", pady=2)
        ttk.Label(row3, text="账号：").pack(side="left")
        ttk.Entry(row3, textvariable=self.username_var, width=40).pack(side="left")

        row4 = ttk.Frame(self.login_frame)
        row4.pack(fill="x", pady=2)
        ttk.Label(row4, text="密码：").pack(side="left")
        ttk.Entry(row4, textvariable=self.password_var, width=40, show="*").pack(side="left")

        # 选项
        opt_frame = ttk.Frame(parent)
        opt_frame.pack(fill="x", pady=4)
        ttk.Checkbutton(opt_frame, text="上报使用统计（仅分数与运行时长，无任何个人信息）",
                        variable=self.stats_var).pack(side="left")

        # 控制按钮
        ctrl = ttk.Frame(parent)
        ctrl.pack(fill="x", pady=6)
        self.start_btn = ttk.Button(ctrl, text="开始运行", command=self._start)
        self.start_btn.pack(side="left")
        self.stop_btn = ttk.Button(ctrl, text="停止", command=self._stop, state="disabled")
        self.stop_btn.pack(side="left", padx=6)
        ttk.Button(ctrl, text="清空日志", command=self._clear_log).pack(side="left", padx=6)
        ttk.Label(ctrl, textvariable=self.status_var, foreground="#666").pack(side="right")

        # 日志区
        log_frame = ttk.LabelFrame(parent, text="运行日志", padding=4)
        log_frame.pack(fill="both", expand=True)
        self.log_text = tk.Text(log_frame, height=14, state="disabled", wrap="word")
        self.log_text.pack(side="left", fill="both", expand=True)
        scroll = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        scroll.pack(side="right", fill="y")
        self.log_text.configure(yscrollcommand=scroll.set)
        self.log_text.tag_configure("error", foreground="#c62828")
        self.log_text.tag_configure("ok", foreground="#2e7d32")

        # 初始化模式显示
        self._switch_mode()

    def _build_batch_ui(self, parent):
        """构建批量处理界面"""
        # 模式选择区
        mode_frame = ttk.LabelFrame(parent, text="批量处理模式", padding=8)
        mode_frame.pack(fill="x", pady=(8, 4))
        self.batch_mode_var = tk.StringVar(value="userid")
        ttk.Radiobutton(mode_frame, text="userId 模式",
                        variable=self.batch_mode_var, value="userid",
                        command=self._on_batch_mode_change).pack(side="left", padx=(0, 20))
        ttk.Radiobutton(mode_frame, text="登录模式（学校 + 账号 + 密码）",
                        variable=self.batch_mode_var, value="login",
                        command=self._on_batch_mode_change).pack(side="left")

        # 文件选择区
        file_frame = ttk.LabelFrame(parent, text="Excel 文件", padding=8)
        file_frame.pack(fill="x", pady=(8, 4))

        row1 = ttk.Frame(file_frame)
        row1.pack(fill="x", pady=2)
        self.batch_file_var = tk.StringVar()
        ttk.Entry(row1, textvariable=self.batch_file_var, width=50).pack(side="left", fill="x", expand=True)
        ttk.Button(row1, text="选择文件", command=self._select_excel_file).pack(side="left", padx=6)

        # 信息区
        info_frame = ttk.Frame(file_frame)
        info_frame.pack(fill="x", pady=4)
        self.batch_info_var = tk.StringVar(value="请先选择模式，系统将自动下载对应模板")
        ttk.Label(info_frame, textvariable=self.batch_info_var, foreground="#666").pack(side="left")

        # 控制按钮
        ctrl = ttk.Frame(parent)
        ctrl.pack(fill="x", pady=6)
        self.batch_start_btn = ttk.Button(ctrl, text="开始批量处理", command=self._batch_start)
        self.batch_start_btn.pack(side="left")
        self.batch_stop_btn = ttk.Button(ctrl, text="停止", command=self._batch_stop, state="disabled")
        self.batch_stop_btn.pack(side="left", padx=6)
        ttk.Button(ctrl, text="清空日志", command=self._batch_clear_log).pack(side="left", padx=6)

        self.batch_status_var = tk.StringVar(value="就绪")
        ttk.Label(ctrl, textvariable=self.batch_status_var, foreground="#666").pack(side="right")

        # 进度条
        progress_frame = ttk.Frame(parent)
        progress_frame.pack(fill="x", pady=4)
        self.batch_progress = ttk.Progressbar(progress_frame, mode="determinate")
        self.batch_progress.pack(side="left", fill="x", expand=True)
        self.batch_progress_label = ttk.Label(progress_frame, text="0/0")
        self.batch_progress_label.pack(side="left", padx=6)

        # 批量日志区
        log_frame = ttk.LabelFrame(parent, text="批量处理日志", padding=4)
        log_frame.pack(fill="both", expand=True)
        self.batch_log_text = tk.Text(log_frame, height=14, state="disabled", wrap="word")
        self.batch_log_text.pack(side="left", fill="both", expand=True)
        scroll = ttk.Scrollbar(log_frame, command=self.batch_log_text.yview)
        scroll.pack(side="right", fill="y")
        self.batch_log_text.configure(yscrollcommand=scroll.set)
        self.batch_log_text.tag_configure("error", foreground="#c62828")
        self.batch_log_text.tag_configure("ok", foreground="#2e7d32")

        # 底部声明
        decl_frame = ttk.Frame(parent)
        decl_frame.pack(fill="x", pady=(4, 0))
        decl_label = ttk.Label(decl_frame, text="项目在github大佬基础上二改，软件完全免费，此版本最终解释权小喵学长所有",
                               foreground="#999", font=("Microsoft YaHei UI", 8))
        decl_label.pack()

        # 初始化时自动触发模式选择
        self._on_batch_mode_change()

    # ---------------- 批量处理相关方法 ----------------
    def _on_batch_mode_change(self):
        """模式选择回调，自动下载对应模板"""
        mode = self.batch_mode_var.get()
        self._batch_clear_log()
        self._batch_append_log(f"已选择 {mode} 模式，正在下载对应模板...\n")

        # 获取桌面路径作为默认保存位置
        import os
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")

        if mode == "userid":
            template_name = "userId批量处理模板.xlsx"
            template_path = os.path.join(desktop, template_name)
            try:
                saved_path = self.batch_processor.create_userid_template(template_path)
                self._batch_append_log(f"模板已下载到：{saved_path}\n", "ok")
                self._batch_append_log("请按照模板格式填写 userId 信息后，选择文件导入\n")
                self.batch_info_var.set(f"userId 模式 - 模板已下载到桌面")
            except Exception as e:
                self._batch_append_log(f"模板下载失败：{str(e)}\n", "error")
                self.batch_info_var.set("模板下载失败")

        elif mode == "login":
            template_name = "登录批量处理模板.xlsx"
            template_path = os.path.join(desktop, template_name)
            try:
                saved_path = self.batch_processor.create_login_template(template_path)
                self._batch_append_log(f"模板已下载到：{saved_path}\n", "ok")
                self._batch_append_log("请按照模板格式填写学校、账号、密码信息后，选择文件导入\n")
                self.batch_info_var.set(f"登录模式 - 模板已下载到桌面")
            except Exception as e:
                self._batch_append_log(f"模板下载失败：{str(e)}\n", "error")
                self.batch_info_var.set("模板下载失败")

    # ---------------- 批量处理相关方法 ----------------
    def _select_excel_file(self):
        """选择 Excel 文件"""
        file_path = filedialog.askopenfilename(
            title="选择 Excel 文件",
            filetypes=[("Excel 文件", "*.xlsx *.xls"), ("所有文件", "*.*")]
        )
        if file_path:
            self.batch_file_var.set(file_path)
            self._parse_excel_file(file_path)

    def _parse_excel_file(self, file_path):
        """解析 Excel 文件"""
        mode = self.batch_mode_var.get()
        self._batch_append_log(f"正在解析 Excel 文件（{mode} 模式）...\n")
        tasks, error = self.batch_processor.parse_excel_by_mode(mode, file_path)

        if error:
            self._batch_append_log(error + "\n", "error")
            self.batch_info_var.set("解析失败")
            self.batch_tasks = []
        else:
            self.batch_tasks = tasks
            self._batch_append_log(f"解析成功，共 {len(tasks)} 个任务\n", "ok")
            self.batch_info_var.set(f"待处理：{len(tasks)} 个账号")
            self.batch_progress["maximum"] = len(tasks)
            self.batch_progress["value"] = 0
            self.batch_progress_label.config(text=f"0/{len(tasks)}")

    def _batch_start(self):
        """开始批量处理"""
        if not self.batch_tasks:
            self._batch_append_log("请先选择并解析 Excel 文件\n", "error")
            return

        if self.batch_running:
            return

        self._batch_clear_log()
        self._batch_append_log(f"开始批量处理，共 {len(self.batch_tasks)} 个任务\n")
        self.batch_running = True
        self.batch_start_btn.config(state="disabled")
        self.batch_stop_btn.config(state="normal")
        self.batch_status_var.set("运行中…")
        self.batch_processor.reset_cancel()

        # 启动工作线程
        threading.Thread(target=self._batch_worker, daemon=True).start()

    def _batch_worker(self):
        """批量处理工作线程"""
        result = self.batch_processor.run_batch(
            self.batch_tasks,
            progress_callback=self._batch_progress_callback,
            result_callback=self._batch_result_callback
        )
        self.queue.put(("batch_done", result))

    def _batch_progress_callback(self, current, total, message):
        """进度回调"""
        self.queue.put(("batch_progress", (current, total, message)))

    def _batch_result_callback(self, task_result):
        """单个任务结果回调"""
        self.queue.put(("batch_result", task_result))

    def _batch_stop(self):
        """停止批量处理"""
        if self.batch_running:
            self.batch_processor.cancel()
            self._batch_append_log("[提示] 已请求停止，将在当前任务结束后退出...\n")

    def _batch_clear_log(self):
        """清空批量日志"""
        self.batch_log_text.configure(state="normal")
        self.batch_log_text.delete("1.0", "end")
        self.batch_log_text.configure(state="disabled")

    def _batch_append_log(self, text, tag=None):
        """追加批量日志"""
        ts = time.strftime("%H:%M:%S")
        self.batch_log_text.configure(state="normal")
        self.batch_log_text.insert("end", "[%s] %s" % (ts, text), tag)
        self.batch_log_text.see("end")
        self.batch_log_text.configure(state="disabled")

    def _on_batch_progress(self, data):
        """处理进度更新"""
        current, total, message = data
        self.batch_progress["value"] = current
        self.batch_progress_label.config(text=f"{current}/{total}")
        self._batch_append_log(message + "\n")

    def _on_batch_result(self, task_result):
        """处理单个任务结果"""
        task = task_result.task
        if task_result.success:
            msg = f"✓ {task.account or task.userid}: 成功 (得分: {task_result.score}, 耗时: {task_result.duration:.1f}s)\n"
            self._batch_append_log(msg, "ok")
        else:
            msg = f"✗ {task.account or task.userid}: 失败 ({task_result.error})\n"
            self._batch_append_log(msg, "error")

    def _on_batch_done(self, result):
        """处理批量处理完成"""
        self.batch_running = False
        self.batch_start_btn.config(state="normal")
        self.batch_stop_btn.config(state="disabled")
        self.batch_status_var.set("完成")

        self._batch_append_log("=" * 50 + "\n")
        self._batch_append_log(f"批量处理完成：成功 {result.success_count} 个，失败 {result.fail_count} 个\n")
        if result.success_count == result.total:
            self._batch_append_log("所有账号处理成功！\n", "ok")
        else:
            self._batch_append_log(f"有 {result.fail_count} 个账号处理失败，请查看日志详情\n", "error")

        messagebox.showinfo(
            APP_TITLE,
            f"批量处理完成！\n\n成功：{result.success_count}\n失败：{result.fail_count}\n总计：{result.total}"
        )

    def _switch_mode(self):
        if self.mode_var.get() == "userid":
            self.login_frame.pack_forget()
            self.userid_frame.pack(fill="x")
        else:
            self.userid_frame.pack_forget()
            self.login_frame.pack(fill="x")

    # ---------------- 日志 ----------------
    def _append_log(self, text, tag=None):
        ts = time.strftime("%H:%M:%S")
        self.log_text.configure(state="normal")
        self.log_text.insert("end", "[%s] %s" % (ts, text), tag)
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _clear_log(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

    def _set_running(self, running):
        self.running = running
        self.start_btn.config(state="disabled" if running else "normal")
        self.stop_btn.config(state="normal" if running else "disabled")
        self.status_var.set("运行中…" if running else "就绪")

    # ---------------- 学校查询 ----------------
    def _query_schools(self):
        keyword = self.school_keyword_var.get().strip()
        if not keyword:
            self._append_log("请先输入学校名称关键词\n", "error")
            return
        self.query_btn.config(state="disabled")
        self._append_log("正在查询学校：%s ...\n" % keyword)
        threading.Thread(target=self._query_schools_worker, args=(keyword,), daemon=True).start()

    def _query_schools_worker(self, keyword):
        try:
            schools = engine.query_schools(keyword)
        except Exception as e:
            self.queue.put(("schools_error", str(e)))
            return
        self.queue.put(("schools", schools))

    def _fill_schools(self, schools):
        self.query_btn.config(state="normal")
        if not schools:
            self._append_log("未查找到任何学校，请换一个关键词\n", "error")
            self.school_combo["values"] = ()
            self.school_var.set("")
            return
        self.school_map = {}
        names = []
        for s in schools:
            name = "%s（%s）" % (s["name"], s["id"])
            names.append(name)
            self.school_map[name] = s
        self.school_combo["values"] = names
        if names:
            self.school_combo.current(0)
        self._append_log("查找到 %d 所学校，请在列表中选择\n" % len(schools), "ok")

    # ---------------- 运行控制 ----------------
    def _start(self):
        if self.running:
            return
        mode = self.mode_var.get()
        if mode == "userid":
            uid = self.userid_var.get()
            is_valid, result = userid_validator.validate_and_clean_userid(uid)
            if not is_valid:
                self._append_log(f"{result}\n", "error")
                return
            
            func = engine.run_by_userid
            kwargs = {"userId": result}
        else:
            name = self.school_var.get()
            school = self.school_map.get(name)
            if not school:
                self._append_log("请先查询并选择学校\n", "error")
                return
            username = self.username_var.get().strip()
            password = self.password_var.get()
            if not username or not password:
                self._append_log("请输入账号和密码\n", "error")
                return
            func = engine.run_by_login
            kwargs = {"school_id": school["id"], "username": username, "password": password}

        self._clear_log()
        self._append_log("开始运行（%s 版）...\n" % ("userId" if mode == "userid" else "登录"))
        self._set_running(True)
        self.cancel_event = threading.Event()
        # 主线程读取 Tkinter 变量后再传入工作线程，避免跨线程访问
        stats = self.stats_var.get()
        threading.Thread(target=self._run_worker, args=(func, kwargs, stats), daemon=True).start()

    def _run_worker(self, func, kwargs, stats):
        def log(msg):
            self.queue.put(("log", str(msg) + "\n"))

        def check_cancel():
            if self.cancel_event.is_set():
                raise engine.RunCancelled()

        try:
            result = func(log=log, check_cancel=check_cancel, stats=stats, **kwargs)
            self.queue.put(("done", ("ok", result)))
        except engine.RunCancelled:
            self.queue.put(("done", ("cancelled", None)))
        except engine.EngineError as e:
            self.queue.put(("done", ("error", str(e))))
        except Exception as e:
            # 只展示异常类型与消息，避免向用户泄露内部路径/接口结构
            self.queue.put(("done", ("error", "%s: %s" % (type(e).__name__, e))))

    def _stop(self):
        if self.cancel_event is not None:
            self.cancel_event.set()
            self._append_log("[提示] 已请求停止，将在当前步骤结束后退出...\n")

    # ---------------- 队列轮询（主线程） ----------------
    def _poll_queue(self):
        try:
            while True:
                kind, payload = self.queue.get_nowait()
                if kind == "log":
                    self._append_log(payload)
                elif kind == "schools":
                    self._fill_schools(payload)
                elif kind == "schools_error":
                    self.query_btn.config(state="normal")
                    self._append_log("查询学校失败：%s\n" % payload, "error")
                elif kind == "done":
                    self._on_done(payload)
                elif kind == "batch_progress":
                    self._on_batch_progress(payload)
                elif kind == "batch_result":
                    self._on_batch_result(payload)
                elif kind == "batch_done":
                    self._on_batch_done(payload)
        except queue.Empty:
            pass
        self.after(100, self._poll_queue)

    def _on_done(self, payload):
        state, data = payload
        self._set_running(False)
        if state == "ok":
            score = data.get("score")
            self._append_log("==== 运行完成，得分：%s ====\n" % score, "ok")
            self.status_var.set("完成（得分 %s）" % score)
            if int(score) == 100:
                messagebox.showinfo(APP_TITLE, "恭喜！考试得分 100 分，已全部完成。\n"
                                     "可前往平台主页的结课选项中查询证书。")
        elif state == "cancelled":
            self._append_log("==== 已取消 ====\n", "error")
            self.status_var.set("已取消")
        else:  # error
            self._append_log("==== 运行出错 ====\n%s\n" % data, "error")
            self.status_var.set("出错")
            messagebox.showerror(APP_TITLE, "运行出错：\n%s" % data)
        self.cancel_event = None


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
