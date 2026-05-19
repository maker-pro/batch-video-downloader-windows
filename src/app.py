from __future__ import annotations

import queue
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .config import load_settings, save_settings
from .models import AppSettings, TaskStatus
from .worker import BatchRunner


class VideoDownloaderApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("批量视频下载工具")
        self.geometry("1180x760")
        self.minsize(980, 620)
        self.settings = load_settings()
        self.runner: BatchRunner | None = None
        self.rows: dict[str, str] = {}
        self._build_style()
        self._build_ui()
        self._load_settings_to_ui()
        self.after(200, self._poll_updates)

    def _build_style(self) -> None:
        style = ttk.Style(self)
        if "vista" in style.theme_names():
            style.theme_use("vista")
        style.configure("Toolbar.TFrame", padding=10)
        style.configure("TButton", padding=(10, 4))
        style.configure("Treeview", rowheight=26)

    def _build_ui(self) -> None:
        root = ttk.Frame(self, padding=12)
        root.pack(fill=tk.BOTH, expand=True)
        root.columnconfigure(0, weight=3)
        root.columnconfigure(1, weight=2)
        root.rowconfigure(1, weight=1)

        settings = ttk.LabelFrame(root, text="下载设置", padding=10)
        settings.grid(row=0, column=0, columnspan=2, sticky="ew")
        settings.columnconfigure(1, weight=1)
        settings.columnconfigure(4, weight=1)

        ttk.Label(settings, text="保存目录").grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.output_var = tk.StringVar()
        ttk.Entry(settings, textvariable=self.output_var).grid(row=0, column=1, sticky="ew")
        ttk.Button(settings, text="选择", command=self._choose_output_dir).grid(row=0, column=2, padx=(8, 16))

        ttk.Label(settings, text="N_m3u8DL-CLI").grid(row=0, column=3, sticky="w", padx=(0, 8))
        self.m3u8dl_var = tk.StringVar()
        ttk.Entry(settings, textvariable=self.m3u8dl_var).grid(row=0, column=4, sticky="ew")
        ttk.Button(settings, text="选择", command=self._choose_m3u8dl).grid(row=0, column=5, padx=(8, 0))

        ttk.Label(settings, text="代理").grid(row=1, column=0, sticky="w", pady=(10, 0), padx=(0, 8))
        self.proxy_var = tk.StringVar()
        ttk.Entry(settings, textvariable=self.proxy_var).grid(row=1, column=1, sticky="ew", pady=(10, 0))

        ttk.Label(settings, text="并发数").grid(row=1, column=3, sticky="w", pady=(10, 0), padx=(0, 8))
        self.concurrency_var = tk.IntVar(value=2)
        ttk.Spinbox(settings, from_=1, to=16, textvariable=self.concurrency_var, width=8).grid(
            row=1, column=4, sticky="w", pady=(10, 0)
        )

        self.system_proxy_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(settings, text="无自定义代理时使用系统代理", variable=self.system_proxy_var).grid(
            row=2, column=1, sticky="w", pady=(10, 0)
        )
        self.playwright_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(settings, text="解析失败时尝试浏览器渲染", variable=self.playwright_var).grid(
            row=2, column=4, sticky="w", pady=(10, 0)
        )

        left = ttk.LabelFrame(root, text="批量 URL（一行一个）", padding=10)
        left.grid(row=1, column=0, sticky="nsew", pady=(12, 0), padx=(0, 8))
        left.rowconfigure(0, weight=1)
        left.columnconfigure(0, weight=1)
        self.url_text = tk.Text(left, wrap=tk.WORD, undo=True, height=16)
        self.url_text.grid(row=0, column=0, sticky="nsew")
        url_scroll = ttk.Scrollbar(left, orient=tk.VERTICAL, command=self.url_text.yview)
        url_scroll.grid(row=0, column=1, sticky="ns")
        self.url_text.configure(yscrollcommand=url_scroll.set)

        actions = ttk.Frame(left)
        actions.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        ttk.Button(actions, text="开始下载", command=self._start).pack(side=tk.LEFT)
        ttk.Button(actions, text="停止", command=self._stop).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(actions, text="清空 URL", command=lambda: self.url_text.delete("1.0", tk.END)).pack(
            side=tk.LEFT, padx=(8, 0)
        )

        right = ttk.LabelFrame(root, text="任务状态", padding=10)
        right.grid(row=1, column=1, sticky="nsew", pady=(12, 0), padx=(8, 0))
        right.rowconfigure(0, weight=1)
        right.columnconfigure(0, weight=1)

        columns = ("status", "message")
        self.tree = ttk.Treeview(right, columns=columns, show="tree headings")
        self.tree.heading("#0", text="URL")
        self.tree.heading("status", text="状态")
        self.tree.heading("message", text="信息")
        self.tree.column("#0", width=280, minwidth=180)
        self.tree.column("status", width=80, minwidth=70, anchor=tk.CENTER)
        self.tree.column("message", width=420, minwidth=220)
        self.tree.grid(row=0, column=0, sticky="nsew")
        task_scroll = ttk.Scrollbar(right, orient=tk.VERTICAL, command=self.tree.yview)
        task_scroll.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=task_scroll.set)

        log_frame = ttk.LabelFrame(root, text="日志", padding=10)
        log_frame.grid(row=2, column=0, columnspan=2, sticky="nsew", pady=(12, 0))
        log_frame.rowconfigure(0, weight=1)
        log_frame.columnconfigure(0, weight=1)
        self.log_text = tk.Text(log_frame, height=7, wrap=tk.WORD, state=tk.DISABLED)
        self.log_text.grid(row=0, column=0, sticky="nsew")
        log_scroll = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        log_scroll.grid(row=0, column=1, sticky="ns")
        self.log_text.configure(yscrollcommand=log_scroll.set)

    def _load_settings_to_ui(self) -> None:
        self.output_var.set(str(self.settings.output_dir))
        self.m3u8dl_var.set(str(self.settings.m3u8dl_path))
        self.proxy_var.set(self.settings.proxy)
        self.concurrency_var.set(self.settings.concurrency)
        self.system_proxy_var.set(self.settings.use_system_proxy)
        self.playwright_var.set(self.settings.enable_playwright)

    def _collect_settings(self) -> AppSettings:
        settings = AppSettings(
            output_dir=Path(self.output_var.get()).expanduser(),
            m3u8dl_path=Path(self.m3u8dl_var.get()).expanduser(),
            proxy=self.proxy_var.get().strip(),
            concurrency=max(1, min(int(self.concurrency_var.get()), 16)),
            use_system_proxy=self.system_proxy_var.get(),
            enable_playwright=self.playwright_var.get(),
        )
        save_settings(settings)
        self.settings = settings
        return settings

    def _choose_output_dir(self) -> None:
        value = filedialog.askdirectory(initialdir=self.output_var.get() or str(Path.cwd()))
        if value:
            self.output_var.set(value)

    def _choose_m3u8dl(self) -> None:
        value = filedialog.askopenfilename(
            title="选择 N_m3u8DL-CLI.exe",
            filetypes=[("N_m3u8DL-CLI", "N_m3u8DL-CLI.exe"), ("Executable", "*.exe"), ("All files", "*.*")],
        )
        if value:
            self.m3u8dl_var.set(value)

    def _start(self) -> None:
        urls = [line.strip() for line in self.url_text.get("1.0", tk.END).splitlines() if line.strip()]
        if not urls:
            messagebox.showwarning("没有 URL", "请先输入至少一个 URL。")
            return
        settings = self._collect_settings()
        if not settings.output_dir.exists():
            settings.output_dir.mkdir(parents=True, exist_ok=True)

        self.tree.delete(*self.tree.get_children())
        self.rows.clear()
        for url in urls:
            row = self.tree.insert("", tk.END, text=url, values=(TaskStatus.PENDING.value, "等待开始"))
            self.rows[url] = row

        self.runner = BatchRunner(settings)
        self.runner.start(urls)
        self._log(f"已启动 {len(urls)} 个任务，并发数 {settings.concurrency}")

    def _stop(self) -> None:
        if self.runner:
            self.runner.stop()
            self._log("已请求停止，正在等待当前下载进程退出")

    def _poll_updates(self) -> None:
        if self.runner:
            while True:
                try:
                    update = self.runner.updates.get_nowait()
                except queue.Empty:
                    break
                row = self.rows.get(update.url)
                if row:
                    self.tree.item(row, values=(update.status.value, update.message))
                self._log(f"[{update.status.value}] {update.url} - {update.message}")
        self.after(200, self._poll_updates)

    def _log(self, message: str) -> None:
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)


def main() -> None:
    app = VideoDownloaderApp()
    app.mainloop()


if __name__ == "__main__":
    main()
