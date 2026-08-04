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
from tkinter import messagebox, ttk

import engine

APP_TITLE = "2026江苏省大学新生安全知识教育 · 一键完成"
APP_SIZE = "760x600"


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

        self._build_ui()
        self.after(100, self._poll_queue)

    # ---------------- 界面构建 ----------------
    def _build_ui(self):
        main = ttk.Frame(self, padding=10)
        main.pack(fill="both", expand=True)

        title = ttk.Label(main, text=APP_TITLE, font=("Microsoft YaHei UI", 13, "bold"))
        title.pack(anchor="w")

        # 模式选择
        mode_frame = ttk.LabelFrame(main, text="运行方式", padding=8)
        mode_frame.pack(fill="x", pady=(8, 4))
        self.mode_var = tk.StringVar(value="userid")
        ttk.Radiobutton(mode_frame, text="userId 版（复制主页链接中的 userId）",
                        variable=self.mode_var, value="userid",
                        command=self._switch_mode).pack(side="left", padx=(0, 20))
        ttk.Radiobutton(mode_frame, text="登录版（学校 + 账号 + 密码）",
                        variable=self.mode_var, value="login",
                        command=self._switch_mode).pack(side="left")

        # userId 表单
        self.userid_frame = ttk.Frame(main, padding=(8, 4))
        self.userid_frame.pack(fill="x")
        ttk.Label(self.userid_frame, text="userId：").pack(side="left")
        self.userid_var = tk.StringVar()
        userid_entry = ttk.Entry(self.userid_frame, textvariable=self.userid_var, width=40)
        userid_entry.pack(side="left", fill="x", expand=True)
        ttk.Label(self.userid_frame, text="（19 位纯数字，不含其他字符）").pack(side="left", padx=6)

        # 登录表单
        self.login_frame = ttk.Frame(main, padding=(8, 4))

        row1 = ttk.Frame(self.login_frame)
        row1.pack(fill="x", pady=2)
        ttk.Label(row1, text="学校关键词：").pack(side="left")
        self.school_keyword_var = tk.StringVar()
        ttk.Entry(row1, textvariable=self.school_keyword_var, width=22).pack(side="left")
        self.query_btn = ttk.Button(row1, text="查询学校", command=self._query_schools)
        self.query_btn.pack(side="left", padx=6)

        row2 = ttk.Frame(self.login_frame)
        row2.pack(fill="x", pady=2)
        ttk.Label(row2, text="选择学校：").pack(side="left")
        self.school_var = tk.StringVar()
        self.school_combo = ttk.Combobox(row2, textvariable=self.school_var,
                                         state="readonly", width=50)
        self.school_combo.pack(side="left", fill="x", expand=True)

        row3 = ttk.Frame(self.login_frame)
        row3.pack(fill="x", pady=2)
        ttk.Label(row3, text="账号：").pack(side="left")
        self.username_var = tk.StringVar()
        ttk.Entry(row3, textvariable=self.username_var, width=40).pack(side="left")

        row4 = ttk.Frame(self.login_frame)
        row4.pack(fill="x", pady=2)
        ttk.Label(row4, text="密码：").pack(side="left")
        self.password_var = tk.StringVar()
        ttk.Entry(row4, textvariable=self.password_var, width=40, show="*").pack(side="left")

        # 选项
        opt_frame = ttk.Frame(main)
        opt_frame.pack(fill="x", pady=4)
        self.stats_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(opt_frame, text="上报使用统计（仅分数与运行时长，无任何个人信息）",
                        variable=self.stats_var).pack(side="left")

        # 控制按钮
        ctrl = ttk.Frame(main)
        ctrl.pack(fill="x", pady=6)
        self.start_btn = ttk.Button(ctrl, text="开始运行", command=self._start)
        self.start_btn.pack(side="left")
        self.stop_btn = ttk.Button(ctrl, text="停止", command=self._stop, state="disabled")
        self.stop_btn.pack(side="left", padx=6)
        ttk.Button(ctrl, text="清空日志", command=self._clear_log).pack(side="left", padx=6)

        self.status_var = tk.StringVar(value="就绪")
        ttk.Label(ctrl, textvariable=self.status_var, foreground="#666").pack(side="right")

        # 日志区
        log_frame = ttk.LabelFrame(main, text="运行日志", padding=4)
        log_frame.pack(fill="both", expand=True)
        self.log_text = tk.Text(log_frame, height=14, state="disabled", wrap="word")
        self.log_text.pack(side="left", fill="both", expand=True)
        scroll = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        scroll.pack(side="right", fill="y")
        self.log_text.configure(yscrollcommand=scroll.set)
        self.log_text.tag_configure("error", foreground="#c62828")
        self.log_text.tag_configure("ok", foreground="#2e7d32")

        self._switch_mode()

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
            uid = self.userid_var.get().strip()
            try:
                int(uid)
            except (TypeError, ValueError):
                self._append_log("userId 应为纯数字（19 位左右），请检查输入\n", "error")
                return
            func = engine.run_by_userid
            kwargs = {"userId": uid}
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
            import traceback
            self.queue.put(("done", ("error", "%s\n%s" % (e, traceback.format_exc()))))

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
            self._append_log("==== 运行出错 ====\n%s\n" % payload, "error")
            self.status_var.set("出错")
            messagebox.showerror(APP_TITLE, "运行出错：\n%s" % payload)
        self.cancel_event = None


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
