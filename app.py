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
import html
from pathlib import Path
import streamlit.components.v1 as components

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
            "Ghi chú": ""
        },
        {
            "Mã": "PL-02",
            "Hạng mục công việc": "Hoàn thiện thiết kế chi tiết & hồ sơ xin phép",
            "Phân khu": "Thiết kế & Pháp lý",
            "Bắt đầu": datetime.date(2026, 8, 20),
            "Hoàn thành": datetime.date(2026, 8, 30),
            "Tiến độ (%)": 90,
            "Trạng thái": "Đã hoàn thiện",
            "Người phụ trách": "Ban QLDA",
            "Ghi chú": "HTCV - HXG - Hyundai Miền Tây đã ký bản vẽ chi tiết; đang gửi Đại lý bổ sung giáp lai"
        },
        {
            "Mã": "PL-03",
            "Hạng mục công việc": "Ký hợp đồng thuê mặt bằng (chưa công chứng)",
            "Phân khu": "Mặt bằng & Pháp lý",
            "Bắt đầu": datetime.date(2026, 9, 1),
            "Hoàn thành": datetime.date(2026, 9, 12),
            "Tiến độ (%)": 100,
            "Trạng thái": "Đã hoàn thiện",
            "Người phụ trách": "Ban Giám Đốc / Pháp chế",
            "Ghi chú": "Đã cập nhật hợp đồng thuê công chứng ngày 12/09/2026; giấy CNQSDĐ ngày 26/08/2026"
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
            "Ghi chú": ""
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
            "Ghi chú": ""
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
            "Ghi chú": ""
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
            "Ghi chú": ""
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
            "Ghi chú": ""
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
            "Ghi chú": ""
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
            "Ghi chú": ""
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
            "Ghi chú": ""
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
            "Ghi chú": ""
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
            "Ghi chú": ""
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
            "Ghi chú": ""
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


def get_online_service(settings):
    import importlib
    import supabase_service
    importlib.invalidate_caches()
    importlib.reload(supabase_service)
    return supabase_service.SupabaseService(settings)




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

tab_gantt, tab_progress, tab_update, tab_qcvn, tab_report, tab_users = st.tabs([
    "📊 BIỂU ĐỒ GANTT",
    "📋 TIẾN ĐỘ CHI TIẾT",
    "📷 CẬP NHẬT HIỆN TRƯỜNG & FILE",
    "⚡ CHECKLIST QCVN 121",
    "📑 BÁO CÁO",
    "ℹ️ HƯỚNG DẪN",
])


# ------------------------------------------------------------------------------
# TAB 1: BIỂU ĐỒ GANTT CÓ ĐƯỜNG LINE ĐỎ THỜI GIAN THỰC & CHẬM TIẾN ĐỘ
# ------------------------------------------------------------------------------
with tab_gantt:
    st.subheader("📊 Biểu Đồ Gantt Tiến Độ Chi Tiết (Có Đường Line Đỏ Hiện Tại)")
    st.caption("🔴 **Đường Line đỏ thẳng đứng** thể hiện mốc thời gian thực. Các hạng mục nằm bên trái đường đỏ mà chưa hoàn thành sẽ được cảnh báo chậm tiến độ.")

    gantt_data = st.session_state.progress_df.copy()
    gantt_data["Bắt đầu_dt"] = pd.to_datetime(gantt_data["Bắt đầu"])
    gantt_data["Hoàn thành_dt"] = pd.to_datetime(gantt_data["Hoàn thành"])

    # Xác định hạng mục đang trong tiến độ thực hiện tại mốc ngày theo dõi
    gantt_data["Đang diễn ra"] = gantt_data.apply(
        lambda r: (r["Bắt đầu"] <= PROJECT_TODAY <= r["Hoàn thành"]),
        axis=1
    )

    # Thông báo nổi bật hạng mục đang thực hiện
    active_tasks = gantt_data[gantt_data["Đang diễn ra"]]
    if not active_tasks.empty:
        active_list_str = " · ".join([
            f"**[{r['Mã']}] {r['Hạng mục công việc']}** ({r['Tiến độ (%)']}%)"
            for _, r in active_tasks.iterrows()
        ])
        st.info(f"🎯 **Hạng mục đang trong tiến độ thực hiện tại mốc ngày theo dõi ({PROJECT_TODAY.strftime('%d/%m/%Y')}):** {active_list_str}", icon="📍")
    
    # Số ngày thi công & chuỗi định dạng
    gantt_data["Số ngày"] = (gantt_data["Hoàn thành_dt"] - gantt_data["Bắt đầu_dt"]).dt.days + 1
    gantt_data["Bắt đầu_str"] = gantt_data["Bắt đầu"].apply(lambda d: d.strftime('%d/%m/%Y'))
    gantt_data["Hoàn thành_str"] = gantt_data["Hoàn thành"].apply(lambda d: d.strftime('%d/%m/%Y'))
    
    # Nhãn hiển thị trên thanh - Tô đậm nếu đang thực hiện
    def format_bar_label(r):
        if r["Đang diễn ra"]:
            return f"⭐ ĐANG THỰC HIỆN: {r['Số ngày']} ngày ({r['Tiến độ (%)']}%)"
        return f"{r['Số ngày']} ngày ({r['Tiến độ (%)']}%)"

    gantt_data["Nhãn thanh"] = gantt_data.apply(format_bar_label, axis=1)
    
    # Trục Y: hiển thị rõ ngày bắt đầu - hoàn thành ngay bên cạnh tên công việc (Tô đậm nếu đang thực hiện)
    def format_y_axis(r):
        base_label = f"[{r['Bắt đầu'].strftime('%d/%m')} ➔ {r['Hoàn thành'].strftime('%d/%m')}] {r['Mã']}: {r['Hạng mục công việc']}"
        if r["Đang diễn ra"]:
            return f"👉 <b>{base_label} ◄ [ĐANG THỰC HIỆN]</b>"
        return base_label

    gantt_data["Trục Y"] = gantt_data.apply(format_y_axis, axis=1)

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

    # Tô đậm viền thanh tiến độ cho các hạng mục đang thực hiện tại ngày theo dõi
    for trace in fig_timeline.data:
        line_colors = []
        line_widths = []
        for y_val in trace.y:
            match = gantt_data[gantt_data["Trục Y"] == y_val]
            if not match.empty and match.iloc[0]["Đang diễn ra"]:
                line_colors.append("#F59E0B")  # Viền vàng hổ phách nổi bật
                line_widths.append(3.5)
            else:
                line_colors.append("rgba(0,0,0,0.15)")
                line_widths.append(1)
        trace.marker.line.color = line_colors
        trace.marker.line.width = line_widths
    
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

    # Gắn cờ chú thích (Pin callout) ngay tại vị trí thanh đang thực hiện hôm nay
    for _, row in gantt_data[gantt_data["Đang diễn ra"]].iterrows():
        fig_timeline.add_annotation(
            x=today_dt,
            y=row["Trục Y"],
            text=f"🎯 ĐANG THỰC HIỆN: {row['Mã']}",
            showarrow=True,
            arrowhead=2,
            arrowsize=1.2,
            arrowwidth=2,
            arrowcolor="#DC2626",
            ax=85,
            ay=-28,
            bgcolor="#FEF3C7",
            bordercolor="#F59E0B",
            borderwidth=2,
            borderpad=5,
            font=dict(size=11, color="#92400E", family="Plus Jakarta Sans"),
            opacity=0.95
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
    gantt_data["Tình trạng hôm nay"] = gantt_data["Đang diễn ra"].apply(lambda x: "⭐ Đang thực hiện" if x else "—")
    schedule_table = gantt_data[["Mã", "Hạng mục công việc", "Phân khu", "Bắt đầu_str", "Hoàn thành_str", "Số ngày", "Tiến độ (%)", "Trạng thái", "Tình trạng hôm nay", "Cảnh báo Tiến độ"]].copy()
    schedule_table.columns = ["Mã CV", "Hạng mục công việc", "Phân khu", "Ngày Bắt Đầu", "Ngày Hoàn Thành", "Thời lượng (ngày)", "Tiến độ (%)", "Trạng thái", "Tiến độ hiện tại", "Tình trạng Cảnh báo"]
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
# TAB 2: BẢNG TIẾN ĐỘ TƯƠNG TÁC CÓ CẢNH BÁO
# ------------------------------------------------------------------------------
with tab_progress:
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
# TAB 3: CẬP NHẬT HIỆN TRƯỜNG & QUẢN LÝ FILE
# ------------------------------------------------------------------------------
with tab_update:
    st.subheader("📷 Cập nhật hiện trường & Quản lý file")
    st.caption("Ghi nhận tiến độ, đính kèm ảnh hiện trường & tệp PDF (bản vẽ, biên bản nghiệm thu) và quản lý thư viện tài liệu dự án.")

    if not ONLINE_MODE:
        st.info("Tính năng này sẽ hoạt động sau khi cấu hình Supabase trên bản online.")
    else:
        subtab_form, subtab_files, subtab_log = st.tabs([
            "📝 Cập nhật tiến độ & Tải tệp",
            "📂 Quản lý file & Hồ sơ hiện trường",
            "📜 Nhật ký cập nhật gần đây",
        ])

        progress_source = st.session_state.progress_df
        task_options = progress_source["Mã"].tolist()

        # ----------------------------------------------------------------------
        # SUB-TAB 1: CẬP NHẬT TIẾN ĐỘ & TẢI TỆP
        # ----------------------------------------------------------------------
        with subtab_form:
            if not CURRENT_USER.can_edit:
                st.info("Tài khoản của bạn có quyền xem. Liên hệ quản trị viên để được cấp quyền cập nhật.")
            else:
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

                # Thẻ thông tin nhanh về hạng mục
                with st.container(border=True):
                    c_m1, c_m2, c_m3, c_m4 = st.columns(4)
                    c_m1.metric("Phân khu", str(selected_task["Phân khu"]))
                    c_m2.metric("Tiến độ hiện tại", f"{int(selected_task['Tiến độ (%)'])}%")
                    c_m3.metric("Hạn hoàn thành", selected_task["Hoàn thành"].strftime("%d/%m/%Y") if hasattr(selected_task["Hoàn thành"], "strftime") else str(selected_task["Hoàn thành"]))
                    c_m4.metric("Người phụ trách", str(selected_task["Người phụ trách"]) or "Chưa phân công")

                update_nonce = st.session_state.get("field_update_nonce", 0)
                status_options = ["Chưa thực hiện", "Đang thi công", "Đã hoàn thiện", "Dời tiến độ"]

                with st.form(f"field_update_form_{selected_task_code}_{update_nonce}", border=True):
                    st.markdown("##### 📌 Thông tin báo cáo hiện trường")
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
                        curr_status = selected_task["Trạng thái"]
                        s_idx = status_options.index(curr_status) if curr_status in status_options else 0
                        field_status = st.selectbox(
                            "Trạng thái",
                            status_options,
                            index=s_idx,
                        )
                    field_note = st.text_area(
                        "Nội dung cập nhật / Ghi chú hiện trường",
                        placeholder="Ví dụ: Đã hoàn thiện đổ bê tông khu vực sửa chữa nhanh, chuẩn bị nghiệm thu cốt thép...",
                        height=90,
                    )

                    st.markdown("##### 📎 Đính kèm tệp & Hình ảnh")
                    c_img, c_pdf = st.columns(2)
                    with c_img:
                        uploaded_images = st.file_uploader(
                            "🖼️ Ảnh hiện trường (JPG, PNG, WebP)",
                            type=["jpg", "jpeg", "png", "webp"],
                            accept_multiple_files=True,
                            max_upload_size=12,
                            help="Có thể chọn nhiều ảnh; tối đa 12 MB mỗi ảnh.",
                            key=f"field_imgs_{update_nonce}",
                        )
                        camera_image = st.camera_input(
                            "Hoặc chụp trực tiếp bằng camera",
                            resolution="720p",
                            key=f"field_cam_{update_nonce}",
                        )
                    with c_pdf:
                        uploaded_pdfs = st.file_uploader(
                            "📄 Tệp PDF đính kèm (Biên bản nghiệm thu, bản vẽ, hồ sơ...)",
                            type=["pdf"],
                            accept_multiple_files=True,
                            max_upload_size=25,
                            help="Biên bản nghiệm thu, bản vẽ thiết kế, hồ sơ pháp lý, chứng chỉ... Tối đa 25 MB mỗi tệp.",
                            key=f"field_pdfs_{update_nonce}",
                        )

                    field_submit = st.form_submit_button(
                        "Lưu cập nhật & Tải lên tệp",
                        type="primary",
                        icon=":material/cloud_upload:",
                        width="stretch",
                    )

                if field_submit:
                    images = [(image.name, image.getvalue()) for image in (uploaded_images or [])]
                    if camera_image is not None:
                        images.append((camera_image.name or "camera.jpg", camera_image.getvalue()))
                    pdfs = [(pdf.name, pdf.getvalue()) for pdf in (uploaded_pdfs or [])]

                    try:
                        with st.spinner("Đang lưu dữ liệu và tải tệp lên hệ thống..."):
                            fresh_service = get_online_service(online_settings)
                            fresh_service.create_field_update(
                                CURRENT_USER,
                                selected_task_code,
                                field_progress,
                                field_status,
                                field_note,
                                images=images,
                                pdfs=pdfs,
                            )
                            reload_online_data(fresh_service, PROJECT_TODAY)
                        st.session_state.field_update_nonce = update_nonce + 1
                        st.toast("Đã lưu cập nhật hiện trường & tệp thành công.", icon="✅")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Không thể lưu cập nhật: {exc}")

                # Tiện ích tải nhanh tài liệu mà không cần đổi % tiến độ
                with st.expander("📎 Tải nhanh tài liệu / PDF bổ sung cho hạng mục này (Không đổi % tiến độ)", expanded=False):
                    st.caption("Dùng để bổ sung biên bản nghiệm thu, chứng chỉ vật tư hoặc bản vẽ mới cho hạng mục mà không làm thay đổi tiến độ công việc.")
                    with st.form(f"quick_doc_form_{selected_task_code}", border=False):
                        q_file = st.file_uploader(
                            "Chọn tệp cần bổ sung (PDF hoặc Ảnh)",
                            type=["pdf", "jpg", "jpeg", "png", "webp"],
                            key=f"quick_file_{selected_task_code}",
                        )
                        q_note = st.text_input(
                            "Ghi chú tài liệu (ví dụ: Biên bản nghiệm thu PCCC, Bản vẽ 3D cập nhật...)",
                            key=f"quick_note_{selected_task_code}",
                        )
                        q_submit = st.form_submit_button("Tải tệp lên", type="secondary", icon=":material/upload_file:")

                    if q_submit:
                        if q_file is None:
                            st.warning("Vui lòng chọn tệp cần tải lên.")
                        else:
                            try:
                                with st.spinner("Đang tải tài liệu lên..."):
                                    fresh_service = get_online_service(online_settings)
                                    fresh_service.upload_task_document(
                                        CURRENT_USER,
                                        selected_task_code,
                                        q_file.name,
                                        q_file.getvalue(),
                                        note=q_note,
                                    )
                                    reload_online_data(fresh_service, PROJECT_TODAY)
                                st.toast(f"Đã tải tệp '{q_file.name}' lên thành công.", icon="✅")
                                st.rerun()
                            except Exception as exc:
                                st.error(f"Lỗi khi tải tài liệu: {exc}")

        # ----------------------------------------------------------------------
        # SUB-TAB 2: QUẢN LÝ FILE & HỒ SƠ HIỆN TRƯỜNG
        # ----------------------------------------------------------------------
        with subtab_files:
            try:
                fresh_service = get_online_service(online_settings)
                all_files = fresh_service.list_all_files(limit=300)
            except Exception as exc:
                st.warning(f"Chưa thể tải danh sách tệp: {exc}")
                all_files = []

            # Thống kê tổng quan
            total_count = len(all_files)
            pdf_count = sum(1 for f in all_files if f["file_type"] == "pdf")
            img_count = sum(1 for f in all_files if f["file_type"] == "image")
            task_with_files = len(set(f["task_code"] for f in all_files if f.get("task_code")))

            m_col1, m_col2, m_col3, m_col4 = st.columns(4)
            m_col1.metric("📦 Tổng số tệp", f"{total_count} tệp")
            m_col2.metric("📄 Tệp tài liệu PDF", f"{pdf_count} tệp")
            m_col3.metric("🖼️ Hình ảnh hiện trường", f"{img_count} ảnh")
            m_col4.metric("🏗️ Hạng mục có hồ sơ", f"{task_with_files} hạng mục")

            st.divider()

            # Bộ lọc và tìm kiếm
            f_col1, f_col2, f_col3 = st.columns([2, 2, 3])
            with f_col1:
                filter_task_opts = ["Tất cả hạng mục"] + task_options
                selected_filter_task = st.selectbox(
                    "Lọc theo hạng mục",
                    filter_task_opts,
                    format_func=lambda code: (
                        "Tất cả hạng mục" if code == "Tất cả hạng mục"
                        else f"[{code}] " + progress_source.loc[progress_source["Mã"] == code, "Hạng mục công việc"].iloc[0]
                    ),
                    key="mgr_filter_task",
                )
            with f_col2:
                selected_filter_type = st.selectbox(
                    "Lọc theo loại tệp",
                    ["Tất cả", "📄 Chỉ tệp PDF", "🖼️ Chỉ hình ảnh"],
                    key="mgr_filter_type",
                )
            with f_col3:
                search_term = st.text_input(
                    "🔍 Tìm kiếm tên tệp hoặc ghi chú",
                    placeholder="Nhập tên tệp (ví dụ: bantin, ngiem_thu, layout...)",
                    key="mgr_search_term",
                )

            # Lọc danh sách
            filtered_files = all_files
            if selected_filter_task != "Tất cả hạng mục":
                filtered_files = [f for f in filtered_files if f["task_code"] == selected_filter_task]

            if selected_filter_type == "📄 Chỉ tệp PDF":
                filtered_files = [f for f in filtered_files if f["file_type"] == "pdf"]
            elif selected_filter_type == "🖼️ Chỉ hình ảnh":
                filtered_files = [f for f in filtered_files if f["file_type"] == "image"]

            if search_term.strip():
                kw = search_term.strip().lower()
                filtered_files = [
                    f for f in filtered_files
                    if kw in f["original_name"].lower()
                    or kw in f["task_code"].lower()
                    or kw in f.get("task_name", "").lower()
                ]

            st.markdown(f"**Danh sách tệp ({len(filtered_files)} kết quả):**")

            if not filtered_files:
                st.info("Chưa có tệp nào phù hợp với điều kiện tìm kiếm/lọc.")
            else:
                for file_item in filtered_files:
                    is_pdf = file_item["file_type"] == "pdf"
                    file_id = file_item["id"]
                    file_name = file_item["original_name"]
                    file_url = file_item.get("url")

                    created_str = ""
                    if file_item.get("created_at"):
                        try:
                            dt_val = pd.to_datetime(file_item["created_at"], utc=True).tz_convert("Asia/Ho_Chi_Minh")
                            created_str = dt_val.strftime("%d/%m/%Y %H:%M")
                        except Exception:
                            created_str = str(file_item["created_at"])[:16]

                    with st.container(border=True):
                        row_left, row_meta, row_actions = st.columns([5, 3, 3])
                        with row_left:
                            if is_pdf:
                                st.markdown(f"📄 **{file_name}**")
                                st.caption(f"🏷️ Loại: `Tài liệu PDF` · Hạng mục: **[{file_item['task_code']}] {file_item.get('task_name', '')}**")
                            else:
                                st.markdown(f"🖼️ **{file_name}**")
                                st.caption(f"🏷️ Loại: `Hình ảnh` · Hạng mục: **[{file_item['task_code']}] {file_item.get('task_name', '')}**")

                        with row_meta:
                            st.write(f"👤 **Người đăng:** {file_item.get('uploader_name', 'Hệ thống')}")
                            st.caption(f"🕒 **Ngày tải:** {created_str}")

                        with row_actions:
                            act_col1, act_col2 = st.columns(2)
                            with act_col1:
                                if file_url:
                                    st.link_button("↗️ Mở tệp", file_url, width="stretch")
                            with act_col2:
                                if CURRENT_USER.can_edit:
                                    with st.popover("🗑️ Xóa", width="stretch"):
                                        st.markdown(f"**Xác nhận xóa tệp?**")
                                        st.caption(f"Tệp `{file_name}` sẽ bị xóa vĩnh viễn khỏi hệ thống.")
                                        if st.button("Xác nhận xóa", type="primary", key=f"del_btn_{file_id}", width="stretch"):
                                            try:
                                                fresh_service = get_online_service(online_settings)
                                                fresh_service.delete_file(CURRENT_USER, file_id)
                                                st.toast(f"Đã xóa tệp '{file_name}' thành công.", icon="✅")
                                                st.rerun()
                                            except Exception as exc:
                                                st.error(f"Lỗi khi xóa: {exc}")

                        # Vùng xem trước tệp
                        if file_url:
                            with st.expander(f"👁️ Xem trước: {file_name}", expanded=False):
                                if is_pdf:
                                    st.markdown(
                                        f'<iframe src="{file_url}#toolbar=1" width="100%" height="520px" style="border: 1px solid #CBD5E1; border-radius: 8px;"></iframe>',
                                        unsafe_allow_html=True,
                                    )
                                    st.link_button("Tải tệp PDF về máy / Mở tab riêng", file_url, icon=":material/download:")
                                else:
                                    st.image(file_url, caption=file_name, width="stretch")

        # ----------------------------------------------------------------------
        # SUB-TAB 3: NHẬT KÝ CẬP NHẬT HIỆN TRƯỜNG
        # ----------------------------------------------------------------------
        with subtab_log:
            try:
                recent_updates = online_service.recent_updates(limit=30)
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

                        # Hình ảnh hiện trường
                        photos = update.get("photos", [])
                        if photos:
                            st.image(
                                [photo["url"] for photo in photos if photo.get("url")],
                                caption=[photo["original_name"] for photo in photos if photo.get("url")],
                                width=240,
                            )

                        # Tài liệu PDF đính kèm
                        documents = update.get("documents", [])
                        if documents:
                            st.markdown("###### 📄 Hồ sơ & Bản vẽ PDF đính kèm:")
                            for doc in documents:
                                if doc.get("url"):
                                    c_dname, c_dbtn = st.columns([4, 2])
                                    with c_dname:
                                        st.markdown(f"📄 **{doc['original_name']}**")
                                    with c_dbtn:
                                        st.link_button("Mở PDF ↗️", doc["url"], width="stretch")
            except Exception as exc:
                st.warning(f"Chưa thể tải nhật ký: {exc}")


# ------------------------------------------------------------------------------
# TAB 4: QUẢN LÝ TIÊU CHUẨN QCVN 121
# ------------------------------------------------------------------------------
with tab_qcvn:
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
# TAB 5: LỘ TRÌNH CỘT MỐC & XUẤT BÁO CÁO
# ------------------------------------------------------------------------------
with tab_report:
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
    st.subheader("📑 Biểu Mẫu & Báo Cáo Giám Sát Hiện Trường Chuẩn")
    st.caption("Bộ đôi hồ sơ báo cáo định kỳ gửi Chủ đầu tư Thế Giới Xe Tải và HTCV: Báo cáo Điều hành PDF và Form HTML chuẩn in ấn A4 (WBS 16 việc, Checklist QCVN 121, ký duyệt 3 bên).")

    pdf_filename = "Bao_cao_dieu_hanh_HMT-CANTHO-2026_2026-09-08.pdf"
    html_filename = "Bao_cao_in_chu_dau_tu_HMT-CANTHO-2026_2026-09-08.html"

    def _find_report_bytes(filename: str):
        candidates = [
            Path(__file__).parent / "reports" / filename,
            Path(__file__).parent.parent / "05_Tien_do_Thi_cong_va_Cam_ket" / "2026-09_Bao_cao_va_Bieu_mau_Dieu_hanh" / filename,
            Path(__file__).parent.parent / filename,
        ]
        for p in candidates:
            if p.exists():
                return p.read_bytes()
        return None

    def _find_report_text(filename: str):
        candidates = [
            Path(__file__).parent / "reports" / filename,
            Path(__file__).parent.parent / "05_Tien_do_Thi_cong_va_Cam_ket" / "2026-09_Bao_cao_va_Bieu_mau_Dieu_hanh" / filename,
            Path(__file__).parent.parent / filename,
        ]
        for p in candidates:
            if p.exists():
                return p.read_text(encoding="utf-8")
        return ""

    pdf_bytes = _find_report_bytes(pdf_filename)
    cur_date_display = PROJECT_TODAY.strftime("%d/%m/%Y")

    # Hàm tạo biểu đồ Gantt SVG trực quan chuẩn in ấn
    def build_gantt_svg(df, today_d):
        min_d = datetime.date(2026, 8, 15)
        max_d = datetime.date(2026, 12, 31)
        total_days = max((max_d - min_d).days, 1)
        chart_x = 290
        chart_w = 700
        row_h = 24
        header_h = 38
        total_h = header_h + len(df) * row_h + 34

        def get_x(d):
            days = (d - min_d).days
            return round(chart_x + (days / total_days) * chart_w, 1)

        today_x = get_x(today_d)

        months = [
            ('Tháng 08/26', datetime.date(2026, 8, 15), datetime.date(2026, 8, 31)),
            ('Tháng 09/26', datetime.date(2026, 9, 1), datetime.date(2026, 9, 30)),
            ('Tháng 10/26', datetime.date(2026, 10, 1), datetime.date(2026, 10, 31)),
            ('Tháng 11/26', datetime.date(2026, 11, 1), datetime.date(2026, 11, 30)),
            ('Tháng 12/26', datetime.date(2026, 12, 1), datetime.date(2026, 12, 31)),
        ]

        svg_parts = [
            f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1005 {total_h}" style="width:100%; height:auto; background:#FFFFFF; border:1px solid #E2E8F0; border-radius:8px; font-family:'Segoe UI',Arial,sans-serif;">'''
        ]

        # Header tháng và các đường gióng dọc
        for idx, (m_label, m_start, m_end) in enumerate(months):
            x1 = get_x(m_start)
            x2 = get_x(m_end) + (get_x(m_end + datetime.timedelta(days=1)) - get_x(m_end) if m_end < max_d else 0)
            mw = x2 - x1
            bg = '#F8FAFC' if idx % 2 == 0 else '#FFFFFF'
            svg_parts.append(f'''<rect x="{x1}" y="0" width="{mw}" height="{header_h}" fill="{bg}" stroke="#E2E8F0" stroke-width="1"/>''')
            svg_parts.append(f'''<line x1="{x1}" y1="{header_h}" x2="{x1}" y2="{header_h + len(df) * row_h}" stroke="#E2E8F0" stroke-width="1" stroke-dasharray="3,3"/>''')
            svg_parts.append(f'''<text x="{x1 + mw/2}" y="24" font-size="11" font-weight="700" fill="#002C6C" text-anchor="middle">{m_label}</text>''')

        # Header cột tên hạng mục
        svg_parts.append(f'''<rect x="0" y="0" width="{chart_x}" height="{header_h}" fill="#002C6C"/>''')
        svg_parts.append(f'''<text x="12" y="24" font-size="11.5" font-weight="700" fill="#FFFFFF">MÃ &amp; TÊN HẠNG MỤC (WBS)</text>''')

        # Hàng công việc WBS
        for i, (_, r) in enumerate(df.iterrows()):
            ry = header_h + i * row_h
            row_bg = '#FFFFFF' if i % 2 == 0 else '#F8FAFC'
            svg_parts.append(f'''<rect x="0" y="{ry}" width="1005" height="{row_h}" fill="{row_bg}"/>''')
            svg_parts.append(f'''<line x1="0" y1="{ry + row_h}" x2="1005" y2="{ry + row_h}" stroke="#F1F5F9" stroke-width="1"/>''')

            code = html.escape(str(r.get('Mã', '')))
            t_name = str(r.get('Hạng mục công việc', ''))
            if len(t_name) > 34:
                t_name = t_name[:32] + '...'
            name_esc = html.escape(t_name)

            svg_parts.append(f'''<text x="10" y="{ry + 16}" font-size="10.5" font-weight="700" fill="#002C6C">{code}</text>''')
            svg_parts.append(f'''<text x="52" y="{ry + 16}" font-size="10" fill="#334155">{name_esc}</text>''')

            # Thanh tiến độ
            start_d = pd.to_datetime(r.get('Bắt đầu')).date()
            end_d = pd.to_datetime(r.get('Hoàn thành')).date()
            pct = int(r.get('Tiến độ (%)', 0))
            stt = str(r.get('Trạng thái', ''))

            bx1 = get_x(start_d)
            bx2 = get_x(end_d)
            bw = max(bx2 - bx1, 8)
            by = ry + 4
            bh = 15

            is_today = (start_d <= today_d <= end_d)
            amber_stroke = ' stroke="#F59E0B" stroke-width="2"' if is_today else ''

            if pct >= 100 or stt == 'Đã hoàn thiện':
                svg_parts.append(f'''<rect x="{bx1}" y="{by}" width="{bw}" height="{bh}" rx="3" fill="#10B981"{amber_stroke}/>''')
                label_x = bx1 + bw / 2 if bw > 28 else bx1 + bw + 4
                text_fill = '#FFFFFF' if bw > 28 else '#059669'
                anchor = 'middle' if bw > 28 else 'start'
                svg_parts.append(f'''<text x="{label_x}" y="{by + 11}" font-size="9" font-weight="700" fill="{text_fill}" text-anchor="{anchor}">{pct}%</text>''')
            elif pct > 0:
                svg_parts.append(f'''<rect x="{bx1}" y="{by}" width="{bw}" height="{bh}" rx="3" fill="#E0F2FE"{amber_stroke}/>''')
                prog_w = max(bw * pct / 100, 4)
                svg_parts.append(f'''<rect x="{bx1}" y="{by}" width="{prog_w}" height="{bh}" rx="3" fill="#0284C7"/>''')
                label_x = bx1 + bw + 4
                svg_parts.append(f'''<text x="{label_x}" y="{by + 11}" font-size="9" font-weight="700" fill="#0284C7">{pct}%</text>''')
            else:
                svg_parts.append(f'''<rect x="{bx1}" y="{by}" width="{bw}" height="{bh}" rx="3" fill="#CBD5E1"{amber_stroke}/>''')
                svg_parts.append(f'''<text x="{bx1 + bw + 4}" y="{by + 11}" font-size="9" font-weight="600" fill="#64748B">0%</text>''')

        # Vạch đỏ mốc hôm nay
        svg_parts.append(f'''<line x1="{today_x}" y1="{header_h}" x2="{today_x}" y2="{header_h + len(df) * row_h}" stroke="#DC2626" stroke-width="2" stroke-dasharray="4,3"/>''')
        badge_text = f'📍 Hôm nay ({today_d.strftime("%d/%m/%Y")})'
        svg_parts.append(f'''<rect x="{today_x - 58}" y="3" width="116" height="18" rx="4" fill="#FEF2F2" stroke="#DC2626" stroke-width="1.5"/>''')
        svg_parts.append(f'''<text x="{today_x}" y="15.5" font-size="9" font-weight="700" fill="#DC2626" text-anchor="middle">{badge_text}</text>''')

        # Chú thích cuối biểu đồ Gantt
        leg_y = header_h + len(df) * row_h + 10
        svg_parts.append(f'''<rect x="0" y="{header_h + len(df) * row_h}" width="1005" height="34" fill="#F8FAFC" stroke="#E2E8F0" stroke-width="1"/>''')
        svg_parts.append(f'''<rect x="290" y="{leg_y + 1}" width="14" height="10" rx="2" fill="#10B981"/>''')
        svg_parts.append(f'''<text x="310" y="{leg_y + 9}" font-size="9.5" fill="#334155">Đã hoàn thành</text>''')
        svg_parts.append(f'''<rect x="410" y="{leg_y + 1}" width="14" height="10" rx="2" fill="#0284C7"/>''')
        svg_parts.append(f'''<text x="430" y="{leg_y + 9}" font-size="9.5" fill="#334155">Đang thực hiện</text>''')
        svg_parts.append(f'''<rect x="530" y="{leg_y + 1}" width="14" height="10" rx="2" fill="#CBD5E1"/>''')
        svg_parts.append(f'''<text x="550" y="{leg_y + 9}" font-size="9.5" fill="#334155">Chưa thực hiện</text>''')
        svg_parts.append(f'''<line x1="645" y1="{leg_y + 6}" x2="665" y2="{leg_y + 6}" stroke="#DC2626" stroke-width="2" stroke-dasharray="3,2"/>''')
        svg_parts.append(f'''<text x="672" y="{leg_y + 9}" font-size="9.5" fill="#DC2626" font-weight="600">Mốc hôm nay</text>''')
        svg_parts.append(f'''<rect x="760" y="{leg_y}" width="16" height="11" rx="2" fill="none" stroke="#F59E0B" stroke-width="2"/>''')
        svg_parts.append(f'''<text x="782" y="{leg_y + 9}" font-size="9.5" fill="#D97706">Đang trong kỳ</text>''')

        svg_parts.append('</svg>')
        return '\n'.join(svg_parts)

    # Hàm xây dựng Form HTML in ấn động từ dữ liệu thực tế hiện tại
    def build_dynamic_printable_html(progress_df, report_date_str):
        total_tasks = len(progress_df)
        completed_tasks = int((progress_df["Tiến độ (%)"] >= 100).sum() + ((progress_df["Trạng thái"] == "Đã hoàn thiện") & (progress_df["Tiến độ (%)"] < 100)).sum())
        overall_progress = round(float(progress_df["Tiến độ (%)"].mean()), 1) if total_tasks > 0 else 0

        try:
            today_d = datetime.datetime.strptime(report_date_str, "%d/%m/%Y").date()
        except Exception:
            today_d = PROJECT_TODAY
        days_left = max((datetime.date(2026, 12, 31) - today_d).days, 0)

        gantt_svg = build_gantt_svg(progress_df, today_d)

        wbs_rows = []
        for _, r in progress_df.iterrows():
            pct = int(r.get("Tiến độ (%)", 0))
            stt_val = str(r.get("Trạng thái", ""))
            pill_color = "#10B981" if (pct >= 100 or stt_val == "Đã hoàn thiện") else ("#0284C7" if pct > 0 else "#94A3B8")
            start_str = pd.to_datetime(r.get("Bắt đầu")).strftime('%d/%m/%Y') if pd.notnull(r.get("Bắt đầu")) else ""
            end_str = pd.to_datetime(r.get("Hoàn thành")).strftime('%d/%m/%Y') if pd.notnull(r.get("Hoàn thành")) else ""
            task_name = html.escape(str(r.get("Hạng mục công việc", "")))
            
            # Cột Ghi chú thực tế: hiện tại không có thông tin thì để trống
            raw_note = str(r.get("Ghi chú", "")).strip()
            if raw_note and raw_note.lower() not in ["none", "nan", ""]:
                escaped_note = html.escape(raw_note).replace("\n", "<br>")
                note_cell = f"<div class='note-text'>{escaped_note}</div>"
            else:
                note_cell = ""

            wbs_rows.append(f"""<tr>
    <td class="code center">{html.escape(str(r.get('Mã', '')))}</td>
    <td><b>{task_name}</b></td>
    <td>{html.escape(str(r.get('Phân khu', '')))}</td>
    <td class="center">{start_str} - {end_str}</td>
    <td class="center strong" style="color:{pill_color}">{pct}%</td>
    <td class="center"><span class="pill" style="background:{pill_color}">{html.escape(stt_val)}</span></td>
    <td>{note_cell}</td>
    <td>{html.escape(str(r.get('Người phụ trách', '')))}</td>
  </tr>""")

        wbs_content = "\n".join(wbs_rows)

        template = f"""<!doctype html>
<html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Báo cáo tiến độ - HMT-CANTHO-2026</title>
<style>
  @page {{ size: A4 portrait; margin: 8mm 10mm; }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 8px 12px; color: #0F172A; background: #fff; font: 11px/1.3 "Segoe UI", Arial, sans-serif; }}
  .header {{ display: flex; justify-content: space-between; gap: 12px; align-items: flex-start; border-bottom: 2.5px solid #002C6C; padding-bottom: 6px; }}
  .header h1 {{ margin: 0; color: #002C6C; font-size: 16.5px; line-height: 1.25; font-weight: 800; text-transform: uppercase; }}
  .subtitle {{ color: #475569; margin-top: 2px; font-size: 10.5px; }}
  .meta {{ text-align: right; min-width: 120px; }}
  .meta-label, .kpi-label {{ color: #64748B; font-size: 9.5px; font-weight: 600; text-transform: uppercase; }}
  .meta-date {{ color: #002C6C; font-size: 13px; font-weight: 800; margin-top: 1px; }}
  .meta-brand {{ color: #94A3B8; font-size: 8.5px; margin-top: 1px; }}
  .kpis {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin: 8px 0; }}
  .kpi {{ padding: 5px; background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 6px; text-align: center; }}
  .kpi-value {{ color: #00AAD2; font-size: 18px; font-weight: 800; }}
  .kpi-value.blue {{ color: #0284C7; }}
  .kpi-value.green {{ color: #10B981; }}
  .kpi-value.amber {{ color: #D97706; }}
  h2 {{ margin: 10px 0 5px; padding-bottom: 3px; border-bottom: 2px solid #00AAD2; color: #002C6C; font-size: 12px; text-transform: uppercase; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 9px; line-height: 1.25; }}
  th, td {{ padding: 3px 5px; border: 1px solid #CBD5E1; vertical-align: middle; }}
  th {{ background: #002C6C; color: #fff; font-weight: 700; text-align: left; font-size: 9px; }}
  tbody tr:nth-child(even) {{ background: #F8FAFC; }}
  .center {{ text-align: center; }}
  .strong {{ font-weight: 800; }}
  .code {{ font-family: Consolas, monospace; font-weight: 800; color: #002C6C; }}
  .pill {{ display: inline-block; padding: 1.5px 5px; border-radius: 5px; color: #fff; font-size: 8px; white-space: nowrap; font-weight: 600; }}
  .note-text {{ font-size: 8px; color: #1E293B; line-height: 1.2; }}
  .signatures {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; margin-top: 12px; break-inside: avoid; text-align: center; font-size: 10px; }}
  .signatures small {{ color: #64748B; font-size: 8.5px; }}
  .signature-line {{ height: 42px; border-bottom: 1px solid #94A3B8; margin: 0 10px 3px; }}
  .btn-print {{ position: fixed; top: 15px; right: 15px; background: #002C6C; color: #fff; padding: 8px 16px; border-radius: 6px; font-weight: 700; border: none; cursor: pointer; box-shadow: 0 2px 8px rgba(0,0,0,0.15); }}
  .section-break {{ break-before: page; margin-top: 6px; }}
  @media print {{
    body {{ margin: 0; }}
    .no-print {{ display: none !important; }}
    thead {{ display: table-header-group; }}
    tr {{ break-inside: avoid; }}
    .section-break {{ break-before: page; }}
  }}
</style></head><body>
<button onclick="window.print()" class="btn-print no-print">🖨️ In Báo Cáo (Ctrl + P)</button>
<header class="header">
  <div>
    <h1>BÁO CÁO TIẾN ĐỘ THI CÔNG & GIÁM SÁT HIỆN TRƯỜNG</h1>
    <div class="subtitle">Dự án: <b>Đại lý 3S Xe Thương Mại Hyundai Miền Tây</b> | Mã: <b>HMT-CANTHO-2026</b></div>
    <div class="subtitle">Chủ đầu tư: <b>Thế giới xe tải</b> | Địa điểm: <b>TP. Cần Thơ</b></div>
  </div>
  <div class="meta">
    <div class="meta-label">Mốc cập nhật</div>
    <div class="meta-date">{report_date_str}</div>
    <div class="meta-brand">Hệ thống QLDA Streamlit<br>Hyundai Miền Tây</div>
  </div>
</header>
<p class="subtitle" style="margin-top:6px; margin-bottom:8px;">
  Số liệu trích xuất thời gian thực từ hệ thống. Tiến độ các hạng mục được đối soát theo nhật ký hiện trường mới nhất.
</p>
<section class="kpis">
  <div class="kpi"><div class="kpi-value">{overall_progress}%</div><div class="kpi-label">Tiến độ tổng thể</div></div>
  <div class="kpi"><div class="kpi-value blue">{completed_tasks}/{total_tasks}</div><div class="kpi-label">Hạng mục hoàn thành</div></div>
  <div class="kpi"><div class="kpi-value green">{days_left} ngày</div><div class="kpi-label">Số ngày còn lại (31/12)</div></div>
  <div class="kpi"><div class="kpi-value amber">16 tỷ VND</div><div class="kpi-label">Ngân sách phê duyệt</div></div>
</section>

<section>
  <h2>1. TIẾN ĐỘ HÌNH ẢNH GANTT (GANTT CHART)</h2>
  <div style="margin-top:6px;">
    {gantt_svg}
  </div>
</section>

<section class="section-break">
  <h2>2. DANH MỤC HẠNG MỤC THI CÔNG CHI TIẾT (WBS)</h2>
  <table>
    <thead>
      <tr>
        <th style="width:55px; text-align:center">Mã</th>
        <th>Tên hạng mục công việc</th>
        <th style="width:120px">Phân khu</th>
        <th style="width:130px; text-align:center">Thời gian thực hiện</th>
        <th style="width:55px; text-align:center">Tiến độ</th>
        <th style="width:85px; text-align:center">Trạng thái</th>
        <th style="width:230px">Ghi chú thực tế</th>
        <th style="width:125px">Phụ trách</th>
      </tr>
    </thead>
    <tbody>
      {wbs_content}
    </tbody>
  </table>
</section>
</body></html>"""
        return template

    # Biên dịch ngay bản in HTML theo dữ liệu thời gian thực
    live_printable_html = build_dynamic_printable_html(st.session_state.progress_df, cur_date_display)
    cur_overall_pct = round(float(st.session_state.progress_df["Tiến độ (%)"].mean()), 1) if not st.session_state.progress_df.empty else 0
    cur_completed = int((st.session_state.progress_df["Tiến độ (%)"] >= 100).sum() + ((st.session_state.progress_df["Trạng thái"] == "Đã hoàn thiện") & (st.session_state.progress_df["Tiến độ (%)"] < 100)).sum())

    col_rep1, col_rep2, col_rep3 = st.columns(3)

    with col_rep1:
        st.markdown(f"""
        <div style="border:1px solid #E2E8F0; border-radius:10px; padding:16px; background:#F8FAFC; min-height:220px; display:flex; flex-direction:column; justify-content:space-between;">
            <div>
                <h4 style="color:#002C6C; margin:0 0 8px 0;">📑 Báo Cáo Điều Hành (.PDF)</h4>
                <p style="font-size:0.85rem; color:#475569; margin-bottom:8px;">
                    Báo cáo điều hành 2 trang chuẩn A4: Mục 1 Biểu đồ Gantt trực quan, Mục 2 Danh mục WBS chi tiết kèm ghi chú thực tế.
                </p>
                <div style="font-size:0.8rem; color:#64748B;">
                    • Tiến độ cập nhật: <b>{cur_overall_pct}% ({cur_completed}/16 việc)</b><br>
                    • Mốc cập nhật: <b>{cur_date_display}</b><br>
                    • Định dạng: <b>PDF 2 trang khổ in A4</b>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        if pdf_bytes:
            st.download_button(
                label="📥 TẢI BÁO CÁO PDF (MỚI NHẤT)",
                data=pdf_bytes,
                file_name=f"Bao_cao_dieu_hanh_HMT-CANTHO_{PROJECT_TODAY.strftime('%Y%m%d')}.pdf",
                mime="application/pdf",
                key="download_pdf_report",
                use_container_width=True
            )
        else:
            st.warning("Chưa tìm thấy tệp PDF.")

    with col_rep2:
        st.markdown(f"""
        <div style="border:1px solid #E2E8F0; border-radius:10px; padding:16px; background:#F8FAFC; min-height:220px; display:flex; flex-direction:column; justify-content:space-between;">
            <div>
                <h4 style="color:#002C6C; margin:0 0 8px 0;">🌐 Bản In Chủ Đầu Tư (.HTML)</h4>
                <p style="font-size:0.85rem; color:#475569; margin-bottom:8px;">
                    Form báo cáo tiến độ A4 chuẩn in ấn, tích hợp Mục 1: Biểu đồ Gantt, Mục 2: WBS 16 việc kèm ghi chú thực tế.
                </p>
                <div style="font-size:0.8rem; color:#64748B;">
                    • Dữ liệu: <b>Thời gian thực (Live 100%)</b><br>
                    • Khổ in: <b>A4 chuẩn in ấn (2 trang)</b><br>
                    • In ấn: <b>Có nút In ngay (Ctrl + P)</b>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.download_button(
            label="📥 TẢI BẢN IN HTML (MỚI NHẤT)",
            data=live_printable_html.encode("utf-8"),
            file_name=f"Bao_cao_in_chu_dau_tu_HMT-CANTHO_{PROJECT_TODAY.strftime('%Y%m%d')}.html",
            mime="text/html",
            key="download_html_report",
            use_container_width=True
        )

    with col_rep3:
        st.markdown("""
        <div style="border:1px solid #E2E8F0; border-radius:10px; padding:16px; background:#F8FAFC; min-height:220px; display:flex; flex-direction:column; justify-content:space-between;">
            <div>
                <h4 style="color:#002C6C; margin:0 0 8px 0;">📊 Dữ Liệu Chi Tiết (.XLSX)</h4>
                <p style="font-size:0.85rem; color:#475569; margin-bottom:8px;">
                    Toàn bộ cơ sở dữ liệu gồm 2 bảng: Tiến độ thi công WBS và Danh mục Checklist đánh giá QCVN 121:2024.
                </p>
                <div style="font-size:0.8rem; color:#64748B;">
                    • Định dạng: <b>Excel (.xlsx)</b><br>
                    • Số sheet: <b>2 worksheets</b><br>
                    • Dữ liệu: <b>Thời gian thực</b>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        def generate_excel():
            import io
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                st.session_state.progress_df.to_excel(writer, sheet_name='Tien_Do_Thi_Cong', index=False)
                df_q.to_excel(writer, sheet_name='QCVN_121_Checklist', index=False)
            return output.getvalue()

        excel_binary = generate_excel()
        st.download_button(
            label="📥 TẢI DỮ LIỆU EXCEL",
            data=excel_binary,
            file_name=f"Bao_Cao_Tien_Do_HD_Mien_Tay_{datetime.date.today().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="download_excel_report",
            use_container_width=True
        )

    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("👁️ Xem Trước Bản In A4 Trực Tiếp (Print Preview)", expanded=True):
        st.caption(f"Trình xem trước bản in A4 đồng bộ trực tiếp theo dữ liệu hệ thống (Mốc ngày: **{cur_date_display}** | Tiến độ: **{cur_overall_pct}%** | Hoàn thành: **{cur_completed}/16** hạng mục).")
        components.html(live_printable_html, height=650, scrolling=True)
        st.caption("💡 **Mẹo in ấn**: Mở tệp HTML tải về bằng Chrome hoặc Edge, bấm **Ctrl + P**, chọn khổ giấy **A4** và **Save as PDF** để có bản in đẹp nhất.")


# ------------------------------------------------------------------------------
# TAB 6: HƯỚNG DẪN TRUY CẬP / QUẢN LÝ TÀI KHOẢN
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
