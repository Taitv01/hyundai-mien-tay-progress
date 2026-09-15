# Hyundai Miền Tây – Quản lý tiến độ thi công

Ứng dụng Streamlit dành cho dự án Đại lý 3S xe thương mại Hyundai Miền Tây tại Cần Thơ, theo dõi giai đoạn 3 và các mốc đến tháng 3/2027.

## Cam kết chủ đầu tư ngày 15/09/2026

- Gantt và báo cáo có hai mức **Hạng mục lớn** (mặc định) / **Công việc chi tiết**. Mức tổng hợp gồm 10 hạng mục 6–15; Gantt hiện 9 hạng mục vì mục 15 tạm ẩn. Có bộ lọc chọn hạng mục lớn cho cả hai mức xem Gantt.
- PDF/HTML/Excel xuất theo mức báo cáo đã chọn. Báo cáo tổng hợp PDF gồm 2 trang: Gantt và bảng hạng mục lớn, không liệt kê các công việc con.
- Thời gian hạng mục lớn bao quát các công việc có mốc áp dụng; tỷ lệ là bình quân công việc con, chưa tính trọng số. Bốn mốc đặt hàng cũ không gộp vào thời gian hoặc tỷ lệ tổng hợp. Dữ liệu tổng hợp chỉ dùng để xem và xuất báo cáo, không ghi đè công việc chi tiết.

- Đối chiếu 58 công việc chi tiết thuộc mục 7–15 với `260915_Tiến độ xây dựng Hyundai Cần Thơ.pdf`, thay cho 12 dòng thi công tổng hợp trước đây. Giữ 4 công việc trước mục 7: tổng cộng 62 công việc hiện hành.
- Mỗi dòng có mã `CK-<mục>-<thứ tự>`, P.I.C, tuần bắt đầu/kết thúc và trang PDF để đối chiếu. Bản cam kết gốc được lưu trong `commitment_20260915.json`, độc lập với các ngày điều chỉnh và ghi chú thực tế.
- Thanh kế hoạch áp dụng từ mục 7 dùng màu nâu `#8B5E3C`. Mục 15 (3 công việc D116) tạm ẩn trên Gantt ứng dụng, HTML và PDF; vẫn có trong bảng chi tiết, cập nhật hiện trường và dữ liệu xuất. Thiết bị D116 thuộc mục 9 vẫn hiện trên Gantt.
- Quy ước hiển thị ngày: W1 = 01–07, W2 = 08–14, W3 = 15–21, W4 = 22–cuối tháng. Đây là quy đổi mốc tuần, không phải ngày lẻ được chủ đầu tư xác nhận.
- Chuẩn bị hồ sơ GPXD: W3–W4 tháng 9; xin GPXD: W3 tháng 9–W2 tháng 10; san lấp: W4 tháng 9–W1 tháng 10; khai trương: W4 tháng 12/2026; cấp chứng nhận: W4 tháng 3/2027.
- Bốn dòng đặt hàng chỉ có mốc cũ màu xanh lá được giữ với ghi chú chưa có mốc mới. Ô “39” ở dòng chuẩn bị hồ sơ GPXD được đối chiếu theo ô W4 tháng 9, không chuyển thành ngày 39.
- Dữ liệu và hồ sơ của 12 công việc tổng hợp cũ được bảo lưu trên Supabase, xem trong mục “Danh mục tổng hợp trước khi đối chiếu PDF”. Không cộng trùng vào tiến độ hiện hành.
- Báo cáo HTML/Excel dùng dữ liệu hiện tại. Bấm **Tạo PDF theo dữ liệu hiện tại** để tạo và tải PDF nhiều trang; không sử dụng lại PDF ngày 08/09 với tên mới.

Kiểm thử: `py -m pytest tests -q` (chạy từ thư mục ứng dụng).

## Chức năng đã hoàn thiện

- Chỉnh sửa tiến độ, ngày thực hiện, tỷ lệ hoàn thành, người phụ trách và ghi chú.
- Tự chuẩn hóa tỷ lệ/trạng thái, phát hiện quá hạn và nhắc việc đến hạn trong 7 ngày.
- Chọn ngày theo dõi để xem lại trạng thái dự án tại một mốc bất kỳ.
- Checklist nội bộ tham chiếu QCVN 121:2024/BGTVT; 9 điều kiện đặc thù xe điện/hybrid đang tạm ẩn nhưng vẫn được bảo lưu trong dữ liệu.
- Gantt tương tác, đường mốc ngày theo dõi, biểu đồ trạng thái và tiến độ theo phân khu.
- Báo cáo giám sát hiện trường: PDF và HTML A4 khổ ngang, Gantt theo tuần và bảng WBS chi tiết theo cam kết CĐT.
- Trình xem trước bản in (Print Preview) trực tiếp trong app và tính năng sinh Form in HTML động theo dữ liệu thời gian thực.
- Tải trọn bộ dữ liệu Excel XLSX và CSV.
- Mở link là xem và cập nhật được ngay, không yêu cầu đăng nhập.
- Đại lý cập nhật phần trăm, trạng thái, ghi chú, chụp/chọn nhiều ảnh hiện trường và đính kèm tệp tài liệu PDF (biên bản nghiệm thu, bản vẽ kỹ thuật, chứng chỉ...).
- Quản lý tệp tập trung: Thư viện hồ sơ hỗ trợ lọc theo hạng mục, lọc theo loại tệp (PDF / Ảnh), tìm kiếm, xem trước trực tiếp (iframe PDF/ảnh), tải về và xóa tệp an toàn.
- Ảnh được xác thực, xoay theo EXIF, thu nhỏ và nén; tệp PDF được kiểm tra cấu trúc và dung lượng trước khi lưu trong bucket riêng tư.
- Dữ liệu online lưu tập trung trên Supabase; Google Sheets chỉ còn là chế độ tùy chọn khi chạy cục bộ.

