from __future__ import annotations

import io
import socket
import urllib.error
from pathlib import Path

import pytest

from supabase_keepalive import (
    build_ping_request,
    is_dns_error,
    load_credentials,
    ping_supabase,
)


class _DummyResponse:
    def __init__(self, body: bytes, status: int = 200):
        self._body = body
        self.status = status

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_build_ping_request_targets_tasks_table_limit_one():
    req = build_ping_request("https://example.supabase.co/", "secret-key-123")
    assert req.full_url == "https://example.supabase.co/rest/v1/tasks?select=code&limit=1"
    assert req.get_method() == "GET"
    assert req.headers["Apikey"] == "secret-key-123"
    assert req.headers["Authorization"] == "Bearer secret-key-123"


def test_build_ping_request_validates_inputs():
    with pytest.raises(ValueError, match="SUPABASE_URL"):
        build_ping_request("not-a-url", "secret")
    with pytest.raises(ValueError, match="SUPABASE_SERVICE_ROLE_KEY"):
        build_ping_request("https://example.supabase.co", "   ")


def test_ping_supabase_succeeds_and_retries_transient_error():
    calls = {"count": 0}

    def flaky_opener(req, timeout=20):
        calls["count"] += 1
        if calls["count"] == 1:
            raise TimeoutError("timed out")
        return _DummyResponse(b'[{"code":"PL-01"}]', status=200)

    result = ping_supabase(
        "https://example.supabase.co",
        "secret-key",
        max_attempts=3,
        retry_delay=0,
        opener=flaky_opener,
    )
    assert result["ok"] is True
    assert result["status"] == 200
    assert result["rows_sampled"] == 1
    assert result["attempt"] == 2


def test_ping_supabase_reports_paused_project_on_dns_error():
    def dns_fail_opener(req, timeout=20):
        raise urllib.error.URLError(socket.gaierror(-2, "Name or service not known"))

    assert is_dns_error(socket.gaierror(-2, "Name or service not known"))
    with pytest.raises(RuntimeError, match="Paused"):
        ping_supabase(
            "https://paused.supabase.co",
            "secret-key",
            max_attempts=3,
            retry_delay=0,
            opener=dns_fail_opener,
        )


def test_ping_supabase_stops_immediately_on_unauthorized():
    calls = {"count": 0}

    def unauth_opener(req, timeout=20):
        calls["count"] += 1
        raise urllib.error.HTTPError(
            req.full_url, 401, "Unauthorized", hdrs=None, fp=io.BytesIO(b"")
        )

    with pytest.raises(RuntimeError, match="HTTP 401"):
        ping_supabase(
            "https://example.supabase.co",
            "bad-key",
            max_attempts=3,
            retry_delay=0,
            opener=unauth_opener,
        )
    assert calls["count"] == 1


def test_load_credentials_reads_toml_when_env_missing(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
    monkeypatch.delenv("SUPABASE_KEY", raising=False)
    monkeypatch.delenv("SUPABASE_ANON_KEY", raising=False)

    toml_file = tmp_path / "secrets.toml"
    toml_file.write_text(
        'SUPABASE_URL = "https://demo.supabase.co"\n'
        'SUPABASE_SERVICE_ROLE_KEY = "demo-role-key"\n',
        encoding="utf-8",
    )
    url, key = load_credentials(secrets_path=toml_file)
    assert url == "https://demo.supabase.co"
    assert key == "demo-role-key"


def test_github_workflow_file_is_configured_every_3_days():
    workflow_path = (
        Path(__file__).parents[1]
        / ".github"
        / "workflows"
        / "supabase-keepalive.yml"
    )
    assert workflow_path.is_file()
    content = workflow_path.read_text(encoding="utf-8")
    assert "*/3 * *" in content
    assert "workflow_dispatch:" in content
    assert "secrets.SUPABASE_URL" in content
    assert "secrets.SUPABASE_SERVICE_ROLE_KEY" in content
    assert "supabase_keepalive.py" in content
