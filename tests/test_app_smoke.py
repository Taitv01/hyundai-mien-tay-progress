from pathlib import Path
import json
import socket
from unittest.mock import patch

from streamlit.testing.v1 import AppTest
import supabase_service
from supabase_service import OnlineSettings


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
    subheaders = [s.value for s in app.subheader]
    assert any("Quản lý file" in s for s in subheaders)
    expander_labels = [e.label for e in app.expander]
    assert any("Chú thích & Quy ước biểu đồ" in l for l in expander_labels)


def test_app_falls_back_to_readonly_when_supabase_dns_fails():
    app_path = Path(__file__).parents[1] / "app.py"
    fake_settings = OnlineSettings(
        url="https://paused-project.supabase.co",
        service_role_key="dummy-key",
    )

    def raise_dns_error(*_args, **_kwargs):
        raise socket.gaierror(-2, "Name or service not known")

    with (
        patch("importlib.reload", side_effect=lambda mod: mod),
        patch.object(supabase_service, "SupabaseService", side_effect=raise_dns_error),
    ):
        app = AppTest.from_file(str(app_path), default_timeout=20)
        app.secrets["SUPABASE_URL"] = fake_settings.url
        app.secrets["SUPABASE_SERVICE_ROLE_KEY"] = fake_settings.service_role_key
        app.run()

        assert not app.exception
        # Không bị dừng trắng trang: vẫn nạp đủ 62 hạng mục cam kết dự phòng
        assert len(app.session_state.progress_df) == 62
        warnings_text = "\n".join(w.value for w in app.warning)
        assert "Chế độ dự phòng" in warnings_text
        assert "Paused" in warnings_text or "tên miền" in warnings_text

        # Các bảng dữ liệu phải bị khóa chỉnh sửa (disabled=True) ở chế độ chỉ xem
        for editor in app.get("arrow_data_frame"):
            if getattr(editor.proto, "editing_mode", None) is not None:
                assert editor.proto.disabled is True

        # Nút "Thử kết nối lại" xóa cờ lỗi và thử lại bình thường không văng ngoại lệ
        app.button(key="banner_retry_supabase").click().run()
        assert not app.exception
        assert len(app.session_state.progress_df) == 62


def test_app_falls_back_cleanly_on_cloudflare_521_html_error():
    app_path = Path(__file__).parents[1] / "app.py"

    def raise_521_error(*_args, **_kwargs):
        raise RuntimeError(
            "{'message': 'Request failed with status 521', 'code': '521', "
            "'details': '<!DOCTYPE html><html><title>supabase.co | 521: Web server is down</title></html>'}"
        )

    with (
        patch("importlib.reload", side_effect=lambda mod: mod),
        patch.object(supabase_service, "SupabaseService", side_effect=raise_521_error),
    ):
        app = AppTest.from_file(str(app_path), default_timeout=20)
        app.secrets["SUPABASE_URL"] = "https://booting-project.supabase.co"
        app.secrets["SUPABASE_SERVICE_ROLE_KEY"] = "dummy-key"
        app.run()

        assert not app.exception
        warnings_text = "\n".join(w.value for w in app.warning)
        assert "521" in warnings_text
        assert "Chế độ dự phòng" in warnings_text
        captions_text = "\n".join(c.value for c in app.caption)
        assert "<!DOCTYPE html>" not in captions_text
        assert "HTTP 521" in captions_text
