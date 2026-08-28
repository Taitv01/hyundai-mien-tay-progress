# Hyundai Miền Tây – Quản lý tiến độ thi công

Ứng dụng Streamlit dành cho dự án Đại lý 3S xe thương mại Hyundai Miền Tây tại Cần Thơ, theo dõi giai đoạn tháng 7–12/2026.

## Chức năng đã hoàn thiện

- Chỉnh sửa tiến độ, ngày thực hiện, tỷ lệ hoàn thành, người phụ trách và ghi chú.
- Tự chuẩn hóa tỷ lệ/trạng thái, phát hiện quá hạn và nhắc việc đến hạn trong 7 ngày.
- Chọn ngày theo dõi để xem lại trạng thái dự án tại một mốc bất kỳ.
- Checklist nội bộ tham chiếu QCVN 121:2024/BGTVT; 9 điều kiện đặc thù xe điện/hybrid đang tạm ẩn nhưng vẫn được bảo lưu trong dữ liệu.
- Gantt tương tác, đường mốc ngày theo dõi, biểu đồ trạng thái và tiến độ theo phân khu.
- Tải báo cáo CSV/XLSX.
- Mở link là xem và cập nhật được ngay, không yêu cầu đăng nhập.
- Đại lý cập nhật phần trăm, trạng thái, ghi chú và nhiều ảnh hiện trường trực tiếp trên điện thoại.
- Ảnh được xác thực, xoay theo EXIF, thu nhỏ và nén trước khi lưu trong bucket riêng tư.
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
- **Supabase Storage:** lưu ảnh trong bucket riêng tư; ảnh chỉ được xem qua URL có thời hạn.
- **Streamlit secrets:** giữ khóa dịch vụ phía máy chủ, không đưa khóa lên GitHub hay trình duyệt.

Khởi tạo backend một lần bằng cách chạy toàn bộ [supabase_setup.sql](supabase_setup.sql) trong Supabase SQL Editor. Sau đó khai báo `SUPABASE_URL` và `SUPABASE_SERVICE_ROLE_KEY` theo tệp `.streamlit/secrets.toml.example`. Hệ thống tự nạp 16 hạng mục cùng 51 điểm kiểm soát ban đầu.

## Quy trình sử dụng cho đại lý

1. Mở link ứng dụng; không cần tài khoản hay mật khẩu.
2. Chọn **Cập nhật hiện trường**, chọn hạng mục cần báo cáo.
3. Chọn tiến độ, trạng thái, nhập nội dung và chọn/chụp ảnh.
4. Bấm **Lưu cập nhật**. Nhật ký và ảnh xuất hiện ngay bên dưới.

Chỉ chia sẻ link cho Ban QLDA và Đại lý vì người có link có thể thay đổi tiến độ và tải ảnh.

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
├── .streamlit/config.toml          # Giao diện và cấu hình máy chủ
├── .streamlit/secrets.toml.example # Mẫu secrets an toàn
└── tests/                          # Kiểm thử logic và smoke test
```

## Triển khai Streamlit Community Cloud

1. Đẩy nội dung thư mục này lên kho GitHub không chứa secrets.
2. Chọn entry point `app.py`.
3. Sao chép `SUPABASE_URL` và `SUPABASE_SERVICE_ROLE_KEY` vào phần **Advanced settings → Secrets**.
4. Không đưa khóa JSON thật vào kho mã nguồn.
