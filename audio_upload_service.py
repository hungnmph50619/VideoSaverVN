"""Upload a local audio/video recording and transcribe it with Whisper on CPU.

All uploads are handled by a server bound to 127.0.0.1 and deleted
after processing. This module shares jobs/status with transcript_service.
"""
import shutil
import subprocess
import tempfile
import threading
import uuid
from pathlib import Path

from flask import Blueprint, jsonify, request

from transcript_service import JOBS, LOCK, LANGS, MODELS, change, write_results

upload_api = Blueprint("upload_api", __name__)
ALLOWED = {".mp3", ".m4a", ".wav", ".mp4", ".webm", ".ogg", ".flac", ".aac", ".wma", ".opus", ".mov", ".mkv"}
MAX_BYTES = 250 * 1024 * 1024


def process_local(job, original):
    try:
        change(job, status="Đang chuẩn bị âm thanh", progress=5)
        if not shutil.which("ffmpeg"):
            raise RuntimeError("Cần cài FFmpeg để xử lý file ghi âm.")
        with tempfile.TemporaryDirectory(prefix="videosaver_audio_") as tmp:
            wav = Path(tmp) / "recording.wav"
            subprocess.run(["ffmpeg", "-nostdin", "-y", "-loglevel", "error", "-i",
                            str(original), "-vn", "-ac", "1", "-ar", "16000", str(wav)],
                           check=True, capture_output=True)
            change(job, status="Đang mở mô hình Whisper", progress=18)
            try:
                from faster_whisper import WhisperModel
            except ImportError as exc:
                raise RuntimeError("Cần cài faster-whisper: py -m pip install -r requirements-transcription.txt") from exc
            model = WhisperModel(job["model"], device="cpu", compute_type="int8")
            change(job, status="Đang nhận dạng giọng nói (CPU)", progress=28)
            # Read duration from the normalized WAV header for meaningful progress.
            import wave
            with wave.open(str(wav), "rb") as recording:
                duration = recording.getnframes() / max(1, recording.getframerate())
            segments, _ = model.transcribe(str(wav),
                language=None if job["language"] == "auto" else job["language"],
                vad_filter=True, beam_size=3)
            cues = []
            for segment in segments:
                phrase = str(segment.text).strip()
                if phrase:
                    cues.append({"start": segment.start, "end": segment.end, "text": phrase})
                if duration:
                    change(job, progress=min(96, round(28 + 68 * float(segment.end) / duration)))
            if not cues:
                raise RuntimeError("Không nhận diện được lời nói. Kiểm tra file có tiếng nói rõ ràng hay không.")
            folder = Path(job["folder"]).expanduser()
            folder.mkdir(parents=True, exist_ok=True)
            txt, srt = write_results(folder, job["filename"], job["id"][:8], cues)
            change(job, status="Hoàn tất", progress=100, txt=txt, srt=srt, segments=len(cues),
                   note="Đã nhận dạng file ghi âm trên máy và lưu TXT / SRT.")
    except subprocess.CalledProcessError as exc:
        change(job, status="Thất bại", error="FFmpeg không đọc được file. Có thể định dạng bị hỏng hoặc không hỗ trợ.")
    except Exception as exc:
        change(job, status="Thất bại", error=str(exc)[:400])
    finally:
        try:
            original.unlink(missing_ok=True)
            original.parent.rmdir()
        except OSError:
            pass
        change(job, finished=True)


@upload_api.post("/api/transcribe-upload")
def upload_recording():
    # Limit enforced even if browser does not send a Content-Length header.
    file = request.files.get("file")
    if file is None or not file.filename:
        return jsonify(error="Hãy chọn một file ghi âm."), 400
    filename = Path(file.filename.replace("\\", "/")).name
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED:
        return jsonify(error="Định dạng chưa hỗ trợ. Chọn MP3, M4A, WAV, FLAC, OGG, MP4, WebM..."), 400
    lang = request.form.get("language", "vi")
    model = request.form.get("model", "small")
    if lang not in LANGS or model not in MODELS:
        return jsonify(error="Ngôn ngữ hoặc mô hình không hợp lệ."), 400
    folder = str(request.form.get("folder") or Path.home() / "Downloads").strip()
    if not folder or len(folder) > 800:
        return jsonify(error="Đường dẫn lưu không hợp lệ."), 400
    with LOCK:
        if any(not job.get("finished") for job in JOBS.values()):
            return jsonify(error="Đang xử lý một tác vụ văn bản khác. Hãy thử lại khi xong."), 409
        job = {"id": uuid.uuid4().hex, "url": "", "filename": filename[:180],
               "folder": folder, "model": model, "language": lang, "mode": "upload",
               "status": "Đang nhận file", "progress": 0, "finished": False,
               "error": "", "note": "", "txt": "", "srt": ""}
        JOBS[job["id"]] = job
    work_dir = Path(tempfile.mkdtemp(prefix="videosaver_uploaded_"))
    source = work_dir / ("source" + suffix)
    try:
        count = 0
        with source.open("wb") as dest:
            while True:
                chunk = file.stream.read(1024 * 1024)
                if not chunk:
                    break
                count += len(chunk)
                if count > MAX_BYTES:
                    raise ValueError("File lớn hơn 250 MB. Hãy chia nhỏ file trước khi tải lên.")
                dest.write(chunk)
        if count == 0:
            raise ValueError("File ghi âm rỗng.")
    except (OSError, ValueError) as exc:
        source.unlink(missing_ok=True)
        try:
            work_dir.rmdir()
        except OSError:
            pass
        with LOCK:
            JOBS.pop(job["id"], None)
        return jsonify(error=str(exc)), 400
    threading.Thread(target=process_local, args=(job, source), daemon=True).start()
    return jsonify(ok=True, id=job["id"])
