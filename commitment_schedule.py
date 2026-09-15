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
             'W3 = 15–21; W4 = 22–cuối tháng. Ngày hiển thị được quy đổi từ ô tuần; các số ghi riêng trên PDF được đối chiếu trong ghi chú.')
LEGACY_CODES = {f'SR-{i:02}' for i in range(1, 6)} | {f'WS-{i:02}' for i in range(1, 6)} | {'OP-01', 'OP-02'}
MAJOR_GROUPS = {
    6: 'Bản vẽ layout/3D, hợp đồng thuê mặt bằng',
    7: 'Giấy phép xây dựng', 8: 'Thi công', 9: 'Dụng cụ thiết bị',
    10: 'Tuyển dụng', 11: 'Hoàn thiện', 12: 'Đào tạo',
    13: 'Hoạt động', 14: 'Khai trương', 15: 'D116 (TCVN: 121)',
}
SUMMARY_NOTE = ('Mỗi dòng là một hạng mục lớn. Thời gian bao quát các công việc con; '
                'tiến độ là bình quân các công việc có mốc áp dụng, chưa tính trọng số. '
                'Các mốc cũ chưa có kế hoạch mới không gộp vào thời gian và tỷ lệ tổng hợp.')


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
        if r['code'] == 'CK-07-02':
            note += ' Ô cuối PDF ghi “15” tại W2 tháng 10; giữ nguyên mốc ô tuần. Ngày 14/10 trong bảng là quy đổi W2, chưa phải xác nhận ngày cấp phép; cần đối chiếu số 15 với CĐT.'
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
    codes = df['Mã'].astype(str)
    return df.loc[~(codes.str.startswith('CK-15-') | codes.eq('HM-15'))].copy()


def major_group(code):
    if code.startswith('CK-') or code.startswith('HM-'):
        return int(code.split('-')[1])
    return 6 if code in {'PL-01', 'PL-02', 'PL-03', 'PL-04'} else 99


def major_label(code):
    group = major_group(str(code))
    return f'{group:02}. {MAJOR_GROUPS.get(group, "Hạng mục khác")}'


def summarize_progress(df):
    """Read-only rollup of live rows. Never persist aggregate rows as field tasks."""
    metadata = {r['code']: r for r in source_rows()}
    work = active_progress(df).copy()
    work['_group'] = work['Mã'].map(major_group)
    result = []
    for group, children in work.groupby('_group', sort=True):
        applicable = children.loc[[bool(metadata.get(c, {}).get('current_weeks', True)) for c in children['Mã']]]
        if applicable.empty:
            continue
        percent = int(round(applicable['Tiến độ (%)'].mean()))
        statuses = set(applicable['Trạng thái'])
        status = ('Đã hoàn thiện' if percent == 100 else 'Dời tiến độ' if 'Dời tiến độ' in statuses
                  else 'Đang thi công' if percent > 0 or 'Đang thi công' in statuses else 'Chưa thực hiện')
        name = MAJOR_GROUPS.get(group, 'Hạng mục khác')
        excluded = len(children) - len(applicable)
        note = f'Tổng hợp {len(applicable)} công việc có mốc áp dụng.'
        if excluded:
            note += f' {excluded} công việc chỉ có mốc cũ được bảo lưu riêng.'
        result.append({
            'Mã': f'HM-{group:02}', 'Hạng mục công việc': name,
            'Phân khu': f'{group:02}. {name}',
            'Bắt đầu': min(applicable['Bắt đầu']), 'Hoàn thành': max(applicable['Hoàn thành']),
            'Tiến độ (%)': percent, 'Trạng thái': status,
            'Người phụ trách': ' / '.join(dict.fromkeys(applicable['Người phụ trách'].str.strip())),
            'Ghi chú': note,
        })
    return pd.DataFrame(result, columns=df.columns.intersection([
        'Mã', 'Hạng mục công việc', 'Phân khu', 'Bắt đầu', 'Hoàn thành',
        'Tiến độ (%)', 'Trạng thái', 'Người phụ trách', 'Ghi chú']))


def commitment_details(df):
    metadata = {r['code']: r for r in source_rows()}
    result = df.copy()
    result['Mục PDF'] = [str(metadata.get(c, {}).get('group', '')) for c in result['Mã']]
    result['Bắt đầu cam kết'] = [week_label(metadata[c]['current_weeks'][0]) if c in metadata and metadata[c]['current_weeks'] else '' for c in result['Mã']]
    result['Kết thúc cam kết'] = [week_label(metadata[c]['current_weeks'][-1]) if c in metadata and metadata[c]['current_weeks'] else '' for c in result['Mã']]
    result['Đối chiếu nguồn'] = [f"{SOURCE} · trang {metadata[c]['page']}" if c in metadata else 'Ngoài phạm vi cập nhật mục 7–15' for c in result['Mã']]
    return result


def bar_color(code):
    if str(code).startswith('HM-'):
        return BROWN if 7 <= major_group(code) <= 15 else '#64748B'
    r = next((r for r in source_rows() if r['code'] == code), None)
    return BROWN if r and r['current_weeks'] else '#059669' if r else '#64748B'
