"""VideoSaver VN - a simple desktop downloader for content you may save."""
import os
import queue
import shutil
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import yt_dlp


class CancelDownload(Exception):
    pass


class VideoSaver(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("VideoSaver VN • Tải video")
        self.geometry("730x550")
        self.minsize(630, 490)
        self.configure(bg="#f4f6fb")
        self.events = queue.Queue()
        self.stop_event = threading.Event()
        self.running = False
        self.make_ui()
        self.after(100, self.poll_events)

    def make_ui(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background="#f4f6fb")
        style.configure("TLabel", background="#f4f6fb", foreground="#263148", font=("Segoe UI", 10))
        style.configure("Title.TLabel", font=("Segoe UI", 22, "bold"), foreground="#17243d")
        style.configure("TButton", font=("Segoe UI", 10), padding=9)
        style.configure("TEntry", padding=8)
        style.configure("TCombobox", padding=5)
        style.configure("Horizontal.TProgressbar", thickness=16)
        outer = ttk.Frame(self, padding=25)
        outer.pack(fill="both", expand=True)
        ttk.Label(outer, text="VideoSaver VN", style="Title.TLabel").pack(anchor="w")
        ttk.Label(outer, text="Dán liên kết video công khai mà bạn có quyền tải về máy.").pack(anchor="w", pady=(2, 18))
        ttk.Label(outer, text="Liên kết video").pack(anchor="w")
        self.url_var = tk.StringVar()
        ttk.Entry(outer, textvariable=self.url_var).pack(fill="x", pady=(5, 14))
        option_row = ttk.Frame(outer)
        option_row.pack(fill="x", pady=(0, 14))
        left = ttk.Frame(option_row)
        left.pack(side="left", fill="x", expand=True, padx=(0, 12))
        ttk.Label(left, text="Định dạng / chất lượng").pack(anchor="w")
        self.format_var = tk.StringVar(value="Video MP4 - tốt nhất")
        self.format_box = ttk.Combobox(left, textvariable=self.format_var, state="readonly", values=[
            "Video MP4 - tốt nhất", "Video MP4 - tối đa 1080p", "Video MP4 - tối đa 720p", "Âm thanh MP3"
        ])
        self.format_box.pack(fill="x", pady=(5, 0))
        right = ttk.Frame(option_row)
        right.pack(side="left", fill="x", expand=True)
        ttk.Label(right, text="Thư mục lưu").pack(anchor="w")
        folder_row = ttk.Frame(right)
        folder_row.pack(fill="x", pady=(5, 0))
        default_dir = Path.home() / "Downloads"
        self.folder_var = tk.StringVar(value=str(default_dir if default_dir.exists() else Path.home()))
        ttk.Entry(folder_row, textvariable=self.folder_var).pack(side="left", fill="x", expand=True)
        self.browse_button = ttk.Button(folder_row, text="Chọn", command=self.pick_folder)
        self.browse_button.pack(side="left", padx=(6, 0))
        button_row = ttk.Frame(outer)
        button_row.pack(fill="x", pady=(2, 16))
        self.download_button = ttk.Button(button_row, text="⬇  Tải xuống", command=self.start_download)
        self.download_button.pack(side="left")
        self.cancel_button = ttk.Button(button_row, text="Hủy tải", command=self.cancel, state="disabled")
        self.cancel_button.pack(side="left", padx=(10, 0))
        ttk.Button(button_row, text="Mở thư mục", command=self.open_folder).pack(side="right")
        ttk.Label(outer, text="Tiến độ").pack(anchor="w")
        self.progress_var = tk.DoubleVar(value=0)
        ttk.Progressbar(outer, mode="determinate", maximum=100, variable=self.progress_var).pack(fill="x", pady=(6, 7))
        self.status_var = tk.StringVar(value="Sẵn sàng")
        ttk.Label(outer, textvariable=self.status_var).pack(anchor="w")
        ttk.Label(outer, text="Nhật ký").pack(anchor="w", pady=(15, 4))
        log_frame = ttk.Frame(outer)
        log_frame.pack(fill="both", expand=True)
        self.log = tk.Text(log_frame, height=7, wrap="word", state="disabled", bg="#ffffff", fg="#263148", relief="flat", padx=10, pady=10, font=("Consolas", 9))
        self.log.pack(side="left", fill="both", expand=True)
        scroll = ttk.Scrollbar(log_frame, orient="vertical", command=self.log.yview)
        scroll.pack(side="right", fill="y")
        self.log.configure(yscrollcommand=scroll.set)
        ttk.Label(outer, text="Lưu ý: Không hỗ trợ nội dung DRM, riêng tư hoặc cần vượt quyền truy cập.").pack(anchor="w", pady=(12, 0))

    def pick_folder(self):
        folder = filedialog.askdirectory(initialdir=self.folder_var.get())
        if folder:
            self.folder_var.set(folder)

    def open_folder(self):
        folder = Path(self.folder_var.get()).expanduser()
        if not folder.is_dir():
            messagebox.showwarning("Thư mục", "Thư mục lưu chưa tồn tại.")
            return
        if os.name == "nt":
            os.startfile(str(folder))
        else:
            import subprocess
            import sys
            subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", str(folder)])

    def add_log(self, line):
        self.log.configure(state="normal")
        self.log.insert("end", line + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def set_running(self, value):
        self.running = value
        self.download_button.configure(state="disabled" if value else "normal")
        self.cancel_button.configure(state="normal" if value else "disabled")
        self.format_box.configure(state="disabled" if value else "readonly")
        self.browse_button.configure(state="disabled" if value else "normal")

    def start_download(self):
        if self.running:
            return
        url = self.url_var.get().strip()
        if not url.startswith(("http://", "https://")):
            messagebox.showwarning("Thiếu liên kết", "Hãy nhập một liên kết http hoặc https hợp lệ.")
            return
        folder = Path(self.folder_var.get()).expanduser()
        try:
            folder.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            messagebox.showerror("Lỗi thư mục", str(exc))
            return
        self.stop_event.clear()
        self.progress_var.set(0)
        self.set_running(True)
        self.status_var.set("Đang chuẩn bị tải...")
        self.add_log("Bắt đầu: " + url)
        threading.Thread(target=self.worker, args=(url, folder, self.format_var.get()), daemon=True).start()

    def cancel(self):
        self.stop_event.set()
        self.status_var.set("Đang yêu cầu hủy...")
        self.add_log("Đã yêu cầu hủy tải.")

    def worker(self, url, folder, selected):
        def hook(data):
            if self.stop_event.is_set():
                raise CancelDownload("Đã hủy theo yêu cầu.")
            if data.get("status") == "downloading":
                total = data.get("total_bytes") or data.get("total_bytes_estimate")
                received = data.get("downloaded_bytes", 0)
                percent = min(100, received * 100 / total) if total else 0
                self.events.put(("progress", percent))
                speed = data.get("speed")
                self.events.put(("status", f"Đang tải: {percent:.1f}%" + (f" • {speed/1024/1024:.2f} MB/s" if speed else "")))
            elif data.get("status") == "finished":
                self.events.put(("status", "Đã tải dữ liệu, đang xử lý tệp..."))

        class Logger:
            def debug(self, msg):
                if msg.startswith("[debug]"):
                    return
            def warning(self, msg):
                self_outer.events.put(("log", "Cảnh báo: " + msg))
            def error(self, msg):
                self_outer.events.put(("log", "Lỗi: " + msg))
        self_outer = self
        formats = {
            "Video MP4 - tốt nhất": "bv*+ba/b",
            "Video MP4 - tối đa 1080p": "bv*[height<=1080]+ba/b[height<=1080]",
            "Video MP4 - tối đa 720p": "bv*[height<=720]+ba/b[height<=720]",
            "Âm thanh MP3": "bestaudio/best",
        }
        options = {
            "format": formats[selected],
            "outtmpl": str(folder / "%(title).180B [%(id)s].%(ext)s"),
            "noplaylist": True,
            "progress_hooks": [hook],
            "logger": Logger(),
            "quiet": True,
            "no_warnings": False,
            "windowsfilenames": True,
            "continuedl": True,
            "retries": 5,
            "fragment_retries": 5,
        }
        if selected == "Âm thanh MP3":
            options["postprocessors"] = [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}]
        else:
            options["merge_output_format"] = "mp4"
        try:
            if not shutil.which("ffmpeg"):
                self.events.put(("log", "Chưa tìm thấy FFmpeg: video có thể không ghép được tiếng/hình và MP3 sẽ không chuyển đổi được."))
            with yt_dlp.YoutubeDL(options) as ydl:
                if self.stop_event.is_set():
                    raise CancelDownload("Đã hủy")
                ydl.download([url])
            if self.stop_event.is_set():
                self.events.put(("cancelled", None))
            else:
                self.events.put(("done", None))
        except (CancelDownload, KeyboardInterrupt):
            self.events.put(("cancelled", None))
        except Exception as exc:
            if self.stop_event.is_set():
                self.events.put(("cancelled", None))
            else:
                self.events.put(("error", str(exc)))

    def poll_events(self):
        try:
            while True:
                kind, value = self.events.get_nowait()
                if kind == "progress":
                    self.progress_var.set(value)
                elif kind == "status":
                    self.status_var.set(value)
                elif kind == "log":
                    self.add_log(value)
                elif kind == "done":
                    self.progress_var.set(100)
                    self.status_var.set("Tải hoàn tất!")
                    self.add_log("✓ Tải hoàn tất.")
                    self.set_running(False)
                elif kind == "cancelled":
                    self.status_var.set("Đã hủy tải")
                    self.add_log("Đã hủy. Tệp tạm có thể còn trong thư mục lưu để tiếp tục tải sau.")
                    self.set_running(False)
                elif kind == "error":
                    self.status_var.set("Tải thất bại")
                    self.add_log("✗ " + value)
                    self.set_running(False)
                    messagebox.showerror("Không thể tải", value)
        except queue.Empty:
            pass
        self.after(100, self.poll_events)


if __name__ == "__main__":
    VideoSaver().mainloop()
