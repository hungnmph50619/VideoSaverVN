# VideoSaver VN 4.0

Ứng dụng **web chạy nội bộ trên Windows** để tải video và trích xuất văn bản. Backend Python + Flask + yt-dlp, tùy chọn faster-whisper chạy CPU.

## Giao diện mới

Bốn trang điều hướng không cần cuộn qua mọi chức năng:
1. **Tải video** — dán URL, phân tích tiêu đề/thumbnail/độ phân giải, chọn chất lượng, thêm vào hàng đợi, xem lượt tải hiện tại.
2. **Lấy văn bản** — phụ đề có sẵn hoặc AI Whisper, lựa chọn tiếng Việt/Anh/tự động và mô hình tiny/base/small/medium; xem nội dung TXT, sao chép, lưu TXT/SRT.
3. **Lịch sử** — danh sách tải kèm trạng thái, số lượt chờ/tải/thành công, lỗi và nút hủy.
4. **Cài đặt** — chọn thư mục mặc định, kiểm tra FFmpeg, xem nhật ký kỹ thuật.

Các lượt tải video được lưu ở \`%USERPROFILE%\.videosavervn\history.json\`. Kết quả TXT và SRT lưu tại thư mục người dùng đã chọn. Lịch sử nhận dạng hiện chỉ tồn tại trong phiên chạy; chưa có tính năng tiếp tục nhận dạng khi tắt máy.

## Cập nhật Windows

Đóng chương trình cũ bằng Ctrl+C trong PowerShell trước khi chạy lệnh:

\`\`\`powershell
cd "$env:USERPROFILE\Downloads\VideoSaverVN-Online"
git pull origin main
py -m pip install -r requirements-transcription.txt
py web_app.py
\`\`\`

Ứng dụng tự mở trình duyệt tại địa chỉ localhost được in trong PowerShell (thường là http://127.0.0.1:5000). Nếu Git báo file bị sửa cục bộ, có thể chạy \`git stash push -m "Backup before update"\`, rồi \`git pull origin main\`. Chỉ làm như vậy nếu bạn muốn tạm giữ các thay đổi thay vì ghi đè.

Cần **FFmpeg** để ghép hình/tiếng và xử lý audio: \`winget install Gyan.FFmpeg\`. Nếu YouTube báo thiếu JavaScript runtime: \`winget install DenoLand.Deno\` và \`py -m pip install -U "yt-dlp[default]"\`. Đóng và mở lại PowerShell sau khi cài những công cụ này.

Whisper dùng CPU, tải mô hình từ mạng trong lần sử dụng đầu tiên; mô hình lớn có thể tốn RAM và rất chậm. Chế độ **Chỉ phụ đề** chạy nhanh hơn nếu video có phụ đề ngôn ngữ đã chọn. Nếu phụ đề không có, nút thử Whisper xuất hiện; chế độ Tự động cũng thử AI khi không lấy được phụ đề.

## Hạn chế

- Video từ các website thay đổi liên tục; không phải link nào cũng tải/phân tích được.
- Tải video theo hàng đợi tuần tự; lấy văn bản xử lý một video mỗi lần.
- Tiến độ đầu quá trình là theo **trạng thái**; một số nguồn không cung cấp kích thước/ETA.
- Chưa kiểm thử tích hợp trên Windows thật. Cần kiểm tra tải, nhận dạng và giao diện trực tiếp.
- Chỉ tải tài liệu bạn sở hữu hoặc có quyền lưu. Không vượt DRM hoặc quyền truy cập.

Bản Tkinter cũ vẫn còn ở \`app.py\` nếu cần quay lại.
