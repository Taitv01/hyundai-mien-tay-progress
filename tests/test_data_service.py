import datetime as dt

import pandas as pd
import pytest

from data_service import (
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

