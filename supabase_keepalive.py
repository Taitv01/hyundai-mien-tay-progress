"""Tác vụ giữ kết nối định kỳ (Keep-Alive) cho cơ sở dữ liệu Supabase gói Free.

Thực hiện một truy vấn đọc tối thiểu qua PostgREST vào bảng `tasks` (LIMIT 1)
để ghi nhận hoạt động cơ sở dữ liệu định kỳ, tránh việc Supabase tự động tạm dừng
(Pause) dự án sau 7 ngày không có truy cập.
"""

from __future__ import annotations

import json
import os
import socket
import sys
import time
import tomllib
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


DEFAULT_TIMEOUT_SECONDS = 20
DEFAULT_MAX_ATTEMPTS = 3
DEFAULT_RETRY_DELAY_SECONDS = 5


def load_credentials(secrets_path: Path | None = None) -> tuple[str, str]:
    """Đọc SUPABASE_URL và khóa truy cập từ biến môi trường hoặc secrets.toml cục bộ."""
    url = os.environ.get("SUPABASE_URL", "").strip()
    key = (
        os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        or os.environ.get("SUPABASE_KEY")
        or os.environ.get("SUPABASE_ANON_KEY")
        or ""
    ).strip()

    if url and key:
        return url, key

    candidate = secrets_path or (Path(__file__).resolve().parent / ".streamlit" / "secrets.toml")
    if candidate.is_file():
        data = tomllib.loads(candidate.read_text(encoding="utf-8"))
        sup = data.get("supabase", {}) if isinstance(data.get("supabase"), dict) else {}
        url = url or str(sup.get("url") or data.get("SUPABASE_URL", "")).strip()
        key = key or str(
            sup.get("service_role_key")
            or data.get("SUPABASE_SERVICE_ROLE_KEY")
            or data.get("SUPABASE_KEY", "")
        ).strip()

    return url, key


def build_ping_request(base_url: str, api_key: str) -> urllib.request.Request:
    """Tạo HTTP GET truy vấn 1 dòng bảng `tasks` qua PostgREST."""
    cleaned_url = (base_url or "").strip().rstrip("/")
    parsed = urllib.parse.urlparse(cleaned_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(
            "SUPABASE_URL không hợp lệ (cần có dạng https://<project-ref>.supabase.co)."
        )
    if not (api_key or "").strip():
        raise ValueError("Thiếu khóa SUPABASE_SERVICE_ROLE_KEY (hoặc SUPABASE_KEY).")

    endpoint = f"{cleaned_url}/rest/v1/tasks?select=code&limit=1"
    headers = {
        "apikey": api_key.strip(),
        "Authorization": f"Bearer {api_key.strip()}",
        "Accept": "application/json",
        "User-Agent": "hyundai-mien-tay-keepalive/1.0",
    }
    return urllib.request.Request(endpoint, headers=headers, method="GET")


def is_dns_error(exc: BaseException) -> bool:
    """Nhận diện lỗi không phân giải được tên miền (thường do dự án Supabase đang Paused)."""
    if isinstance(exc, socket.gaierror):
        return True
    reason = getattr(exc, "reason", None)
    if isinstance(reason, socket.gaierror):
        return True
    text = str(exc).lower()
    dns_markers = (
        "name or service not known",
        "getaddrinfo failed",
        "temporary failure in name resolution",
        "nodename nor servname provided",
        "no address associated with hostname",
        "nxdomain",
    )
    return any(marker in text for marker in dns_markers)


def ping_supabase(
    base_url: str,
    api_key: str,
    *,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    retry_delay: float = DEFAULT_RETRY_DELAY_SECONDS,
    opener=urllib.request.urlopen,
) -> dict[str, object]:
    """Gửi truy vấn Keep-Alive tới Supabase với cơ chế thử lại khi mạng chập chờn."""
    request = build_ping_request(base_url, api_key)
    host = urllib.parse.urlparse(base_url.strip()).hostname or "supabase"
    last_error: Exception | None = None

    for attempt in range(1, max(1, max_attempts) + 1):
        try:
            with opener(request, timeout=timeout) as response:
                status = getattr(response, "status", 200)
                raw_body = response.read().decode("utf-8", errors="replace")
                rows = json.loads(raw_body) if raw_body.strip() else []
                row_count = len(rows) if isinstance(rows, list) else 0
                return {
                    "ok": True,
                    "status": status,
                    "host": host,
                    "rows_sampled": row_count,
                    "attempt": attempt,
                }
        except urllib.error.HTTPError as exc:
            # Lỗi xác thực 401/403 hoặc sai đường dẫn 404 không cần thử lại
            if exc.code in {400, 401, 403, 404}:
                raise RuntimeError(
                    f"Supabase trả về mã HTTP {exc.code} trên {host}. "
                    "Vui lòng kiểm tra lại SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY "
                    "và đảm bảo đã chạy supabase_setup.sql."
                ) from exc
            last_error = exc
        except Exception as exc:
            last_error = exc
            if is_dns_error(exc):
                raise RuntimeError(
                    f"Không thể phân giải tên miền {host} ({exc}). "
                    "Dự án Supabase có thể đang bị tạm dừng (Paused) — "
                    "vui lòng vào Supabase Dashboard bấm 'Restore project' trước."
                ) from exc

        if attempt < max_attempts and retry_delay > 0:
            time.sleep(retry_delay)

    raise RuntimeError(
        f"Keep-Alive thất bại sau {max_attempts} lần thử tới {host}: {last_error}"
    ) from last_error


def main() -> int:
    try:
        url, key = load_credentials()
        if not url or not key:
            print(
                "LỖI CẤU HÌNH: Chưa khai báo SUPABASE_URL và SUPABASE_SERVICE_ROLE_KEY.\n"
                "Trên GitHub: vào Settings -> Secrets and variables -> Actions -> "
                "New repository secret để thêm SUPABASE_URL và SUPABASE_SERVICE_ROLE_KEY.",
                file=sys.stderr,
            )
            return 1

        result = ping_supabase(url, key)
        print(
            f"[OK] Supabase Keep-Alive thành công: host={result['host']} "
            f"status={result['status']} rows_sampled={result['rows_sampled']} "
            f"(lần thử {result['attempt']})."
        )
        return 0
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
