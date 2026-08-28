from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_app_starts_without_runtime_exception():
    app_path = Path(__file__).parents[1] / "app.py"
    app = AppTest.from_file(str(app_path), default_timeout=20).run()
    assert not app.exception
    labels = {metric.label for metric in app.metric}
    assert "Tổng hạng mục" in labels
    assert "Cốt lõi EV theo QCVN" in labels
