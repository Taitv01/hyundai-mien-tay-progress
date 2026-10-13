import datetime as dt

import pandas as pd
import pytest

from data_service import (
    apply_qcvn_updates,
    credentials_from_config,
    normalize_progress_data,
    normalize_qcvn_data,
)


def progress_frame(**overrides):
    row = {
        "Mã": "CV-01",
        "Hạng mục công việc": "Công việc thử nghiệm",
        "Phân khu": "Showroom (XDCB)",
        "Bắt đầu": "2026-08-20",
        "Hoàn thành": "2026-08-30",
        "Tiến độ (%)": 0,
        "Trạng thái": "Chưa thực hiện",
        "Người phụ trách": "Ban QLDA",
        "Ghi chú": "",
    }
    row.update(overrides)
    return pd.DataFrame([row])


def qcvn_frame(**overrides):
    row = {
        "STT": 1,
        "Nhóm": "I. Mặt bằng",
        "Hạng mục": "Khu vực tiếp nhận",
        "Đặc thù EV": "FALSE",
        "Đánh giá": "Chưa đạt",
        "Ghi chú": "",
    }
    row.update(overrides)
    return pd.DataFrame([row])


def test_progress_normalization_syncs_percent_and_status():
    result = normalize_progress_data(
        progress_frame(**{"Tiến độ (%)": 45}),
        current_date=dt.date(2026, 8, 28),
    )

    assert result.loc[0, "Tiến độ (%)"] == 45
    assert result.loc[0, "Trạng thái"] == "Đang thi công"
    assert result.loc[0, "Cảnh báo Tiến độ"] == "Sắp đến hạn (2 ngày)"


def test_progress_normalization_completes_100_percent_and_repairs_dates():
    result = normalize_progress_data(
        progress_frame(
            **{
                "Tiến độ (%)": 100,
                "Hoàn thành": "2026-08-10",
            }
        ),
        current_date=dt.date(2026, 8, 28),
    )

    assert result.loc[0, "Trạng thái"] == "Đã hoàn thiện"
    assert result.loc[0, "Hoàn thành"] == dt.date(2026, 8, 20)
    assert result.loc[0, "_alert_type"] == "COMPLETED"


def test_progress_normalization_detects_overdue():
    result = normalize_progress_data(
        progress_frame(**{"Hoàn thành": "2026-08-25"}),
        current_date=dt.date(2026, 8, 28),
    )

    assert result.loc[0, "Cảnh báo Tiến độ"] == "Quá hạn (3 ngày)"
    assert result.loc[0, "_alert_type"] == "OVERDUE"


def test_qcvn_normalization_parses_boolean_and_rejects_duplicate_stt():
    normalized = normalize_qcvn_data(qcvn_frame(**{"Đặc thù EV": "Có"}))
    assert bool(normalized.loc[0, "Đặc thù EV"]) is True

    duplicate = pd.concat([qcvn_frame(), qcvn_frame()], ignore_index=True)
    with pytest.raises(ValueError, match="không được trùng"):
        normalize_qcvn_data(duplicate)


def test_credentials_are_read_from_nested_server_config():
    credentials = credentials_from_config(
        {"service_account": {"type": "service_account", "client_email": "bot@example.com"}}
    )
    assert credentials["client_email"] == "bot@example.com"


def test_apply_qcvn_updates_handles_subset_and_hidden_ev_column():
    target = pd.DataFrame([
        {"STT": 1, "Nhóm": "I. Mặt bằng", "Hạng mục": "HM 1", "Đặc thù EV": False, "Đánh giá": "Chưa đạt", "Ghi chú": ""},
        {"STT": 2, "Nhóm": "I. Mặt bằng", "Hạng mục": "HM 2", "Đặc thù EV": True, "Đánh giá": "Chưa đạt", "Ghi chú": "EV note"},
        {"STT": 3, "Nhóm": "II. Thiết bị", "Hạng mục": "HM 3", "Đặc thù EV": False, "Đánh giá": "Đạt", "Ghi chú": "Old note"},
    ])
    target = normalize_qcvn_data(target)

    # Giả lập bảng hiển thị trên UI: chỉ hiển thị STT 1 (do lọc nhóm) và không có cột "Đặc thù EV"
    edited = pd.DataFrame([
        {"STT": 1, "Nhóm": "I. Mặt bằng", "Hạng mục": "HM 1 sửa đổi", "Đánh giá": "Đạt", "Ghi chú": "Đã nghiệm thu"},
    ])

    result = apply_qcvn_updates(target, edited)

    # Đảm bảo không gặp lỗi dtype int64 và STT 1 được cập nhật
    assert result.loc[result["STT"] == 1, "Đánh giá"].iloc[0] == "Đạt"
    assert result.loc[result["STT"] == 1, "Hạng mục"].iloc[0] == "HM 1 sửa đổi"
    assert result.loc[result["STT"] == 1, "Ghi chú"].iloc[0] == "Đã nghiệm thu"

    # Đảm bảo các dòng không hiển thị trên UI vẫn giữ nguyên vẹn
    assert bool(result.loc[result["STT"] == 2, "Đặc thù EV"].iloc[0]) is True
    assert result.loc[result["STT"] == 2, "Ghi chú"].iloc[0] == "EV note"
    assert result.loc[result["STT"] == 3, "Đánh giá"].iloc[0] == "Đạt"
    assert result.loc[result["STT"] == 3, "Ghi chú"].iloc[0] == "Old note"
    assert pd.api.types.is_integer_dtype(result["STT"])


def test_apply_qcvn_updates_handles_cleared_nan_note():
    target = normalize_qcvn_data(pd.DataFrame([
        {"STT": 1, "Nhóm": "I. Mặt bằng", "Hạng mục": "HM 1", "Đặc thù EV": False, "Đánh giá": "Đạt", "Ghi chú": "Ghi chú cũ"},
    ]))

    # Người dùng xóa nội dung ghi chú (trở thành None/NaN trên data_editor)
    edited = pd.DataFrame([
        {"STT": 1, "Nhóm": "I. Mặt bằng", "Hạng mục": "HM 1", "Đánh giá": "Đang thi công", "Ghi chú": None},
    ])

    result = apply_qcvn_updates(target, edited)
    assert result.loc[0, "Đánh giá"] == "Đang thi công"
    assert result.loc[0, "Ghi chú"] == ""


