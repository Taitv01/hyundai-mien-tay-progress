"""Chuẩn hóa dữ liệu và đồng bộ Google Sheets cho ứng dụng tiến độ."""

from __future__ import annotations

import datetime as dt
import math
from collections.abc import Mapping
from typing import Any

import gspread
import pandas as pd


PROGRESS_COLUMNS = [
    "Mã",
    "Hạng mục công việc",
    "Phân khu",
    "Bắt đầu",
    "Hoàn thành",
    "Tiến độ (%)",
    "Trạng thái",
    "Người phụ trách",
    "Ghi chú",
]

QCVN_COLUMNS = [
    "STT",
    "Nhóm",
    "Hạng mục",
    "Đặc thù EV",
    "Đánh giá",
    "Ghi chú",
]

PROGRESS_STATUSES = {
    "Chưa thực hiện",
    "Đang thi công",
    "Đã hoàn thiện",
    "Dời tiến độ",
}

QCVN_STATUSES = {
    "Đạt",
    "Đang thi công",
    "Đang mua sắm",
    "Đang đào tạo",
    "Chưa đạt",
}

PROGRESS_WORKSHEET = "Tien_Do_Thi_Cong"
QCVN_WORKSHEET = "QCVN_121_Checklist"


def _require_columns(df: pd.DataFrame, required: list[str], label: str) -> None:
    missing = [column for column in required if column not in df.columns]
    if missing:
        raise ValueError(f"{label} thiếu cột bắt buộc: {', '.join(missing)}")


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return False
    return str(value).strip().lower() in {"true", "1", "yes", "y", "x", "có"}


def normalize_progress_data(
    df: pd.DataFrame,
    current_date: dt.date | None = None,
) -> pd.DataFrame:
    """Kiểm tra kiểu dữ liệu, đồng bộ trạng thái và tạo cảnh báo tiến độ."""

    current_date = current_date or dt.date.today()
    _require_columns(df, PROGRESS_COLUMNS, "Bảng tiến độ")

    result = df[PROGRESS_COLUMNS].copy()
    result["Mã"] = result["Mã"].fillna("").astype(str).str.strip()
    result["Hạng mục công việc"] = (
        result["Hạng mục công việc"].fillna("").astype(str).str.strip()
    )
    result["Phân khu"] = result["Phân khu"].fillna("").astype(str).str.strip()
    result["Người phụ trách"] = (
        result["Người phụ trách"].fillna("").astype(str).str.strip()
    )
    result["Ghi chú"] = result["Ghi chú"].fillna("").astype(str).str.strip()

    for column in ("Bắt đầu", "Hoàn thành"):
        parsed = pd.to_datetime(result[column], errors="coerce")
        if parsed.isna().any():
            bad_rows = [str(index + 1) for index in result.index[parsed.isna()]]
            raise ValueError(
                f"Cột {column} có ngày không hợp lệ tại dòng: {', '.join(bad_rows)}"
            )
        result[column] = parsed.dt.date

    progress = pd.to_numeric(result["Tiến độ (%)"], errors="coerce").fillna(0)
    result["Tiến độ (%)"] = progress.clip(0, 100).round().astype(int)
    result["Trạng thái"] = result["Trạng thái"].fillna("").astype(str).str.strip()

    invalid_statuses = sorted(set(result["Trạng thái"]) - PROGRESS_STATUSES)
    if invalid_statuses:
        raise ValueError(
            "Trạng thái tiến độ không hợp lệ: " + ", ".join(invalid_statuses)
        )

    alerts: list[str] = []
    alert_types: list[str] = []
    for index in result.index:
        start = result.at[index, "Bắt đầu"]
        end = result.at[index, "Hoàn thành"]
        status = result.at[index, "Trạng thái"]
        percent = int(result.at[index, "Tiến độ (%)"])

        if end < start:
            end = start
            result.at[index, "Hoàn thành"] = start

        if status == "Đã hoàn thiện" or percent == 100:
            status = "Đã hoàn thiện"
            percent = 100
        elif status == "Chưa thực hiện" and percent > 0:
            status = "Đang thi công"

        result.at[index, "Trạng thái"] = status
        result.at[index, "Tiến độ (%)"] = percent

        if status == "Đã hoàn thiện":
            alerts.append("Đã hoàn thành")
            alert_types.append("COMPLETED")
        elif status == "Dời tiến độ":
            alerts.append("Đã dời tiến độ")
            alert_types.append("DELAYED")
        elif end < current_date:
            days_late = (current_date - end).days
            alerts.append(f"Quá hạn ({days_late} ngày)")
            alert_types.append("OVERDUE")
        elif end <= current_date + dt.timedelta(days=7):
            days_left = (end - current_date).days
            alerts.append(f"Sắp đến hạn ({days_left} ngày)")
            alert_types.append("URGENT")
        elif start <= current_date:
            alerts.append("Đang trong kế hoạch")
            alert_types.append("IN_PROGRESS")
        else:
            alerts.append("Chưa tới hạn")
            alert_types.append("FUTURE")

    result["Cảnh báo Tiến độ"] = alerts
    result["_alert_type"] = alert_types
    return result


