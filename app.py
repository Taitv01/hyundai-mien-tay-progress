# -*- coding: utf-8 -*-
"""
HỆ THỐNG QUẢN LÝ TIẾN ĐỘ THI CÔNG & CHỨNG NHẬN QCVN 121
DỰ ÁN: ĐẠI LÝ 3S XE THƯƠNG MẠI HYUNDAI MIỀN TÂY (GIAI ĐOẠN 3: T7/2026 - T12/2026)
Tích hợp: Cảnh báo Quá hạn, Nhắc nhở Chậm tiến độ & Đường Line Đỏ Thời gian thực trên Gantt Chart
"""

import streamlit as st
import pandas as pd
import datetime
import plotly.express as px

from data_service import (
    credentials_from_config,
    load_from_google_sheets,
    normalize_progress_data,
    normalize_qcvn_data,
    save_to_google_sheets,
)
from supabase_service import AppUser, OnlineSettings, ROLE_LABELS, SupabaseService


# Theo yêu cầu vận hành hiện tại: mở link là có thể cập nhật.
PUBLIC_ACCESS_MODE = True
# Dữ liệu EV/Hybrid vẫn được giữ trong Supabase và chỉ tạm ẩn khỏi giao diện.
SHOW_EV_HYBRID_CHECKLIST = False

