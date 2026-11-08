# VideoSaver VN

Ứng dụng desktop miễn phí, giao diện tiếng Việt cho Windows để tải các video mà bạn được phép lưu lại, dựa trên [yt-dlp](https://github.com/yt-dlp/yt-dlp).

## Tính năng

- Dán đường dẫn video rồi bấm **Tải xuống**.
- Video chất lượng tốt nhất, giới hạn 1080p / 720p, hoặc trích xuất MP3.
- Chọn thư mục lưu, xem tiến độ / tốc độ, mở thư mục kết quả.
- Có nút hủy, hỗ trợ tải tiếp tệp đang tải dở nếu nguồn hỗ trợ.
- Không tải playlist hàng loạt, không vượt DRM hay quyền truy cập.

## Chạy trên Windows

1. Cài [Python 3.11+](https://www.python.org/downloads/) và đánh dấu **Add python.exe to PATH**.
2. Cài FFmpeg (để ghép video + âm thanh và chuyển MP3):

   ```powershell
   winget install Gyan.FFmpeg
   ```

3. Mở PowerShell trong thư mục dự án và chạy:

   ```powershell
   py -m pip install -r requirements.txt
   py app.py
   ```

   Nếu lệnh `py` không khả dụng, thử `python`.

4. Nếu công cụ báo lỗi với YouTube, cập nhật yt-dlp và cài môi trường JavaScript theo [hướng dẫn chính thức](https://github.com/yt-dlp/yt-dlp/wiki/EJS):

   ```powershell
   py -m pip install -U "yt-dlp[default]"
   winget install DenoLand.Deno
   ```

   Sau khi cài FFmpeg hoặc Deno, đóng và mở lại PowerShell.

## Tạo file .exe

```powershell
py -m pip install pyinstaller
py -m PyInstaller --noconfirm --onefile --windowed --name VideoSaverVN app.py
```

File tại `dist/VideoSaverVN.exe`. FFmpeg vẫn cần được cài trong PATH của máy chạy phần mềm. GitHub Actions cũng có workflow tạo `.exe` artifact cho Windows (chưa kiểm thử trên runner).

## Lưu ý

Chỉ tải nội dung bạn sở hữu hoặc được phép tải. Trang nguồn có thể thay đổi và khiến yt-dlp phải cập nhật; ứng dụng không cam kết hỗ trợ mọi trang hay mọi video. Hiện tại đây là bản MVP chưa được kiểm thử tải video thực tế trong môi trường Windows.
