# -*- coding: utf-8 -*-
"""Kiểm thử dữ liệu Nhân sự Đại lý 3S và Theo dõi Hiện trạng Dịch vụ."""

import pandas as pd

from dealer_status_data import (
    HR_COLUMNS,
    SERVICE_STATUS_COLUMNS,
    apply_hr_updates,
    apply_service_status_updates,
    get_initial_hr_data,
    get_initial_service_status_data,
    normalize_hr_data,
    normalize_service_status_data,
)


def test_initial_hr_data_has_expected_structure_and_note_column():
    df = get_initial_hr_data()
    assert list(df.columns) == HR_COLUMNS
    assert "Ghi chú" in df.columns
    assert len(df) >= 40
    active_count = int(df["Trạng thái"].isin(["Đã nhận việc", "Chờ đào tạo"]).sum())
    assert active_count == 31
    cl1_count = int(df["Chứng chỉ Hyundai"].str.contains("CL1", na=False).sum())
    assert cl1_count == 5


def test_apply_hr_updates_preserves_unfiltered_rows_and_updates_notes():
    base = get_initial_hr_data()
    subset = base[base["Bộ phận"] == "Ban Giám đốc"].copy()
    subset.loc[subset["Mã NS"] == "NS-01", "Ghi chú"] = "Ghi chú mới từ người dùng"

    updated = apply_hr_updates(base, subset, is_filtered=True)
    assert len(updated) == len(base)
    assert (
        updated.loc[updated["Mã NS"] == "NS-01", "Ghi chú"].iloc[0]
        == "Ghi chú mới từ người dùng"
    )


def test_initial_service_status_data_has_all_32_items():
    df = get_initial_service_status_data()
    assert list(df.columns) == SERVICE_STATUS_COLUMNS
    assert len(df) == 32
    assert "Hiện trạng (09/11/2026)" in df.columns
    assert "Ghi chú" in df.columns


def test_apply_service_status_updates_merges_by_code():
    base = get_initial_service_status_data()
    subset = base.iloc[:3].copy()
    subset.loc[subset["Mã DV"] == "DV-03", "Ghi chú"] = "Đã cập nhật tiến độ nhà xưởng 09/11"

    updated = apply_service_status_updates(base, subset, is_filtered=True)
    assert len(updated) == len(base)
    assert (
        updated.loc[updated["Mã DV"] == "DV-03", "Ghi chú"].iloc[0]
        == "Đã cập nhật tiến độ nhà xưởng 09/11"
    )