# ==============================================================================
# 1. CẤU HÌNH TRANG & GIAO DIỆN
# ==============================================================================
st.set_page_config(
    page_title="Tiến độ Hyundai Miền Tây | QCVN 121",
    page_icon="🚛",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .hero-container {
        background: linear-gradient(135deg, #002C6C 0%, #001737 100%);
        color: white;
        padding: 1.5rem 2rem;
        border-radius: 12px;
        margin-bottom: 1.2rem;
        border-left: 6px solid #00AAD2;
        box-shadow: 0 4px 12px rgba(0, 44, 108, 0.15);
    }
    .hero-title {
        font-size: 1.8rem;
        font-weight: 700;
        margin: 0;
        color: #FFFFFF !important;
    }
    .hero-sub {
        font-size: 0.95rem;
        color: #CBD5E1;
        margin-top: 0.3rem;
    }
    
    /* Alert Boxes */
    .overdue-alert-box {
        background-color: #FEF2F2;
        border: 1px solid #FECACA;
        border-left: 6px solid #DC2626;
        border-radius: 10px;
        padding: 1rem 1.4rem;
        margin-bottom: 1.2rem;
    }
    .urgent-alert-box {
        background-color: #FFFBEB;
        border: 1px solid #FDE68A;
        border-left: 6px solid #F59E0B;
        border-radius: 10px;
        padding: 1rem 1.4rem;
        margin-bottom: 1.2rem;
    }
    .ev-highlight-card {
        background-color: #F0FDF4;
        border: 1px solid #BBF7D0;
        border-left: 5px solid #16A34A;
        border-radius: 10px;
        padding: 1rem 1.2rem;
        margin-bottom: 1rem;
    }

    /* Tab Buttons */
    button[data-baseweb="tab"] {
        font-size: 1rem !important;
        font-weight: 600 !important;
        padding: 10px 20px !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        color: #002C6C !important;
        font-weight: 700 !important;
        border-bottom-color: #002C6C !important;
    }
</style>
""", unsafe_allow_html=True)


# ==============================================================================
# 2. KHỞI TẠO BỘ DỮ LIỆU & TỰ ĐỘNG TÍNH TOÁN CẢNH BÁO TIẾN ĐỘ
# ==============================================================================

def get_initial_progress_data():
    """Khởi tạo danh mục tiến độ thi công Giai đoạn 3 (T7/2026 - T12/2026)"""
    data = [
        # Nhóm mốc quan trọng tháng 8 & 9/2026 (Pháp lý & Thiết kế)
        {
            "Mã": "PL-01",
            "Hạng mục công việc": "Lên bản vẽ chi tiết (dựa trên BV layout và 3D)",
            "Phân khu": "Thiết kế & Pháp lý",
            "Bắt đầu": datetime.date(2026, 8, 15),
            "Hoàn thành": datetime.date(2026, 8, 29),
            "Tiến độ (%)": 100,
            "Trạng thái": "Đã hoàn thiện",
            "Người phụ trách": "Ban QLDA / TVTK",
            "Ghi chú": "Cột mốc quan trọng 29/08/2026"
        },
        {
            "Mã": "PL-02",
            "Hạng mục công việc": "Hoàn thiện thiết kế chi tiết & hồ sơ xin phép",
            "Phân khu": "Thiết kế & Pháp lý",
            "Bắt đầu": datetime.date(2026, 8, 20),
            "Hoàn thành": datetime.date(2026, 8, 30),
            "Tiến độ (%)": 85,
            "Trạng thái": "Đang thi công",
            "Người phụ trách": "Ban QLDA",
            "Ghi chú": "Cột mốc quan trọng 30/08/2026"
        },
        {
            "Mã": "PL-03",
            "Hạng mục công việc": "Ký hợp đồng thuê mặt bằng (chưa công chứng)",
            "Phân khu": "Mặt bằng & Pháp lý",
            "Bắt đầu": datetime.date(2026, 9, 1),
            "Hoàn thành": datetime.date(2026, 9, 12),
            "Tiến độ (%)": 0,
            "Trạng thái": "Chưa thực hiện",
            "Người phụ trách": "Ban Giám Đốc / Pháp chế",
            "Ghi chú": "Mốc cam kết 12/09/2026"
        },
        {
            "Mã": "PL-04",
            "Hạng mục công việc": "Đặt cọc thuê đất mặt bằng đại lý",
            "Phân khu": "Mặt bằng & Pháp lý",
            "Bắt đầu": datetime.date(2026, 9, 13),
            "Hoàn thành": datetime.date(2026, 9, 19),
            "Tiến độ (%)": 0,
            "Trạng thái": "Chưa thực hiện",
            "Người phụ trách": "Ban Tài chính - Kế toán",
            "Ghi chú": "Mốc thanh toán cọc 19/09/2026"
        },
        
        # Nhóm Showroom (Phần XDCB) - Bắt đầu sau khi hoàn tất thuê/cọc đất
        {
            "Mã": "SR-01",
            "Hạng mục công việc": "Showroom: Xây, trát tường bao & tường ngăn",
            "Phân khu": "Showroom (XDCB)",
            "Bắt đầu": datetime.date(2026, 9, 20),
            "Hoàn thành": datetime.date(2026, 10, 15),
            "Tiến độ (%)": 0,
            "Trạng thái": "Chưa thực hiện",
            "Người phụ trách": "Nhà thầu xây dựng",
            "Ghi chú": "Bắt đầu sau khi cọc đất (20/09/2026)"
        },
        {
            "Mã": "SR-02",
            "Hạng mục công việc": "Showroom: Ốp lát gạch nền granite & khu vệ sinh",
            "Phân khu": "Showroom (XDCB)",
            "Bắt đầu": datetime.date(2026, 10, 16),
            "Hoàn thành": datetime.date(2026, 11, 5),
            "Tiến độ (%)": 0,
            "Trạng thái": "Chưa thực hiện",
            "Người phụ trách": "Nhà thầu hoàn thiện",
            "Ghi chú": "Gạch granite chống trượt GDSI"
        },
        {
            "Mã": "SR-03",
            "Hạng mục công việc": "Showroom: Gia công lắp dựng vách kính, cửa nhôm",
            "Phân khu": "Showroom (XDCB)",
            "Bắt đầu": datetime.date(2026, 11, 1),
            "Hoàn thành": datetime.date(2026, 11, 20),
            "Tiến độ (%)": 0,
            "Trạng thái": "Chưa thực hiện",
            "Người phụ trách": "Nhà thầu nhôm kính",
            "Ghi chú": "Kính cường lực an toàn mặt tiền"
        },
        {
            "Mã": "SR-04",
            "Hạng mục công việc": "Showroom: Bả matit, sơn nước trong và ngoài",
            "Phân khu": "Showroom (XDCB)",
            "Bắt đầu": datetime.date(2026, 11, 10),
            "Hoàn thành": datetime.date(2026, 11, 30),
            "Tiến độ (%)": 0,
            "Trạng thái": "Chưa thực hiện",
            "Người phụ trách": "Nhà thầu sơn",
            "Ghi chú": "Màu chuẩn nhận diện thương hiệu"
        },
        {
            "Mã": "SR-05",
            "Hạng mục công việc": "Showroom: Lắp đặt hệ thống Điện, Nước & Chiếu sáng",
            "Phân khu": "Showroom (XDCB)",
            "Bắt đầu": datetime.date(2026, 10, 15),
            "Hoàn thành": datetime.date(2026, 11, 25),
            "Tiến độ (%)": 0,
            "Trạng thái": "Chưa thực hiện",
            "Người phụ trách": "Nhà thầu M&E",
            "Ghi chú": "Dự kiến bắt đầu 15/10/2026"
        },

        # Nhóm Xưởng Dịch vụ & Thiết bị kiểm định (QCVN 121)
        {
            "Mã": "WS-01",
            "Hạng mục công việc": "Xưởng dịch vụ: Nền bê tông chịu tải & sơn Epoxy",
            "Phân khu": "Xưởng Dịch vụ 3S",
            "Bắt đầu": datetime.date(2026, 9, 25),
            "Hoàn thành": datetime.date(2026, 10, 30),
            "Tiến độ (%)": 0,
            "Trạng thái": "Chưa thực hiện",
            "Người phụ trách": "Nhà thầu xây dựng",
            "Ghi chú": "Dự kiến bắt đầu 25/09/2026"
        },
        {
            "Mã": "WS-02",
            "Hạng mục công việc": "Lắp đặt hệ thống cầu nâng tải trọng lớn & cầu cắt kéo",
            "Phân khu": "Xưởng Dịch vụ 3S",
            "Bắt đầu": datetime.date(2026, 11, 1),
            "Hoàn thành": datetime.date(2026, 11, 20),
            "Tiến độ (%)": 0,
            "Trạng thái": "Chưa thực hiện",
            "Người phụ trách": "NCC Thiết bị Garage",
            "Ghi chú": "Cầu nâng xe tải 2 trụ & 4 trụ"
        },
        {
            "Mã": "WS-03",
            "Hạng mục công việc": "Lắp đặt dây chuyền kiểm định KCS (Phanh, Đèn, Khói/Khí thải)",
            "Phân khu": "Thiết bị QCVN 121",
            "Bắt đầu": datetime.date(2026, 11, 15),
            "Hoàn thành": datetime.date(2026, 12, 5),
            "Tiến độ (%)": 0,
            "Trạng thái": "Chưa thực hiện",
            "Người phụ trách": "NCC Thiết bị kiểm định",
            "Ghi chú": "Bắt buộc theo QCVN 121:2024"
        },
        {
            "Mã": "WS-04",
            "Hạng mục công việc": "Trang bị dụng cụ bảo hộ cách điện & bàn nâng pin Xe Điện/Hybrid",
            "Phân khu": "Trang bị Xe Điện (EV)",
            "Bắt đầu": datetime.date(2026, 11, 20),
            "Hoàn thành": datetime.date(2026, 12, 10),
            "Tiến độ (%)": 0,
            "Trạng thái": "Chưa thực hiện",
            "Người phụ trách": "Bộ phận Kỹ thuật / Dịch vụ",
            "Ghi chú": "Đặc thù bắt buộc cho EV/Hybrid"
        },
        {
            "Mã": "WS-05",
            "Hạng mục công việc": "Nghiệm thu PCCC & Hệ thống xử lý nước thải dịch vụ",
            "Phân khu": "Môi trường & PCCC",
            "Bắt đầu": datetime.date(2026, 11, 25),
            "Hoàn thành": datetime.date(2026, 12, 15),
            "Tiến độ (%)": 0,
            "Trạng thái": "Chưa thực hiện",
            "Người phụ trách": "Cơ quan PCCC / Môi trường",
            "Ghi chú": "Điều kiện cần để cấp chứng nhận"
        },
        {
            "Mã": "OP-01",
            "Hạng mục công việc": "Đánh giá cấp Chứng nhận cơ sở bảo hành bảo dưỡng QCVN 121:2024/BGTVT",
            "Phân khu": "Kiểm định & Chứng nhận",
            "Bắt đầu": datetime.date(2026, 12, 10),
            "Hoàn thành": datetime.date(2026, 12, 25),
            "Tiến độ (%)": 0,
            "Trạng thái": "Chưa thực hiện",
            "Người phụ trách": "Tổ chức đánh giá sự phù hợp / Cơ quan tiếp nhận",
            "Ghi chú": "Công bố hợp quy trước khi đưa cơ sở vào hoạt động"
        },
        {
            "Mã": "OP-02",
            "Hạng mục công việc": "HTCV nghiệm thu tiêu chuẩn đại lý & Khai trương hoạt động",
            "Phân khu": "Vận hành & Khai trương",
            "Bắt đầu": datetime.date(2026, 12, 20),
            "Hoàn thành": datetime.date(2026, 12, 31),
            "Tiến độ (%)": 0,
            "Trạng thái": "Chưa thực hiện",
            "Người phụ trách": "Ban Giám Đốc & HTCV",
            "Ghi chú": "Chính thức đi vào hoạt động"
        }
    ]
    df = pd.DataFrame(data)
    df["Bắt đầu"] = pd.to_datetime(df["Bắt đầu"]).dt.date
    df["Hoàn thành"] = pd.to_datetime(df["Hoàn thành"]).dt.date
    df["Tiến độ (%)"] = df["Tiến độ (%)"].astype(int)
    return df


def get_qcvn121_items():
    """Checklist nội bộ 51 điểm kiểm soát có tham chiếu QCVN 121:2024/BGTVT."""
    items = [
        # Nhóm I: Mặt bằng & Cơ sở hạ tầng (1-10)
        {"STT": 1, "Nhóm": "I. Mặt bằng & Cơ sở hạ tầng", "Hạng mục": "Diện tích mặt bằng phù hợp với quy mô và tải trọng xe thương mại", "Đặc thù EV": False, "Đánh giá": "Đạt", "Ghi chú": "Diện tích > 4.000m2"},
        {"STT": 2, "Nhóm": "I. Mặt bằng & Cơ sở hạ tầng", "Hạng mục": "Khu vực tiếp nhận và trả xe rộng rãi, thông thoáng", "Đặc thù EV": False, "Đánh giá": "Đạt", "Ghi chú": "Bố trí tại cửa xưởng dịch vụ"},
        {"STT": 3, "Nhóm": "I. Mặt bằng & Cơ sở hạ tầng", "Hạng mục": "Khu vực bảo dưỡng nhanh và sửa chữa chung phân khoang rõ ràng", "Đặc thù EV": False, "Đánh giá": "Đang thi công", "Ghi chú": "Có vạch sơn phân chia khoang"},
        {"STT": 4, "Nhóm": "I. Mặt bằng & Cơ sở hạ tầng", "Hạng mục": "Khu vực kiểm tra chất lượng xuất xưởng (KCS)", "Đặc thù EV": False, "Đánh giá": "Chưa đạt", "Ghi chú": "Bố trí cuối dây chuyền"},
        {"STT": 5, "Nhóm": "I. Mặt bằng & Cơ sở hạ tầng", "Hạng mục": "Khu vực rửa xe và làm sạch chi tiết", "Đặc thù EV": False, "Đánh giá": "Đang thi công", "Ghi chú": "Có hố thu gom bùn cát"},
        {"STT": 6, "Nhóm": "I. Mặt bằng & Cơ sở hạ tầng", "Hạng mục": "Kho phụ tùng, vật tư thay thế chính hãng theo chuẩn GDSI", "Đặc thù EV": False, "Đánh giá": "Đang thi công", "Ghi chú": "Giá kệ tiêu chuẩn Hyundai"},
        {"STT": 7, "Nhóm": "I. Mặt bằng & Cơ sở hạ tầng", "Hạng mục": "Bãi đỗ xe chờ sửa chữa và xe đã hoàn thiện", "Đặc thù EV": False, "Đánh giá": "Đạt", "Ghi chú": "Sức chứa > 20 xe tải"},
        {"STT": 8, "Nhóm": "I. Mặt bằng & Cơ sở hạ tầng", "Hạng mục": "Đường nội bộ thuận tiện cho xe tải nặng, xe khách quay đầu", "Đặc thù EV": False, "Đánh giá": "Đạt", "Ghi chú": "Lộ giới nội bộ > 8 mét"},
        {"STT": 9, "Nhóm": "I. Mặt bằng & Cơ sở hạ tầng", "Hạng mục": "Hệ thống thông gió, thu gom khí xả động cơ trong xưởng", "Đặc thù EV": False, "Đánh giá": "Chưa đạt", "Ghi chú": "Ống hút mềm chịu nhiệt"},
        {"STT": 10, "Nhóm": "I. Mặt bằng & Cơ sở hạ tầng", "Hạng mục": "Hệ thống chiếu sáng tự nhiên và đèn LED đạt chuẩn độ rọi", "Đặc thù EV": False, "Đánh giá": "Đang thi công", "Ghi chú": "Độ rọi > 300 lux"},

        # Nhóm II: Thiết bị sửa chữa & Nâng hạ (11-25)
        {"STT": 11, "Nhóm": "II. Thiết bị sửa chữa & Nâng hạ", "Hạng mục": "Cầu nâng xe ô tô tải trọng phù hợp (2 trụ/4 trụ/cắt kéo)", "Đặc thù EV": False, "Đánh giá": "Đang mua sắm", "Ghi chú": "Đã có kiểm định an toàn"},
        {"STT": 12, "Nhóm": "II. Thiết bị sửa chữa & Nâng hạ", "Hạng mục": "Kích cá sấu thủy lực, giá đỡ an toàn chữ A (Mễ kê tải nặng)", "Đặc thù EV": False, "Đánh giá": "Đang mua sắm", "Ghi chú": "Tải trọng 5 - 15 tấn"},
        {"STT": 13, "Nhóm": "II. Thiết bị sửa chữa & Nâng hạ", "Hạng mục": "Cần cẩu móc động cơ di động thủy lực", "Đặc thù EV": False, "Đánh giá": "Đang mua sắm", "Ghi chú": "Sức nâng 2 - 3 tấn"},
        {"STT": 14, "Nhóm": "II. Thiết bị sửa chữa & Nâng hạ", "Hạng mục": "Thiết bị kích nâng hạ hộp số chuyên dùng", "Đặc thù EV": False, "Đánh giá": "Đang mua sắm", "Ghi chú": "Loại sàn/hầm chuyên dụng"},
        {"STT": 15, "Nhóm": "II. Thiết bị sửa chữa & Nâng hạ", "Hạng mục": "Máy nén khí và hệ thống đường ống dẫn khí nén cao áp", "Đặc thù EV": False, "Đánh giá": "Đang mua sắm", "Ghi chú": "Áp lực 10 - 12 bar"},
        {"STT": 16, "Nhóm": "II. Thiết bị sửa chữa & Nâng hạ", "Hạng mục": "Thiết bị tháo lắp lốp xe thương mại hạng nặng", "Đặc thù EV": False, "Đánh giá": "Đang mua sắm", "Ghi chú": "Đường kính mâm đến 26 inch"},
        {"STT": 17, "Nhóm": "II. Thiết bị sửa chữa & Nâng hạ", "Hạng mục": "Máy cân bằng động bánh xe điện tử", "Đặc thù EV": False, "Đánh giá": "Đang mua sắm", "Ghi chú": "Màn hình LED hiển thị"},
        {"STT": 18, "Nhóm": "II. Thiết bị sửa chữa & Nâng hạ", "Hạng mục": "Bộ cờ lê cân lực (cần xiết lực có kiểm định hiệu chuẩn)", "Đặc thù EV": False, "Đánh giá": "Đang mua sắm", "Ghi chú": "Dải đo từ 20 đến 800 Nm"},
        {"STT": 19, "Nhóm": "II. Thiết bị sửa chữa & Nâng hạ", "Hạng mục": "Tủ đồ nghề dụng cụ cầm tay tiêu chuẩn cho KTV", "Đặc thù EV": False, "Đánh giá": "Đạt", "Ghi chú": "Trang bị theo từng khoang"},
        {"STT": 20, "Nhóm": "II. Thiết bị sửa chữa & Nâng hạ", "Hạng mục": "Thiết bị chẩn đoán lỗi điện tử chuyên hãng Hyundai (GDS-M)", "Đặc thù EV": False, "Đánh giá": "Đạt", "Ghi chú": "Bản quyền chính hãng HTCV"},
        {"STT": 21, "Nhóm": "II. Thiết bị sửa chữa & Nâng hạ", "Hạng mục": "Thiết bị kiểm tra, nạp và bảo dưỡng bình ắc quy", "Đặc thù EV": False, "Đánh giá": "Đang mua sắm", "Ghi chú": "Đo nội trở và dung lượng"},
        {"STT": 22, "Nhóm": "II. Thiết bị sửa chữa & Nâng hạ", "Hạng mục": "Máy hút, thu hồi và nạp gas điều hòa tự động", "Đặc thù EV": False, "Đánh giá": "Đang mua sắm", "Ghi chú": "Gas R134a / R1234yf"},
        {"STT": 23, "Nhóm": "II. Thiết bị sửa chữa & Nâng hạ", "Hạng mục": "Thiết bị thay dầu phanh và xả gió phanh tự động", "Đặc thù EV": False, "Đánh giá": "Đang mua sắm", "Ghi chú": "Áp lực khí nén"},
        {"STT": 24, "Nhóm": "II. Thiết bị sửa chữa & Nâng hạ", "Hạng mục": "Thiết bị hút/hứng dầu nhớt thải di động", "Đặc thù EV": False, "Đánh giá": "Đang mua sắm", "Ghi chú": "Bình chứa 80 lít"},
        {"STT": 25, "Nhóm": "II. Thiết bị sửa chữa & Nâng hạ", "Hạng mục": "Máy ép thủy lực trục đứng", "Đặc thù EV": False, "Đánh giá": "Đang mua sắm", "Ghi chú": "Lực ép 30 - 50 tấn"},

        # Nhóm III: Thiết bị kiểm định xuất xưởng (26-32)
        {"STT": 26, "Nhóm": "III. Thiết bị kiểm định KCS", "Hạng mục": "Thiết bị kiểm tra phanh xe thương mại (Băng thử rulo tải nặng)", "Đặc thù EV": False, "Đánh giá": "Đang mua sắm", "Ghi chú": "Tải trọng trục 13 tấn"},
        {"STT": 27, "Nhóm": "III. Thiết bị kiểm định KCS", "Hạng mục": "Thiết bị kiểm tra độ trượt ngang bánh xe", "Đặc thù EV": False, "Đánh giá": "Đang mua sắm", "Ghi chú": "Cảm biến điện tử chính xác"},
        {"STT": 28, "Nhóm": "III. Thiết bị kiểm định KCS", "Hạng mục": "Thiết bị kiểm tra và căn chỉnh góc chiếu đèn pha (Headlight tester)", "Đặc thù EV": False, "Đánh giá": "Đang mua sắm", "Ghi chú": "Camera kỹ thuật số tự động"},
        {"STT": 29, "Nhóm": "III. Thiết bị kiểm định KCS", "Hạng mục": "Thiết bị đo độ mờ khói khí thải động cơ Diesel", "Đặc thù EV": False, "Đánh giá": "Đang mua sắm", "Ghi chú": "Có tem kiểm định hiệu chuẩn"},
        {"STT": 30, "Nhóm": "III. Thiết bị kiểm định KCS", "Hạng mục": "Thiết bị đo nồng độ khí xả xe xăng (CO, HC, CO2, O2, Lambda)", "Đặc thù EV": False, "Đánh giá": "Đang mua sắm", "Ghi chú": "Chuẩn OIML Class 0"},
        {"STT": 31, "Nhóm": "III. Thiết bị kiểm định KCS", "Hạng mục": "Thiết bị đo độ ồn phương tiện", "Đặc thù EV": False, "Đánh giá": "Đang mua sắm", "Ghi chú": "Dải đo 30 - 130 dBA"},
        {"STT": 32, "Nhóm": "III. Thiết bị kiểm định KCS", "Hạng mục": "Thiết bị đo độ rơ và góc quay vô lăng lái", "Đặc thù EV": False, "Đánh giá": "Đang mua sắm", "Ghi chú": "Thước đo chuyên dụng"},

        # Nhóm IV: YÊU CẦU ĐẶC THÙ XE ĐIỆN & HYBRID (33-40) - HIGHLIGHT
        {"STT": 33, "Nhóm": "IV. Yêu cầu đặc thù XE ĐIỆN / HYBRID", "Hạng mục": "⚡ Thiết bị, dụng cụ bảo vệ an toàn cách điện cho kỹ thuật viên", "Đặc thù EV": True, "Đánh giá": "Đang mua sắm", "Ghi chú": "QCVN 121 mục 2.2.2.17: theo yêu cầu của nhà sản xuất xe"},
        {"STT": 34, "Nhóm": "IV. Yêu cầu đặc thù XE ĐIỆN / HYBRID", "Hạng mục": "⚡ Đồng hồ kiểm tra dòng điện và điện áp cao", "Đặc thù EV": True, "Đánh giá": "Đang mua sắm", "Ghi chú": "QCVN 121 mục 2.2.2.18: theo quy định của nhà sản xuất xe"},
        {"STT": 35, "Nhóm": "IV. Yêu cầu đặc thù XE ĐIỆN / HYBRID", "Hạng mục": "⚡ Thiết bị, dụng cụ nâng, hạ, di chuyển pin và sạc pin", "Đặc thù EV": True, "Đánh giá": "Đang mua sắm", "Ghi chú": "QCVN 121 mục 2.2.2.19: theo yêu cầu của nhà sản xuất xe"},
        {"STT": 36, "Nhóm": "IV. Yêu cầu đặc thù XE ĐIỆN / HYBRID", "Hạng mục": "⚡ Trụ sạc thử nghiệm và thiết bị chẩn đoán cổng sạc pin cao áp", "Đặc thù EV": True, "Đánh giá": "Chưa đạt", "Ghi chú": "Điểm kiểm soát nội bộ; xác nhận cấu hình với HTCV/nhà sản xuất"},
        {"STT": 37, "Nhóm": "IV. Yêu cầu đặc thù XE ĐIỆN / HYBRID", "Hạng mục": "⚡ Khu vực cách ly sự cố pin và phương tiện ứng phó cháy pin", "Đặc thù EV": True, "Đánh giá": "Chưa đạt", "Ghi chú": "Điểm kiểm soát nội bộ; xác nhận phương án với PCCC và nhà sản xuất"},
        {"STT": 38, "Nhóm": "IV. Yêu cầu đặc thù XE ĐIỆN / HYBRID", "Hạng mục": "⚡ Bộ dụng cụ sửa chữa cầm tay có cách điện phù hợp", "Đặc thù EV": True, "Đánh giá": "Đang mua sắm", "Ghi chú": "Điểm kiểm soát nội bộ; thông số theo tài liệu sửa chữa của hãng"},
        {"STT": 39, "Nhóm": "IV. Yêu cầu đặc thù XE ĐIỆN / HYBRID", "Hạng mục": "⚡ Biển cảnh báo và rào chắn cách ly khoang sửa xe điện", "Đặc thù EV": True, "Đánh giá": "Đang thi công", "Ghi chú": "Điểm kiểm soát nội bộ về an toàn vận hành"},
        {"STT": 40, "Nhóm": "IV. Yêu cầu đặc thù XE ĐIỆN / HYBRID", "Hạng mục": "⚡ Thiết bị giám sát nhiệt độ và bộ ngắt mạch khẩn cấp", "Đặc thù EV": True, "Đánh giá": "Đang mua sắm", "Ghi chú": "Điểm kiểm soát nội bộ; xác nhận với HTCV/nhà sản xuất"},

        # Nhóm V: PCCC, An toàn lao động & Môi trường (41-46)
        {"STT": 41, "Nhóm": "V. PCCC, ATLĐ & Môi trường", "Hạng mục": "Hệ thống PCCC tự động và bình chữa cháy xách tay thẩm duyệt", "Đặc thù EV": False, "Đánh giá": "Đang thi công", "Ghi chú": "Đã có thẩm duyệt thiết kế PCCC"},
        {"STT": 42, "Nhóm": "V. PCCC, ATLĐ & Môi trường", "Hạng mục": "Trang bị bảo hộ lao động cá nhân đầy đủ cho Kỹ thuật viên", "Đặc thù EV": False, "Đánh giá": "Đạt", "Ghi chú": "Quần áo, giày mũi thép, kính"},
        {"STT": 43, "Nhóm": "V. PCCC, ATLĐ & Môi trường", "Hạng mục": "Hệ thống xử lý nước thải dịch vụ đạt tiêu chuẩn QCVN 40", "Đặc thù EV": False, "Đánh giá": "Đang thi công", "Ghi chú": "Bể tách mỡ & hệ vi sinh"},
        {"STT": 44, "Nhóm": "V. PCCC, ATLĐ & Môi trường", "Hạng mục": "Khu vực lưu chứa chất thải nguy hại (nhớt thải, lọc nhớt, ắc quy)", "Đặc thù EV": False, "Đánh giá": "Đang thi công", "Ghi chú": "Kho kín có gờ chống tràn"},
        {"STT": 45, "Nhóm": "V. PCCC, ATLĐ & Môi trường", "Hạng mục": "Tủ thuốc và dụng cụ sơ cấp cứu y tế tại xưởng", "Đặc thù EV": False, "Đánh giá": "Đạt", "Ghi chú": "Đầy đủ vật tư cấp cứu ban đầu"},
        {"STT": 46, "Nhóm": "V. PCCC, ATLĐ & Môi trường", "Hạng mục": "Nội quy an toàn lao động và quy trình vận hành thiết bị niêm yết", "Đặc thù EV": False, "Đánh giá": "Đạt", "Ghi chú": "Bảng mica tại từng vị trí máy"},

        # Nhóm VI: Nhân sự & Hệ thống quản lý (47-51)
        {"STT": 47, "Nhóm": "VI. Nhân sự & Phần mềm quản lý", "Hạng mục": "Quản đốc xưởng / Trưởng phòng dịch vụ có bằng cấp chuyên ngành", "Đặc thù EV": False, "Đánh giá": "Đạt", "Ghi chú": "Đại học Ô tô / Chứng chỉ HTCV"},
        {"STT": 48, "Nhóm": "VI. Nhân sự & Phần mềm quản lý", "Hạng mục": "Đội ngũ Kỹ thuật viên có chứng chỉ đào tạo nghề ô tô hợp lệ", "Đặc thù EV": False, "Đánh giá": "Đạt", "Ghi chú": "100% KTV có bằng nghề"},
        {"STT": 49, "Nhóm": "VI. Nhân sự & Phần mềm quản lý", "Hạng mục": "⚡ Kỹ thuật viên phụ trách xe điện được đào tạo an toàn điện cao áp", "Đặc thù EV": True, "Đánh giá": "Đang đào tạo", "Ghi chú": "Điểm kiểm soát nội bộ theo chương trình đào tạo của HTCV"},
        {"STT": 50, "Nhóm": "VI. Nhân sự & Phần mềm quản lý", "Hạng mục": "Phần mềm DMS quản lý tiếp nhận và lịch sử sửa chữa bảo dưỡng", "Đặc thù EV": False, "Đánh giá": "Đạt", "Ghi chú": "Hệ thống DMS của HTCV"},
        {"STT": 51, "Nhóm": "VI. Nhân sự & Phần mềm quản lý", "Hạng mục": "Quy trình kiểm soát chất lượng dịch vụ và bảo hành bằng văn bản", "Đặc thù EV": False, "Đánh giá": "Đạt", "Ghi chú": "Ban hành quy trình chuẩn 3S"}
    ]
    df = pd.DataFrame(items)
    df["STT"] = df["STT"].astype(int)
    df["Đặc thù EV"] = df["Đặc thù EV"].astype(bool)
    return df


def calculate_progress_alerts(df, current_date=None):
    """Tương thích với tên hàm cũ; logic được kiểm thử trong data_service."""
    return normalize_progress_data(df, current_date=current_date)


def get_google_sheet_settings():
    """Đọc cấu hình Google Sheets phía máy chủ, không hiển thị khóa bí mật."""
    try:
        config = dict(st.secrets.get("google_sheets", {}))
    except Exception:
        return {}, None

    if not config:
        return {}, None
    try:
        credentials = credentials_from_config(config)
    except (ValueError, TypeError):
        credentials = None
    return config, credentials


def get_online_settings():
    """Đọc cấu hình Supabase từ secrets phía máy chủ."""
    try:
        secrets_root = st.secrets
        config = dict(secrets_root.get("supabase", {}))
    except Exception:
        return None
    url = str(
        config.get("url") or secrets_root.get("SUPABASE_URL", "")
    ).strip()
    service_role_key = str(
        config.get("service_role_key")
        or secrets_root.get("SUPABASE_SERVICE_ROLE_KEY", "")
    ).strip()
    if not url or not service_role_key:
        return None
    return OnlineSettings(
        url=url,
        service_role_key=service_role_key,
        photos_bucket=str(
            config.get("photos_bucket")
            or secrets_root.get("SUPABASE_PHOTOS_BUCKET", "progress-photos")
        ),
        bootstrap_username=str(config.get("bootstrap_username", "")),
        bootstrap_password_hash=str(config.get("bootstrap_password_hash", "")),
        bootstrap_display_name=str(
            config.get("bootstrap_display_name", "Quản trị hệ thống")
        ),
    )


@st.cache_resource(show_spinner=False)
def get_online_service(settings):
    return SupabaseService(settings)


def reload_online_data(service, current_date):
    st.session_state.progress_df = service.load_progress(current_date=current_date)
    st.session_state.qcvn_df = service.load_qcvn()
    st.session_state.online_data_loaded = True


# ==============================================================================
# 3. ĐĂNG NHẬP, ONLINE BACKEND & SESSION STATE
# ==============================================================================

st.session_state.setdefault("project_today", datetime.date.today())
online_settings = get_online_settings()
ONLINE_MODE = online_settings is not None
online_service = get_online_service(online_settings) if ONLINE_MODE else None
CURRENT_USER = st.session_state.get("current_user")

if ONLINE_MODE and PUBLIC_ACCESS_MODE:
    try:
        CURRENT_USER = online_service.get_or_create_public_editor()
        st.session_state.current_user = CURRENT_USER
    except Exception as exc:
        st.error(f"Không thể khởi tạo quyền cập nhật công khai: {exc}")
        st.stop()
elif ONLINE_MODE and CURRENT_USER is None:
    st.title("Đăng nhập hệ thống tiến độ Hyundai Miền Tây")
    st.caption("Dành cho Ban QLDA, Đại lý và người được cấp quyền.")
    try:
        online_service.bootstrap_admin()
    except Exception:
        st.error(
            "Kho dữ liệu online chưa được khởi tạo. Quản trị viên cần chạy "
            "tệp `supabase_setup.sql` trong Supabase SQL Editor."
        )
        st.stop()

    with st.form("login_form", border=True):
        login_username = st.text_input("Tên đăng nhập", autocomplete="username")
        login_password = st.text_input(
            "Mật khẩu", type="password", autocomplete="current-password"
        )
        login_submit = st.form_submit_button(
            "Đăng nhập", type="primary", icon=":material/login:", width="stretch"
        )
    if login_submit:
        user = online_service.authenticate(login_username, login_password)
        if user is None:
            st.error("Tên đăng nhập hoặc mật khẩu không đúng.")
        else:
            online_service.mark_login(user)
            st.session_state.current_user = user
            st.session_state.pop("online_data_loaded", None)
            st.rerun()
    st.stop()

if ONLINE_MODE:
    CURRENT_USER = st.session_state.current_user
    try:
        online_service.seed_if_empty(get_initial_progress_data(), get_qcvn121_items())
        if not st.session_state.get("online_data_loaded"):
            reload_online_data(online_service, st.session_state.project_today)
    except Exception as exc:
        st.error(f"Không thể kết nối kho dữ liệu online: {exc}")
        st.stop()
else:
    st.session_state.setdefault("progress_df", get_initial_progress_data())
    st.session_state.setdefault("qcvn_df", get_qcvn121_items())


# ==============================================================================
# 4. THANH ĐIỀU HƯỚNG BÊN TRÁI (SIDEBAR)
# ==============================================================================

# Ngày theo dõi mặc định là ngày hệ thống và có thể điều chỉnh ở thanh bên.
PROJECT_TODAY = st.session_state.project_today

# Áp dụng tính toán cảnh báo tiến độ
df_analyzed = calculate_progress_alerts(st.session_state.progress_df, current_date=PROJECT_TODAY)
st.session_state.progress_df = df_analyzed
st.session_state.qcvn_df = normalize_qcvn_data(st.session_state.qcvn_df)

overdue_items = df_analyzed[df_analyzed["_alert_type"] == "OVERDUE"]
urgent_items = df_analyzed[df_analyzed["_alert_type"] == "URGENT"]
delayed_items = df_analyzed[df_analyzed["_alert_type"] == "DELAYED"]
sheet_config, sheet_credentials = get_google_sheet_settings()
configured_sheet = str(
    sheet_config.get("spreadsheet_url") or sheet_config.get("spreadsheet_id") or ""
)
st.session_state.setdefault("sheet_reference", configured_sheet)

with st.sidebar:
    st.markdown("## 🚛 HYUNDAI MIỀN TÂY")
    st.caption("Dự án Đại lý 3S Xe Thương Mại - TP. Cần Thơ")
    
    st.markdown("---")

    # Mốc thời gian dùng cho toàn bộ cảnh báo và đường Gantt.
    st.date_input(
        "Ngày theo dõi",
        key="project_today",
        min_value=datetime.date(2026, 7, 1),
        max_value=datetime.date(2027, 12, 31),
        help="Mặc định là ngày hệ thống. Thay đổi để xem lại cảnh báo tại một mốc khác.",
    )

    # Cảnh báo nhanh trên Sidebar
    if len(overdue_items) > 0:
        st.error(f"🚨 **{len(overdue_items)} Hạng mục QUÁ HẠN!**")
    if len(urgent_items) > 0:
        st.warning(f"⚠️ **{len(urgent_items)} Hạng mục SẮP ĐẾN HẠN (<7 ngày)**")
    if len(overdue_items) == 0 and len(urgent_items) == 0:
        st.success("✅ **Tiến độ đang được kiểm soát tốt!**")

    # Countdown Box
    target_date = datetime.date(2026, 12, 31)
    days_left = max(0, (target_date - PROJECT_TODAY).days)
    
    st.metric(
        label="⏳ ĐẾM NGƯỢC KHAI TRƯƠNG",
        value=f"{days_left} Ngày",
        delta="Mục tiêu: 31/12/2026"
    )

    st.markdown("---")

    if ONLINE_MODE:
        st.success("Dữ liệu online đang hoạt động", icon=":material/cloud_done:")
        if PUBLIC_ACCESS_MODE:
            st.caption("Mở trực tiếp · Không yêu cầu đăng nhập")
        else:
            st.caption(f"**{CURRENT_USER.display_name}** · {ROLE_LABELS[CURRENT_USER.role]}")
        if st.button("Làm mới dữ liệu", icon=":material/refresh:", width="stretch"):
            reload_online_data(online_service, PROJECT_TODAY)
            st.rerun()
        if not PUBLIC_ACCESS_MODE and st.button(
            "Đăng xuất", icon=":material/logout:", width="stretch"
        ):
            st.session_state.clear()
            st.rerun()
    else:
        with st.expander("Đồng bộ Google Sheets", icon=":material/cloud_sync:"):
            st.text_input(
                "URL hoặc ID Google Sheet",
                key="sheet_reference",
                placeholder="https://docs.google.com/spreadsheets/d/...",
            )
            if sheet_credentials is None:
                st.info(
                    "Chưa có Service Account trong `.streamlit/secrets.toml`. "
                    "Ứng dụng vẫn hoạt động với dữ liệu trong phiên hiện tại."
                )
            else:
                st.success("Đã nhận cấu hình Service Account từ secrets phía máy chủ.")
                with st.container(horizontal=True):
                    if st.button("Tải từ Sheet", icon=":material/download:"):
                        try:
                            progress, qcvn = load_from_google_sheets(
                                sheet_credentials,
                                st.session_state.sheet_reference,
                                current_date=PROJECT_TODAY,
                            )
                            st.session_state.progress_df = progress
                            st.session_state.qcvn_df = qcvn
                            st.toast("Đã tải dữ liệu từ Google Sheets.", icon="✅")
                            st.rerun()
                        except Exception as exc:
                            st.error(f"Không thể tải Google Sheets: {exc}")

                    if st.button("Lưu lên Sheet", type="primary", icon=":material/upload:"):
                        try:
                            save_to_google_sheets(
                                sheet_credentials,
                                st.session_state.sheet_reference,
                                st.session_state.progress_df,
                                st.session_state.qcvn_df,
                                current_date=PROJECT_TODAY,
                            )
                            st.toast("Đã lưu dữ liệu lên Google Sheets.", icon="✅")
                        except Exception as exc:
                            st.error(f"Không thể lưu Google Sheets: {exc}")

        st.space("small")
        if st.button("Khôi phục dữ liệu gốc", icon=":material/restart_alt:", width="stretch"):
            st.session_state.progress_df = get_initial_progress_data()
            st.session_state.qcvn_df = get_qcvn121_items()
            st.toast("Đã khôi phục dữ liệu gốc!", icon="🔄")
            st.rerun()

    st.markdown("---")
    st.caption("📌 **Phiên bản:** Enterprise v4.0 Online")
    st.caption("© 2026 Thế Giới Xe Tải & Hyundai Tiên Phong")


# ==============================================================================
# 5. KHU VỰC TIÊU ĐỀ CHÍNH & TRUNG TÂM CẢNH BÁO TIẾN ĐỘ (ALERT CENTER)
# ==============================================================================

st.markdown(f"""
<div class="hero-container">
    <div style="display:flex; justify-content:space-between; align-items:flex-start;">
        <div>
            <h1 class="hero-title">🚛 HỆ THỐNG QUẢN LÝ TIẾN ĐỘ THI CÔNG & QCVN 121</h1>
            <div class="hero-sub">Dự án Đại lý 3S Hyundai Miền Tây | Giám sát Giai đoạn 3 (Tháng 7/2026 – Tháng 12/2026)</div>
        </div>
        <div style="text-align:right;">
            <div style="font-size:0.85rem; color:#94A3B8;">Mốc kiểm tra:</div>
            <div style="font-size:1.15rem; font-weight:800; color:#38BDF8;">📅 {PROJECT_TODAY.strftime('%d/%m/%Y')}</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# 🚨 TRUNG TÂM CẢNH BÁO CHẬM TIẾN ĐỘ & SẮP ĐẾN HẠN
if len(overdue_items) > 0 or len(urgent_items) > 0 or len(delayed_items) > 0:
    c_al1, c_al2 = st.columns(2)

    with c_al1:
        with st.container(border=True):
            if len(overdue_items) > 0:
                st.error(f"Có {len(overdue_items)} hạng mục đã quá hạn tiến độ.")
                for _, row in overdue_items.iterrows():
                    days_late = (PROJECT_TODAY - row["Hoàn thành"]).days
                    st.markdown(
                        f"- **[{row['Mã']}] {row['Hạng mục công việc']}** — "
                        f"hạn {row['Hoàn thành'].strftime('%d/%m/%Y')}, trễ {days_late} ngày"
                    )
            else:
                st.success("Không có hạng mục nào bị quá hạn tại mốc đang chọn.")

    with c_al2:
        with st.container(border=True):
            if len(urgent_items) > 0:
                st.warning(f"Có {len(urgent_items)} hạng mục đến hạn trong 7 ngày tới.")
                for _, row in urgent_items.iterrows():
                    days_left = (row["Hoàn thành"] - PROJECT_TODAY).days
                    st.markdown(
                        f"- **[{row['Mã']}] {row['Hạng mục công việc']}** — "
                        f"hạn {row['Hoàn thành'].strftime('%d/%m/%Y')}, còn {days_left} ngày"
                    )
            else:
                st.success("Không có hạng mục sắp đến hạn trong 7 ngày tới.")


# ==============================================================================
# 6. KHU VỰC THỐNG KÊ CHỈ SỐ KPI TỔNG QUAN
# ==============================================================================

total_tasks = len(df_analyzed)
done_tasks = len(df_analyzed[df_analyzed["Trạng thái"] == "Đã hoàn thiện"])
in_prog_tasks = len(df_analyzed[df_analyzed["Trạng thái"] == "Đang thi công"])
num_delayed = len(delayed_items)
num_overdue = len(overdue_items)
avg_prog = float(df_analyzed["Tiến độ (%)"].mean())

df_q_all = st.session_state.qcvn_df
df_q = (
    df_q_all
    if SHOW_EV_HYBRID_CHECKLIST
    else df_q_all[df_q_all["Đặc thù EV"] == False].copy()
)
total_qcvn = len(df_q)
qcvn_achieved = len(df_q[df_q["Đánh giá"] == "Đạt"])

with st.container(horizontal=True):
    st.metric("Tổng hạng mục", f"{total_tasks} đầu việc", f"Tiến độ: {avg_prog:.1f}%", border=True)
    st.metric("Đã hoàn thiện", f"{done_tasks} / {total_tasks}", f"{(done_tasks/total_tasks)*100:.0f}% tổng số", border=True)
    st.metric("Cảnh báo chậm trễ", f"{num_overdue} quá hạn", f"Dời: {num_delayed}", delta_color="inverse", border=True)
    st.metric("Checklist QCVN 121", f"{qcvn_achieved} / {total_qcvn} đạt", f"{(qcvn_achieved/total_qcvn)*100:.0f}% nội bộ", border=True)

st.markdown("<br>", unsafe_allow_html=True)


# ==============================================================================
# 7. CÁC PHÂN HỆ TAB CHỨC NĂNG CHÍNH
# ==============================================================================

tab_update, tab1, tab2, tab3, tab4, tab_users = st.tabs([
    "📷 CẬP NHẬT HIỆN TRƯỜNG",
    "📋 TIẾN ĐỘ CHI TIẾT",
    "⚡ CHECKLIST QCVN 121",
    "📊 BIỂU ĐỒ GANTT",
    "📑 BÁO CÁO",
    "ℹ️ HƯỚNG DẪN",
])


# ------------------------------------------------------------------------------
# TAB CẬP NHẬT HIỆN TRƯỜNG & HÌNH ẢNH
# ------------------------------------------------------------------------------
with tab_update:
    st.subheader("Cập nhật tiến độ và hình ảnh hiện trường")
    if not ONLINE_MODE:
        st.info("Tính năng này sẽ hoạt động sau khi cấu hình Supabase trên bản online.")
    elif not CURRENT_USER.can_edit:
        st.info("Tài khoản của bạn có quyền xem. Liên hệ quản trị viên để được cấp quyền cập nhật.")
    else:
        progress_source = st.session_state.progress_df
        task_options = progress_source["Mã"].tolist()
        selected_task_code = st.selectbox(
            "Chọn hạng mục cần cập nhật",
            task_options,
            format_func=lambda code: (
                f"[{code}] "
                + progress_source.loc[
                    progress_source["Mã"] == code, "Hạng mục công việc"
                ].iloc[0]
            ),
            key="field_task_code",
        )
        selected_task = progress_source[progress_source["Mã"] == selected_task_code].iloc[0]
        update_nonce = st.session_state.get("field_update_nonce", 0)
        status_options = ["Chưa thực hiện", "Đang thi công", "Đã hoàn thiện", "Dời tiến độ"]

        with st.form(f"field_update_form_{selected_task_code}_{update_nonce}", border=True):
            c_progress, c_status = st.columns(2)
            with c_progress:
                field_progress = st.slider(
                    "Tiến độ hoàn thành",
                    min_value=0,
                    max_value=100,
                    value=int(selected_task["Tiến độ (%)"]),
                    step=5,
                    format="%d%%",
                )
            with c_status:
                field_status = st.selectbox(
                    "Trạng thái",
                    status_options,
                    index=status_options.index(selected_task["Trạng thái"]),
                )
            field_note = st.text_area(
                "Nội dung cập nhật",
                placeholder="Ví dụ: Đã hoàn thành tô trát khu vực tiếp nhận, đang chờ nghiệm thu...",
                height=100,
            )
            uploaded_images = st.file_uploader(
                "Ảnh hiện trường",
                type=["jpg", "jpeg", "png", "webp"],
                accept_multiple_files=True,
                max_upload_size=12,
                help="Có thể chọn nhiều ảnh; tối đa 12 MB mỗi ảnh.",
            )
            camera_image = st.camera_input(
                "Hoặc chụp ảnh trực tiếp",
                resolution="720p",
            )
            field_submit = st.form_submit_button(
                "Lưu cập nhật",
                type="primary",
                icon=":material/cloud_upload:",
                width="stretch",
            )

        if field_submit:
            images = [(image.name, image.getvalue()) for image in uploaded_images]
            if camera_image is not None:
                images.append((camera_image.name or "camera.jpg", camera_image.getvalue()))
            try:
                with st.spinner("Đang lưu dữ liệu và tải ảnh..."):
                    online_service.create_field_update(
                        CURRENT_USER,
                        selected_task_code,
                        field_progress,
                        field_status,
                        field_note,
                        images,
                    )
                    reload_online_data(online_service, PROJECT_TODAY)
                st.session_state.field_update_nonce = update_nonce + 1
                st.toast("Đã lưu cập nhật hiện trường.", icon="✅")
                st.rerun()
            except Exception as exc:
                st.error(f"Không thể lưu cập nhật: {exc}")

    if ONLINE_MODE:
        st.divider()
        st.subheader("Nhật ký cập nhật gần đây")
        try:
            recent_updates = online_service.recent_updates(limit=20)
            if not recent_updates:
                st.caption("Chưa có bản cập nhật hiện trường nào.")
            for update in recent_updates:
                created_at = pd.to_datetime(update["created_at"], utc=True).tz_convert(
                    "Asia/Ho_Chi_Minh"
                )
                with st.container(border=True):
                    st.markdown(
                        f"**[{update['task_code']}] {update['progress']}% · {update['status']}**"
                    )
                    st.caption(
                        f"{update['updated_by_name']} · "
                        f"{created_at.strftime('%d/%m/%Y %H:%M')}"
                    )
                    if update.get("note"):
                        st.write(update["note"])
                    photos = update.get("photos", [])
                    if photos:
                        st.image(
                            [photo["url"] for photo in photos if photo.get("url")],
                            caption=[photo["original_name"] for photo in photos if photo.get("url")],
                            width=240,
                        )
        except Exception as exc:
            st.warning(f"Chưa thể tải nhật ký: {exc}")


# ------------------------------------------------------------------------------
# TAB 1: BẢNG TIẾN ĐỘ TƯƠNG TÁC CÓ CẢNH BÁO
# ------------------------------------------------------------------------------
with tab1:
    st.subheader("📋 Bảng Tiến Độ Thi Công Chi Tiết & Giám Sát Chậm Trễ")
    st.caption("💡 Cột `Cảnh báo Tiến độ` tự động phát hiện các đầu việc Quá hạn, Sắp đến hạn hoặc Đã hoàn thành so với mốc thời gian thực.")

    col_config = {
        "Mã": st.column_config.TextColumn("Mã CV", width="small", disabled=True),
        "Hạng mục công việc": st.column_config.TextColumn("Hạng mục công việc", width="large", required=True),
        "Phân khu": st.column_config.SelectboxColumn(
            "Phân khu",
            options=["Thiết kế & Pháp lý", "Mặt bằng & Pháp lý", "Showroom (XDCB)", "Xưởng Dịch vụ 3S", "Thiết bị QCVN 121", "Trang bị Xe Điện (EV)", "Môi trường & PCCC", "Kiểm định & Chứng nhận", "Vận hành & Khai trương"],
            required=True
        ),
        "Bắt đầu": st.column_config.DateColumn("Ngày bắt đầu", format="YYYY-MM-DD", required=True),
        "Hoàn thành": st.column_config.DateColumn("Ngày hoàn thành", format="YYYY-MM-DD", required=True),
        "Tiến độ (%)": st.column_config.ProgressColumn("Tiến độ", min_value=0, max_value=100, format="%d%%"),
        "Trạng thái": st.column_config.SelectboxColumn(
            "Trạng thái",
            options=["Chưa thực hiện", "Đang thi công", "Đã hoàn thiện", "Dời tiến độ"],
            required=True
        ),
        "Cảnh báo Tiến độ": st.column_config.TextColumn("🚨 Cảnh báo Tiến độ", width="medium", disabled=True),
        "Người phụ trách": st.column_config.TextColumn("Người phụ trách", width="medium"),
        "Ghi chú": st.column_config.TextColumn("Ghi chú mốc thời gian", width="large")
    }

    # Bảng Master editor
    display_cols = ["Mã", "Hạng mục công việc", "Phân khu", "Bắt đầu", "Hoàn thành", "Tiến độ (%)", "Trạng thái", "Cảnh báo Tiến độ", "Người phụ trách", "Ghi chú"]
    edited_progress = st.data_editor(
        st.session_state.progress_df[display_cols],
        column_config=col_config,
        width="stretch",
        hide_index=True,
        num_rows="fixed",
        disabled=not (ONLINE_MODE and CURRENT_USER.can_edit) if ONLINE_MODE else False,
        key="master_progress_editor_v3"
    )

    # Cập nhật khi có thay đổi
    if not edited_progress[display_cols].equals(st.session_state.progress_df[display_cols]):
        try:
            normalized_progress = calculate_progress_alerts(edited_progress, current_date=PROJECT_TODAY)
            if ONLINE_MODE:
                online_service.save_progress(normalized_progress, CURRENT_USER)
                reload_online_data(online_service, PROJECT_TODAY)
            else:
                st.session_state.progress_df = normalized_progress
            st.toast("Đã cập nhật tiến độ.", icon="✅")
            st.rerun()
        except Exception as exc:
            st.error(f"Không thể lưu bảng tiến độ: {exc}")

    # Toolbar xuất dữ liệu
    col_t1, col_t2 = st.columns([2, 5])
    with col_t1:
        csv_prog = st.session_state.progress_df[display_cols].to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            "📥 Tải CSV Tiến Độ & Cảnh Báo",
            data=csv_prog,
            file_name=f"Tien_Do_HD_Mien_Tay_{datetime.date.today().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            width="stretch"
        )


# ------------------------------------------------------------------------------
# TAB 2: QUẢN LÝ TIÊU CHUẨN QCVN 121
# ------------------------------------------------------------------------------
with tab2:
    st.subheader("⚡ Checklist nội bộ tham chiếu QCVN 121:2024/BGTVT")
    st.caption(
        "Các dòng dưới đây là điểm kiểm soát quản lý nội bộ, không phải "
        "các điều khoản nguyên văn của QCVN. "
        "[Xem văn bản QCVN 121 chính thức](https://vbpl.vn/FileData/TW/Lists/vbpq/Attachments/173120/VanBanGoc_Th%C3%B4ng%20t%C6%B0%2050.2024.TT-BGTVT.%20QCVN%20121.pdf)"
    )
    if not SHOW_EV_HYBRID_CHECKLIST:
        hidden_ev_count = len(df_q_all) - len(df_q)
        st.info(
            f"Đang tạm ẩn {hidden_ev_count} điều kiện đặc thù Xe điện/Hybrid. "
            "Dữ liệu vẫn được bảo lưu để bật lại khi cần."
        )

    # Bộ lọc hiển thị
    nhom_list = ["Tất cả"] + list(df_q["Nhóm"].unique())
    selected_nhom = st.selectbox("Lọc theo Nhóm tiêu chuẩn:", options=nhom_list)

    display_qcvn = df_q.copy()
    if selected_nhom != "Tất cả":
        display_qcvn = display_qcvn[display_qcvn["Nhóm"] == selected_nhom]

    qcvn_config = {
        "STT": st.column_config.NumberColumn("STT", width="small", disabled=True),
        "Nhóm": st.column_config.TextColumn("Nhóm tiêu chuẩn", width="medium", disabled=True),
        "Hạng mục": st.column_config.TextColumn("Nội dung tiêu chuẩn kỹ thuật", width="large"),
        "Đặc thù EV": st.column_config.CheckboxColumn("⚡ Đặc thù EV", width="small"),
        "Đánh giá": st.column_config.SelectboxColumn(
            "Trạng thái đánh giá",
            options=["Đạt", "Đang thi công", "Đang mua sắm", "Đang đào tạo", "Chưa đạt"],
            required=True
        ),
        "Ghi chú": st.column_config.TextColumn("Thông số kỹ thuật / Ghi chú", width="medium")
    }

    edited_qcvn = st.data_editor(
        display_qcvn,
        column_config=qcvn_config,
        width="stretch",
        hide_index=True,
        num_rows="fixed",
        column_order=["STT", "Nhóm", "Hạng mục", "Đánh giá", "Ghi chú"],
        disabled=not (ONLINE_MODE and CURRENT_USER.can_edit) if ONLINE_MODE else False,
        key="master_qcvn_editor_v3"
    )

    if not edited_qcvn.equals(display_qcvn):
        try:
            updated_qcvn = st.session_state.qcvn_df.copy()
            for _, row in edited_qcvn.iterrows():
                updated_qcvn.loc[updated_qcvn["STT"] == row["STT"], :] = row
            if ONLINE_MODE:
                online_service.save_qcvn(updated_qcvn, CURRENT_USER)
                reload_online_data(online_service, PROJECT_TODAY)
            else:
                st.session_state.qcvn_df = updated_qcvn
            st.toast("Đã cập nhật checklist QCVN 121.", icon="✅")
            st.rerun()
        except Exception as exc:
            st.error(f"Không thể lưu checklist: {exc}")


# ------------------------------------------------------------------------------
# TAB 3: BIỂU ĐỒ GANTT CÓ ĐƯỜNG LINE ĐỎ THỜI GIAN THỰC & CHẬM TIẾN ĐỘ
# ------------------------------------------------------------------------------
with tab3:
    st.subheader("📊 Biểu Đồ Gantt Tiến Độ Chi Tiết (Có Đường Line Đỏ Hiện Tại)")
    st.caption("🔴 **Đường Line đỏ thẳng đứng** thể hiện mốc thời gian thực. Các hạng mục nằm bên trái đường đỏ mà chưa hoàn thành sẽ được cảnh báo chậm tiến độ.")

    gantt_data = st.session_state.progress_df.copy()
    gantt_data["Bắt đầu_dt"] = pd.to_datetime(gantt_data["Bắt đầu"])
    gantt_data["Hoàn thành_dt"] = pd.to_datetime(gantt_data["Hoàn thành"])
    
    # Số ngày thi công & chuỗi định dạng
    gantt_data["Số ngày"] = (gantt_data["Hoàn thành_dt"] - gantt_data["Bắt đầu_dt"]).dt.days + 1
    gantt_data["Bắt đầu_str"] = gantt_data["Bắt đầu"].apply(lambda d: d.strftime('%d/%m/%Y'))
    gantt_data["Hoàn thành_str"] = gantt_data["Hoàn thành"].apply(lambda d: d.strftime('%d/%m/%Y'))
    
    # Nhãn hiển thị trên thanh
    gantt_data["Nhãn thanh"] = gantt_data.apply(
        lambda r: f"{r['Số ngày']} ngày ({r['Tiến độ (%)']}%)",
        axis=1
    )
    
    # Trục Y: hiển thị rõ ngày bắt đầu - hoàn thành ngay bên cạnh tên công việc
    gantt_data["Trục Y"] = gantt_data.apply(
        lambda r: f"[{r['Bắt đầu'].strftime('%d/%m')} ➔ {r['Hoàn thành'].strftime('%d/%m')}] {r['Mã']}: {r['Hạng mục công việc']}",
        axis=1
    )

    # Phân loại màu sắc (đặc biệt đổi màu đỏ rực cho mục Quá hạn / Dời tiến độ)
    color_scheme = {
        "Đã hoàn thiện": "#059669",   # Green
        "Đang thi công": "#0284C7",    # Blue
        "Chưa thực hiện": "#94A3B8",   # Gray
        "Dời tiến độ": "#EF4444"      # Red
    }

    fig_timeline = px.timeline(
        gantt_data,
        x_start="Bắt đầu_dt",
        x_end="Hoàn thành_dt",
        y="Trục Y",
        color="Trạng thái",
        text="Nhãn thanh",
        color_discrete_map=color_scheme,
        custom_data=["Bắt đầu_str", "Hoàn thành_str", "Số ngày", "Tiến độ (%)", "Trạng thái", "Người phụ trách", "Ghi chú", "Phân khu", "Cảnh báo Tiến độ"]
    )
    
    # Custom hover template
    fig_timeline.update_traces(
        textposition="outside",
        hovertemplate=(
            "<b>%{y}</b><br><br>"
            "📅 <b>Ngày bắt đầu:</b> %{customdata[0]}<br>"
            "🏁 <b>Ngày hoàn thành:</b> %{customdata[1]}<br>"
            "⏳ <b>Thời lượng:</b> %{customdata[2]} ngày<br>"
            "📊 <b>Tiến độ:</b> %{customdata[3]}%<br>"
            "📌 <b>Trạng thái:</b> %{customdata[4]}<br>"
            "🚨 <b>Tình trạng:</b> %{customdata[8]}<br>"
            "🏢 <b>Phân khu:</b> %{customdata[7]}<br>"
            "👤 <b>Phụ trách:</b> %{customdata[5]}<br>"
            "📝 <b>Ghi chú:</b> %{customdata[6]}"
            "<extra></extra>"
        )
    )
    
    # 🔴 THÊM ĐƯỜNG LINE ĐỎ MỐC THỜI GIAN HIỆN TẠI (TODAY LINE)
    today_dt = pd.to_datetime(PROJECT_TODAY)
    fig_timeline.add_vline(
        x=today_dt,
        line_width=2.5,
        line_dash="dash",
        line_color="#DC2626",
        annotation_text=f"📍 HÔM NAY ({PROJECT_TODAY.strftime('%d/%m/%Y')})",
        annotation_position="top right",
        annotation_font=dict(size=12, color="#DC2626", family="Plus Jakarta Sans"),
        annotation_bgcolor="rgba(254, 242, 242, 0.85)"
    )

    fig_timeline.update_yaxes(autorange="reversed", title="", tickfont=dict(size=12))
    fig_timeline.update_xaxes(
        title="Dòng Thời Gian Dự Án (Tháng 8/2026 – Tháng 12/2026)",
        dtick="M1",
        tickformat="%m/%Y",
        gridcolor="#E2E8F0"
    )
    fig_timeline.update_layout(
        height=600,
        margin=dict(l=320, r=40, t=30, b=20),
        plot_bgcolor="#FFFFFF",
        paper_bgcolor="#FFFFFF",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig_timeline, width="stretch")

    # Bảng Tra cứu Lịch trình Nhanh kèm Cảnh báo
    st.markdown("##### 📅 Bảng Lịch Trình Chi Tiết Bắt Đầu - Hoàn Thành & Tình Trạng Quá Hạn:")
    schedule_table = gantt_data[["Mã", "Hạng mục công việc", "Phân khu", "Bắt đầu_str", "Hoàn thành_str", "Số ngày", "Tiến độ (%)", "Trạng thái", "Cảnh báo Tiến độ"]].copy()
    schedule_table.columns = ["Mã CV", "Hạng mục công việc", "Phân khu", "Ngày Bắt Đầu", "Ngày Hoàn Thành", "Thời lượng (ngày)", "Tiến độ (%)", "Trạng thái", "Tình trạng Cảnh báo"]
    st.dataframe(schedule_table, width="stretch", hide_index=True)

    # 2 Biểu đồ Phân tích
    st.markdown("<br>", unsafe_allow_html=True)
    ch1, ch2 = st.columns(2)
    with ch1:
        st.markdown("##### 📌 Tỷ Trọng Trạng Thái Hạng Mục")
        st_counts = gantt_data["Trạng thái"].value_counts().reset_index()
        st_counts.columns = ["Trạng thái", "Số lượng"]
        fig_donut = px.pie(
            st_counts,
            names="Trạng thái",
            values="Số lượng",
            color="Trạng thái",
            color_discrete_map=color_scheme,
            hole=0.45
        )
        fig_donut.update_layout(margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig_donut, width="stretch")

    with ch2:
        st.markdown("##### 📌 Tiến Độ Trung Bình Theo Phân Khu")
        pk_prog = gantt_data.groupby("Phân khu")["Tiến độ (%)"].mean().reset_index()
        fig_bar_pk = px.bar(
            pk_prog,
            x="Tiến độ (%)",
            y="Phân khu",
            orientation="h",
            color="Tiến độ (%)",
            color_continuous_scale="Blues",
            range_x=[0, 100]
        )
        fig_bar_pk.update_layout(
            margin=dict(l=10, r=10, t=10, b=10),
            yaxis=dict(title="")
        )
        st.plotly_chart(fig_bar_pk, width="stretch")


# ------------------------------------------------------------------------------
# TAB 4: LỘ TRÌNH CỘT MỐC & XUẤT BÁO CÁO
# ------------------------------------------------------------------------------
with tab4:
    st.subheader("📑 Lộ Trình Cột Mốc Trọng Tâm & Xuất Hồ Sơ Báo Cáo")

    col_m1, col_m2 = st.columns(2)
    with col_m1:
        st.info("""
        **📍 Các Mốc Trọng Tâm Tháng 8 - 9/2026:**
        * **29/08/2026**: Hoàn thiện Bản vẽ chi tiết (Layout 2D & 3D).
        * **30/08/2026**: Hoàn tất Thiết kế chi tiết & hồ sơ cấp phép xây dựng.
        * **12/09/2026**: Ký Hợp đồng thuê mặt bằng (chưa công chứng).
        * **19/09/2026**: Đặt cọc thuê đất mặt bằng đại lý.
        """)

    with col_m2:
        st.success("""
        **📍 Các Mốc Thi Công & Nghiệm Thu Khai Trương:**
        * **10 - 11/2026**: Hoàn thành XDCB Showroom & Kết cấu xưởng 3S.
        * **11 - 12/2026**: Lắp đặt thiết bị kiểm định & an toàn Xe Điện QCVN 121.
        * **12/2026**: Nghiệm thu PCCC, Đánh giá chứng nhận QCVN 121:2024/BGTVT.
        * **31/12/2026**: Nghiệm thu chuẩn đại lý HTCV & **Chính thức Khai trương**.
        """)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("#### 📥 Xuất Toàn Bộ Báo Cáo Ra Tệp Excel (.XLSX):")

    def generate_excel():
        import io
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            st.session_state.progress_df.to_excel(writer, sheet_name='Tien_Do_Thi_Cong', index=False)
            df_q.to_excel(writer, sheet_name='QCVN_121_Checklist', index=False)
        return output.getvalue()

    excel_binary = generate_excel()
    st.download_button(
        label="📊 TẢI TRỌN BỘ BÁO CÁO TIẾN ĐỘ & CHECKLIST QCVN 121 (.XLSX)",
        data=excel_binary,
        file_name=f"Bao_Cao_Tien_Do_HD_Mien_Tay_{datetime.date.today().strftime('%Y%m%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        width="stretch"
    )


# ------------------------------------------------------------------------------
# TAB QUẢN LÝ TÀI KHOẢN
# ------------------------------------------------------------------------------
with tab_users:
    st.subheader("Hướng dẫn truy cập")
    if PUBLIC_ACCESS_MODE:
        st.success("Không cần đăng nhập. Mở link là có thể xem và cập nhật.")
        st.warning(
            "Hãy chỉ chia sẻ link cho Ban QLDA và Đại lý vì người có link "
            "có thể thay đổi tiến độ và tải ảnh hiện trường."
        )
    elif not ONLINE_MODE:
        st.info("Quản lý tài khoản chỉ có trên bản online.")
    else:
        st.markdown(f"Đang đăng nhập: **{CURRENT_USER.display_name}**")
        with st.expander("Đổi mật khẩu", icon=":material/password:"):
            with st.form("change_password_form"):
                current_password = st.text_input("Mật khẩu hiện tại", type="password")
                new_password = st.text_input("Mật khẩu mới", type="password")
                confirm_password = st.text_input("Nhập lại mật khẩu mới", type="password")
                change_submit = st.form_submit_button(
                    "Đổi mật khẩu", type="primary", icon=":material/save:"
                )
            if change_submit:
                if new_password != confirm_password:
                    st.error("Mật khẩu nhập lại không khớp.")
                else:
                    try:
                        online_service.change_password(
                            CURRENT_USER, current_password, new_password
                        )
                        st.success("Đã đổi mật khẩu.")
                    except Exception as exc:
                        st.error(f"Không thể đổi mật khẩu: {exc}")

        if CURRENT_USER.is_admin:
            st.divider()
            st.markdown("#### Tạo tài khoản cho Đại lý")
            with st.form("create_user_form", border=True):
                new_username = st.text_input("Tên đăng nhập mới")
                new_display_name = st.text_input("Tên người dùng/đơn vị")
                new_user_password = st.text_input("Mật khẩu ban đầu", type="password")
                role_label = st.selectbox(
                    "Quyền sử dụng",
                    ["Đại lý cập nhật", "Chỉ xem", "Quản trị"],
                )
                create_submit = st.form_submit_button(
                    "Tạo tài khoản", type="primary", icon=":material/person_add:"
                )
            if create_submit:
                role_by_label = {label: role for role, label in ROLE_LABELS.items()}
                try:
                    online_service.create_user(
                        CURRENT_USER,
                        new_username,
                        new_display_name,
                        new_user_password,
                        role_by_label[role_label],
                    )
                    st.toast("Đã tạo tài khoản mới.", icon="✅")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Không thể tạo tài khoản: {exc}")

            try:
                users_df = online_service.list_users(CURRENT_USER)
                if not users_df.empty:
                    display_users = users_df[
                        ["username", "display_name", "role", "is_active", "created_at", "last_login_at"]
                    ].copy()
                    display_users["role"] = display_users["role"].map(ROLE_LABELS)
                    display_users.columns = [
                        "Tên đăng nhập",
                        "Người dùng/đơn vị",
                        "Quyền",
                        "Đang hoạt động",
                        "Ngày tạo",
                        "Đăng nhập gần nhất",
                    ]
                    st.dataframe(display_users, hide_index=True, width="stretch")

                    other_users = users_df[users_df["id"] != CURRENT_USER.id]
                    if not other_users.empty:
                        user_to_toggle = st.selectbox(
                            "Chọn tài khoản để khóa/mở",
                            other_users["id"].tolist(),
                            format_func=lambda user_id: other_users.loc[
                                other_users["id"] == user_id, "username"
                            ].iloc[0],
                        )
                        current_active = bool(
                            other_users.loc[
                                other_users["id"] == user_to_toggle, "is_active"
                            ].iloc[0]
                        )
                        action_label = "Khóa tài khoản" if current_active else "Mở lại tài khoản"
                        if st.button(action_label, icon=":material/manage_accounts:"):
                            online_service.set_user_active(
                                CURRENT_USER, user_to_toggle, not current_active
                            )
                            st.toast("Đã cập nhật trạng thái tài khoản.", icon="✅")
                            st.rerun()
            except Exception as exc:
                st.error(f"Không thể tải danh sách tài khoản: {exc}")
