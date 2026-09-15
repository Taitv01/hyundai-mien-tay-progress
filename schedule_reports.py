"""Shared weekly Gantt and detailed reports; PDF is generated from current data."""
import datetime as dt
import html
import io

import pandas as pd

from commitment_schedule import BROWN, SOURCE, WEEK_NOTE, commitment_details, gantt_progress, source_rows, week_date, week_label

CSS = '''
@page { size:A4 landscape; margin:9mm; }
body { font-family: sans-serif; font-size:10px; color:#172B3A; margin:0; }
h1 { font-size:18px; color:#002C6C; margin:0 0 5px; }
h2 { font-size:13px; color:#002C6C; margin:8px 0; }
p { margin:4px 0 8px; }
table { width:100%; border-collapse:collapse; table-layout:fixed; }
th { background:#002C6C; color:white; font-weight:bold; }
td,th { border:1px solid #CCD3DA; padding:5px; vertical-align:top; }
.gantt td,.gantt th { padding:4px 2px; font-size:9px; }
.gantt td { height:22px; }
.detail td { font-size:9px; line-height:1.3; }
.muted { color:#586875; font-size:9px; }
.page { page-break-after:always; margin-bottom:28px; }
.page:last-child { page-break-after:auto; }
thead { display:table-header-group; }
tr { break-inside:avoid; }
@media print { .page { margin-bottom:0; } .no-print { display:none; } body { print-color-adjust:exact; -webkit-print-color-adjust:exact; } }
'''


def esc(value):
    return html.escape(str(value)).replace('\n', '<br>')


