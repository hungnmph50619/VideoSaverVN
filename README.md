# VideoSaver VN 3.0 — Local Web Download Manager

Ứng dụng tải video về máy Windows với giao diện web tiếng Việt, chạy **cục bộ** (Flask + yt-dlp + FFmpeg).

## Có gì mới trong v3

- Dashboard responsive, gọn hơn, có font Unicode và thông báo tiếng Việt.
- **Phân tích video**: tên video, kênh đăng, thumbnail, thời lượng và các độ phân giải do nguồn cung cấp.
- Chọn tối đa 144p, 240p, 360p, 480p, 720p, 1080p, 1440p, 2160p hoặc tốt nhất; MP3/M4A/Opus.
- **Hàng đợi**: thêm nhiều URL, tải lần lượt, hủy từng lượt, hiển thị phần trăm, tốc độ và ETA khi nguồn cung cấp.
- **Lịch sử** lưu dưới `%USERPROFILE%\.videosavervn\history.json`; trạng thái tải gián đoạn được đánh dấu khi mở lại.
- **Chọn thư mục** bằng hộp thoại Windows hoặc nhập đường dẫn.
- **Tự chọn cổng khả dụng**: ưu tiên 5000, 8765, 5080 rồi cổng ngẫu nhiên nếu cần.
- Nhật ký lỗi được thu gọn. Bản Tkinter cũ vẫn ở `app.py`.

## Cập nhật trên Windows

Đóng cửa sổ chương trình cũ (nhấn Ctrl+C trong PowerShell đang chạy Flask) rồi mở PowerShell:

```powershell
cd "$env:USERPROFILE\Downloads\VideoSaverVN-Online"
git pull origin main
py -m pip install -r requirements.txt
py web_app.py
```

Địa chỉ chính xác được in trong PowerShell và trình duyệt sẽ được mở tự động. Thường là http://127.0.0.1:5000. **Không được mở chương trình cũ cùng lúc trên cùng cổng.** Nếu `git pull` báo có thay đổi cục bộ ở `web_app.py` (do bạn đã đổi cổng 8765 sang 5000 trước đây), chạy `git restore web_app.py` **chỉ khi bạn không cần giữ chỉnh sửa cục bộ**, rồi `git pull origin main`.

Nếu FFmpeg thiếu, cài `winget install Gyan.FFmpeg` rồi khởi động lại PowerShell. Nếu YouTube thiếu môi trường JS:

```powershell
winget install DenoLand.Deno
py -m pip install -U "yt-dlp[default]"
```

## Lưu ý

Phân tích video cần kết nối Internet và nguồn được yt-dlp hỗ trợ; có những video không thể phân tích hoặc tải. Chỉ tải nội dung sở hữu hoặc được phép lưu; không hỗ trợ DRM, nội dung riêng tư hay vượt quyền truy cập.

Bản này **chưa kiểm thử tải thực tế trên máy Windows của người dùng**. Hãy báo lỗi kèm nhật ký ở trang web nếu gặp sự cố.
