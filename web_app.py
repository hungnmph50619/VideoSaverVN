"""VideoSaver VN 3.0 - a local-only Flask video download manager."""
import json
import os
import queue
import secrets
import shutil
import socket
import threading
import time
import uuid
import webbrowser
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

import yt_dlp
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)
app.json.ensure_ascii = False
TOKEN = secrets.token_urlsafe(32)
LOCK = threading.RLock()
TASKS = []
WORK = queue.Queue()
CANCELLED = set()
ACTIVE = None
LOGS = []
DATA_DIR = Path.home() / ".videosavervn"
DATA_FILE = DATA_DIR / "history.json"
DEFAULT_FOLDER = str(Path.home() / "Downloads")
MAX_TASKS = 200
QUALITY = ("best", "2160", "1440", "1080", "720", "480", "360", "240", "144", "mp3", "m4a", "opus")

def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M")

def log(msg):
    with LOCK:
        LOGS.append(str(msg)[:350])
        del LOGS[:-80]

def persist():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with LOCK:
        data = [dict(x) for x in TASKS[-MAX_TASKS:]]
    try:
        tmp = DATA_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(DATA_FILE)
    except OSError as exc:
        log("Không lưu được lịch sử: " + str(exc))

def restore():
    if not DATA_FILE.exists():
        return
    try:
        entries = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        if not isinstance(entries, list):
            return
        for item in entries[-MAX_TASKS:]:
            if not isinstance(item, dict) or not isinstance(item.get("id"), str):
                continue
            if item.get("status") in ("waiting", "downloading", "processing"):
                item["status"] = "interrupted"
            TASKS.append(item)
    except (OSError, ValueError) as exc:
        log("Không đọc được lịch sử: " + str(exc))

restore()

def validate_url(url):
    try:
        p = urlsplit(url)
        host = p.hostname or ""
        return p.scheme in ("https", "http") and bool(host) and not p.username and not p.password and len(url) <= 2048
    except ValueError:
        return False

def err(msg, code=400):
    return jsonify(error=msg), code

@app.after_request
def headers(resp):
    resp.headers["Cache-Control"] = "no-store"
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["Content-Security-Policy"] = "default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' https: data:; script-src 'self' 'unsafe-inline'; connect-src 'self'"
    return resp

@app.before_request
def authorize():
    # The local page is the only supported client. Prevent cross-site requests.
    if request.path.startswith("/api/"):
        if request.headers.get("X-VideoSaver-Token") != TOKEN:
            return err("Phiên làm việc không hợp lệ.", 403)

@app.get("/")
def index():
    return render_template("index.html", token=TOKEN, folder=DEFAULT_FOLDER)

@app.get("/api/state")
def state():
    with LOCK:
        return jsonify(tasks=list(reversed(TASKS[-MAX_TASKS:])), logs=LOGS[-35:],
                       active=ACTIVE, ffmpeg=bool(shutil.which("ffmpeg")))

@app.post("/api/analyze")
def analyze():
    data = request.get_json(silent=True) or {}
    url = str(data.get("url") or "").strip()
    if not validate_url(url):
        return err("Hãy nhập đường dẫn video http/https hợp lệ.")
    try:
        with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True, "noplaylist": True,
                               "skip_download": True, "socket_timeout": 15, "ignoreerrors": False}) as ydl:
            info = ydl.extract_info(url, download=False)
        if not info or info.get("_type") in ("playlist", "multi_video"):
            return err("Không đọc được thông tin video đơn.", 422)
        heights = sorted({int(f["height"]) for f in info.get("formats", [])
                          if isinstance(f.get("height"), (int, float)) and f.get("vcodec") != "none"})
        return jsonify(title=str(info.get("title") or "Video chưa có tên")[:230],
                       uploader=str(info.get("uploader") or "Không rõ kênh")[:120],
                       duration=info.get("duration"), thumbnail=info.get("thumbnail"),
                       heights=heights, webpage_url=str(info.get("webpage_url") or url))
    except Exception as exc:
        return err("Không phân tích được video: " + str(exc)[:250], 422)

def task_update(task, **fields):
    with LOCK:
        task.update(fields)