def report_sections(df, report_date):
    metadata = {r['code']: r for r in source_rows()}
    title = f'<h1>TIẾN ĐỘ DỰ ÁN HYUNDAI MIỀN TÂY — CẦN THƠ</h1><p>Chủ đầu tư: Thế Giới Xe Tải · Mốc theo dõi: <b>{report_date:%d/%m/%Y}</b><br>Nguồn cam kết: {esc(SOURCE)} · {len(df)} công việc đang theo dõi, gồm 58 dòng thuộc mục 7–15.</p>'
    legend = f'<p class="muted"><b style="color:{BROWN}">■ Màu nâu: kế hoạch áp dụng từ mục 7.</b> Mục 15 tạm ẩn trên Gantt; vẫn có trong bảng chi tiết.<br>{WEEK_NOTE}</p>'
    visible = gantt_progress(df)
    # Historical purchasing milestones have no new dates; do not extend the new Gantt back to May.
    dated = visible.loc[[bool(metadata.get(c, {}).get('current_weeks', True)) for c in visible['Mã']]]
    first = min(pd.to_datetime(dated['Bắt đầu']).min().date(), dt.date(2026, 9, 1)).replace(day=1)
    last = max(pd.to_datetime(dated['Hoàn thành']).max().date(), dt.date(2026, 12, 31))
    months = []
    cursor = first
    while cursor <= last:
        months.append((cursor.year, cursor.month))
        cursor = dt.date(cursor.year+cursor.month//12, cursor.month%12+1, 1)
    weeks = [dict(year=y, month=m, week=w) for y,m in months for w in range(1,5)]
    head = '<thead><tr><th rowspan="2" style="width:34%">Mã / Hạng mục — Diễn giải</th>' + ''.join(f'<th colspan="4">{m:02}/{y}</th>' for y,m in months) + '</tr><tr>' + ''.join(f'<th>W{w["week"]}</th>' for w in weeks) + '</tr></thead>'
    sections = []
    for start in range(0, len(visible), 18):
        lines = []
        for _, r in visible.iloc[start:start+18].iterrows():
            code = r['Mã']
            item = metadata.get(code)
            label = f'<b>{esc(code)}</b> · {esc(r["Hạng mục công việc"])}<br><span class="muted">{esc(r["Phân khu"])}</span>'
            cells = []
            historical = item and not item['current_weeks']
            if historical:
                cells = [f'<td colspan="{len(weeks)}" style="color:#059669">Đã hoàn thiện theo mốc cũ trong PDF; chưa có mốc mới.</td>']
            else:
                for w in weeks:
                    overlaps = r['Bắt đầu'] <= week_date(w, True) and r['Hoàn thành'] >= week_date(w)
                    color = BROWN if item else '#059669' if r['Tiến độ (%)'] == 100 else '#64748B'
                    in_week = week_date(w) <= report_date <= week_date(w, True)
                    style = f'background-color:{color};color:white;' if overlaps else 'background-color:#FFFFFF;'
                    if in_week:
                        style += 'border-left:2px solid #C83232;'
                    cells.append(f'<td style="{style}">{"&#160;"}</td>')
            lines.append(f'<tr><td>{label}</td>{"".join(cells)}</tr>')
        sections.append(title + f'<h2>1. BIỂU ĐỒ GANTT THEO TUẦN · Công việc {start+1}–{min(start+18,len(visible))}/{len(visible)}</h2>' + legend + '<table class="gantt">' + head + '<tbody>' + ''.join(lines) + '</tbody></table>')
    for start in range(0, len(df), 10):
        lines = []
        for _, r in df.iloc[start:start+10].iterrows():
            item = metadata.get(r['Mã'])
            weeks = item['current_weeks'] if item else []
            period = f'{week_label(weeks[0])}<br>→ {week_label(weeks[-1])}' if weeks else 'Chưa có mốc mới trên PDF' if item else 'Ngoài phạm vi mục 7–15'
            period += f'<br><span class="muted">Hiển thị: {r["Bắt đầu"]:%d/%m/%Y} – {r["Hoàn thành"]:%d/%m/%Y}</span>'
            lines.append('<tr>' + ''.join(f'<td>{v}</td>' for v in [f'<b>{esc(r["Mã"])}</b><br>{esc(r["Phân khu"])}',esc(r['Hạng mục công việc']),period,f'{r["Tiến độ (%)"]}%<br>{esc(r["Trạng thái"])}',esc(r['Người phụ trách']),esc(r['Ghi chú'])]) + '</tr>')
        head = '<thead><tr><th style="width:12%">Mã / Hạng mục</th><th style="width:21%">Diễn giải công việc</th><th style="width:19%">Mốc cam kết theo tuần</th><th style="width:10%">Thực tế</th><th style="width:9%">P.I.C</th><th style="width:29%">Nguồn và ghi chú</th></tr></thead>'
        sections.append(title + f'<h2>2. BẢNG CHI TIẾT · Công việc {start+1}–{min(start+10,len(df))}/{len(df)}</h2><p class="muted">{WEEK_NOTE} Tiến độ thực tế không suy ra từ độ dài thanh kế hoạch.</p><table class="detail">' + head + '<tbody>' + ''.join(lines) + '</tbody></table>')
    return sections


def build_printable_html(df, report_date):
    sections = report_sections(df, report_date)
    return '<!doctype html><html lang="vi"><head><meta charset="utf-8"><title>Tiến độ cam kết Hyundai Miền Tây 15/09/2026</title><style>'+CSS+'</style></head><body><button class="no-print" onclick="window.print()">In báo cáo</button>' + ''.join('<section class="page">'+s+'</section>' for s in sections) + '</body></html>'


def build_pdf(df, report_date):
    import fitz
    doc = fitz.open()
    metadata = {r['code']: r for r in source_rows()}
    def color(h):
        return tuple(int(h[i:i+2],16)/255 for i in (1,3,5))
    def box(page, rect, text, background=None, size=8, foreground='#172B3A'):
        rect = fitz.Rect(rect)
        page.draw_rect(rect, color=color('#CCD3DA'), fill=color(background) if background else None, width=.4)
        if not text:
            return
        content = f'<div style="font-family:sans-serif;font-size:{size}px;color:{foreground}">{text}</div>'
        page.insert_htmlbox(rect + (3,2,-3,-2), content)
    def new_page(subtitle):
        page = doc.new_page(width=842,height=595)
        content = (f'<h2 style="color:#002C6C;margin:0;font-size:16px">TIẾN ĐỘ DỰ ÁN HYUNDAI MIỀN TÂY — CẦN THƠ</h2>'
                   f'<p style="margin:4px 0;font-size:9px">Chủ đầu tư: Thế Giới Xe Tải · Mốc theo dõi: {report_date:%d/%m/%Y} · Nguồn cam kết: PDF 15/09/2026<br>'
                   f'{esc(subtitle)}<br>{WEEK_NOTE}</p>')
        page.insert_htmlbox(fitz.Rect(26,18,816,87),content)
        return page
    visible = gantt_progress(df)
    dated = visible.loc[[bool(metadata.get(c, {}).get('current_weeks', True)) for c in visible['Mã']]]
    first = min(pd.to_datetime(dated['Bắt đầu']).min().date(),dt.date(2026,9,1)).replace(day=1)
    last = max(pd.to_datetime(dated['Hoàn thành']).max().date(),dt.date(2026,12,31))
    months = []
    cursor = first
    while cursor <= last:
        months.append((cursor.year,cursor.month))
        cursor = dt.date(cursor.year+cursor.month//12,cursor.month%12+1,1)
    weeks = [dict(year=y,month=m,week=w) for y,m in months for w in range(1,5)]
    left, label_width, width = 26, 310, 790
    cell_w = (width-label_width)/len(weeks)
    for start in range(0,len(visible),16):
        page = new_page(f'1. GANTT · Công việc {start+1}–{min(start+16,len(visible))}/{len(visible)} · Màu nâu: cam kết áp dụng. Mục 15 tạm ẩn trên biểu đồ.')
        box(page,(left,88,left+label_width,124),'<b>Mã / Hạng mục — Diễn giải</b>','#002C6C',9,'#FFFFFF')
        for i,(y,m) in enumerate(months):
            x = left+label_width+i*4*cell_w
            box(page,(x,88,x+4*cell_w,106),f'<b>{m:02}/{y}</b>','#002C6C',8,'#FFFFFF')
        for i,w in enumerate(weeks):
            x = left+label_width+i*cell_w
            box(page,(x,106,x+cell_w,124),f'W{w["week"]}','#002C6C',8,'#FFFFFF')
        for i,(_,r) in enumerate(visible.iloc[start:start+16].iterrows()):
            y = 124+i*26
            item = metadata.get(r['Mã'])
            box(page,(left,y,left+label_width,y+26),f'<b>{esc(r["Mã"])}</b> · {esc(r["Hạng mục công việc"])}<br><span style="font-size:7px;color:#586875">{esc(r["Phân khu"])}</span>',size=8)
            if item and not item['current_weeks']:
                box(page,(left+label_width,y,816,y+26),'Đã hoàn thiện theo mốc cũ trên PDF; chưa có mốc mới.',size=8,foreground='#059669')
                continue
            for j,w in enumerate(weeks):
                x = left+label_width+j*cell_w
                overlaps = r['Bắt đầu'] <= week_date(w,True) and r['Hoàn thành'] >= week_date(w)
                fill = BROWN if item else '#059669' if r['Tiến độ (%)']==100 else '#64748B'
                box(page,(x,y,x+cell_w,y+26),'',fill if overlaps else None)
                if week_date(w) <= report_date <= week_date(w,True):
                    page.draw_line((x,y),(x,y+26),color=color('#C83232'),width=1)
    widths = [77,163,150,66,58,276]
    for start in range(0,len(df),10):
        page = new_page(f'2. BẢNG CHI TIẾT · Công việc {start+1}–{min(start+10,len(df))}/{len(df)} · Bao gồm đầy đủ mục 15.')
        x = 26
        for label,w in zip(['Mã / Mục','Diễn giải công việc','Mốc cam kết theo tuần','Thực tế','P.I.C','Nguồn / Ghi chú'],widths):
            box(page,(x,88,x+w,112),f'<b>{label}</b>','#002C6C',8,'#FFFFFF')
            x += w
        for i,(_,r) in enumerate(df.iloc[start:start+10].iterrows()):
            y = 112+i*44
            item = metadata.get(r['Mã'])
            current = item['current_weeks'] if item else []
            period = f'{week_label(current[0])}<br>→ {week_label(current[-1])}' if current else 'Chỉ có mốc cũ trên PDF' if item else 'Ngoài phạm vi mục 7–15'
            period += f'<br><span style="font-size:7px">{r["Bắt đầu"]:%d/%m/%Y} – {r["Hoàn thành"]:%d/%m/%Y}</span>'
            values = [f'<b>{esc(r["Mã"])}</b><br>{esc(r["Phân khu"])}',esc(r['Hạng mục công việc']),period,f'{r["Tiến độ (%)"]}%<br>{esc(r["Trạng thái"])}',esc(r['Người phụ trách']),esc(r['Ghi chú'])]
            x = 26
            for value,w in zip(values,widths):
                box(page,(x,y,x+w,y+44),value,size=8)
                x += w
    for i, page in enumerate(doc):
        page.insert_text((770, 583), f'{i+1}/{len(doc)}', fontsize=8, color=(.35,.4,.45))
    doc.subset_fonts()
    content = doc.tobytes(garbage=4, deflate=True)
    doc.close()
    return content


def build_excel(df, qcvn):
    from openpyxl.styles import PatternFill, Font, Alignment
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        commitment_details(df).to_excel(writer, sheet_name='Tien_Do_Thi_Cong', index=False)
        qcvn.to_excel(writer, sheet_name='QCVN_121_Checklist', index=False)
        for sheet in writer.book:
            sheet.freeze_panes = 'C2'
            sheet.auto_filter.ref = sheet.dimensions
            for c in sheet[1]:
                c.fill = PatternFill('solid', fgColor='002C6C')
                c.font = Font(color='FFFFFF', bold=True)
            for row in sheet.iter_rows(min_row=2):
                for c in row:
                    c.alignment = Alignment(vertical='top', wrap_text=True)
                if sheet.title == 'Tien_Do_Thi_Cong' and str(row[0].value).startswith('CK-'):
                    row[0].font = Font(color=BROWN[1:], bold=True)
            for col in sheet.columns:
                sheet.column_dimensions[col[0].column_letter].width = 24
            sheet.column_dimensions['B'].width = 48
            sheet.column_dimensions['I'].width = 90
    return output.getvalue()
