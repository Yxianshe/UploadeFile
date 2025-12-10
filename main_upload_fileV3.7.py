import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext, simpledialog
import paramiko
import os
import posixpath
import threading
import json
import datetime
import time
import socket
import stat

# --- 配色方案 ---
COLORS = {
    "bg": "#121212", "card": "#1E1E1E", "input_bg": "#424242",
    "text": "#E0E0E0", "text_dim": "#AAAAAA",
    "accent": "#00E676", "accent_hover": "#00C853",
    "download": "#2979FF", "download_hover": "#2962FF",
    "save": "#FFD600", "save_hover": "#FBC02D",
    "stop": "#FF5252", "stop_hover": "#D32F2F",
    "connect": "#00B0FF", "connect_hover": "#0091EA", 
    "border": "#666666",
    "terminal_bg": "#F5F5F5", "terminal_fg": "#212121",
    "cmd_input_bg": "#FFFFFF", "cmd_input_fg": "#000000",
    "status_ok": "#00E676", "status_err": "#FF5252"
}
FONTS = {
    "main": ("Microsoft YaHei UI", 10), "bold": ("Microsoft YaHei UI", 10, "bold"),
    "code": ("Consolas", 10), "status": ("Microsoft YaHei UI", 12, "bold"), "cmd": ("Consolas", 11)
}
HISTORY_FILE = os.path.join(os.path.expanduser("~"), ".sftp_uploader_history.json")

class ModernButton(tk.Canvas):
    def __init__(self, parent, text, command=None, width=120, height=40, radius=20, bg_color=COLORS["accent"], hover_color=COLORS["accent_hover"], text_color="#000000"):
        super().__init__(parent, width=width, height=height, bg=parent['bg'], highlightthickness=0)
        self.command, self.text, self.radius = command, text, radius
        self.normal_bg, self.hover_bg, self.text_color = bg_color, hover_color, text_color
        self.state = "normal"
        self.rect_id = self._draw_rounded_rect(2, 2, width-2, height-2, radius, self.normal_bg)
        self.text_id = self.create_text(width/2, height/2, text=text, fill=self.text_color, font=FONTS["bold"])
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)
        self.bind("<ButtonRelease-1>", self._on_release)

    def _draw_rounded_rect(self, x1, y1, x2, y2, r, color):
        points = [x1+r, y1, x1+r, y1, x2-r, y1, x2-r, y1, x2, y1, x2, y1+r, x2, y1+r, x2, y2-r, x2, y2-r, x2, y2, x2-r, y2, x2-r, y2, x1+r, y2, x1+r, y2, x1, y2, x1, y2-r, x1, y2-r, x1, y1+r, x1, y1+r, x1, y1]
        return self.create_polygon(points, smooth=True, fill=color)

    def _on_enter(self, e): 
        if self.state == "normal": self.itemconfig(self.rect_id, fill=self.hover_bg)
    def _on_leave(self, e): 
        if self.state == "normal": self.itemconfig(self.rect_id, fill=self.normal_bg)
    def _on_click(self, e): 
        if self.state == "normal": self.move(self.text_id, 1, 1)
    def _on_release(self, e): 
        if self.state == "normal": 
            self.move(self.text_id, -1, -1)
            if self.command: self.command()
            
    def set_state(self, state):
        self.state = state
        if state == "disabled": 
            self.itemconfig(self.rect_id, fill=COLORS["border"])
            self.itemconfig(self.text_id, fill=COLORS["text_dim"])
        else: 
            self.itemconfig(self.rect_id, fill=self.normal_bg)
            self.itemconfig(self.text_id, fill=self.text_color)
            
    def set_text(self, text): self.itemconfig(self.text_id, text=text)
    def set_color(self, bg, hover): 
        self.normal_bg = bg
        self.hover_bg = hover
        if self.state == "normal": self.itemconfig(self.rect_id, fill=bg)

class SFTPUploaderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("SFTP Pro (V39 Split Auth)")
        self.center_window(720, 1200)
        self.root.configure(bg=COLORS["bg"])

        self.use_jump = tk.BooleanVar(value=True)
        self.upload_mode = tk.StringVar(value="folder")
        self.force_overwrite = tk.BooleanVar(value=False)
        
        self.config_name = tk.StringVar()
        self.current_profile_name = tk.StringVar()
        self.cmd_var = tk.StringVar()
        
        self.up_local_path = tk.StringVar()
        self.up_remote_path = tk.StringVar()
        self.down_remote_path = tk.StringVar()
        self.down_local_path = tk.StringVar()
        
        # --- 状态管理 ---
        self.is_running = False
        self.is_connected = False
        self.ssh_client = None     
        self.sftp_client = None    
        self.jump_client = None    
        
        self.current_action = "upload"
        self.jump_inputs = {}
        self.target_inputs = {}
        self.completed_size = 0  
        self.history_records = []
        
        self.start_time = 0
        self.last_update_time = 0
        self.last_size = 0

        self._init_styles()
        self._init_ui()
        
        self.history_records = self._load_history()
        self._update_combo()
        if self.history_records:
            self._apply_history(self.history_records[0])
        
        self.log(f"Config File: {HISTORY_FILE}", "INFO")

    def center_window(self, width, height):
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = int((screen_width / 2) - (width / 2))
        y = int((screen_height / 2) - (height / 2))
        self.root.geometry(f'{width}x{height}+{x}+{y}')

    def _init_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TCombobox", fieldbackground=COLORS["input_bg"], background=COLORS["bg"], foreground="black", selectforeground="black", arrowcolor="white", bordercolor=COLORS["border"])
        style.configure("TNotebook", background=COLORS["bg"], borderwidth=0)
        style.configure("TNotebook.Tab", background=COLORS["card"], foreground=COLORS["text_dim"], padding=[20, 10], font=FONTS["main"], borderwidth=0)
        style.map("TNotebook.Tab", background=[("selected", COLORS["input_bg"])], foreground=[("selected", COLORS["accent"])])
        style.configure("Terminal.Horizontal.TProgressbar", background=COLORS["accent"], troughcolor=COLORS["terminal_bg"], bordercolor=COLORS["terminal_bg"], thickness=5)

    def _init_ui(self):
        main_frame = tk.Frame(self.root, bg=COLORS["bg"], padx=20, pady=20)
        main_frame.pack(fill="both", expand=True)

        # 1. 配置栏
        top_card = self._create_card(main_frame)
        tk.Label(top_card, text="配置管理", bg=COLORS["card"], fg=COLORS["accent"], font=FONTS["bold"]).pack(side="left")
        self.history_combo = ttk.Combobox(top_card, textvariable=self.current_profile_name, state="readonly", font=FONTS["main"])
        self.history_combo.pack(side="left", padx=15, fill="x", expand=True)
        self.history_combo.bind("<<ComboboxSelected>>", self._on_history_select)
        tk.Label(top_card, text="别名:", bg=COLORS["card"], fg=COLORS["text_dim"], font=FONTS["main"]).pack(side="left")
        self._create_flat_entry(top_card, self.config_name, 15).pack(side="left", padx=5)
        self.btn_save = ModernButton(top_card, text="💾 保存配置", width=100, height=30, radius=15, bg_color=COLORS["save"], hover_color=COLORS["save_hover"], text_color="#000000", command=self._manual_save_config)
        self.btn_save.pack(side="right", padx=5)
        self.btn_clear = ModernButton(top_card, text="🗑️ 清空历史", width=100, height=30, radius=15, bg_color=COLORS["stop"], hover_color=COLORS["stop_hover"], text_color="#FFFFFF", command=self._clear_history_handler)
        self.btn_clear.pack(side="right", padx=5)

        # 2. 参数设置
        conn_notebook = ttk.Notebook(main_frame)
        conn_notebook.pack(fill="x", pady=10)
        self.tab_setup = tk.Frame(conn_notebook, bg=COLORS["bg"])
        conn_notebook.add(self.tab_setup, text="连接设置 (Server Config)")

        jump_group = self._create_group(self.tab_setup, "跳板机 (Jump Host)")
        cb_frame = tk.Frame(jump_group, bg=COLORS["card"])
        cb_frame.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 10))
        tk.Checkbutton(cb_frame, text="启用转发", variable=self.use_jump, command=self._toggle_jump, bg=COLORS["card"], fg=COLORS["accent"], selectcolor=COLORS["input_bg"], activebackground=COLORS["card"], activeforeground=COLORS["accent"], font=FONTS["main"]).pack(side="left")
        self._add_input_row(jump_group, 1, "IP地址:", "jump_host", "")
        self._add_input_row(jump_group, 2, "用户名:", "jump_user", "")
        self._add_input_row(jump_group, 3, "密钥Key (可选):", "jump_key", "", is_file=True) 
        self._add_input_row(jump_group, 4, "密码:", "jump_pass", "", is_password=True)
        self.jump_inputs["jump_port"] = tk.Entry(self.root)
        self.jump_inputs["jump_port"].insert(0, "22")

        target_group = self._create_group(self.tab_setup, "目标服务器 (Target)")
        self._add_input_row(target_group, 0, "IP地址:", "target_host", "")
        self._add_input_row(target_group, 1, "用户名:", "target_user", "")
        self._add_input_row(target_group, 2, "密钥Key (选填):", "target_key", os.path.expanduser("~/.ssh/id_rsa"), is_file=True)
        
        # [NEW] 拆分 静态密码 和 PortalPIN
        self._add_input_row(target_group, 3, "密码:", "target_static_pwd", "", is_password=True)
        self._add_input_row(target_group, 4, "PortalPIN (集群):", "target_pass", "", is_password=True)
        
        tk.Label(target_group, text="(普通服务器填密码；集群填PIN；动态码强制弹窗)", bg=COLORS["card"], fg=COLORS["text_dim"], font=("Arial", 8)).grid(row=5, column=1, sticky="w")
        
        self.target_inputs["target_port"] = tk.Entry(self.root)
        self.target_inputs["target_port"].insert(0, "22")

        # 3. 传输操作区
        self.action_notebook = ttk.Notebook(main_frame)
        self.action_notebook.pack(fill="x", pady=10)
        self.action_notebook.bind("<<NotebookTabChanged>>", self._on_action_tab_change)

        self.tab_upload = tk.Frame(self.action_notebook, bg=COLORS["bg"])
        self.action_notebook.add(self.tab_upload, text=" 📤 上传 (Upload) ")
        up_frame = self._create_group(self.tab_upload, "上传配置")
        mode_frame = tk.Frame(up_frame, bg=COLORS["card"])
        mode_frame.grid(row=0, column=1, sticky="w", pady=5)
        tk.Radiobutton(mode_frame, text="上传文件夹", variable=self.upload_mode, value="folder", bg=COLORS["card"], fg=COLORS["text"], selectcolor=COLORS["input_bg"], activebackground=COLORS["card"]).pack(side="left", padx=5)
        tk.Radiobutton(mode_frame, text="上传单文件", variable=self.upload_mode, value="file", bg=COLORS["card"], fg=COLORS["text"], selectcolor=COLORS["input_bg"], activebackground=COLORS["card"]).pack(side="left", padx=5)
        self._add_input_row(up_frame, 1, "本地源路径:", "up_local", "", is_path=True, text_var=self.up_local_path)
        self._add_input_row(up_frame, 2, "远程目标目录:", "up_remote", "", text_var=self.up_remote_path)

        self.tab_download = tk.Frame(self.action_notebook, bg=COLORS["bg"])
        self.action_notebook.add(self.tab_download, text=" 📥 下载 (Download) ")
        down_frame = self._create_group(self.tab_download, "下载配置")
        tk.Label(down_frame, text="提示: 自动识别远程是文件还是文件夹。", bg=COLORS["card"], fg=COLORS["text_dim"]).grid(row=0, column=1, sticky="w")
        self._add_input_row(down_frame, 1, "远程源路径:", "down_remote", "", text_var=self.down_remote_path)
        self._add_input_row(down_frame, 2, "本地保存目录:", "down_local", "", is_path=True, is_folder_only=True, text_var=self.down_local_path)

        # 4. 控制区
        ctrl_frame = tk.Frame(main_frame, bg=COLORS["bg"])
        ctrl_frame.pack(fill="x", pady=5)
        
        self.progress_bar = ttk.Progressbar(ctrl_frame, style="Terminal.Horizontal.TProgressbar", mode="indeterminate")
        self.progress_bar.pack(fill="x", pady=(0, 5))
        
        # [连接状态灯 & 强制覆盖开关]
        status_frame = tk.Frame(ctrl_frame, bg=COLORS["bg"])
        status_frame.pack(pady=(0, 5), fill="x")
        
        left_box = tk.Frame(status_frame, bg=COLORS["bg"])
        left_box.pack(side="left")
        self.status_indicator = tk.Label(left_box, text="●", fg=COLORS["stop"], bg=COLORS["bg"], font=("Arial", 16))
        self.status_indicator.pack(side="left")
        self.status_label = tk.Label(left_box, text="未连接 (Disconnected)", bg=COLORS["bg"], fg=COLORS["text_dim"], font=FONTS["status"])
        self.status_label.pack(side="left", padx=5)
        
        chk_overwrite = tk.Checkbutton(status_frame, text="强制覆盖 (不跳过同名文件)", variable=self.force_overwrite, 
                                     bg=COLORS["bg"], fg=COLORS["text_dim"], 
                                     selectcolor=COLORS["input_bg"], activebackground=COLORS["bg"], 
                                     activeforeground=COLORS["accent"], font=("Microsoft YaHei UI", 9))
        chk_overwrite.pack(side="right", padx=10)

        # [进度标签]
        self.progress_label = tk.Label(ctrl_frame, text="READY", bg=COLORS["bg"], fg=COLORS["text_dim"], font=("Consolas", 10))
        self.progress_label.pack(pady=(0, 10))

        # 按钮区
        btn_box = tk.Frame(ctrl_frame, bg=COLORS["bg"])
        btn_box.pack()

        # 连接/断开按钮
        self.btn_connect = ModernButton(btn_box, text="🔗 连接服务器", width=120, height=45, bg_color=COLORS["connect"], hover_color=COLORS["connect_hover"], text_color="#FFFFFF", command=self.connect_session)
        self.btn_connect.pack(side="left", padx=10)
        
        self.btn_disconnect = ModernButton(btn_box, text="❌ 断开连接", width=120, height=45, bg_color=COLORS["stop"], hover_color=COLORS["stop_hover"], text_color="#FFFFFF", command=self.disconnect_session)
        self.btn_disconnect.pack(side="left", padx=10)
        self.btn_disconnect.set_state("disabled")

        # 分割线
        tk.Frame(btn_box, width=2, height=40, bg=COLORS["border"]).pack(side="left", padx=15)

        # 传输/停止按钮
        self.btn_start = ModernButton(btn_box, text="▶ 开始传输", width=150, height=45, bg_color=COLORS["accent"], hover_color=COLORS["accent_hover"], text_color="#000000", command=self.start_thread)
        self.btn_start.pack(side="left", padx=10)
        
        self.btn_stop = ModernButton(btn_box, text="⏹ 中止任务", width=120, height=45, bg_color=COLORS["stop"], hover_color=COLORS["stop_hover"], text_color="#FFFFFF", command=self.stop_task)
        self.btn_stop.pack(side="left", padx=10)
        self.btn_stop.set_state("disabled")

        # 5. 终端
        term_frame = tk.LabelFrame(main_frame, text="交互式终端 (Interactive Shell)", bg=COLORS["bg"], fg=COLORS["text_dim"], font=FONTS["bold"], padx=2, pady=2, relief="flat")
        term_frame.pack(fill="both", expand=True, pady=(10, 0))
        self.term = scrolledtext.ScrolledText(term_frame, bg=COLORS["terminal_bg"], fg=COLORS["terminal_fg"], height=12, insertbackground="black", font=FONTS["code"], borderwidth=0, padx=10, pady=10)
        self.term.pack(fill="both", expand=True)
        self.term.tag_config("INFO", foreground="#555555")
        self.term.tag_config("SUCCESS", foreground="#2E7D32")
        self.term.tag_config("WARN", foreground="#F9A825")
        self.term.tag_config("ERROR", foreground="#D32F2F")
        self.term.tag_config("CMD", foreground="#1565C0")
        self.term.tag_config("MFA", foreground="#673AB7", font=("Consolas", 10, "bold"))
        self.term.tag_config("INPUT", foreground="#000000", font=("Consolas", 10, "bold"))

        cmd_bar = tk.Frame(term_frame, bg=COLORS["cmd_input_bg"], padx=5, pady=5)
        cmd_bar.pack(fill="x", side="bottom")
        tk.Label(cmd_bar, text=">>", bg=COLORS["cmd_input_bg"], fg=COLORS["accent"], font=FONTS["bold"]).pack(side="left")
        self.cmd_entry = tk.Entry(cmd_bar, textvariable=self.cmd_var, bg=COLORS["cmd_input_bg"], fg=COLORS["cmd_input_fg"], font=FONTS["cmd"], relief="flat", insertbackground="black")
        self.cmd_entry.pack(side="left", fill="x", expand=True, padx=5)
        self.cmd_entry.bind("<Return>", self.run_custom_command)
        tk.Button(cmd_bar, text="发送指令", command=self.run_custom_command, bg=COLORS["accent"], fg="black", font=("Arial", 9, "bold"), bd=0, padx=10).pack(side="right")

        self._toggle_jump()

    # --- UI Helpers ---
    def _create_card(self, parent): 
        f = tk.Frame(parent, bg=COLORS["card"], padx=15, pady=10)
        f.pack(fill="x", pady=5)
        return f
    def _create_group(self, parent, title): 
        f = tk.LabelFrame(parent, text=title, bg=COLORS["card"], fg=COLORS["text"], padx=15, pady=10, relief="flat", font=FONTS["bold"])
        f.pack(fill="x", padx=5, pady=5)
        f.columnconfigure(1, weight=1)
        return f
    def _create_flat_entry(self, parent, var, width=20, show=""): 
        e = tk.Entry(parent, textvariable=var, width=width, show=show, bg=COLORS["input_bg"], fg="white", relief="flat", borderwidth=0, font=FONTS["main"])
        tk.Frame(parent, bg=COLORS["border"], height=1).pack(side="bottom", fill="x")
        return e
    def _add_input_row(self, parent, row, label, key, default, is_file=False, is_path=False, is_folder_only=False, is_password=False, text_var=None):
        tk.Label(parent, text=label, bg=COLORS["card"], fg=COLORS["text_dim"], font=FONTS["main"]).grid(row=row, column=0, sticky="e", padx=5, pady=8)
        container = tk.Frame(parent, bg=COLORS["input_bg"], padx=5, pady=5)
        container.grid(row=row, column=1, sticky="ew", padx=5)
        if text_var: 
            e = tk.Entry(container, textvariable=text_var, show="*" if is_password else "", bg=COLORS["input_bg"], fg="white", relief="flat", borderwidth=0, font=FONTS["main"])
        else:
            e = tk.Entry(container, show="*" if is_password else "", bg=COLORS["input_bg"], fg="white", relief="flat", borderwidth=0, font=FONTS["main"])
            e.insert(0, default)
            if "jump" in key: self.jump_inputs[key] = e
            else: self.target_inputs[key] = e
        e.pack(fill="x")
        if is_file or is_path or is_folder_only: 
            if "jump" in key or "target" in key: 
                tk.Button(parent, text="✖", command=lambda: self._clear_input(key), bg=COLORS["stop"], fg="white", relief="flat", bd=0, font=FONTS["main"], width=2, cursor="hand2").grid(row=row, column=3, padx=2)
            tk.Button(parent, text="📂", command=lambda: self._browse(key, is_path, is_folder_only, text_var), bg=COLORS["input_bg"], fg="white", relief="flat", bd=0, font=FONTS["main"], cursor="hand2").grid(row=row, column=2, padx=5)

    def _clear_input(self, key):
        t = self.jump_inputs[key] if "jump" in key else self.target_inputs[key]
        t.delete(0, tk.END)

    def _on_action_tab_change(self, event):
        tab_id = self.action_notebook.index("current")
        if tab_id == 0:
            self.current_action = "upload"
            self.btn_start.set_text("▶ 开始上传")
            self.btn_start.set_color(COLORS["accent"], COLORS["accent_hover"])
        else:
            self.current_action = "download"
            self.btn_start.set_text("▼ 开始下载")
            self.btn_start.set_color(COLORS["download"], COLORS["download_hover"])

    # --- 逻辑 ---
    def _load_history(self):
        if os.path.exists(HISTORY_FILE):
            try: 
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except: 
                pass
        return []

    def _manual_save_config(self):
        self._save_history()
        messagebox.showinfo("保存", "配置已成功保存！")

    def _save_history(self):
        j = {k: v.get() for k, v in self.jump_inputs.items()}
        t = {k: v.get() for k, v in self.target_inputs.items()}
        label = self.config_name.get().strip() or f"{t['target_user']}@{t['target_host']}"
        data = {
            "label": label, "config_name": self.config_name.get(), "upload_mode": self.upload_mode.get(), "use_jump": self.use_jump.get(), 
            "up_local": self.up_local_path.get(), "up_remote": self.up_remote_path.get(),
            "down_local": self.down_local_path.get(), "down_remote": self.down_remote_path.get(),
            "jump_config": j, "target_config": t
        }
        self.history_records = [r for r in self.history_records if r['label'] != label]
        self.history_records.insert(0, data)
        try: 
            with open(HISTORY_FILE, "w", encoding="utf-8") as f: 
                json.dump(self.history_records[:10], f, indent=4)
            self._update_combo()
            self.history_combo.current(0)
        except: 
            pass

    def _clear_history_handler(self):
        if not self.history_records: return
        if not messagebox.askyesno("确认清空", "⚠️ 确定要清空所有记录吗？"): return
        if os.path.exists(HISTORY_FILE):
            try: os.remove(HISTORY_FILE)
            except: pass
        self.history_records = []
        self._update_combo()
        self.current_profile_name.set("")
        self.config_name.set("")
        self.log("History cleared.", "WARN")

    def _update_combo(self): 
        self.history_combo['values'] = [r['label'] for r in self.history_records]
        if not self.history_records: self.history_combo.set("")

    def _on_history_select(self, e):
        idx = self.history_combo.current()
        if idx >= 0: self._apply_history(self.history_records[idx])

    def _apply_history(self, r):
        self.use_jump.set(r.get("use_jump", True))
        self.up_local_path.set(r.get("up_local", ""))
        self.up_remote_path.set(r.get("up_remote", ""))
        self.down_local_path.set(r.get("down_local", ""))
        self.down_remote_path.set(r.get("down_remote", ""))
        self.upload_mode.set(r.get("upload_mode", "folder"))
        self.config_name.set(r.get("config_name", ""))
        for k, v in r.get("jump_config", {}).items():
            if k in self.jump_inputs: 
                self.jump_inputs[k].delete(0, tk.END)
                self.jump_inputs[k].insert(0, v)
        for k, v in r.get("target_config", {}).items():
            if k in self.target_inputs: 
                self.target_inputs[k].delete(0, tk.END)
                self.target_inputs[k].insert(0, v)
        self._toggle_jump()

    def _browse(self, key, is_path, is_folder_only, text_var):
        path = ""
        if is_folder_only or (is_path and self.upload_mode.get() == "folder"):
            path = filedialog.askdirectory()
        else:
            path = filedialog.askopenfilename()
        if path:
            if text_var: text_var.set(path)
            else:
                t = self.jump_inputs[key] if "jump" in key else self.target_inputs[key]
                t.delete(0, tk.END)
                t.insert(0, path)
    
    def _toggle_jump(self): pass
    def log(self, m, level="INFO"):
        ts = datetime.datetime.now().strftime("[%H:%M:%S] ")
        self.term.insert(tk.END, ts, "INFO")
        self.term.insert(tk.END, m + "\n", level)
        self.term.see(tk.END)

    def _set_connected_ui(self, connected):
        if connected:
            self.status_indicator.config(fg=COLORS["status_ok"])
            self.status_label.config(text="已连接 (Connected)", fg=COLORS["status_ok"])
            self.btn_connect.set_state("disabled")
            self.btn_disconnect.set_state("normal")
            self.is_connected = True
        else:
            self.status_indicator.config(fg=COLORS["stop"])
            self.status_label.config(text="未连接 (Disconnected)", fg=COLORS["stop"])
            self.btn_connect.set_state("normal")
            self.btn_disconnect.set_state("disabled")
            self.is_connected = False

    # --- 🔒 Thread-Safe Helpers ---
    def _thread_safe_askstring(self, title, prompt, is_password=False):
        result = {"value": None}
        event = threading.Event()
        def _ask():
            try:
                show_char = '*' if is_password else None
                val = simpledialog.askstring(title, prompt, parent=self.root, show=show_char)
                result["value"] = val
            finally:
                event.set()
        self.root.after(0, _ask)
        event.wait()
        return result["value"] if result["value"] is not None else ""

    # --- 🔒 MFA Handler (核心分流逻辑) ---
    def mfa_interactive_handler(self, title, instructions, prompt_list):
        self.log(f"--- 🔒 Interactive Auth Required ---", "MFA")
        resp = []
        
        # 获取两个框的内容
        gui_static_pwd = self.target_inputs["target_static_pwd"].get().strip()
        gui_pin = self.target_inputs["target_pass"].get().strip()
        
        for i, (prompt, echo) in enumerate(prompt_list):
            self.log(f"Server asks: {prompt.strip()}", "INFO")
            prompt_lower = prompt.lower()
            
            # 1. 动态码/OTP (最高优先级，必须弹窗)
            is_otp_request = any(x in prompt_lower for x in ["code", "verification", "otp", "microsoft", "动态"])
            
            if is_otp_request:
                user_input = self._thread_safe_askstring(
                    "身份验证 (OTP)", 
                    f"服务器提示: {prompt}\n(请输入)", 
                    is_password=True
                )
                self.log(f">> Sending MANUAL input.", "WARN")
                resp.append(user_input)
                continue

            # 2. 如果服务器明确问 "Password:" 且我们填了静态密码 -> 发送静态密码
            if "password" in prompt_lower and gui_static_pwd and ("pin" not in prompt_lower):
                self.log(f">> Auto-filled Static Password.", "SUCCESS")
                resp.append(gui_static_pwd)
                continue
                
            # 3. 如果服务器问 "PIN" 或者 "PortalPIN" 且我们填了 PIN -> 发送 PIN
            if ("pin" in prompt_lower) and gui_pin:
                self.log(f">> Auto-filled PortalPIN.", "SUCCESS")
                resp.append(gui_pin)
                continue

            # 4. 兜底逻辑：如果无法匹配或者没填，就弹窗
            user_input = self._thread_safe_askstring(
                "需要输入", 
                f"服务器提示: {prompt}\n(请输入)", 
                is_password=(not echo)
            )
            self.log(f">> Sending MANUAL input.", "WARN")
            resp.append(user_input)
            
        return resp

    # --- 连接核心逻辑 ---
    def _try_load_key(self, key_path, password):
        key_classes = []
        if hasattr(paramiko, "RSAKey"): key_classes.append(paramiko.RSAKey)
        if hasattr(paramiko, "Ed25519Key"): key_classes.append(paramiko.Ed25519Key)
        if hasattr(paramiko, "ECDSAKey"): key_classes.append(paramiko.ECDSAKey)
        if hasattr(paramiko, "DSSKey"): key_classes.append(paramiko.DSSKey)
        for k_cls in key_classes:
            try: return k_cls.from_private_key_file(key_path, password=password or None)
            except: continue
        return None

    def _connect_node_generic(self, h, p, u, k, pwd, sock=None):
        if sock:
            transport = paramiko.Transport(sock)
        else:
            sock_raw = socket.create_connection((h, int(p)), timeout=60)
            transport = paramiko.Transport(sock_raw)
        
        transport.start_client(timeout=60)
        k = os.path.expanduser(k)
        auth_success = False

        # 1. 尝试 Key 认证
        if k and os.path.exists(k):
            pkey = self._try_load_key(k, pwd)
            if pkey:
                try: 
                    transport.auth_publickey(u, pkey)
                    auth_success = True
                except: 
                    self.log(f"Key rejected by {h}.", "WARN")
        
        # 2. 尝试 静态密码 认证
        if not auth_success and not transport.is_authenticated() and pwd:
            try: 
                transport.auth_password(u, pwd)
                auth_success = True
            except: 
                pass
        
        # 3. 尝试 交互式认证 (Interactive)
        # 这里会触发 mfa_interactive_handler，里面会根据 Prompt 智能选择填密码还是PIN
        if not transport.is_authenticated():
            try: 
                transport.auth_interactive(u, self.mfa_interactive_handler)
                auth_success = True
            except Exception as e: 
                pass
        
        if not transport.is_authenticated():
            transport.close()
            raise Exception(f"Auth Failed for {h}. Check User/Key/PIN/MFA.")
        
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client._transport = transport 
        return client

    def _get_ssh_connection(self):
        t = {k: v.get() for k, v in self.target_inputs.items()}
        j = {k: v.get() for k, v in self.jump_inputs.items()}
        jc = None
        if self.use_jump.get():
            if not j['jump_host']: raise Exception("Jump Host IP missing")
            self.log(f"Connecting to Jump Host: {j['jump_host']}...", "INFO")
            jc = self._connect_node_generic(j['jump_host'], j['jump_port'], j['jump_user'], j['jump_key'], j['jump_pass'])
            sock = jc.get_transport().open_channel("direct-tcpip", (t['target_host'], int(t['target_port'])), (j['jump_host'], 0))
            self.log("Tunnel established. Connecting to Target...", "INFO")
            # [关键] 这里传入 target_static_pwd 作为默认密码尝试
            tc = self._connect_node_generic(t['target_host'], t['target_port'], t['target_user'], t['target_key'], t.get('target_static_pwd'), sock=sock)
        else:
            if not t['target_host']: raise Exception("Target Host IP missing")
            self.log(f"Direct connection to {t['target_host']}...", "INFO")
            # [关键] 这里传入 target_static_pwd 作为默认密码尝试
            tc = self._connect_node_generic(t['target_host'], t['target_port'], t['target_user'], t['target_key'], t.get('target_static_pwd'))
        return tc, jc

    # --- 持久化连接管理 ---
    def connect_session(self):
        self._save_history()
        self.btn_connect.set_state("disabled")
        self.log(">>> Initiating Connection...", "CMD")
        threading.Thread(target=self._connect_thread, daemon=True).start()

    def _connect_thread(self):
        try:
            self.ssh_client, self.jump_client = self._get_ssh_connection()
            self.sftp_client = self.ssh_client.open_sftp()
            
            # 保持连接活跃
            self.ssh_client.get_transport().set_keepalive(30)
            
            self.log("Connection Established & Ready.", "SUCCESS")
            self.root.after(0, lambda: self._set_connected_ui(True))
        except Exception as e:
            self.log(f"Connection Failed: {e}", "ERROR")
            self.root.after(0, lambda: self._set_connected_ui(False))
            self._close_all_sessions()

    def disconnect_session(self):
        self.log(">>> Disconnecting...", "WARN")
        self._close_all_sessions()
        self._set_connected_ui(False)
        self.log("Session Closed.", "INFO")

    def _close_all_sessions(self):
        try:
            if self.sftp_client: self.sftp_client.close()
        except: pass
        try:
            if self.ssh_client: self.ssh_client.close()
        except: pass
        try:
            if self.jump_client: self.jump_client.close()
        except: pass
        self.sftp_client = None
        self.ssh_client = None
        self.jump_client = None

    # --- 任务执行 ---
    def start_thread(self):
        if self.current_action == "upload" and not self.up_local_path.get(): 
            return messagebox.showerror("Error", "请选择本地源路径")
        if self.current_action == "download" and not self.down_remote_path.get(): 
            return messagebox.showerror("Error", "请填写远程源路径")
        
        # 必须先连接
        if not self.is_connected or not self.sftp_client:
            return messagebox.showerror("Error", "请先点击 [🔗 连接服务器]")
        
        self.is_running = True
        self.btn_start.set_state("disabled")
        self.btn_stop.set_state("normal")
        
        self.progress_bar.config(mode="indeterminate")
        self.progress_bar.start(10)
        
        self.completed_size = 0
        self.start_time = time.time()
        self.last_update_time = self.start_time
        self.last_size = 0
        
        self.log(f">>> Start {self.current_action.upper()}", "CMD")
        threading.Thread(target=self.run_process, daemon=True).start()

    def stop_task(self):
        if self.is_running:
            self.is_running = False
            self.log("Aborting task...", "WARN")
            self.btn_stop.set_state("disabled")

    def run_process(self):
        try:
            try:
                self.sftp_client.listdir('.')
            except:
                raise Exception("连接已断开，请重新点击 [连接服务器]")

            if self.current_action == "upload": 
                self.do_upload(self.sftp_client)
            else: 
                self.do_download(self.sftp_client)
                
            if self.is_running: 
                self.log("TASK COMPLETE.", "SUCCESS")
                messagebox.showinfo("Done", "传输完成")
            else: 
                self.log("Task Aborted.", "WARN")
        except Exception as e: 
            self.log(f"ERROR: {e}", "ERROR")
            if "连接已断开" in str(e) or "Socket" in str(e):
                 self.root.after(0, lambda: self._set_connected_ui(False))
            messagebox.showerror("Error", str(e))
        finally:
            self.is_running = False
            self.root.after(0, self.progress_bar.stop) 
            self.btn_start.set_state("normal")
            self.btn_stop.set_state("disabled")

    def update_status(self, current_file_name, chunk_size=0):
        self.completed_size += chunk_size
        now = time.time()
        if now - self.last_update_time > 0.5:
            duration = now - self.last_update_time
            diff_size = self.completed_size - self.last_size
            speed = diff_size / duration if duration > 0 else 0
            
            mb_transferred = self.completed_size / 1048576
            speed_mb = speed / 1048576
            
            status_text = f"已传: {mb_transferred:.1f} MB | 速度: {speed_mb:.1f} MB/s | 文件: {current_file_name[-30:]}"
            self.progress_label.config(text=status_text)
            self.last_update_time = now
            self.last_size = self.completed_size

    def do_upload(self, sftp):
        lp = self.up_local_path.get()
        rb = self.up_remote_path.get()
        self.log("Start Uploading...", "INFO")
        
        if self.upload_mode.get() == "folder":
            base = os.path.basename(os.path.normpath(lp))
            rp = posixpath.join(rb, base)
            self.upload_r(sftp, lp, rp)
        else:
            rp = posixpath.join(rb, os.path.basename(lp))
            self.upload_f(sftp, lp, rp)

    def upload_r(self, sftp, local, remote):
        if not self.is_running: return
        try: sftp.stat(remote)
        except: 
            try: sftp.mkdir(remote)
            except: 
                try: sftp.mkdir(posixpath.dirname(remote))
                except: pass
                sftp.mkdir(remote)
        for item in os.listdir(local):
            if not self.is_running: return
            l = os.path.join(local, item)
            r = posixpath.join(remote, item)
            if os.path.isdir(l): self.upload_r(sftp, l, r)
            else: self.upload_f(sftp, l, r)

    def upload_f(self, sftp, local, remote):
        if not self.is_running: return
        fname = os.path.basename(local)
        
        size = os.path.getsize(local)
        need = True
        
        if not self.force_overwrite.get():
            try:
                attr = sftp.stat(remote)
                if attr.st_size == size: 
                    self.log(f"Skip: {fname}", "INFO")
                    self.root.after(0, lambda: self.update_status(fname, size)) 
                    need = False
            except: pass
        
        if need:
            self.log(f"Uploading: {fname}", "CMD")
            self._current_file_prev_transferred = 0
            
            def detailed_cb(transferred, total):
                if not self.is_running: raise Exception("Stop")
                chunk = transferred - self._current_file_prev_transferred
                self._current_file_prev_transferred = transferred
                self.root.after(0, lambda: self.update_status(fname, chunk))
            
            try: 
                sftp.put(local, remote, callback=detailed_cb)
                self.log(f"OK: {fname}", "SUCCESS")
            except Exception as e: 
                if "Stop" not in str(e): self.log(f"Fail: {e}", "ERROR")

    def do_download(self, sftp):
        rp = self.down_remote_path.get()
        ld = self.down_local_path.get()
        self.log("Start Downloading...", "INFO")
        
        try: r_stat = sftp.stat(rp)
        except: raise Exception("远程路径不存在")
        
        if stat.S_ISDIR(r_stat.st_mode):
            local_folder = os.path.join(ld, posixpath.basename(rp.rstrip('/')))
            self.download_r(sftp, rp, local_folder)
        else:
            local_file = os.path.join(ld, posixpath.basename(rp))
            self.download_f(sftp, rp, local_file, r_stat.st_size)

    def download_r(self, sftp, remote_dir, local_dir):
        if not self.is_running: return
        if not os.path.exists(local_dir): os.makedirs(local_dir)
        for entry in sftp.listdir_attr(remote_dir):
            if not self.is_running: break
            r_path = posixpath.join(remote_dir, entry.filename)
            l_path = os.path.join(local_dir, entry.filename)
            if stat.S_ISDIR(entry.st_mode): self.download_r(sftp, r_path, l_path)
            else: self.download_f(sftp, r_path, l_path, entry.st_size)

    def download_f(self, sftp, remote_file, local_file, size):
        if not self.is_running: return
        fname = os.path.basename(remote_file)
        need = True
        
        if not self.force_overwrite.get():
            if os.path.exists(local_file) and os.path.getsize(local_file) == size:
                self.log(f"Skip: {fname}", "INFO")
                self.root.after(0, lambda: self.update_status(fname, size))
                need = False
            
        if need:
            self.log(f"Downloading: {fname}", "CMD")
            
            self._current_file_prev_transferred = 0
            def detailed_cb(transferred, total):
                if not self.is_running: raise Exception("Stop")
                chunk = transferred - self._current_file_prev_transferred
                self._current_file_prev_transferred = transferred
                self.root.after(0, lambda: self.update_status(fname, chunk))
                
            try: 
                sftp.get(remote_file, local_file, callback=detailed_cb)
                self.log(f"OK: {fname}", "SUCCESS")
            except Exception as e:
                if "Stop" not in str(e): self.log(f"Fail: {e}", "ERROR")

    # --- 终端独立命令 ---
    def run_custom_command(self, event=None):
        cmd = self.cmd_var.get().strip()
        if not cmd: return
        self.cmd_var.set("")
        self.log(f"remote$ {cmd}", "INPUT")
        
        if self.is_connected and self.ssh_client:
            threading.Thread(target=self._run_cmd_existing, args=(cmd,), daemon=True).start()
        else:
            self.log("未连接，尝试建立临时连接...", "WARN")
            threading.Thread(target=self._run_cmd_temp, args=(cmd,), daemon=True).start()

    def _run_cmd_existing(self, cmd):
        try:
            stdin, stdout, stderr = self.ssh_client.exec_command(cmd)
            out = stdout.read().decode().strip()
            err = stderr.read().decode().strip()
            if out: self.log(out, "INFO")
            if err: self.log(err, "ERROR")
            if not out and not err: self.log("[No Output]", "INFO")
        except Exception as e:
            self.log(f"CMD Error: {e}", "ERROR")
            if "Socket" in str(e):
                 self.root.after(0, lambda: self._set_connected_ui(False))

    def _run_cmd_temp(self, cmd):
        c = None
        j = None
        try:
            c, j = self._get_ssh_connection()
            stdin, stdout, stderr = c.exec_command(cmd)
            out = stdout.read().decode().strip()
            err = stderr.read().decode().strip()
            if out: self.log(out, "INFO")
            if err: self.log(err, "ERROR")
        except Exception as e: self.log(f"CMD Error: {e}", "ERROR")
        finally:
            if c: c.close()
            if j: j.close()

if __name__ == "__main__":
    root = tk.Tk()
    SFTPUploaderApp(root)
    root.mainloop()