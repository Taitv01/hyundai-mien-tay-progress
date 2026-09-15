"""Cam kết CĐT 15/09/2026: mỗi dòng PDF là một công việc độc lập."""
import calendar
import datetime as dt
import json
from pathlib import Path

import pandas as pd

SOURCE = '260915_Tiến độ xây dựng Hyundai Cần Thơ.pdf'
VERSION = '2026-09-15'
BROWN = '#8B5E3C'
WEEK_NOTE = ('Quy đổi để hiển thị: W1 = ngày 01–07; W2 = 08–14; '
             'W3 = 15–21; W4 = 22–cuối tháng. PDF cam kết theo tuần, không ấn định ngày lẻ.')
LEGACY_CODES = {f'SR-{i:02}' for i in range(1, 6)} | {f'WS-{i:02}' for i in range(1, 6)} | {'OP-01', 'OP-02'}


def source_rows():
    return json.loads((Path(__file__).parent / 'commitment_20260915.json').read_text(encoding='utf-8'))


def week_label(w):
    return f"Tuần {w['week']} tháng {w['month']:02}/{w['year']}"


def week_date(w, end=False):
    day = (calendar.monthrange(w['year'], w['month'])[1] if w['week'] == 4 else w['week'] * 7) if end else (w['week']-1)*7+1
    return dt.date(w['year'], w['month'], day)


def commitment_data():
    data = []
    for r in source_rows():
        weeks = r['current_weeks']
        historical = not weeks
        if historical:
            weeks = [w for f in r['source_fills'] if f['color'] == 'green' for w in f['weeks']]
        note = (f"Cam kết CĐT 15/09/2026, mục {r['group']}, trang {r['page']}: "
                f"{r['description']} bắt đầu vào {week_label(weeks[0]).lower()}, "
                f"kết thúc {week_label(weeks[-1]).lower()}.")
        if historical:
            note = (f"PDF trang {r['page']}: chỉ có mốc cũ màu xanh lá "
                    f"({week_label(weeks[0])} – {week_label(weeks[-1])}), đã hoàn thiện theo chú giải; "
                    "chưa có mốc cam kết mới cho địa điểm mới.")
        if r['source_status']:
            note += f" Tình trạng ghi trên PDF: {r['source_status']}."
        if r['code'] == 'CK-07-01':
            note += ' Ô cuối trên PDF ghi “39”; giữ mốc tuần 4 tháng 9, không diễn giải thành ngày 39.'
        data.append({
            'Mã': r['code'], 'Hạng mục công việc': r['description'],
            'Phân khu': f"{r['group']:02}. {r['section']}",
            'Bắt đầu': week_date(weeks[0]), 'Hoàn thành': week_date(weeks[-1], True),
            'Tiến độ (%)': 100 if historical else 0,
            'Trạng thái': 'Đã hoàn thiện' if historical else ('Đang thi công' if r['group'] == 7 else 'Chưa thực hiện'),
            'Người phụ trách': r['pic'], 'Ghi chú': note,
        })
    return pd.DataFrame(data)


def active_progress(df):
    """Keep legacy records in storage for their notes/files; replace their aggregate schedule."""
    if df['Mã'].astype(str).str.startswith('CK-').any():
        return df.loc[~df['Mã'].isin(LEGACY_CODES)].reset_index(drop=True)
    return df.copy()


def gantt_progress(df):
    # Hide by WBS group, not by the word D116: equipment in group 9 stays visible.
    return df.loc[~df['Mã'].astype(str).str.startswith('CK-15-')].copy()


def commitment_details(df):
    metadata = {r['code']: r for r in source_rows()}
    result = df.copy()
    result['Mục PDF'] = [str(metadata.get(c, {}).get('group', '')) for c in result['Mã']]
    result['Bắt đầu cam kết'] = [week_label(metadata[c]['current_weeks'][0]) if c in metadata and metadata[c]['current_weeks'] else '' for c in result['Mã']]
    result['Kết thúc cam kết'] = [week_label(metadata[c]['current_weeks'][-1]) if c in metadata and metadata[c]['current_weeks'] else '' for c in result['Mã']]
    result['Đối chiếu nguồn'] = [f"{SOURCE} · trang {metadata[c]['page']}" if c in metadata else 'Ngoài phạm vi cập nhật mục 7–15' for c in result['Mã']]
    return result


def bar_color(code):
    r = next((r for r in source_rows() if r['code'] == code), None)
    return BROWN if r and r['current_weeks'] else '#059669' if r else '#64748B'
