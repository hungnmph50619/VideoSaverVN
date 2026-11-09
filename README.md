# VideoSaver VN — Web UI

Giao diện web hiện đại chạy **cục bộ** trên máy Windows. Video tải xuống ổ cứng của bạn, không qua máy chủ bên ngoài của dự án. Backend Python sử dụng yt-dlp.

## Cài đặt

Mở PowerShell trong thư mục repository:

```powershell
py -m pip install -r requirements.txt
winget install Gyan.FFmpeg
py web_app.py
```

Ứng dụng tự mở trình duyệt tại **http://127.0.0.1:8765**. Chỉ máy của bạn truy cập được giao diện này. Nếu vừa cài FFmpeg, đóng và mở lại PowerShell.

Các mức MP4 tối đa: 144p, 240p, 360p, 480p, 720p, 1080p, 1440p, 2160p và chất lượng tốt nhất. Âm thanh: MP3, M4A, Opus. Mức thực tế phụ thuộc nguồn.

- Chạy bản web: `py web_app.py`
- Chạy giao diện Tkinter cũ: `py app.py`

Nếu YouTube báo thiếu JavaScript runtime, cài Deno và cập nhật yt-dlp:

```powershell
winget install DenoLand.Deno
py -m pip install -U "yt-dlp[default]"
```

Đây là bản MVP, chưa thử nghiệm tải video trực tiếp trên Windows. Chỉ sử dụng với nội dung bạn được phép tải, không vượt DRM hay quyền truy cập.