> Lưu ý pháp lý: 51 dòng trong ứng dụng là checklist quản lý nội bộ, không phải 51 điều khoản nguyên văn của QCVN. Theo mục 3.1 của QCVN 121:2024/BGTVT, cơ sở phải công bố hợp quy trước khi hoạt động; việc công bố dựa trên kết quả của tổ chức đánh giá sự phù hợp được chỉ định. Ba nhóm thiết bị cho xe điện/hybrid tại mục 2.2.2.17–2.2.2.19 phải được cấu hình theo yêu cầu hoặc quy định của nhà sản xuất xe. Luôn đối chiếu [văn bản QCVN 121 chính thức](https://vbpl.vn/FileData/TW/Lists/vbpq/Attachments/173120/VanBanGoc_Th%C3%B4ng%20t%C6%B0%2050.2024.TT-BGTVT.%20QCVN%20121.pdf) và tư vấn chuyên môn trước khi dùng checklist cho hồ sơ công bố hợp quy.

## Chạy cục bộ

Yêu cầu Python 3.10 trở lên. Tại thư mục ứng dụng, chạy:

```powershell
py -m pip install -r requirements.txt
py -m streamlit run app.py
```

Mở `http://localhost:8501`. Nếu chưa cấu hình Google Sheets, ứng dụng vẫn hoạt động bình thường với dữ liệu trong phiên trình duyệt; dữ liệu phiên sẽ mất khi đóng tab hoặc khởi động lại máy chủ.

## Mô hình online khuyến nghị

- **Streamlit Community Cloud:** cung cấp đường link HTTPS để mở trên máy tính hoặc điện thoại.
- **Supabase Database:** lưu tiến độ, checklist, tài khoản và nhật ký thay đổi.
- **Supabase Storage:** lưu ảnh và tệp PDF trong bucket riêng tư; tệp chỉ được xem qua URL có thời hạn.
- **Streamlit secrets:** giữ khóa dịch vụ phía máy chủ, không đưa khóa lên GitHub hay trình duyệt.

Khởi tạo backend một lần bằng cách chạy toàn bộ [supabase_setup.sql](supabase_setup.sql) trong Supabase SQL Editor. Sau đó khai báo `SUPABASE_URL` và `SUPABASE_SERVICE_ROLE_KEY` theo tệp `.streamlit/secrets.toml.example`. Kho trống tự nạp 62 công việc cùng 51 điểm kiểm soát ban đầu. Kho đã có dữ liệu cần nạp thêm các mã cam kết mới; không ghi đè các bản ghi thực tế cũ.

## Quy trình sử dụng cho đại lý

1. Mở link ứng dụng; không cần tài khoản hay mật khẩu.
2. Chọn **Cập nhật hiện trường & File**, chọn hạng mục cần báo cáo.
3. Chọn tiến độ, trạng thái, nhập nội dung, chọn/chụp ảnh và đính kèm tệp PDF nếu có.
4. Bấm **Lưu cập nhật**. Nhật ký, ảnh và file PDF xuất hiện ngay trong nhật ký.
5. Mở tab con **Quản lý file & Hồ sơ hiện trường** để tra cứu, xem trước, tải về hoặc xóa tệp khi cần.

Chỉ chia sẻ link cho Ban QLDA và Đại lý vì người có link có thể thay đổi tiến độ và tải ảnh/tệp.

## Google Sheets (tùy chọn khi chạy cục bộ)

1. Tạo dự án Google Cloud, bật Google Sheets API và Google Drive API.
2. Tạo Service Account và tải khóa JSON.
3. Chia sẻ Google Sheet cho email Service Account với quyền Editor.
4. Sao chép `.streamlit/secrets.toml.example` thành `.streamlit/secrets.toml`.
5. Điền `spreadsheet_url` và các trường Service Account vào tệp secrets.
6. Khởi động lại ứng dụng, mở mục “Đồng bộ Google Sheets” ở thanh bên rồi chọn “Tải từ Sheet” hoặc “Lưu lên Sheet”.

Ứng dụng sử dụng hai worksheet:

- `Tien_Do_Thi_Cong`
- `QCVN_121_Checklist`

Không dán khóa Service Account vào giao diện và không commit `.streamlit/secrets.toml`. Tệp này đã được chặn trong `.gitignore`.

## Cấu trúc

```text
08_App_Theo_doi_Tien_do_Thi_cong/
├── app.py                         # Giao diện Streamlit
├── data_service.py                # Chuẩn hóa dữ liệu và Google Sheets
├── supabase_service.py            # Tài khoản, dữ liệu online và xử lý ảnh
├── supabase_setup.sql              # Lược đồ database/storage chạy một lần
├── requirements.txt               # Thư viện chạy ứng dụng
├── credentials_sample.json        # Khóa mẫu, không dùng để đăng nhập
├── reports/                       # Form báo cáo chuẩn (PDF điều hành & HTML in ấn A4)
├── .streamlit/config.toml          # Giao diện và cấu hình máy chủ
├── .streamlit/secrets.toml.example # Mẫu secrets an toàn
└── tests/                          # Kiểm thử logic và smoke test
```

## Triển khai Streamlit Community Cloud

1. Đẩy nội dung thư mục này lên kho GitHub không chứa secrets.
2. Chọn entry point `app.py`.
3. Sao chép `SUPABASE_URL` và `SUPABASE_SERVICE_ROLE_KEY` vào phần **Advanced settings → Secrets**.
4. Không đưa khóa JSON thật vào kho mã nguồn.
