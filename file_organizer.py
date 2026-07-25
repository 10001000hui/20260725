# -*- coding: utf-8 -*-
import os
import shutil
import threading
import ctypes
import time
import logging
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog

# --- Config & Globals ---
DEFAULT_CATEGORIES = {
    "圖片 (Images)": {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"},
    "文件 (Documents)": {".pdf", ".docx", ".doc", ".txt", ".rtf"},
    "試算表 (Spreadsheets)": {".xlsx", ".xls", ".csv"},
    "簡報 (Presentations)": {".pptx", ".ppt"},
    "影片 (Videos)": {".mp4", ".mkv", ".avi", ".mov", ".wmv"},
    "音訊 (Audio)": {".mp3", ".wav", ".aac", ".flac", ".ogg"},
    "壓縮檔 (Archives)": {".zip", ".rar", ".7z", ".tar", ".gz"},
    "程式碼 (Code)": {".py", ".js", ".html", ".css", ".java", ".cpp", ".c"}
}

FALLBACK_CATEGORY = "其他 (Others)"

class FileOrganizerApp(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("資料夾整理小幫手 (Folder Organizer)")
        self.geometry("600x480")
        self.resizable(True, True)
        self.minsize(600, 480)
        self.center_window(600, 480)
        self.grab_set()  # Make modal window
        
        # Load system-native light style
        self.style = ttk.Style(self)
        self.style.theme_use("winnative")  # Native Windows styling
        
        # Dynamic rules for this session
        self.custom_categories = {}
        
        # Migration transaction memory
        self.migration_history = []
        self.abort_requested = False
        self.is_running = False
        
        # Variables
        self.path_var = tk.StringVar()
        self.recursive_var = tk.BooleanVar(value=False)
        self.ignore_hidden_var = tk.BooleanVar(value=True)
        
        self.create_widgets()

    def center_window(self, width, height):
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
        
    def create_widgets(self):
        # 1. Path selection frame
        path_frame = ttk.LabelFrame(self, text=" 步驟 1：選擇整理目標資料夾 ")
        path_frame.pack(fill="x", padx=15, pady=10)
        
        self.path_entry = ttk.Entry(path_frame, textvariable=self.path_var, width=42)
        self.path_entry.pack(side="left", padx=(10, 5), pady=10)
        
        self.browse_btn = ttk.Button(path_frame, text="瀏覽...", command=self.browse_folder)
        self.browse_btn.pack(side="left", padx=2, pady=10)
        
        self.input_btn = ttk.Button(path_frame, text="輸入路徑", command=self.input_folder_path)
        self.input_btn.pack(side="left", padx=(2, 10), pady=10)
        
        # 2. Options and Rules frame
        opt_frame = ttk.LabelFrame(self, text=" 步驟 2：設定與規則 ")
        opt_frame.pack(fill="both", expand=True, padx=15, pady=5)
        
        chk_sub = ttk.Checkbutton(opt_frame, text="包含子資料夾（遞迴整理）", 
                                  variable=self.recursive_var, command=self.on_recursive_toggle)
        chk_sub.pack(anchor="w", padx=15, pady=8)
        
        chk_hidden = ttk.Checkbutton(opt_frame, text="忽略系統與隱藏檔案（建議勾選）", 
                                     variable=self.ignore_hidden_var)
        chk_hidden.pack(anchor="w", padx=15, pady=5)
        
        # Rules buttons frame
        btn_rules_frame = ttk.Frame(opt_frame)
        btn_rules_frame.pack(fill="x", padx=15, pady=10)
        
        self.view_rules_btn = ttk.Button(btn_rules_frame, text="檢視目前分類規則", command=self.view_rules)
        self.view_rules_btn.pack(side="left")
        self.view_rules_btn.pack_configure(padx=(0, 10))
        
        self.add_rule_btn = ttk.Button(btn_rules_frame, text="自訂新增分類...", command=self.add_custom_rule)
        self.add_rule_btn.pack(side="left")
        
        # Stats summary label
        self.stats_lbl = ttk.Label(opt_frame, text="預計整理檔案總數：0 個", font=("Arial", 10, "bold"))
        self.stats_lbl.pack(anchor="w", padx=15, pady=10)
        
        # 3. Control frame
        ctrl_frame = ttk.LabelFrame(self, text=" 步驟 3：執行分類 ")
        ctrl_frame.pack(fill="x", padx=15, pady=10)
        
        btn_box = ttk.Frame(ctrl_frame)
        btn_box.pack(fill="x", padx=10, pady=5)
        
        self.start_btn = ttk.Button(btn_box, text="開始整理", command=self.confirm_and_start)
        self.start_btn.pack(side="left", padx=(0, 10))
        
        self.abort_btn = ttk.Button(btn_box, text="中止整理", state="disabled", command=self.abort_process)
        self.abort_btn.pack(side="left", padx=(0, 10))
        
        self.undo_btn = ttk.Button(btn_box, text="復原上一次整理", state="disabled", command=self.undo_migration)
        self.undo_btn.pack(side="left")
        
        self.progress = ttk.Progressbar(ctrl_frame, orient="horizontal", mode="determinate")
        self.progress.pack(fill="x", padx=10, pady=10)
        
        self.status_lbl = ttk.Label(ctrl_frame, text="狀態：準備就緒")
        self.status_lbl.pack(anchor="w", padx=10, pady=(0, 10))

    def on_recursive_toggle(self):
        if self.recursive_var.get():
            confirm = messagebox.askyesno(
                "遞迴整理安全警示", 
                "開啟「包含子資料夾」將會遍歷所有深層目錄，並將裡面的檔案複製出來分類。\n這可能會變更您原本在子資料夾中建立好的檔案結構。\n\n確定要啟用此設定嗎？"
            )
            if not confirm:
                self.recursive_var.set(False)
        self.update_pre_scan()

    def get_active_rules(self):
        # Merge default rules and custom session rules
        rules = DEFAULT_CATEGORIES.copy()
        rules.update(self.custom_categories)
        return rules

    def is_hidden_or_system(self, file_path):
        # 1. Dotfile check
        if os.path.basename(file_path).startswith('.'):
            return True
        # 2. Windows Attributes API check
        try:
            attrs = ctypes.windll.kernel32.GetFileAttributesW(str(file_path))
            if attrs != -1:
                # FILE_ATTRIBUTE_HIDDEN = 2, FILE_ATTRIBUTE_SYSTEM = 4
                return bool(attrs & (2 | 4))
        except Exception:
            pass
        return False

    def get_blacklist_folders(self):
        # Folders that should never be searched or processed
        blacklist = set(DEFAULT_CATEGORIES.keys())
        blacklist.add(FALLBACK_CATEGORY)
        for custom_name in self.custom_categories.keys():
            blacklist.add(custom_name)
        return blacklist

    def scan_files(self, root_dir, recursive, ignore_hidden):
        if not root_dir or not os.path.isdir(root_dir):
            return []
        
        files_to_process = []
        blacklist = self.get_blacklist_folders()
        report_log_name = "classification_report.log"
        
        try:
            for root, dirs, files in os.walk(root_dir):
                # Calculate relative path components to filter blacklisted folders
                rel_path = os.path.relpath(root, root_dir)
                if rel_path != ".":
                    parts = rel_path.split(os.sep)
                    # If any part of the path is in the blacklist, skip traversing further
                    if any(p in blacklist for p in parts):
                        # Clear dirs so walk won't go deeper
                        dirs.clear()
                        continue
                
                # Filter directories in current layer to prevent entering blacklisted folders
                dirs[:] = [d for d in dirs if d not in blacklist]
                
                for f in files:
                    if f == report_log_name:
                        continue
                        
                    full_path = os.path.join(root, f)
                    
                    # Ignore hidden/system
                    if ignore_hidden and self.is_hidden_or_system(full_path):
                        continue
                        
                    files_to_process.append(full_path)
                    
                if not recursive:
                    break # Only run first layer
        except Exception as e:
            logging.error(f"Error scanning directory {root_dir}: {str(e)}")
            
        return files_to_process

    def browse_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            # Canonicalize path
            folder = os.path.abspath(folder)
            self.path_var.set(folder)
            self.update_pre_scan()

    def input_folder_path(self):
        folder = simpledialog.askstring("輸入路徑", "請輸入或貼上要整理的資料夾路徑：", parent=self)
        if folder:
            folder = folder.strip()
            if os.path.isdir(folder):
                folder = os.path.abspath(folder)
                self.path_var.set(folder)
                self.update_pre_scan()
            else:
                messagebox.showerror("路徑錯誤", f"輸入的資料夾路徑不存在：\n{folder}", parent=self)

    def update_pre_scan(self):
        folder = self.path_var.get()
        if not folder or not os.path.isdir(folder):
            self.stats_lbl.config(text="預計整理檔案總數：0 個")
            return
            
        # Run pre-scan in a non-blocking thread to avoid UI freeze
        def task():
            files = self.scan_files(folder, self.recursive_var.get(), self.ignore_hidden_var.get())
            self.after(0, lambda: self.stats_lbl.config(text=f"預計整理檔案總數：{len(files)} 個"))
            
        threading.Thread(target=task, daemon=True).start()

    def view_rules(self):
        rules_win = tk.Toplevel(self)
        rules_win.title("目前分類與副檔名對照表")
        rules_win.geometry("500x400")
        rules_win.resizable(True, True)
        
        # Simple treeview layout
        tree = ttk.Treeview(rules_win, columns=("Category", "Extensions"), show="headings")
        tree.heading("Category", text="資料夾分類名稱")
        tree.heading("Extensions", text="副檔名映射規則")
        tree.column("Category", width=180, anchor="w")
        tree.column("Extensions", width=300, anchor="w")
        
        scroll = ttk.Scrollbar(rules_win, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)
        
        tree.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        scroll.pack(side="right", fill="y", padx=(0, 10), pady=10)
        
        # Populate rules
        all_rules = self.get_active_rules()
        for cat, exts in all_rules.items():
            ext_str = ", ".join(sorted(exts))
            tree.insert("", "end", values=(cat, ext_str))
            
        # Add fallback info
        tree.insert("", "end", values=(FALLBACK_CATEGORY, "無法識別或無副檔名之檔案預設分流區"))

    def add_custom_rule(self):
        add_win = tk.Toplevel(self)
        add_win.title("新增自訂分類")
        add_win.geometry("380x220")
        add_win.resizable(False, False)
        add_win.grab_set()  # Modal
        
        lbl_zh = ttk.Label(add_win, text="分類中文名稱：")
        lbl_zh.grid(row=0, column=0, padx=15, pady=15, sticky="w")
        ent_zh = ttk.Entry(add_win, width=25)
        ent_zh.grid(row=0, column=1, padx=15, pady=15)
        
        lbl_en = ttk.Label(add_win, text="分類英文名稱：")
        lbl_en.grid(row=1, column=0, padx=15, pady=10, sticky="w")
        ent_en = ttk.Entry(add_win, width=25)
        ent_en.grid(row=1, column=1, padx=15, pady=10)
        
        lbl_ext = ttk.Label(add_win, text="副檔名 (逗號分隔)：\n例如: .psd, .ai")
        lbl_ext.grid(row=2, column=0, padx=15, pady=10, sticky="w")
        ent_ext = ttk.Entry(add_win, width=25)
        ent_ext.grid(row=2, column=1, padx=15, pady=10)
        
        def save_rule():
            zh = ent_zh.get().strip()
            en = ent_en.get().strip()
            ext_raw = ent_ext.get().strip()
            
            if not zh or not en:
                messagebox.showerror("格式錯誤", "中英文分類名稱皆不得為空！", parent=add_win)
                return
            if not ext_raw:
                messagebox.showerror("格式錯誤", "副檔名定義清單不得為空！", parent=add_win)
                return
                
            # Process extensions
            exts = set()
            for part in ext_raw.split(','):
                cleaned = part.strip().lower()
                if cleaned:
                    if not cleaned.startswith('.'):
                        cleaned = '.' + cleaned
                    exts.add(cleaned)
            
            cat_name = f"{zh} ({en})"
            self.custom_categories[cat_name] = exts
            messagebox.showinfo("成功", f"成功新增自訂分類規則：\n{cat_name}", parent=add_win)
            add_win.destroy()
            self.update_pre_scan()
            
        btn_save = ttk.Button(add_win, text="確定新增", command=save_rule)
        btn_save.grid(row=3, column=0, columnspan=2, pady=15)

    def confirm_and_start(self):
        folder = self.path_var.get()
        if not folder or not os.path.isdir(folder):
            messagebox.showerror("路徑錯誤", "請先點擊「瀏覽...」選擇一個有效的資料夾！")
            return
            
        confirm = messagebox.askyesno(
            "整理確認", 
            f"即將開始複製分類整理資料夾：\n{folder}\n\n是否確定執行？"
        )
        if confirm:
            self.start_organizing()

    def start_organizing(self):
        if self.is_running:
            return
            
        self.is_running = True
        self.abort_requested = False
        
        # UI disabling during run
        self.start_btn.config(state="disabled")
        self.browse_btn.config(state="disabled")
        self.input_btn.config(state="disabled")
        self.path_entry.config(state="disabled")
        self.add_rule_btn.config(state="disabled")
        self.view_rules_btn.config(state="disabled")
        self.undo_btn.config(state="disabled")
        self.abort_btn.config(state="normal")
        
        # Start Worker Thread
        threading.Thread(target=self.organize_worker, daemon=True).start()

    def abort_process(self):
        self.abort_requested = True
        self.status_lbl.config(text="狀態：正在發送中斷請求...")

    def organize_worker(self):
        root_dir = self.path_var.get()
        recursive = self.recursive_var.get()
        ignore_hidden = self.ignore_hidden_var.get()
        
        # Clear migration history of this session
        self.migration_history = []
        
        # Pre-scan files list
        files_to_copy = self.scan_files(root_dir, recursive, ignore_hidden)
        total_files = len(files_to_copy)
        
        if total_files == 0:
            self.after(0, self.finish_organizing, 0, 0, [])
            return
            
        rules = self.get_active_rules()
        success_count = 0
        failure_list = [] # List of tuples: (filename, reason)
        category_stats = {cat: 0 for cat in list(rules.keys()) + [FALLBACK_CATEGORY]}
        
        # Initialize Logger inside the target folder
        log_path = os.path.join(root_dir, "classification_report.log")
        logger = logging.getLogger("organizer_logger")
        logger.setLevel(logging.INFO)
        # Clear old handlers
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        
        try:
            fh = logging.FileHandler(log_path, mode="w", encoding="utf-8")
            formatter = logging.Formatter("[%(asctime)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
            fh.setFormatter(formatter)
            logger.addHandler(fh)
        except Exception as e:
            # Fallback if logging file creation itself fails
            failure_list.append(("日誌檔建立失敗", str(e)))
            
        logger.info(f"分類任務啟動。目標目錄: {root_dir}")
        logger.info(f"參數設定 - 包含子資料夾: {recursive}, 忽略隱藏/系統檔: {ignore_hidden}")
        
        for idx, file_path in enumerate(files_to_copy):
            if self.abort_requested:
                logger.info("分類任務由使用者手動中止。")
                break
                
            file_name = os.path.basename(file_path)
            # Update GUI progress
            self.after(0, self._update_progress_ui, idx, total_files, file_name)
            
            # 1. Determine Category
            ext = Path(file_path).suffix.lower().strip()
            matched_category = FALLBACK_CATEGORY
            
            for cat, extensions in rules.items():
                if ext in extensions:
                    matched_category = cat
                    break
            
            # 2. Create Target Folder on demand
            dest_folder = os.path.join(root_dir, matched_category)
            
            # 3. Handle File copy & name collisions
            try:
                os.makedirs(dest_folder, exist_ok=True)
                dest_path = os.path.join(dest_folder, file_name)
                
                # Recursively solve naming collision
                if os.path.exists(dest_path):
                    base, suffix = os.path.splitext(file_name)
                    counter = 1
                    while True:
                        new_name = f"{base}({counter}){suffix}"
                        new_dest_path = os.path.join(dest_folder, new_name)
                        if not os.path.exists(new_dest_path):
                            dest_path = new_dest_path
                            break
                        counter += 1
                
                # Execute metadata-preserving copy
                shutil.copy2(file_path, dest_path)
                
                # Track in memory and report in log
                self.migration_history.append((file_path, dest_path))
                success_count += 1
                category_stats[matched_category] += 1
                logger.info(f"成功分類: {file_path} -> {dest_path}")
                
            except PermissionError as pe:
                reason = "存取被拒/檔案鎖定中"
                failure_list.append((file_name, reason))
                logger.error(f"分類失敗 (PermissionError): {file_path}。原因: {str(pe)}")
            except OSError as oe:
                reason = "作業系統 I/O 錯誤"
                failure_list.append((file_name, reason))
                logger.error(f"分類失敗 (OSError): {file_path}。原因: {str(oe)}")
            except Exception as ex:
                reason = f"未預期錯誤: {type(ex).__name__}"
                failure_list.append((file_name, reason))
                logger.error(f"分類失敗 (Unexpected): {file_path}。原因: {str(ex)}")
                
            # Tiny backoff to allow progress updates representation
            time.sleep(0.01)
            
        logger.info(f"分類任務結束。成功處理: {success_count} 個, 失敗: {len(failure_list)} 個")
        self.after(0, self.finish_organizing, success_count, total_files, failure_list, category_stats)

    def _update_progress_ui(self, index, total, filename):
        val = int(((index + 1) / total) * 100)
        self.progress["value"] = val
        self.status_lbl.config(text=f"狀態：正在處理第 {index + 1} / {total} 個檔案：{filename}")

    def finish_organizing(self, success_count, total, failure_list, category_stats=None):
        self.is_running = False
        self.progress["value"] = 100
        
        # Restore UI elements
        self.start_btn.config(state="normal")
        self.browse_btn.config(state="normal")
        self.input_btn.config(state="normal")
        self.path_entry.config(state="normal")
        self.add_rule_btn.config(state="normal")
        self.view_rules_btn.config(state="normal")
        self.abort_btn.config(state="disabled")
        
        if self.abort_requested:
            self.status_lbl.config(text="狀態：使用者手動中止整理。")
        else:
            self.status_lbl.config(text="狀態：整理完成！")
            
        if len(self.migration_history) > 0:
            self.undo_btn.config(state="normal")
            
        # Re-trigger pre-scan count update
        self.update_pre_scan()
        
        # POPUP Completion Modal (Strict PRD Format Check)
        self.show_completion_report(success_count, total, failure_list, category_stats)

    def show_completion_report(self, success_count, total, failure_list, category_stats):
        report_win = tk.Toplevel(self)
        report_win.title("整理結果報告")
        report_win.geometry("520x440")
        report_win.resizable(False, False)
        report_win.grab_set()  # Modal Dialog
        
        # Bind Enter key to close the window
        report_win.bind("<Return>", lambda e: report_win.destroy())
        
        # Header - STRICT Title Constraint: "整理了 N 個檔案"
        title_str = f"整理了 {success_count} 個檔案"
        lbl_title = ttk.Label(report_win, text=title_str, font=("Arial", 16, "bold"), foreground="#005A9C")
        lbl_title.pack(pady=15)
        
        # Stats summary text
        sum_str = f"掃描檔案總數：{total} 個 | 成功複製：{success_count} 個 | 失敗：{len(failure_list)} 個"
        lbl_sum = ttk.Label(report_win, text=sum_str, font=("Arial", 10, "bold"))
        lbl_sum.pack(pady=5)
        
        # Tabbed result details
        notebook = ttk.Notebook(report_win)
        notebook.pack(fill="both", expand=True, padx=15, pady=10)
        
        # Tab 1: Category Details
        tab_cat = ttk.Frame(notebook)
        notebook.add(tab_cat, text="分類計數明細")
        
        tree_cat = ttk.Treeview(tab_cat, columns=("Category", "Count"), show="headings", height=8)
        tree_cat.heading("Category", text="分類資料夾")
        tree_cat.heading("Count", text="複製成功檔案數")
        tree_cat.column("Category", width=250, anchor="w")
        tree_cat.column("Count", width=180, anchor="center")
        tree_cat.pack(fill="both", expand=True, padx=10, pady=10)
        
        if category_stats:
            for cat, count in category_stats.items():
                if count > 0 or cat == FALLBACK_CATEGORY:
                    tree_cat.insert("", "end", values=(cat, f"{count} 個"))
                    
        # Tab 2: Failure List
        tab_fail = ttk.Frame(notebook)
        notebook.add(tab_fail, text=f"失敗與阻礙項目 ({len(failure_list)})")
        
        tree_fail = ttk.Treeview(tab_fail, columns=("File", "Reason"), show="headings", height=8)
        tree_fail.heading("File", text="檔名")
        tree_fail.heading("Reason", text="失效原因")
        tree_fail.column("File", width=250, anchor="w")
        tree_fail.column("Reason", width=180, anchor="w")
        
        scroll_fail = ttk.Scrollbar(tab_fail, orient="vertical", command=tree_fail.yview)
        tree_fail.configure(yscrollcommand=scroll_fail.set)
        
        tree_fail.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=10)
        scroll_fail.pack(side="right", fill="y", padx=(0, 10), pady=10)
        
        for f_name, reason in failure_list:
            tree_fail.insert("", "end", values=(f_name, reason))
            
        # Close tip
        lbl_tip = ttk.Label(report_win, text="（提示：可以按 Enter 鍵確認並關閉此視窗）", font=("Arial", 9), foreground="gray")
        lbl_tip.pack(pady=(5, 0))
        
        # Close button
        btn_close = ttk.Button(report_win, text="關閉報告", command=report_win.destroy)
        btn_close.pack(pady=10)
        btn_close.focus_set()

    def undo_migration(self):
        if len(self.migration_history) == 0:
            messagebox.showwarning("復原無效", "目前無可復原的歷史分類紀錄。")
            return
            
        confirm = messagebox.askyesno(
            "確認復原", 
            "確定要撤銷上一次分類整理嗎？\n系統將精確刪除當次複製出的所有檔案，並移除變為空的子資料夾。\n原資料夾內的檔案將完整保留。"
        )
        
        if not confirm:
            return
            
        success_undo = 0
        failed_undo = 0
        directories_to_check = set()
        
        for src, dest in self.migration_history:
            try:
                if os.path.exists(dest):
                    os.remove(dest)
                    success_undo += 1
                    
                    # Track folder to potentially clean up empty dir
                    parent = os.path.dirname(dest)
                    directories_to_check.add(parent)
            except Exception as e:
                failed_undo += 1
                logging.error(f"Undo failed for file {dest}: {str(e)}")
                
        # Clean up empty created directories
        deleted_dirs = 0
        # Sort by depth descending so subdirectories are deleted before parent directories
        for folder in sorted(list(directories_to_check), key=len, reverse=True):
            try:
                # Only remove if directory is completely empty
                if os.path.exists(folder) and len(os.listdir(folder)) == 0:
                    os.rmdir(folder)
                    deleted_dirs += 1
            except Exception as e:
                logging.error(f"Undo directory clean failed for {folder}: {str(e)}")
                
        self.migration_history = []
        self.undo_btn.config(state="disabled")
        self.progress["value"] = 0
        self.status_lbl.config(text="狀態：已復原上一次整理")
        
        # Reload pre-scan file count
        self.update_pre_scan()
        
        messagebox.showinfo(
            "復原完畢", 
            f"撤銷分類整理成功！\n共刪除複製檔案：{success_undo} 個\n清理空資料夾：{deleted_dirs} 個\n失敗：{failed_undo} 個"
        )


class FileRenamerApp(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("批次改檔名 (Batch Rename)")
        self.geometry("640x550")
        self.resizable(True, True)
        self.minsize(640, 550)
        self.center_window(640, 550)
        self.grab_set()
        
        self.path_var = tk.StringVar()
        self.prefix_var = tk.StringVar()
        self.add_date_var = tk.BooleanVar(value=False)
        self.replace_var = tk.BooleanVar(value=False)
        self.serial_var = tk.BooleanVar(value=False)
        
        self.serial_start_var = tk.StringVar(value="1")
        self.serial_digits_var = tk.StringVar(value="2")
        
        self.is_running = False
        self.abort_requested = False
        self.proposed_changes = []
        
        self.create_widgets()
        
    def center_window(self, width, height):
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
        
    def create_widgets(self):
        # 1. Path selection frame
        path_frame = ttk.LabelFrame(self, text=" 步驟 1：選擇目標資料夾 ")
        path_frame.pack(fill="x", padx=15, pady=10)
        
        self.path_entry = ttk.Entry(path_frame, textvariable=self.path_var, width=45)
        self.path_entry.pack(side="left", padx=(10, 5), pady=10)
        
        self.browse_btn = ttk.Button(path_frame, text="瀏覽...", command=self.browse_folder)
        self.browse_btn.pack(side="left", padx=2, pady=10)
        
        self.input_btn = ttk.Button(path_frame, text="輸入路徑", command=self.input_folder_path)
        self.input_btn.pack(side="left", padx=(2, 10), pady=10)
        
        # 2. Options frame
        rules_frame = ttk.LabelFrame(self, text=" 步驟 2：設定更名規則 ")
        rules_frame.pack(fill="x", padx=15, pady=5)
        
        # Row 0: Prefix entry & Date checkbox
        lbl_prefix = ttk.Label(rules_frame, text="加前綴字元：")
        lbl_prefix.grid(row=0, column=0, padx=(15, 5), pady=8, sticky="e")
        self.prefix_entry = ttk.Entry(rules_frame, textvariable=self.prefix_var, width=18)
        self.prefix_entry.grid(row=0, column=1, padx=5, pady=8, sticky="w")
        
        self.chk_date = ttk.Checkbutton(rules_frame, text="加今日日期 (YYYY-MM-DD_)", variable=self.add_date_var)
        self.chk_date.grid(row=0, column=2, columnspan=2, sticky="w", padx=15, pady=8)
        
        # Row 1: Checkbox 2: Find & Replace
        self.chk_replace = ttk.Checkbutton(rules_frame, text="尋找並取代文字", variable=self.replace_var, command=self.toggle_replace_entries)
        self.chk_replace.grid(row=1, column=0, columnspan=2, sticky="w", padx=15, pady=5)
        
        lbl_find = ttk.Label(rules_frame, text="尋找文字：")
        lbl_find.grid(row=2, column=0, padx=(30, 5), pady=5, sticky="e")
        self.find_entry = ttk.Entry(rules_frame, width=18, state="disabled")
        self.find_entry.grid(row=2, column=1, padx=5, pady=5, sticky="w")
        
        lbl_replace = ttk.Label(rules_frame, text="取代為：")
        lbl_replace.grid(row=2, column=2, padx=5, pady=5, sticky="e")
        self.replace_entry = ttk.Entry(rules_frame, width=18, state="disabled")
        self.replace_entry.grid(row=2, column=3, padx=(5, 15), pady=5, sticky="w")
        
        # Row 3: Checkbox 3: Serial Number
        self.chk_serial = ttk.Checkbutton(rules_frame, text="遞增流水號", variable=self.serial_var, command=self.toggle_serial_entries)
        self.chk_serial.grid(row=3, column=0, columnspan=2, sticky="w", padx=15, pady=5)
        
        lbl_serial_start = ttk.Label(rules_frame, text="起始值：")
        lbl_serial_start.grid(row=4, column=0, padx=(30, 5), pady=5, sticky="e")
        self.serial_start_entry = ttk.Entry(rules_frame, textvariable=self.serial_start_var, width=18, state="disabled")
        self.serial_start_entry.grid(row=4, column=1, padx=5, pady=5, sticky="w")
        
        lbl_serial_digits = ttk.Label(rules_frame, text="補零位數：")
        lbl_serial_digits.grid(row=4, column=2, padx=5, pady=5, sticky="e")
        self.serial_digits_entry = ttk.Entry(rules_frame, textvariable=self.serial_digits_var, width=18, state="disabled")
        self.serial_digits_entry.grid(row=4, column=3, padx=(5, 15), pady=5, sticky="w")
        
        # 3. Preview frame
        preview_frame = ttk.LabelFrame(self, text=" 步驟 3：預覽與確認更名 ")
        preview_frame.pack(fill="both", expand=True, padx=15, pady=10)
        
        # Use sub-frame for treeview + scrollbar
        tree_frame = ttk.Frame(preview_frame)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.tree = ttk.Treeview(tree_frame, columns=("Original", "New"), show="headings", height=5)
        self.tree.heading("Original", text="修改前檔名")
        self.tree.heading("New", text="修改後檔名")
        self.tree.column("Original", width=270, anchor="w")
        self.tree.column("New", width=270, anchor="w")
        
        scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        
        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        
        status_box = ttk.Frame(preview_frame)
        status_box.pack(fill="x", padx=10, pady=5)
        
        self.renamer_status_lbl = ttk.Label(status_box, text="預計修改檔案數：0 個", font=("Arial", 10, "bold"))
        self.renamer_status_lbl.pack(side="left")
        
        btn_box = ttk.Frame(preview_frame)
        btn_box.pack(fill="x", padx=10, pady=10)
        
        self.preview_btn = ttk.Button(btn_box, text="預覽更名結果", command=self.generate_preview)
        self.preview_btn.pack(side="left", padx=(0, 10))
        
        self.execute_btn = ttk.Button(btn_box, text="執行更名", state="disabled", command=self.execute_rename)
        self.execute_btn.pack(side="left", padx=(0, 10))
        
        btn_close = ttk.Button(btn_box, text="關閉", command=self.destroy)
        btn_close.pack(side="left")
        
    def toggle_replace_entries(self):
        state = "normal" if self.replace_var.get() else "disabled"
        self.find_entry.config(state=state)
        self.replace_entry.config(state=state)
        
    def toggle_serial_entries(self):
        state = "normal" if self.serial_var.get() else "disabled"
        self.serial_start_entry.config(state=state)
        self.serial_digits_entry.config(state=state)
        
    def browse_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.path_var.set(os.path.abspath(folder))
            
    def input_folder_path(self):
        folder = simpledialog.askstring("輸入路徑", "請輸入或貼上要整理的資料夾路徑：", parent=self)
        if folder:
            folder = folder.strip()
            if os.path.isdir(folder):
                self.path_var.set(os.path.abspath(folder))
            else:
                messagebox.showerror("路徑錯誤", f"輸入的資料夾路徑不存在：\n{folder}", parent=self)

    def sanitize_filename_input(self, text):
        # Strip forbidden characters: \ / : * ? " < > |
        forbidden = ['\\', '/', ':', '*', '?', '"', '<', '>', '|']
        result = text
        for char in forbidden:
            result = result.replace(char, '')
        return result

    def generate_preview(self):
        # Clear existing rows
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.proposed_changes.clear()
        
        folder = self.path_var.get()
        if not folder or not os.path.isdir(folder):
            messagebox.showerror("路徑錯誤", "請先選擇有效的資料夾！", parent=self)
            self.execute_btn.config(state="disabled")
            return
            
        if not self.prefix_var.get() and not self.add_date_var.get() and not self.replace_var.get() and not self.serial_var.get():
            messagebox.showwarning("規則未設定", "請至少啟用一種更名規則！", parent=self)
            self.execute_btn.config(state="disabled")
            return
            
        # Compile parameter values
        prefix_val = self.sanitize_filename_input(self.prefix_var.get())
        
        date_prefix = ""
        if self.add_date_var.get():
            from datetime import datetime
            date_prefix = datetime.now().strftime("%Y-%m-%d_")
            
        find_str = ""
        replace_str = ""
        if self.replace_var.get():
            find_str = self.sanitize_filename_input(self.find_entry.get())
            replace_str = self.sanitize_filename_input(self.replace_entry.get())
            if not find_str:
                messagebox.showwarning("參數缺失", "已啟用『取代文字』但『尋找文字』欄位為空！", parent=self)
                self.execute_btn.config(state="disabled")
                return
                
        serial_enabled = self.serial_var.get()
        start_val = 1
        digits_val = 2
        if serial_enabled:
            try:
                start_val = int(self.serial_start_var.get())
                if start_val < 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror("參數錯誤", "流水號起始值必須為非負整數！", parent=self)
                self.execute_btn.config(state="disabled")
                return
                
            try:
                digits_val = int(self.serial_digits_var.get())
                if digits_val <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror("參數錯誤", "流水號補零位數必須為正整數！", parent=self)
                self.execute_btn.config(state="disabled")
                return

        # Scan files recursively (Deep Traverse Strategy)
        files = []
        try:
            for root_dir, dirs, filenames in os.walk(folder):
                for filename in filenames:
                    # 1. Ignore dotfiles (starts with .)
                    if filename.startswith('.'):
                        continue
                    # 2. Ignore system files
                    if filename.lower() in ("desktop.ini", "thumbs.db"):
                        continue
                    # 3. Ignore file organizer report log
                    if filename == "classification_report.log":
                        continue
                    # 4. Ignore hidden files on Windows
                    full_path = os.path.join(root_dir, filename)
                    try:
                        if os.name == 'nt':
                            import ctypes
                            attrs = ctypes.windll.kernel32.GetFileAttributesW(full_path)
                            if attrs != -1 and (attrs & 2): # FILE_ATTRIBUTE_HIDDEN = 2
                                continue
                    except Exception:
                        pass
                    
                    # 5. Skip files with no extension (as required by PRD Option 2)
                    name_part, ext = os.path.splitext(filename)
                    if not ext or ext == ".":
                        continue
                        
                    files.append(full_path)
        except Exception as e:
            messagebox.showerror("讀取失敗", f"無法遞迴掃描該資料夾內容：\n{str(e)}", parent=self)
            self.execute_btn.config(state="disabled")
            return

        # Sort alphabetically to ensure consistent sequence numbering
        files.sort()
        
        # Run diff calculation
        seq = start_val
        for file_path in files:
            original_name = os.path.basename(file_path)
            name_part, ext = os.path.splitext(original_name)
            
            new_name_part = name_part
            
            # 1. Apply prefix
            if prefix_val:
                new_name_part = f"{prefix_val}{new_name_part}"
                
            # 2. Apply date prefix
            if date_prefix:
                new_name_part = f"{date_prefix}{new_name_part}"
                
            # 3. Find and replace
            if self.replace_var.get() and find_str:
                new_name_part = new_name_part.replace(find_str, replace_str)
                
            # 4. Apply serial number suffix
            if serial_enabled:
                serial_suffix = f"_{seq:0{digits_val}d}"
                new_name_part = f"{new_name_part}{serial_suffix}"
                seq += 1
                
            # Reattach extension
            new_name = f"{new_name_part}{ext}"
            
            # Calculate display path relative to root folder
            rel_original = os.path.relpath(file_path, folder)
            rel_new = os.path.join(os.path.dirname(rel_original), new_name)
            
            if new_name != original_name:
                self.proposed_changes.append((file_path, new_name))
                self.tree.insert("", "end", values=(rel_original, rel_new))
                
        self.renamer_status_lbl.config(text=f"預計修改檔案數：{len(self.proposed_changes)} 個")
        
        if len(self.proposed_changes) > 0:
            self.execute_btn.config(state="normal")
        else:
            self.execute_btn.config(state="disabled")
            messagebox.showinfo("無變更", "目前資料夾內的檔案無須進行更名變更！", parent=self)

    def execute_rename(self):
        if self.is_running:
            # Clicked while running: Abort action
            self.abort_requested = True
            self.renamer_status_lbl.config(text="狀態：正在中止作業...")
            self.execute_btn.config(state="disabled")
            return
            
        if len(self.proposed_changes) == 0:
            return
            
        confirm = messagebox.askyesno(
            "確認更名", 
            f"即將批次更名 {len(self.proposed_changes)} 個檔案。\n此動作將直接修改磁碟實體檔名，且無法自動復原。\n\n確定執行嗎？",
            parent=self
        )
        if not confirm:
            return
            
        # Lock UI
        self.set_ui_state("disabled")
        
        self.is_running = True
        self.abort_requested = False
        
        # Toggle execution button
        self.execute_btn.config(text="中止更名", state="normal")
        
        # Start worker thread
        import threading
        threading.Thread(target=self.rename_worker, daemon=True).start()

    def set_ui_state(self, state):
        self.browse_btn.config(state=state)
        self.input_btn.config(state=state)
        self.path_entry.config(state=state)
        self.prefix_entry.config(state=state)
        
        self.chk_date.config(state=state)
        self.chk_replace.config(state=state)
        self.chk_serial.config(state=state)
        
        self.preview_btn.config(state=state)
        
        if state == "normal":
            self.toggle_replace_entries()
            self.toggle_serial_entries()
        else:
            self.find_entry.config(state="disabled")
            self.replace_entry.config(state="disabled")
            self.serial_start_entry.config(state="disabled")
            self.serial_digits_entry.config(state="disabled")

    def rename_worker(self):
        success_count = 0
        collision_count = 0
        error_count = 0
        
        total = len(self.proposed_changes)
        
        for idx, (old_path, new_name) in enumerate(self.proposed_changes):
            if self.abort_requested:
                break
                
            folder = os.path.dirname(old_path)
            new_path = os.path.join(folder, new_name)
            
            # Update progress
            progress_msg = f"正在更名：{idx+1}/{total}"
            self.safe_update_status(progress_msg)
            
            if os.path.exists(new_path):
                collision_count += 1
                continue
                
            try:
                os.rename(old_path, new_path)
                success_count += 1
            except Exception as e:
                error_count += 1
                logging.error(f"Rename failed: {old_path} -> {new_path}. Error: {str(e)}")
                
        # Finish job
        self.is_running = False
        self.safe_update_status("狀態：更名作業結束")
        self.safe_show_summary(success_count, collision_count, error_count)

    def safe_update_status(self, text):
        self.after(0, lambda: self.renamer_status_lbl.config(text=text))

    def safe_show_summary(self, success, collision, error):
        def gui_finish():
            messagebox.showinfo(
                "更名完成", 
                f"批次更名程序執行完畢！\n\n成功更名：{success} 個\n命名衝突略過：{collision} 個\n其他失敗：{error} 個",
                parent=self
            )
            # Restore UI
            self.execute_btn.config(text="執行更名", state="disabled")
            self.set_ui_state("normal")
            
            # Clear preview table
            for item in self.tree.get_children():
                self.tree.delete(item)
            self.proposed_changes.clear()
            self.renamer_status_lbl.config(text="預計修改檔案數：0 個")
            
        self.after(0, gui_finish)


import fitz  # PyMuPDF

class PdfToolboxApp(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("PDF 萬能工具箱 (PDF Toolbox)")
        self.geometry("780x580")
        self.resizable(True, True)
        self.minsize(780, 580)
        self.center_window(780, 580)
        self.grab_set()
        
        self.active_tab_idx = None
        self.is_running = False
        
        self.create_layout()
        
    def center_window(self, width, height):
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
        
    def create_layout(self):
        self.main_pane = ttk.Frame(self)
        self.main_pane.pack(fill="both", expand=True)
        
        sidebar = ttk.LabelFrame(self.main_pane, text=" 功能選單 ", width=180)
        sidebar.pack(side="left", fill="y", padx=(10, 5), pady=10)
        sidebar.pack_propagate(False)
        
        self.nav_list = tk.Listbox(sidebar, font=("Arial", 11), bd=0, selectmode="single", highlightthickness=0)
        self.nav_list.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.tabs = [
            "PDF 合併",
            "PDF 拆分與提取",
            "PDF 密碼保護",
            "PDF 頁面旋轉",
            "PDF 轉圖片",
            "PDF 文字圖片提取",
            "PDF 浮水印",
            "圖片轉 PDF"
        ]
        for tab in self.tabs:
            self.nav_list.insert("end", f"  {tab}")
            
        self.nav_list.bind("<<ListboxSelect>>", self.on_tab_change)
        
        self.content_frame = ttk.LabelFrame(self.main_pane, text=" 操作面板 ")
        self.content_frame.pack(side="right", fill="both", expand=True, padx=(5, 10), pady=10)
        
        self.nav_list.selection_set(0)
        self.on_tab_change(None)
        
    def on_tab_change(self, event):
        if self.is_running:
            messagebox.showwarning("執行中", "目前有作業正在執行，請稍候或等候完畢再切換！", parent=self)
            self.nav_list.selection_clear(0, "end")
            self.nav_list.selection_set(self.active_tab_idx)
            return
            
        selection = self.nav_list.curselection()
        if not selection:
            return
        idx = selection[0]
        self.active_tab_idx = idx
        
        for child in self.content_frame.winfo_children():
            child.destroy()
            
        tab_name = self.tabs[idx]
        self.content_frame.config(text=f" {tab_name} ")
        
        if idx == 0:
            self.build_merge_tab()
        elif idx == 1:
            self.build_split_tab()
        elif idx == 2:
            self.build_encrypt_tab()
        elif idx == 3:
            self.build_rotate_tab()
        elif idx == 4:
            self.build_to_image_tab()
        elif idx == 5:
            self.build_extract_assets_tab()
        elif idx == 6:
            self.build_watermark_tab()
        elif idx == 7:
            self.build_images_to_pdf_tab()

    # --- Tab 1: Merge ---
    def build_merge_tab(self):
        self.merge_files = []
        
        lbl_info = ttk.Label(self.content_frame, text="步驟 1：新增需要合併的 PDF 檔案，並調整排列順序。")
        lbl_info.pack(anchor="w", padx=15, pady=10)
        
        list_frame = ttk.Frame(self.content_frame)
        list_frame.pack(fill="both", expand=True, padx=15, pady=5)
        
        self.merge_listbox = tk.Listbox(list_frame, height=8, selectmode="single")
        self.merge_listbox.pack(side="left", fill="both", expand=True)
        
        scroll = ttk.Scrollbar(list_frame, orient="vertical", command=self.merge_listbox.yview)
        self.merge_listbox.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        
        ctrl_frame = ttk.Frame(self.content_frame)
        ctrl_frame.pack(fill="x", padx=15, pady=5)
        
        ttk.Button(ctrl_frame, text="新增檔案", command=self.merge_add_file).pack(side="left", padx=2)
        ttk.Button(ctrl_frame, text="移除選定", command=self.merge_remove_file).pack(side="left", padx=2)
        ttk.Button(ctrl_frame, text="上移", command=self.merge_move_up).pack(side="left", padx=2)
        ttk.Button(ctrl_frame, text="下移", command=self.merge_move_down).pack(side="left", padx=2)
        
        out_frame = ttk.Frame(self.content_frame)
        out_frame.pack(fill="x", padx=15, pady=10)
        
        ttk.Label(out_frame, text="輸出路徑：").pack(side="left")
        self.merge_out_var = tk.StringVar()
        self.merge_out_entry = ttk.Entry(out_frame, textvariable=self.merge_out_var, width=40)
        self.merge_out_entry.pack(side="left", fill="x", expand=True, padx=5)
        ttk.Button(out_frame, text="瀏覽...", command=self.merge_browse_output).pack(side="left")
        
        self.merge_exec_btn = ttk.Button(self.content_frame, text="執行合併", command=self.execute_merge)
        self.merge_exec_btn.pack(anchor="w", padx=15, pady=10)

    def merge_add_file(self):
        paths = filedialog.askopenfilenames(filetypes=[("PDF 檔案", "*.pdf")])
        for p in paths:
            ap = os.path.abspath(p)
            if ap not in self.merge_files:
                self.merge_files.append(ap)
                self.merge_listbox.insert("end", os.path.basename(ap))
                
    def merge_remove_file(self):
        sel = self.merge_listbox.curselection()
        if sel:
            idx = sel[0]
            self.merge_listbox.delete(idx)
            self.merge_files.pop(idx)
            
    def merge_move_up(self):
        sel = self.merge_listbox.curselection()
        if sel and sel[0] > 0:
            idx = sel[0]
            self.merge_files[idx], self.merge_files[idx-1] = self.merge_files[idx-1], self.merge_files[idx]
            val = self.merge_listbox.get(idx)
            self.merge_listbox.delete(idx)
            self.merge_listbox.insert(idx-1, val)
            self.merge_listbox.selection_set(idx-1)
            
    def merge_move_down(self):
        sel = self.merge_listbox.curselection()
        if sel and sel[0] < len(self.merge_files) - 1:
            idx = sel[0]
            self.merge_files[idx], self.merge_files[idx+1] = self.merge_files[idx+1], self.merge_files[idx]
            val = self.merge_listbox.get(idx)
            self.merge_listbox.delete(idx)
            self.merge_listbox.insert(idx+1, val)
            self.merge_listbox.selection_set(idx+1)
            
    def merge_browse_output(self):
        path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF 檔案", "*.pdf")])
        if path:
            self.merge_out_var.set(os.path.abspath(path))

    def execute_merge(self):
        if len(self.merge_files) < 2:
            messagebox.showerror("檔案不足", "請至少新增 2 個 PDF 檔案再執行合併！", parent=self)
            return
        out_path = self.merge_out_var.get()
        if not out_path:
            messagebox.showerror("路徑未指定", "請選擇合併後的 PDF 儲存路徑！", parent=self)
            return
            
        self.is_running = True
        self.merge_exec_btn.config(state="disabled")
        
        import threading
        threading.Thread(target=self._merge_worker, args=(out_path,), daemon=True).start()
        
    def _merge_worker(self, out_path):
        success = False
        error_msg = ""
        try:
            doc_out = fitz.open()
            for filepath in self.merge_files:
                doc_in = fitz.open(filepath)
                doc_out.insert_pdf(doc_in)
                doc_in.close()
            doc_out.save(out_path)
            doc_out.close()
            success = True
        except Exception as e:
            error_msg = str(e)
            
        def finish():
            self.is_running = False
            self.merge_exec_btn.config(state="normal")
            if success:
                messagebox.showinfo("完成", f"PDF 合併成功！\n已儲存至：\n{out_path}", parent=self)
                self.merge_files.clear()
                self.merge_listbox.delete(0, "end")
                self.merge_out_var.set("")
            else:
                messagebox.showerror("合併失敗", f"合併 PDF 檔案時出錯：\n{error_msg}", parent=self)
        self.after(0, finish)

    # --- Tab 2: Split & Extract ---
    def build_split_tab(self):
        self.split_in_var = tk.StringVar()
        self.split_pages_var = tk.StringVar(value="1")
        self.split_out_var = tk.StringVar()
        
        in_frame = ttk.LabelFrame(self.content_frame, text=" 步驟 1：選擇來源 PDF ")
        in_frame.pack(fill="x", padx=15, pady=10)
        self.split_in_entry = ttk.Entry(in_frame, textvariable=self.split_in_var, width=45)
        self.split_in_entry.pack(side="left", fill="x", expand=True, padx=5, pady=10)
        ttk.Button(in_frame, text="瀏覽...", command=self.split_browse_input).pack(side="left", padx=5)
        
        page_frame = ttk.LabelFrame(self.content_frame, text=" 步驟 2：設定提取頁碼範圍 ")
        page_frame.pack(fill="x", padx=15, pady=5)
        ttk.Label(page_frame, text="輸入頁碼範圍範例：1-3, 5-8 (1-based)\n輸入 'all' 代表全部單頁拆分").pack(anchor="w", padx=10, pady=5)
        self.split_pages_entry = ttk.Entry(page_frame, textvariable=self.split_pages_var, width=30)
        self.split_pages_entry.pack(fill="x", padx=10, pady=10)
        
        out_frame = ttk.LabelFrame(self.content_frame, text=" 步驟 3：選擇儲存資料夾 ")
        out_frame.pack(fill="x", padx=15, pady=10)
        self.split_out_entry = ttk.Entry(out_frame, textvariable=self.split_out_var, width=45)
        self.split_out_entry.pack(side="left", fill="x", expand=True, padx=5, pady=10)
        ttk.Button(out_frame, text="瀏覽...", command=self.split_browse_output).pack(side="left", padx=5)
        
        self.split_exec_btn = ttk.Button(self.content_frame, text="執行提取/拆分", command=self.execute_split)
        self.split_exec_btn.pack(anchor="w", padx=15, pady=10)

    def split_browse_input(self):
        path = filedialog.askopenfilename(filetypes=[("PDF 檔案", "*.pdf")])
        if path:
            self.split_in_var.set(os.path.abspath(path))
            
    def split_browse_output(self):
        path = filedialog.askdirectory()
        if path:
            self.split_out_var.set(os.path.abspath(path))

    def parse_page_ranges(self, range_str, total_pages):
        pages = []
        if range_str.lower().strip() == "all":
            return list(range(total_pages))
            
        parts = range_str.split(",")
        for part in parts:
            part = part.strip()
            if "-" in part:
                subparts = part.split("-")
                start = int(subparts[0].strip()) - 1
                end = int(subparts[1].strip()) - 1
                start = max(0, min(start, total_pages - 1))
                end = max(0, min(end, total_pages - 1))
                if start <= end:
                    pages.extend(list(range(start, end + 1)))
                else:
                    pages.extend(list(range(start, end - 1, -1)))
            else:
                p = int(part) - 1
                p = max(0, min(p, total_pages - 1))
                pages.append(p)
        return pages

    def execute_split(self):
        in_path = self.split_in_var.get()
        pages_str = self.split_pages_var.get().strip()
        out_dir = self.split_out_var.get()
        
        if not in_path or not os.path.isfile(in_path):
            messagebox.showerror("錯誤", "請先選擇有效的來源 PDF 檔案！", parent=self)
            return
        if not pages_str:
            messagebox.showerror("錯誤", "請輸入提取頁碼範圍！", parent=self)
            return
        if not out_dir or not os.path.isdir(out_dir):
            messagebox.showerror("錯誤", "請先選擇有效的儲存資料夾！", parent=self)
            return
            
        self.is_running = True
        self.split_exec_btn.config(state="disabled")
        
        import threading
        threading.Thread(target=self._split_worker, args=(in_path, pages_str, out_dir), daemon=True).start()
        
    def _split_worker(self, in_path, pages_str, out_dir):
        success = False
        error_msg = ""
        try:
            doc_in = fitz.open(in_path)
            total = len(doc_in)
            
            if pages_str.lower() == "all":
                for i in range(total):
                    doc_single = fitz.open()
                    doc_single.insert_pdf(doc_in, from_page=i, to_page=i)
                    out_filename = f"{os.path.splitext(os.path.basename(in_path))[0]}_page_{i+1}.pdf"
                    doc_single.save(os.path.join(out_dir, out_filename))
                    doc_single.close()
                success = True
            else:
                page_indices = self.parse_page_ranges(pages_str, total)
                if page_indices:
                    doc_out = fitz.open()
                    for idx in page_indices:
                        doc_out.insert_pdf(doc_in, from_page=idx, to_page=idx)
                    out_filename = f"{os.path.splitext(os.path.basename(in_path))[0]}_extracted.pdf"
                    doc_out.save(os.path.join(out_dir, out_filename))
                    doc_out.close()
                    success = True
                else:
                    error_msg = "解譯出的頁碼範圍無效！"
            doc_in.close()
        except Exception as e:
            error_msg = str(e)
            
        def finish():
            self.is_running = False
            self.split_exec_btn.config(state="normal")
            if success:
                messagebox.showinfo("完成", f"PDF 拆分/提取作業成功！\n已儲存至：\n{out_dir}", parent=self)
                self.split_in_var.set("")
                self.split_out_var.set("")
            else:
                messagebox.showerror("失敗", f"拆分出錯：\n{error_msg}", parent=self)
        self.after(0, finish)

    # --- Tab 3: Encryption/Decryption ---
    def build_encrypt_tab(self):
        self.enc_in_var = tk.StringVar()
        self.enc_pwd_var = tk.StringVar()
        self.dec_pwd_var = tk.StringVar()
        self.enc_out_var = tk.StringVar()
        
        in_frame = ttk.LabelFrame(self.content_frame, text=" 步驟 1：選擇來源 PDF ")
        in_frame.pack(fill="x", padx=15, pady=10)
        self.enc_in_entry = ttk.Entry(in_frame, textvariable=self.enc_in_var, width=45)
        self.enc_in_entry.pack(side="left", fill="x", expand=True, padx=5, pady=10)
        ttk.Button(in_frame, text="瀏覽...", command=self.enc_browse_input).pack(side="left", padx=5)
        
        config_frame = ttk.LabelFrame(self.content_frame, text=" 步驟 2：設定密碼操作 ")
        config_frame.pack(fill="x", padx=15, pady=5)
        
        ttk.Label(config_frame, text="設定加密密碼（若要加密檔案）：").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        self.enc_pwd_entry = ttk.Entry(config_frame, textvariable=self.enc_pwd_var, width=20, show="*")
        self.enc_pwd_entry.grid(row=0, column=1, sticky="w", padx=5, pady=5)
        
        ttk.Label(config_frame, text="輸入現有密碼（若要解密檔案）：").grid(row=1, column=0, sticky="e", padx=5, pady=5)
        self.dec_pwd_entry = ttk.Entry(config_frame, textvariable=self.dec_pwd_var, width=20, show="*")
        self.dec_pwd_entry.grid(row=1, column=1, sticky="w", padx=5, pady=5)
        
        out_frame = ttk.LabelFrame(self.content_frame, text=" 步驟 3：選擇輸出 PDF 路徑 ")
        out_frame.pack(fill="x", padx=15, pady=10)
        self.enc_out_entry = ttk.Entry(out_frame, textvariable=self.enc_out_var, width=45)
        self.enc_out_entry.pack(side="left", fill="x", expand=True, padx=5, pady=10)
        ttk.Button(out_frame, text="瀏覽...", command=self.enc_browse_output).pack(side="left", padx=5)
        
        action_frame = ttk.Frame(self.content_frame)
        action_frame.pack(fill="x", padx=15, pady=10)
        
        self.enc_exec_btn = ttk.Button(action_frame, text="執行加密", command=lambda: self.execute_encrypt_decrypt(True))
        self.enc_exec_btn.pack(side="left", padx=5)
        
        self.dec_exec_btn = ttk.Button(action_frame, text="執行解密", command=lambda: self.execute_encrypt_decrypt(False))
        self.dec_exec_btn.pack(side="left", padx=5)

    def enc_browse_input(self):
        path = filedialog.askopenfilename(filetypes=[("PDF 檔案", "*.pdf")])
        if path:
            self.enc_in_var.set(os.path.abspath(path))
            
    def enc_browse_output(self):
        path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF 檔案", "*.pdf")])
        if path:
            self.enc_out_var.set(os.path.abspath(path))

    def execute_encrypt_decrypt(self, is_encrypt):
        in_path = self.enc_in_var.get()
        out_path = self.enc_out_var.get()
        enc_pwd = self.enc_pwd_var.get()
        dec_pwd = self.dec_pwd_var.get()
        
        if not in_path or not os.path.isfile(in_path):
            messagebox.showerror("錯誤", "請選擇有效的來源 PDF 檔案！", parent=self)
            return
        if not out_path:
            messagebox.showerror("錯誤", "請選擇輸出的 PDF 儲存路徑！", parent=self)
            return
            
        if is_encrypt and not enc_pwd:
            messagebox.showerror("錯誤", "加密請設定加密密碼！", parent=self)
            return
        if not is_encrypt and not dec_pwd:
            messagebox.showerror("錯誤", "解密請輸入現有密碼！", parent=self)
            return
            
        self.is_running = True
        self.enc_exec_btn.config(state="disabled")
        self.dec_exec_btn.config(state="disabled")
        
        import threading
        threading.Thread(target=self._encrypt_worker, args=(in_path, out_path, is_encrypt, enc_pwd, dec_pwd), daemon=True).start()
        
    def _encrypt_worker(self, in_path, out_path, is_encrypt, enc_pwd, dec_pwd):
        success = False
        error_msg = ""
        try:
            doc = fitz.open(in_path)
            
            if doc.is_encrypted:
                auth = doc.authenticate(dec_pwd)
                if not auth:
                    raise Exception("現有密碼不正確，無法開啟 PDF！")
                    
            if is_encrypt:
                doc.save(out_path, encryption=fitz.PDF_ENCRYPT_AES_256, user_pw=enc_pwd, owner_pw=enc_pwd)
                success = True
            else:
                doc.save(out_path)
                success = True
            doc.close()
        except Exception as e:
            error_msg = str(e)
            
        def finish():
            self.is_running = False
            self.enc_exec_btn.config(state="normal")
            self.dec_exec_btn.config(state="normal")
            if success:
                action = "加密" if is_encrypt else "解密"
                messagebox.showinfo("完成", f"PDF {action}作業成功！\n儲存至：\n{out_path}", parent=self)
                self.enc_in_var.set("")
                self.enc_pwd_var.set("")
                self.dec_pwd_var.set("")
                self.enc_out_var.set("")
            else:
                messagebox.showerror("失敗", f"密碼操作失敗：\n{error_msg}", parent=self)
        self.after(0, finish)

    # --- Tab 4: Rotate Pages ---
    def build_rotate_tab(self):
        self.rot_in_var = tk.StringVar()
        self.rot_pages_var = tk.StringVar(value="1")
        self.rot_angle_var = tk.StringVar(value="90")
        self.rot_out_var = tk.StringVar()
        
        in_frame = ttk.LabelFrame(self.content_frame, text=" 步驟 1：選擇來源 PDF ")
        in_frame.pack(fill="x", padx=15, pady=10)
        self.rot_in_entry = ttk.Entry(in_frame, textvariable=self.rot_in_var, width=45)
        self.rot_in_entry.pack(side="left", fill="x", expand=True, padx=5, pady=10)
        ttk.Button(in_frame, text="瀏覽...", command=self.rot_browse_input).pack(side="left", padx=5)
        
        config_frame = ttk.LabelFrame(self.content_frame, text=" 步驟 2：設定旋轉頁面與角度 ")
        config_frame.pack(fill="x", padx=15, pady=5)
        
        ttk.Label(config_frame, text="設定旋轉頁碼範圍 (例如 1-3, 5 或 all)：").pack(anchor="w", padx=10, pady=5)
        self.rot_pages_entry = ttk.Entry(config_frame, textvariable=self.rot_pages_var, width=30)
        self.rot_pages_entry.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(config_frame, text="選擇順時針旋轉角度：").pack(anchor="w", padx=10, pady=5)
        angle_cb = ttk.Combobox(config_frame, textvariable=self.rot_angle_var, values=["90", "180", "270"], state="readonly")
        angle_cb.pack(anchor="w", padx=10, pady=5)
        
        out_frame = ttk.LabelFrame(self.content_frame, text=" 步驟 3：選擇輸出 PDF 路徑 ")
        out_frame.pack(fill="x", padx=15, pady=10)
        self.rot_out_entry = ttk.Entry(out_frame, textvariable=self.rot_out_var, width=45)
        self.rot_out_entry.pack(side="left", fill="x", expand=True, padx=5, pady=10)
        ttk.Button(out_frame, text="瀏覽...", command=self.rot_browse_output).pack(side="left", padx=5)
        
        self.rot_exec_btn = ttk.Button(self.content_frame, text="執行旋轉頁面", command=self.execute_rotate)
        self.rot_exec_btn.pack(anchor="w", padx=15, pady=10)

    def rot_browse_input(self):
        path = filedialog.askopenfilename(filetypes=[("PDF 檔案", "*.pdf")])
        if path:
            self.rot_in_var.set(os.path.abspath(path))
            
    def rot_browse_output(self):
        path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF 檔案", "*.pdf")])
        if path:
            self.rot_out_var.set(os.path.abspath(path))

    def execute_rotate(self):
        in_path = self.rot_in_var.get()
        pages_str = self.rot_pages_var.get().strip()
        angle = self.rot_angle_var.get()
        out_path = self.rot_out_var.get()
        
        if not in_path or not os.path.isfile(in_path):
            messagebox.showerror("錯誤", "請選擇有效的來源 PDF 檔案！", parent=self)
            return
        if not pages_str:
            messagebox.showerror("錯誤", "請指定旋轉頁碼範圍！", parent=self)
            return
        if not out_path:
            messagebox.showerror("錯誤", "請指定輸出 PDF 儲存路徑！", parent=self)
            return
            
        self.is_running = True
        self.rot_exec_btn.config(state="disabled")
        
        import threading
        threading.Thread(target=self._rotate_worker, args=(in_path, pages_str, angle, out_path), daemon=True).start()
        
    def _rotate_worker(self, in_path, pages_str, angle, out_path):
        success = False
        error_msg = ""
        try:
            doc = fitz.open(in_path)
            total = len(doc)
            page_indices = self.parse_page_ranges(pages_str, total)
            
            deg = int(angle)
            for idx in page_indices:
                page = doc[idx]
                curr_rot = page.rotation
                new_rot = (curr_rot + deg) % 360
                page.set_rotation(new_rot)
                
            doc.save(out_path)
            doc.close()
            success = True
        except Exception as e:
            error_msg = str(e)
            
        def finish():
            self.is_running = False
            self.rot_exec_btn.config(state="normal")
            if success:
                messagebox.showinfo("完成", f"PDF 頁面旋轉成功！\n儲存至：\n{out_path}", parent=self)
                self.rot_in_var.set("")
                self.rot_out_var.set("")
            else:
                messagebox.showerror("失敗", f"頁面旋轉失敗：\n{error_msg}", parent=self)
        self.after(0, finish)

    # --- Tab 5: PDF to Images ---
    def build_to_image_tab(self):
        self.img_in_var = tk.StringVar()
        self.img_format_var = tk.StringVar(value="PNG")
        self.img_dpi_var = tk.StringVar(value="150")
        self.img_out_var = tk.StringVar()
        
        in_frame = ttk.LabelFrame(self.content_frame, text=" 步驟 1：選擇來源 PDF ")
        in_frame.pack(fill="x", padx=15, pady=10)
        self.img_in_entry = ttk.Entry(in_frame, textvariable=self.img_in_var, width=45)
        self.img_in_entry.pack(side="left", fill="x", expand=True, padx=5, pady=10)
        ttk.Button(in_frame, text="瀏覽...", command=self.img_browse_input).pack(side="left", padx=5)
        
        config_frame = ttk.LabelFrame(self.content_frame, text=" 步驟 2：設定輸出格式與解析度 (DPI) ")
        config_frame.pack(fill="x", padx=15, pady=5)
        
        ttk.Label(config_frame, text="輸出圖片格式：").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        fmt_cb = ttk.Combobox(config_frame, textvariable=self.img_format_var, values=["PNG", "JPG"], state="readonly")
        fmt_cb.grid(row=0, column=1, sticky="w", padx=5, pady=5)
        
        ttk.Label(config_frame, text="DPI 解析度 (推薦 150/300)：").grid(row=1, column=0, sticky="e", padx=5, pady=5)
        dpi_cb = ttk.Combobox(config_frame, textvariable=self.img_dpi_var, values=["150", "300"], state="readonly")
        dpi_cb.grid(row=1, column=1, sticky="w", padx=5, pady=5)
        
        out_frame = ttk.LabelFrame(self.content_frame, text=" 步驟 3：選擇儲存圖片資料夾 ")
        out_frame.pack(fill="x", padx=15, pady=10)
        self.img_out_entry = ttk.Entry(out_frame, textvariable=self.img_out_var, width=45)
        self.img_out_entry.pack(side="left", fill="x", expand=True, padx=5, pady=10)
        ttk.Button(out_frame, text="瀏覽...", command=self.img_browse_output).pack(side="left", padx=5)
        
        self.img_exec_btn = ttk.Button(self.content_frame, text="執行轉換為圖片", command=self.execute_to_image)
        self.img_exec_btn.pack(anchor="w", padx=15, pady=10)

    def img_browse_input(self):
        path = filedialog.askopenfilename(filetypes=[("PDF 檔案", "*.pdf")])
        if path:
            self.img_in_var.set(os.path.abspath(path))
            
    def img_browse_output(self):
        path = filedialog.askdirectory()
        if path:
            self.img_out_var.set(os.path.abspath(path))

    def execute_to_image(self):
        in_path = self.img_in_var.get()
        fmt = self.img_format_var.get().lower()
        dpi_str = self.img_dpi_var.get()
        out_dir = self.img_out_var.get()
        
        if not in_path or not os.path.isfile(in_path):
            messagebox.showerror("錯誤", "請選擇有效的來源 PDF 檔案！", parent=self)
            return
        if not out_dir or not os.path.isdir(out_dir):
            messagebox.showerror("錯誤", "請選擇有效的圖片儲存資料夾！", parent=self)
            return
            
        self.is_running = True
        self.img_exec_btn.config(state="disabled")
        
        import threading
        threading.Thread(target=self._to_image_worker, args=(in_path, fmt, dpi_str, out_dir), daemon=True).start()
        
    def _to_image_worker(self, in_path, fmt, dpi_str, out_dir):
        success = False
        error_msg = ""
        try:
            doc = fitz.open(in_path)
            dpi = int(dpi_str)
            zoom = dpi / 72.0
            matrix = fitz.Matrix(zoom, zoom)
            
            base_name = os.path.splitext(os.path.basename(in_path))[0]
            
            for i, page in enumerate(doc):
                pix = page.get_pixmap(matrix=matrix)
                out_name = f"{base_name}_page_{i+1}.{fmt}"
                pix.save(os.path.join(out_dir, out_name))
            doc.close()
            success = True
        except Exception as e:
            error_msg = str(e)
            
        def finish():
            self.is_running = False
            self.img_exec_btn.config(state="normal")
            if success:
                messagebox.showinfo("完成", f"PDF 頁面轉圖片成功！\n已匯出至：\n{out_dir}", parent=self)
                self.img_in_var.set("")
                self.img_out_var.set("")
            else:
                messagebox.showerror("失敗", f"轉換為圖片失敗：\n{error_msg}", parent=self)
        self.after(0, finish)

    # --- Tab 6: Extract Assets ---
    def build_extract_assets_tab(self):
        self.ext_in_var = tk.StringVar()
        self.ext_text_var = tk.BooleanVar(value=True)
        self.ext_img_var = tk.BooleanVar(value=True)
        self.ext_out_var = tk.StringVar()
        
        in_frame = ttk.LabelFrame(self.content_frame, text=" 步驟 1：選擇來源 PDF ")
        in_frame.pack(fill="x", padx=15, pady=10)
        self.ext_in_entry = ttk.Entry(in_frame, textvariable=self.ext_in_var, width=45)
        self.ext_in_entry.pack(side="left", fill="x", expand=True, padx=5, pady=10)
        ttk.Button(in_frame, text="瀏覽...", command=self.ext_browse_input).pack(side="left", padx=5)
        
        config_frame = ttk.LabelFrame(self.content_frame, text=" 步驟 2：選擇提取標的 ")
        config_frame.pack(fill="x", padx=15, pady=5)
        
        self.chk_ext_text = ttk.Checkbutton(config_frame, text="提取文字內容為 TXT 文件", variable=self.ext_text_var)
        self.chk_ext_text.pack(anchor="w", padx=15, pady=8)
        
        self.chk_ext_img = ttk.Checkbutton(config_frame, text="提取內建嵌入的原始圖片素材 (JPG/PNG)", variable=self.ext_img_var)
        self.chk_ext_img.pack(anchor="w", padx=15, pady=8)
        
        out_frame = ttk.LabelFrame(self.content_frame, text=" 步驟 3：選擇提取儲存資料夾 ")
        out_frame.pack(fill="x", padx=15, pady=10)
        self.ext_out_entry = ttk.Entry(out_frame, textvariable=self.ext_out_var, width=45)
        self.ext_out_entry.pack(side="left", fill="x", expand=True, padx=5, pady=10)
        ttk.Button(out_frame, text="瀏覽...", command=self.ext_browse_output).pack(side="left", padx=5)
        
        self.ext_exec_btn = ttk.Button(self.content_frame, text="執行素材提取", command=self.execute_extract)
        self.ext_exec_btn.pack(anchor="w", padx=15, pady=10)

    def ext_browse_input(self):
        path = filedialog.askopenfilename(filetypes=[("PDF 檔案", "*.pdf")])
        if path:
            self.ext_in_var.set(os.path.abspath(path))
            
    def ext_browse_output(self):
        path = filedialog.askdirectory()
        if path:
            self.ext_out_var.set(os.path.abspath(path))

    def execute_extract(self):
        in_path = self.ext_in_var.get()
        ext_text = self.ext_text_var.get()
        ext_img = self.ext_img_var.get()
        out_dir = self.ext_out_var.get()
        
        if not in_path or not os.path.isfile(in_path):
            messagebox.showerror("錯誤", "請選擇有效的來源 PDF 檔案！", parent=self)
            return
        if not ext_text and not ext_img:
            messagebox.showwarning("警告", "請至少勾選一項提取標的！", parent=self)
            return
        if not out_dir or not os.path.isdir(out_dir):
            messagebox.showerror("錯誤", "請選擇有效的提取儲存資料夾！", parent=self)
            return
            
        self.is_running = True
        self.ext_exec_btn.config(state="disabled")
        
        import threading
        threading.Thread(target=self._extract_worker, args=(in_path, ext_text, ext_img, out_dir), daemon=True).start()
        
    def _extract_worker(self, in_path, ext_text, ext_img, out_dir):
        success = False
        error_msg = ""
        try:
            doc = fitz.open(in_path)
            base_name = os.path.splitext(os.path.basename(in_path))[0]
            
            if ext_text:
                full_text = []
                for i, page in enumerate(doc):
                    full_text.append(f"--- Page {i+1} ---\n" + page.get_text())
                txt_path = os.path.join(out_dir, f"{base_name}_extracted_text.txt")
                with open(txt_path, "w", encoding="utf-8") as f:
                    f.write("\n\n".join(full_text))
                    
            if ext_img:
                img_count = 1
                for page_idx in range(len(doc)):
                    img_list = doc.get_page_images(page_idx)
                    for img in img_list:
                        xref = img[0]
                        base_image = doc.extract_image(xref)
                        image_bytes = base_image["image"]
                        image_ext = base_image["ext"]
                        img_name = f"{base_name}_extracted_img_{img_count}.{image_ext}"
                        with open(os.path.join(out_dir, img_name), "wb") as f:
                            f.write(image_bytes)
                        img_count += 1
                        
            doc.close()
            success = True
        except Exception as e:
            error_msg = str(e)
            
        def finish():
            self.is_running = False
            self.ext_exec_btn.config(state="normal")
            if success:
                messagebox.showinfo("完成", f"PDF 素材提取成功！\n已儲存至：\n{out_dir}", parent=self)
                self.ext_in_var.set("")
                self.ext_out_var.set("")
            else:
                messagebox.showerror("失敗", f"提取素材時出錯：\n{error_msg}", parent=self)
        self.after(0, finish)

    # --- Tab 7: Watermark ---
    def build_watermark_tab(self):
        self.wm_in_var = tk.StringVar()
        self.wm_text_var = tk.StringVar(value="僅供內部審閱 CONFIDENTIAL")
        self.wm_opacity_var = tk.StringVar(value="0.3")
        self.wm_out_var = tk.StringVar()
        
        in_frame = ttk.LabelFrame(self.content_frame, text=" 步驟 1：選擇來源 PDF ")
        in_frame.pack(fill="x", padx=15, pady=10)
        self.wm_in_entry = ttk.Entry(in_frame, textvariable=self.wm_in_var, width=45)
        self.wm_in_entry.pack(side="left", fill="x", expand=True, padx=5, pady=10)
        ttk.Button(in_frame, text="瀏覽...", command=self.wm_browse_input).pack(side="left", padx=5)
        
        config_frame = ttk.LabelFrame(self.content_frame, text=" 步驟 2：設定浮水印字串與透明度 ")
        config_frame.pack(fill="x", padx=15, pady=5)
        
        ttk.Label(config_frame, text="文字浮水印內容：").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        self.wm_text_entry = ttk.Entry(config_frame, textvariable=self.wm_text_var, width=30)
        self.wm_text_entry.grid(row=0, column=1, sticky="w", padx=5, pady=5)
        
        ttk.Label(config_frame, text="透明度 (0.1 至 1.0，預設 0.3)：").grid(row=1, column=0, sticky="e", padx=5, pady=5)
        self.wm_opacity_entry = ttk.Entry(config_frame, textvariable=self.wm_opacity_var, width=10)
        self.wm_opacity_entry.grid(row=1, column=1, sticky="w", padx=5, pady=5)
        
        out_frame = ttk.LabelFrame(self.content_frame, text=" 步驟 3：選擇輸出 PDF 儲存路徑 ")
        out_frame.pack(fill="x", padx=15, pady=10)
        self.wm_out_entry = ttk.Entry(out_frame, textvariable=self.wm_out_var, width=45)
        self.wm_out_entry.pack(side="left", fill="x", expand=True, padx=5, pady=10)
        ttk.Button(out_frame, text="瀏覽...", command=self.wm_browse_output).pack(side="left", padx=5)
        
        self.wm_exec_btn = ttk.Button(self.content_frame, text="執行加入浮水印", command=self.execute_watermark)
        self.wm_exec_btn.pack(anchor="w", padx=15, pady=10)

    def wm_browse_input(self):
        path = filedialog.askopenfilename(filetypes=[("PDF 檔案", "*.pdf")])
        if path:
            self.wm_in_var.set(os.path.abspath(path))
            
    def wm_browse_output(self):
        path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF 檔案", "*.pdf")])
        if path:
            self.wm_out_var.set(os.path.abspath(path))

    def execute_watermark(self):
        in_path = self.wm_in_var.get()
        wm_text = self.wm_text_var.get()
        opacity_str = self.wm_opacity_var.get()
        out_path = self.wm_out_var.get()
        
        if not in_path or not os.path.isfile(in_path):
            messagebox.showerror("錯誤", "請選擇有效的來源 PDF 檔案！", parent=self)
            return
        if not wm_text:
            messagebox.showerror("錯誤", "請輸入浮水印字串！", parent=self)
            return
            
        try:
            opacity = float(opacity_str)
            if not (0.01 <= opacity <= 1.0):
                raise ValueError
        except ValueError:
            messagebox.showerror("參數錯誤", "透明度必須在 0.1 與 1.0 之間！", parent=self)
            return
            
        if not out_path:
            messagebox.showerror("錯誤", "請選擇輸出的 PDF 儲存路徑！", parent=self)
            return
            
        self.is_running = True
        self.wm_exec_btn.config(state="disabled")
        
        import threading
        threading.Thread(target=self._watermark_worker, args=(in_path, wm_text, opacity, out_path), daemon=True).start()
        
    def _watermark_worker(self, in_path, wm_text, opacity, out_path):
        success = False
        error_msg = ""
        try:
            doc = fitz.open(in_path)
            for page in doc:
                rect = page.rect
                width, height = rect.width, rect.height
                text_rect = fitz.Rect(50, height/2 - 100, width - 50, height/2 + 100)
                
                page.insert_textbox(
                    text_rect,
                    wm_text,
                    fontsize=36,
                    fontname="helv",
                    color=(0.7, 0.7, 0.7),
                    fill_opacity=opacity,
                    align=fitz.TEXT_ALIGN_CENTER
                )
                
            doc.save(out_path)
            doc.close()
            success = True
        except Exception as e:
            error_msg = str(e)
            
        def finish():
            self.is_running = False
            self.wm_exec_btn.config(state="normal")
            if success:
                messagebox.showinfo("完成", f"加入浮水印作業成功！\n儲存至：\n{out_path}", parent=self)
                self.wm_in_var.set("")
                self.wm_out_var.set("")
            else:
                messagebox.showerror("失敗", f"加水印失敗：\n{error_msg}", parent=self)
        self.after(0, finish)

    # --- Tab 8: Images to PDF ---
    def build_images_to_pdf_tab(self):
        self.imgpdf_files = []
        
        lbl_info = ttk.Label(self.content_frame, text="步驟 1：新增需要合併的 JPG/PNG 圖片，並調整排列順序。")
        lbl_info.pack(anchor="w", padx=15, pady=10)
        
        list_frame = ttk.Frame(self.content_frame)
        list_frame.pack(fill="both", expand=True, padx=15, pady=5)
        
        self.imgpdf_listbox = tk.Listbox(list_frame, height=8, selectmode="single")
        self.imgpdf_listbox.pack(side="left", fill="both", expand=True)
        
        scroll = ttk.Scrollbar(list_frame, orient="vertical", command=self.imgpdf_listbox.yview)
        self.imgpdf_listbox.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        
        ctrl_frame = ttk.Frame(self.content_frame)
        ctrl_frame.pack(fill="x", padx=15, pady=5)
        
        ttk.Button(ctrl_frame, text="新增圖片", command=self.imgpdf_add_file).pack(side="left", padx=2)
        ttk.Button(ctrl_frame, text="移除選定", command=self.imgpdf_remove_file).pack(side="left", padx=2)
        ttk.Button(ctrl_frame, text="上移", command=self.imgpdf_move_up).pack(side="left", padx=2)
        ttk.Button(ctrl_frame, text="下移", command=self.imgpdf_move_down).pack(side="left", padx=2)
        
        out_frame = ttk.Frame(self.content_frame)
        out_frame.pack(fill="x", padx=15, pady=10)
        
        ttk.Label(out_frame, text="輸出 PDF 路徑：").pack(side="left")
        self.imgpdf_out_var = tk.StringVar()
        self.imgpdf_out_entry = ttk.Entry(out_frame, textvariable=self.imgpdf_out_var, width=40)
        self.imgpdf_out_entry.pack(side="left", fill="x", expand=True, padx=5)
        ttk.Button(out_frame, text="瀏覽...", command=self.imgpdf_browse_output).pack(side="left")
        
        self.imgpdf_exec_btn = ttk.Button(self.content_frame, text="執行轉換為 PDF", command=self.execute_images_to_pdf)
        self.imgpdf_exec_btn.pack(anchor="w", padx=15, pady=10)

    def imgpdf_add_file(self):
        paths = filedialog.askopenfilenames(filetypes=[("圖片檔案", "*.jpg;*.jpeg;*.png")])
        for p in paths:
            ap = os.path.abspath(p)
            if ap not in self.imgpdf_files:
                self.imgpdf_files.append(ap)
                self.imgpdf_listbox.insert("end", os.path.basename(ap))
                
    def imgpdf_remove_file(self):
        sel = self.imgpdf_listbox.curselection()
        if sel:
            idx = sel[0]
            self.imgpdf_listbox.delete(idx)
            self.imgpdf_files.pop(idx)
            
    def imgpdf_move_up(self):
        sel = self.imgpdf_listbox.curselection()
        if sel and sel[0] > 0:
            idx = sel[0]
            self.imgpdf_files[idx], self.imgpdf_files[idx-1] = self.imgpdf_files[idx-1], self.imgpdf_files[idx]
            val = self.imgpdf_listbox.get(idx)
            self.imgpdf_listbox.delete(idx)
            self.imgpdf_listbox.insert(idx-1, val)
            self.imgpdf_listbox.selection_set(idx-1)
            
    def imgpdf_move_down(self):
        sel = self.imgpdf_listbox.curselection()
        if sel and sel[0] < len(self.imgpdf_files) - 1:
            idx = sel[0]
            self.imgpdf_files[idx], self.imgpdf_files[idx+1] = self.imgpdf_files[idx+1], self.imgpdf_files[idx]
            val = self.imgpdf_listbox.get(idx)
            self.imgpdf_listbox.delete(idx)
            self.imgpdf_listbox.insert(idx+1, val)
            self.imgpdf_listbox.selection_set(idx+1)
            
    def imgpdf_browse_output(self):
        path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF 檔案", "*.pdf")])
        if path:
            self.imgpdf_out_var.set(os.path.abspath(path))

    def execute_images_to_pdf(self):
        if len(self.imgpdf_files) == 0:
            messagebox.showerror("檔案不足", "請至少新增 1 張圖片進行轉換！", parent=self)
            return
        out_path = self.imgpdf_out_var.get()
        if not out_path:
            messagebox.showerror("路徑未指定", "請指定輸出 PDF 儲存路徑！", parent=self)
            return
            
        self.is_running = True
        self.imgpdf_exec_btn.config(state="disabled")
        
        import threading
        threading.Thread(target=self._images_to_pdf_worker, args=(out_path,), daemon=True).start()
        
    def _images_to_pdf_worker(self, out_path):
        success = False
        error_msg = ""
        try:
            doc_out = fitz.open()
            for filepath in self.imgpdf_files:
                img_doc = fitz.open(filepath)
                pdf_bytes = img_doc.convert_to_pdf()
                img_doc.close()
                
                img_pdf = fitz.open("pdf", pdf_bytes)
                doc_out.insert_pdf(img_pdf)
                img_pdf.close()
                
            doc_out.save(out_path)
            doc_out.close()
            success = True
        except Exception as e:
            error_msg = str(e)
            
        def finish():
            self.is_running = False
            self.imgpdf_exec_btn.config(state="normal")
            if success:
                messagebox.showinfo("完成", f"圖片轉 PDF 成功！\n儲存至：\n{out_path}", parent=self)
                self.imgpdf_files.clear()
                self.imgpdf_listbox.delete(0, "end")
                self.imgpdf_out_var.set("")
            else:
                messagebox.showerror("失敗", f"圖片轉 PDF 失敗：\n{error_msg}", parent=self)
        self.after(0, finish)


class MyButlerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("我的檔案管家")
        self.geometry("450x300")
        self.resizable(True, True)
        self.minsize(450, 300)
        self.center_window(450, 300)
        
        self.style = ttk.Style(self)
        self.style.theme_use("winnative")
        
        self.create_widgets()
        
    def center_window(self, width, height):
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
        
    def create_widgets(self):
        # Upper welcome banner
        lbl_welcome = ttk.Label(self, text="歡迎使用 我的檔案管家", font=("Arial", 16, "bold"), foreground="#005A9C")
        lbl_welcome.pack(pady=(25, 5))
        
        lbl_desc = ttk.Label(self, text="請選擇您要啟動的工具模組：", font=("Arial", 10))
        lbl_desc.pack(pady=(0, 15))
        
        # Lower button area frame
        btn_frame = ttk.LabelFrame(self, text=" 功能按鈕區 ")
        btn_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        btn_frame.columnconfigure(0, weight=1)
        btn_frame.columnconfigure(1, weight=1)
        btn_frame.rowconfigure(0, weight=1)
        btn_frame.rowconfigure(1, weight=1)
        
        # Dynamic tool launch button
        btn_organizer = ttk.Button(btn_frame, text="資料夾整理小幫手", width=22, command=self.open_organizer)
        btn_organizer.grid(row=0, column=0, padx=20, pady=15)
        
        # Batch Renamer launch button
        btn_renamer = ttk.Button(btn_frame, text="批次改檔名", width=22, command=self.open_renamer)
        btn_renamer.grid(row=0, column=1, padx=20, pady=15)
        
        # PDF Toolbox launch button
        btn_pdf_toolbox = ttk.Button(btn_frame, text="PDF 萬能工具箱", width=22, command=self.open_pdf_toolbox)
        btn_pdf_toolbox.grid(row=1, column=0, padx=20, pady=10)
        
        # Preset placeholder button 4
        btn_placeholder4 = ttk.Button(btn_frame, text="（預留功能按鈕 4）", width=22, state="disabled")
        btn_placeholder4.grid(row=1, column=1, padx=20, pady=10)
        
    def open_organizer(self):
        FileOrganizerApp(self)

    def open_renamer(self):
        FileRenamerApp(self)

    def open_pdf_toolbox(self):
        PdfToolboxApp(self)


if __name__ == "__main__":
    app = MyButlerApp()
    app.mainloop()