def normalize_qcvn_data(df: pd.DataFrame) -> pd.DataFrame:
    """Kiểm tra cấu trúc checklist nội bộ tham chiếu QCVN 121."""

    _require_columns(df, QCVN_COLUMNS, "Checklist QCVN 121")
    result = df[QCVN_COLUMNS].copy()
    stt = pd.to_numeric(result["STT"], errors="coerce")
    if stt.isna().any():
        raise ValueError("Cột STT của checklist phải là số nguyên.")
    result["STT"] = stt.astype(int)
    if result["STT"].duplicated().any():
        raise ValueError("Cột STT của checklist không được trùng.")

    for column in ("Nhóm", "Hạng mục", "Đánh giá", "Ghi chú"):
        result[column] = result[column].fillna("").astype(str).str.strip()
    result["Đặc thù EV"] = result["Đặc thù EV"].map(_as_bool).astype(bool)

    invalid_statuses = sorted(set(result["Đánh giá"]) - QCVN_STATUSES)
    if invalid_statuses:
        raise ValueError(
            "Trạng thái checklist không hợp lệ: " + ", ".join(invalid_statuses)
        )
    return result.sort_values("STT").reset_index(drop=True)


def credentials_from_config(config: Mapping[str, Any]) -> dict[str, Any]:
    """Đọc Service Account từ cấu hình secrets mà không đưa khóa ra giao diện."""

    raw = config.get("service_account")
    if isinstance(raw, Mapping):
        return dict(raw)

    raw_json = config.get("credentials_json")
    if isinstance(raw_json, str) and raw_json.strip():
        import json

        parsed = json.loads(raw_json)
        if not isinstance(parsed, dict):
            raise ValueError("google_sheets.credentials_json phải là một JSON object.")
        return parsed
    raise ValueError(
        "Chưa cấu hình [google_sheets.service_account] trong .streamlit/secrets.toml."
    )


def _open_spreadsheet(credentials: Mapping[str, Any], sheet_reference: str):
    reference = sheet_reference.strip()
    if not reference:
        raise ValueError("Chưa nhập URL hoặc ID Google Sheet.")
    client = gspread.service_account_from_dict(dict(credentials))
    if reference.startswith("http://") or reference.startswith("https://"):
        return client.open_by_url(reference)
    return client.open_by_key(reference)


def load_from_google_sheets(
    credentials: Mapping[str, Any],
    sheet_reference: str,
    current_date: dt.date | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Tải và chuẩn hóa hai worksheet dữ liệu của ứng dụng."""

    spreadsheet = _open_spreadsheet(credentials, sheet_reference)
    progress = pd.DataFrame(
        spreadsheet.worksheet(PROGRESS_WORKSHEET).get_all_records(
            default_blank="", numericise_ignore=["all"]
        )
    )
    qcvn = pd.DataFrame(
        spreadsheet.worksheet(QCVN_WORKSHEET).get_all_records(
            default_blank="", numericise_ignore=["all"]
        )
    )
    return (
        normalize_progress_data(progress, current_date=current_date),
        normalize_qcvn_data(qcvn),
    )


def _sheet_rows(df: pd.DataFrame) -> list[list[Any]]:
    export = df[[column for column in df.columns if not column.startswith("_")]].copy()
    rows: list[list[Any]] = [list(export.columns)]
    for record in export.itertuples(index=False, name=None):
        row: list[Any] = []
        for value in record:
            if isinstance(value, (dt.date, dt.datetime, pd.Timestamp)):
                row.append(value.isoformat())
            elif pd.isna(value):
                row.append("")
            elif isinstance(value, bool):
                row.append("TRUE" if value else "FALSE")
            else:
                row.append(value)
        rows.append(row)
    return rows


def _replace_worksheet(spreadsheet: Any, title: str, rows: list[list[Any]]) -> None:
    try:
        worksheet = spreadsheet.worksheet(title)
        worksheet.clear()
    except gspread.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(
            title=title,
            rows=max(100, len(rows) + 20),
            cols=max(20, len(rows[0]) + 5),
        )
    worksheet.update(values=rows, range_name="A1")
    worksheet.freeze(rows=1)


def save_to_google_sheets(
    credentials: Mapping[str, Any],
    sheet_reference: str,
    progress_df: pd.DataFrame,
    qcvn_df: pd.DataFrame,
    current_date: dt.date | None = None,
) -> None:
    """Ghi bản dữ liệu đã kiểm tra lên hai worksheet chuẩn."""

    progress = normalize_progress_data(progress_df, current_date=current_date)
    qcvn = normalize_qcvn_data(qcvn_df)
    spreadsheet = _open_spreadsheet(credentials, sheet_reference)
    _replace_worksheet(spreadsheet, PROGRESS_WORKSHEET, _sheet_rows(progress))
    _replace_worksheet(spreadsheet, QCVN_WORKSHEET, _sheet_rows(qcvn))