def downloader(task):
    global ACTIVE
    ident = task["id"]
    with LOCK:
        if ident in CANCELLED:
            task_update(task, status="cancelled")
            CANCELLED.discard(ident)
            return
        ACTIVE = ident
        task_update(task, status="downloading")
    log("Bắt đầu tải: " + task["title"])
    selection = task["quality"]
    if selection == "best":
        fmt = "bv*+ba/b"
    elif selection in ("mp3", "m4a", "opus"):
        fmt = "bestaudio/best"
    else:
        # Fallback only to equal or lower resolution; no silent upscale.
        fmt = f"bv*[height<={selection}]+ba/b[height<={selection}]/best[height<={selection}]"
    class CancelTask(Exception):
        pass
    def hook(data):
        with LOCK:
            if ident in CANCELLED:
                raise CancelTask("Đã hủy")
        if data.get("status") == "downloading":
            total = data.get("total_bytes") or data.get("total_bytes_estimate") or 0
            bytes_done = data.get("downloaded_bytes") or 0
            progress = round(min(99, 100 * bytes_done / total), 1) if total else 0
            speed = data.get("speed")
            eta = data.get("eta")
            task_update(task, progress=progress, speed=round(speed / 1048576, 2) if speed else None,
                        eta=eta if isinstance(eta, (int, float)) else None)
        elif data.get("status") == "finished":
            task_update(task, status="processing", progress=99)
    class Logger:
        def debug(self, msg): pass
        def warning(self, msg): log("Cảnh báo: " + str(msg))
        def error(self, msg): log("Lỗi: " + str(msg))
    opts = {"format": fmt, "outtmpl": str(Path(task["folder"]) / "%(title).180B [%(id)s].%(ext)s"),
            "noplaylist": True, "windowsfilenames": True, "continuedl": True,
            "progress_hooks": [hook], "logger": Logger(), "quiet": True,
            "retries": 5, "fragment_retries": 5}
    if selection in ("mp3", "m4a", "opus"):
        opts["postprocessors"] = [{"key": "FFmpegExtractAudio",
                                   "preferredcodec": selection, "preferredquality": "192"}]
    else:
        opts["merge_output_format"] = "mp4"
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([task["url"]])
        with LOCK:
            cancelled = ident in CANCELLED
        task_update(task, status="cancelled" if cancelled else "done",
                    progress=task["progress"] if cancelled else 100, speed=None, eta=None)
        log(("Đã hủy: " if cancelled else "✓ Hoàn tất: ") + task["title"])
    except Exception as exc:
        with LOCK:
            cancelled = ident in CANCELLED
        task_update(task, status="cancelled" if cancelled else "failed", speed=None, eta=None,
                    error="" if cancelled else str(exc)[:320])
        log(("Đã hủy: " if cancelled else "✕ Lỗi: ") + (task["title"] if cancelled else str(exc)[:260]))
    finally:
        with LOCK:
            CANCELLED.discard(ident)
            ACTIVE = None
        persist()

def worker():
    while True:
        item = WORK.get()
        try:
            downloader(item)
        except Exception as exc:
            task_update(item, status="failed", error=str(exc)[:200])
            log("Lỗi xử lý hàng đợi: " + str(exc))
            persist()
        finally:
            WORK.task_done()

threading.Thread(target=worker, daemon=True).start()

@app.post("/api/add")
def add():
    body = request.get_json(silent=True) or {}
    url = str(body.get("url") or "").strip()
    quality = str(body.get("quality") or "best")
    folder = str(body.get("folder") or DEFAULT_FOLDER).strip()
    if not validate_url(url):
        return err("Liên kết không hợp lệ.")
    if quality not in QUALITY:
        return err("Định dạng tải không hợp lệ.")
    if len(folder) > 800:
        return err("Đường dẫn thư mục quá dài.")
    try:
        p = Path(folder).expanduser()
        p.mkdir(parents=True, exist_ok=True)
        if not p.is_dir():
            raise ValueError("Đường dẫn không phải thư mục.")
    except (OSError, ValueError) as exc:
        return err("Không thể sử dụng thư mục: " + str(exc))
    with LOCK:
        task = {"id": uuid.uuid4().hex, "url": url,
                "title": str(body.get("title") or url)[:200],
                "thumbnail": str(body.get("thumbnail") or "")[:2000],
                "quality": quality, "folder": str(p), "created": now(),
                "status": "waiting", "progress": 0, "speed": None, "eta": None, "error": ""}
        TASKS.append(task)
        if len(TASKS) > MAX_TASKS:
            TASKS.pop(0)
        WORK.put(task)
    persist()
    return jsonify(ok=True, id=task["id"])

@app.post("/api/cancel")
def cancel():
    ident = str((request.get_json(silent=True) or {}).get("id", ""))
    with LOCK:
        item = next((x for x in TASKS if x["id"] == ident), None)
        if not item:
            return err("Không tìm thấy lượt tải.", 404)
        if item["status"] in ("waiting", "downloading", "processing"):
            CANCELLED.add(ident)
            if item["status"] == "waiting":
                item["status"] = "cancelled"
        else:
            return err("Lượt tải đã kết thúc.", 409)
    persist()
    return jsonify(ok=True)

@app.post("/api/open-folder")
def open_folder():
    folder = str((request.get_json(silent=True) or {}).get("folder") or DEFAULT_FOLDER)
    p = Path(folder).expanduser()
    if not p.is_dir():
        return err("Thư mục không tồn tại.")
    if os.name != "nt":
        return err("Chức năng mở Explorer chỉ hỗ trợ Windows.")
    try:
        os.startfile(str(p))
    except OSError as exc:
        return err(str(exc))
    return jsonify(ok=True)

@app.post("/api/select-folder")
def select_folder():
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        selected = filedialog.askdirectory(parent=root, initialdir=DEFAULT_FOLDER)
        root.destroy()
        return jsonify(folder=selected or "")
    except Exception as exc:
        return err("Không mở được hộp thoại chọn thư mục: " + str(exc))

def free_port():
    # Prefer 5000 when available, but auto-select a Windows-allowed port.
    for port in (5000, 8765, 5080, 0):
        try:
            sock = socket.socket()
            sock.bind(("127.0.0.1", port))
            chosen = sock.getsockname()[1]
            sock.close()
            return chosen
        except OSError:
            continue
    raise RuntimeError("Không tìm được cổng localhost khả dụng.")

if __name__ == "__main__":
    port = free_port()
    url = f"http://127.0.0.1:{port}"
    print("VideoSaver VN 3.0:", url)
    threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False, threaded=True)
