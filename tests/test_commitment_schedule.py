import datetime as dt

from commitment_schedule import commitment_data, gantt_progress, source_rows, summarize_progress
from schedule_reports import build_printable_html


def test_pdf_milestones_and_all_work_packages():
    df = commitment_data().set_index('Mã')
    assert len(df) == 58
    assert df.index.is_unique
    assert df.loc['CK-07-01','Bắt đầu'] == dt.date(2026,9,15)
    assert df.loc['CK-07-01','Hoàn thành'] == dt.date(2026,9,30)
    assert df.loc['CK-07-02','Hoàn thành'] == dt.date(2026,10,14)
    assert df.loc['CK-08-01','Bắt đầu'] == dt.date(2026,9,22)
    assert df.loc['CK-14-03','Bắt đầu'] == dt.date(2026,12,22)
    assert df.loc['CK-15-03','Hoàn thành'] == dt.date(2027,3,31)
    assert len([r for r in source_rows() if not r['current_weeks']]) == 4
    assert len(df.loc[df['Phân khu'].str.startswith('08.')]) == 25


def test_hide_only_group_15_not_d116_equipment_or_detailed_report():
    df = commitment_data()
    visible = gantt_progress(df)
    assert len(visible) == 55
    assert not visible['Mã'].str.startswith('CK-15-').any()
    assert visible['Hạng mục công việc'].str.contains('D116').sum() == 2
    assert len(df) == 58
    report = build_printable_html(df, dt.date(2026,9,15))
    chart, details = report.split('2. BẢNG CHI TIẾT', 1)
    assert 'CK-15-' not in chart
    assert 'CK-15-03' in details
    assert '#8B5E3C' in chart


def test_summary_uses_current_equipment_schedule_and_live_changes():
    df = commitment_data()
    before = df.copy(deep=True)
    summary = summarize_progress(df).set_index('Mã')
    assert len(summary) == 9
    assert summary.loc['HM-08','Bắt đầu'] == dt.date(2026,9,22)
    assert summary.loc['HM-08','Hoàn thành'] == dt.date(2026,12,14)
    assert summary.loc['HM-09','Bắt đầu'] == dt.date(2026,11,1)
    assert summary.loc['HM-09','Tiến độ (%)'] == 0
    assert '4 công việc chỉ có mốc cũ' in summary.loc['HM-09','Ghi chú']
    assert df.equals(before)
    df.loc[df['Mã']=='CK-07-02','Hoàn thành'] = dt.date(2026,10,20)
    df.loc[df['Mã']=='CK-07-01','Tiến độ (%)'] = 100
    updated = summarize_progress(df).set_index('Mã')
    assert updated.loc['HM-07','Hoàn thành'] == dt.date(2026,10,20)
    assert updated.loc['HM-07','Tiến độ (%)'] == 50


def test_summary_report_has_only_parent_rows_and_retains_group_15_in_table():
    df = summarize_progress(commitment_data())
    assert len(gantt_progress(df)) == 8
    report = build_printable_html(df, dt.date(2026,9,15))
    chart, table = report.split('2. TỔNG HỢP HẠNG MỤC LỚN',1)
    assert 'HM-15' not in chart
    assert 'HM-15' in table
    assert 'CK-' not in report
