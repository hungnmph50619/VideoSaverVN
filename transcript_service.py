"""Local transcription service: subtitle-first, optional CPU speech recognition."""
import html
import re
import shutil
import subprocess
import tempfile
import threading
import uuid
from pathlib import Path

import yt_dlp
from flask import Blueprint, jsonify, request

transcript_api = Blueprint("transcript_api", __name__)
JOBS = {}
LOCK = threading.RLock()
LANGS = ("vi", "en", "auto")
MODELS = ("tiny", "base", "small", "medium")
MODES = ("subtitles", "speech", "auto")

def stamp(seconds):
    seconds = max(0.0, float(seconds or 0))
    hours = int(seconds // 3600)
    minutes = int(seconds % 3600 // 60)
    secs = int(seconds % 60)
    millis = int(round((seconds - int(seconds)) * 1000))
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

def parse_timestamp(value):
    value = value.replace(",", ".")
    parts = value.split(":")
    try:
        sec = float(parts[-1]) + 60 * int(parts[-2])
        if len(parts) == 3:
            sec += 3600 * int(parts[0])
        return sec
    except (ValueError, IndexError):
        return 0.0

def clean_caption(value):
    value = re.sub(r"<[^>]+>", "", value)
    value = html.unescape(value)
    value = value.replace("\u200b", "").replace("\u200e", "")
    return re.sub(r"\s+", " ", value).strip()

def read_subtitles(text):
    """Parse VTT or SRT cues. Strip duplicate rolling auto-caption lines."""
    cues = []
    text = text.lstrip("\ufeff")
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        match = re.match(r"(?P<start>(?:\d{2}:)?\d{2}:\d{2}[.,]\d{3})\s*-->\s*(?P<end>(?:\d{2}:)?\d{2}:\d{2}[.,]\d{3})", lines[i])
        i += 1
        if not match:
            continue
        bits = []
        while i < len(lines) and lines[i].strip():
            line = clean_caption(lines[i])
            if line:
                bits.append(line)
            i += 1
        phrase = " ".join(bits).strip()
        if phrase and (not cues or phrase != cues[-1]["text"]):
            cues.append({"start":parse_timestamp(match["start"]), "end":parse_timestamp(match["end"]), "text":phrase})
    return cues

def write_results(folder, title, media_id, cues):
    safe = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", str(title))[:95].strip(" .") or "video"
    base = Path(folder) / f"{safe} [{media_id}]"
    txt = base.with_suffix(".txt")
    srt = base.with_suffix(".srt")
    # Preserve the ID even if titles contain punctuation or dots.
    txt = Path(str(base) + ".txt")
    srt = Path(str(base) + ".srt")
    txt.write_text("\n".join(c["text"] for c in cues) + "\n", encoding="utf-8-sig")
    srt.write_text("\n\n".join(f"{i}\n{stamp(c['start'])} --> {stamp(c['end'])}\n{c['text']}" for i,c in enumerate(cues,1)) + "\n", encoding="utf-8-sig")
    return str(txt), str(srt)

def change(job, **changes):
    with LOCK:
        job.update(changes)

def get_subtitles(url, language, temp, job):
    with yt_dlp.YoutubeDL({"quiet":True,"no_warnings":True,"skip_download":True,"noplaylist":True}) as dl:
        info = dl.extract_info(url, download=False)
    if not info:
        raise RuntimeError("Không lấy được thông tin video.")
    langs = ([language] if language != "auto" else ["vi", "en"])
    if language == "auto":
        langs += [k for k in (info.get("subtitles") or {}) if k not in langs]
        langs += [k for k in (info.get("automatic_captions") or {}) if k not in langs]
    selected = None
    for kind in ("subtitles","automatic_captions"):
        available = info.get(kind) or {}
        for lang in langs:
            options = available.get(lang) or []
            if options:
                selected = (kind,lang)
                break
        if selected:
            break
    if not selected:
        raise RuntimeError("Không tìm thấy phụ đề ở ngôn ngữ đã chọn. Có thể thử nhận dạng giọng nói bằng Whisper.")
    kind, lang = selected
    options = {"quiet":True,"no_warnings":True,"skip_download":True,"noplaylist":True,
               "writesubtitles":kind=="subtitles","writeautomaticsub":kind=="automatic_captions",
               "subtitleslangs":[lang], "subtitlesformat":"vtt/srt",
               "outtmpl":str(temp / "captions.%(ext)s")}
    with yt_dlp.YoutubeDL(options) as dl:
        dl.download([url])
    files = list(temp.glob("captions*.vtt")) + list(temp.glob("captions*.srt"))
    if not files:
        raise RuntimeError("Không tải được tệp phụ đề.")
    cues = read_subtitles(files[0].read_text(encoding="utf-8-sig", errors="replace"))
    if not cues:
        raise RuntimeError("Phụ đề trống hoặc không đọc được.")
    change(job, note=f"Đã lấy phụ đề {lang} ({'tự động' if kind == 'automatic_captions' else 'do người đăng cung cấp'}).")
    return info, cues

def speech_to_text(url, language, temp, job):
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise RuntimeError('Chưa cài faster-whisper. Chạy: py -m pip install faster-whisper') from exc
    if not shutil.which("ffmpeg"):
        raise RuntimeError("Không tìm thấy FFmpeg để xử lý âm thanh.")
    change(job, status="Đang tải âm thanh", progress=8)
    with yt_dlp.YoutubeDL({"quiet":True,"no_warnings":True,"format":"bestaudio/best",
                           "noplaylist":True,"outtmpl":str(temp / "audio.%(ext)s")}) as dl:
        info = dl.extract_info(url, download=True)
    files = [f for f in temp.glob("audio.*") if f.is_file() and not f.name.endswith((".part",".ytdl"))]
    if not files:
        raise RuntimeError("Không tải được âm thanh.")
    wav = temp / "audio.wav"
    subprocess.run(["ffmpeg","-nostdin","-y","-loglevel","error","-i",str(files[0]),
                    "-vn","-ac","1","-ar","16000",str(wav)],check=True)
    change(job, status="Đang tải hoặc mở mô hình AI", progress=20)
    # Small model balances Vietnamese quality and CPU requirements; no remote transcription API.
    model = WhisperModel(job["model"], device="cpu", compute_type="int8")
    change(job, status="Đang nhận dạng giọng nói (CPU)", progress=30)
    segments, _ = model.transcribe(str(wav), language=None if language=="auto" else language,
                                   vad_filter=True, beam_size=3)
    cues=[]
    duration = float(info.get("duration") or 0)
    for segment in segments:
        phrase = str(segment.text).strip()
        if phrase:
            cues.append({"start":segment.start,"end":segment.end,"text":phrase})
            if duration > 0:
                change(job, progress=min(95, round(30 + 65 * float(segment.end) / duration)))
    if not cues:
        raise RuntimeError("Không nhận dạng được lời nói trong video.")
    change(job,note=f"Đã nhận dạng giọng nói bằng faster-whisper {job['model']} (CPU).")
    return info,cues

def execute(job):
    try:
        change(job,status="Đang xử lý", progress=3)
        with tempfile.TemporaryDirectory(prefix="videosaver_text_") as tmp:
            temp=Path(tmp)
            info=cues=None
            if job["mode"] in ("subtitles","auto"):
                try:
                    info,cues=get_subtitles(job["url"],job["language"],temp,job)
                except Exception as exc:
                    if job["mode"]=="subtitles":
                        raise
                    change(job,note="Không lấy được phụ đề (" + str(exc)[:120] + "); đang thử nhận dạng giọng nói.")
            if cues is None:
                info,cues=speech_to_text(job["url"],job["language"],temp,job)
            folder=Path(job["folder"])
            folder.mkdir(parents=True,exist_ok=True)
            title=info.get("title") or "video"
            media_id=re.sub(r"[^a-zA-Z0-9_-]","",str(info.get("id") or "output"))[:40]
            txt,srt=write_results(folder,title,media_id,cues)
            change(job,status="Hoàn tất",progress=100,txt=txt,srt=srt,segments=len(cues))
    except Exception as exc:
        change(job,status="Thất bại",error=str(exc)[:400])
    finally:
        change(job,finished=True)

@transcript_api.post("/api/transcribe")
def start():
    data=request.get_json(silent=True) or {}
    url=str(data.get("url") or "").strip()
    from urllib.parse import urlsplit
    try:
        parsed = urlsplit(url)
        good = parsed.scheme in ("http", "https") and bool(parsed.hostname) and not parsed.username and not parsed.password and len(url) <= 2048
    except ValueError:
        good = False
    if not good:
        return jsonify(error="Liên kết không hợp lệ."),400
    lang=str(data.get("language") or "vi")
    mode=str(data.get("mode") or "auto")
    model=str(data.get("model") or "small")
    if lang not in LANGS or mode not in MODES or model not in MODELS:
        return jsonify(error="Lựa chọn nhận dạng không hợp lệ."),400
    folder=str(data.get("folder") or (Path.home() / "Downloads")).strip()
    if len(folder)>800:
        return jsonify(error="Đường dẫn quá dài."),400
    with LOCK:
        if any(not j.get("finished") for j in JOBS.values()):
            return jsonify(error="Đang xử lý một video khác. Hãy đợi tác vụ hiện tại kết thúc."),409
        job={"id":uuid.uuid4().hex,"url":url,"folder":folder,"mode":mode,"language":lang,
             "model":model,"status":"Đang chuẩn bị","progress":0,"finished":False,"error":"","note":"","txt":"","srt":""}
        JOBS[job["id"]]=job
        for ident in list(JOBS)[:-15]:
            if JOBS[ident].get("finished"):
                JOBS.pop(ident,None)
    threading.Thread(target=execute,args=(job,),daemon=True).start()
    return jsonify(ok=True,id=job["id"])

@transcript_api.get("/api/transcribe-status")
def check():
    with LOCK:
        return jsonify(jobs=list(JOBS.values())[-15:])


@transcript_api.get("/api/transcript-preview/<identifier>")
def preview(identifier):
    # Only read files belonging to recorded completed jobs.
    with LOCK:
        job = JOBS.get(identifier)
        if not job or not job.get("finished") or not job.get("txt"):
            return jsonify(error="Chưa có kết quả văn bản."), 404
        filename = job["txt"]
    try:
        with open(filename, "r", encoding="utf-8-sig") as handle:
            content = handle.read(300000)
        return jsonify(text=content, truncated=len(content) >= 300000)
    except OSError:
        return jsonify(error="Không đọc được file kết quả; có thể file đã được di chuyển."), 404
