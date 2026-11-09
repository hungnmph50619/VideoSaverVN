"""VideoSaver VN - local web UI. Bind only to loopback; do not expose this server."""
import os
import secrets
import shutil
import threading
import webbrowser
from pathlib import Path
from urllib.parse import urlparse

import yt_dlp
from flask import Flask, jsonify, render_template, request

server = Flask(__name__)
server.config["JSON_AS_ASCII"] = False
TOKEN = secrets.token_urlsafe(32)
LOCK = threading.Lock()
STOP = threading.Event()
STATE = {"running": False, "status": "Sẵn sàng", "progress": 0, "speed": "", "logs": []}
DOWNLOAD_DIR = Path.home() / "Downloads"
QUALITIES = ["best", "2160", "1440", "1080", "720", "480", "360", "240", "144", "mp3", "m4a", "opus"]

def update(**kwargs):
    with LOCK:
        STATE.update(kwargs)

def log(message):
    with LOCK:
        STATE["logs"].append(str(message)[:350])
        STATE["logs"] = STATE["logs"][-70:]

def valid_url(url):
    try:
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https") and bool(parsed.hostname) and not parsed.username and not parsed.password
    except ValueError:
        return False

@server.before_request
def protect():
    if request.path.startswith("/api/") and request.headers.get("X-VideoSaver-Token") != TOKEN:
        return jsonify(error="Yêu cầu không hợp lệ"), 403

@server.get("/")
def home():
    return render_template("index.html", token=TOKEN, download_dir=str(DOWNLOAD_DIR))

@server.get("/api/status")
def status():
    with LOCK:
        return jsonify(dict(STATE))

@server.get("/api/health")
def health():
    return jsonify(ffmpeg=bool(shutil.which("ffmpeg")), formats=QUALITIES)

def download_job(url, quality, folder):
    def hook(d):
        if STOP.is_set():
            raise RuntimeError("Đã hủy theo yêu cầu")
        if d.get("status") == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            amount = d.get("downloaded_bytes", 0)
            percent = round(100 * amount / total, 1) if total else 0
            speed = d.get("speed") or 0
            update(progress=percent, speed=(f"{speed/1048576:.2f} MB/s" if speed else ""), status="Đang tải video...")
        elif d.get("status") == "finished":
            update(status="Đang ghép hoặc chuyển đổi...", progress=99)
    class Logger:
        def debug(self, msg): pass
        def warning(self, msg): log("Cảnh báo: " + msg)
        def error(self, msg): log("Lỗi: " + msg)
    if quality == "best":
        fmt = "bv*+ba/b"
    elif quality in ("mp3", "m4a", "opus"):
        fmt = "bestaudio/best"
    else:
        fmt = f"bv*[height<={quality}]+ba/b[height<={quality}]/best[height<={quality}]"
    opts = {
        "format": fmt, "outtmpl": str(folder / "%(title).180B [%(id)s].%(ext)s"),
        "noplaylist": True, "continuedl": True, "windowsfilenames": True,
        "progress_hooks": [hook], "logger": Logger(), "quiet": True,
        "retries": 5, "fragment_retries": 5,
    }
    if quality in ("mp3", "m4a", "opus"):
        opts["postprocessors"] = [{"key": "FFmpegExtractAudio", "preferredcodec": quality, "preferredquality": "192"}]
    else:
        opts["merge_output_format"] = "mp4"
    try:
        if not shutil.which("ffmpeg"):
            log("Không tìm thấy FFmpeg. Video có thể không ghép được âm thanh.")
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
        if STOP.is_set():
            update(status="Đã hủy")
            log("Đã hủy. Có thể còn tệp tải dở.")
        else:
            update(status="Tải hoàn tất!", progress=100)
            log("✓ Tải hoàn tất vào " + str(folder))
    except Exception as e:
        update(status="Đã hủy" if STOP.is_set() else "Tải thất bại")
        log("Đã hủy" if STOP.is_set() else "✗ " + str(e))
    finally:
        update(running=False, speed="")

@server.post("/api/download")
def start_download():
    data = request.get_json(silent=True) or {}
    url = str(data.get("url", "")).strip()
    quality = str(data.get("quality", "best"))
    folder_input = str(data.get("folder", "")).strip()
    if not valid_url(url):
        return jsonify(error="Vui lòng nhập URL http/https hợp lệ."), 400
    if quality not in QUALITIES:
        return jsonify(error="Chất lượng không hợp lệ."), 400
    folder = Path(folder_input or DOWNLOAD_DIR).expanduser()
    try:
        folder.mkdir(parents=True, exist_ok=True)
        if not folder.is_dir():
            raise ValueError("Đường dẫn không phải thư mục.")
    except (OSError, ValueError) as e:
        return jsonify(error="Không tạo được thư mục: " + str(e)), 400
    with LOCK:
        if STATE["running"]:
            return jsonify(error="Đang tải một video khác."), 409
        STATE.update(running=True, status="Đang chuẩn bị...", progress=0, speed="", logs=["Bắt đầu: " + url])
        STOP.clear()
    threading.Thread(target=download_job, args=(url, quality, folder), daemon=True).start()
    return jsonify(ok=True)

@server.post("/api/cancel")
def cancel():
    STOP.set()
    return jsonify(ok=True)

@server.post("/api/open-folder")
def open_folder():
    data = request.get_json(silent=True) or {}
    folder = Path(str(data.get("folder") or DOWNLOAD_DIR)).expanduser()
    if not folder.is_dir():
        return jsonify(error="Thư mục chưa tồn tại."), 400
    if os.name == "nt":
        os.startfile(str(folder))
    else:
        return jsonify(error="Tính năng này hỗ trợ Windows."), 400
    return jsonify(ok=True)

if __name__ == "__main__":
    print("VideoSaver VN Web: http://127.0.0.1:8765")
    threading.Timer(1.2, lambda: webbrowser.open("http://127.0.0.1:8765")).start()
    server.run(host="127.0.0.1", port=8765, debug=False, use_reloader=False)
