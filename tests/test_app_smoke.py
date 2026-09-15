from pathlib import Path
import json

from streamlit.testing.v1 import AppTest


def test_app_starts_without_runtime_exception():
    app_path = Path(__file__).parents[1] / "app.py"
    app = AppTest.from_file(str(app_path), default_timeout=20).run()
    assert not app.exception
    labels = {metric.label for metric in app.metric}
    assert "Tổng hạng mục" in labels
    assert "Checklist QCVN 121" in labels
    assert "Cốt lõi EV theo QCVN" not in labels
    def gantt_labels():
        spec = json.loads(app.get('plotly_chart')[0].proto.spec)
        return [label for trace in spec['data'] for label in trace['y']]
    assert len(gantt_labels()) == 9
    assert all('HM-' in label for label in gantt_labels())
    assert not any('HM-15' in label for label in gantt_labels())
    assert app.selectbox(key='report_level').value == 'Hạng mục lớn'
    app.selectbox(key='gantt_level').select('Công việc chi tiết').run()
    assert not app.exception
    assert len(gantt_labels()) == 59
    app.multiselect(key='gantt_major_groups').select('07. Giấy phép xây dựng').run()
    assert len(gantt_labels()) == 2
    app.selectbox(key='gantt_level').select('Hạng mục lớn').run()
    assert len(gantt_labels()) == 1
    assert len(app.session_state.progress_df) == 62
