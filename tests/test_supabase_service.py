import io

import pytest
from PIL import Image

from supabase_service import (
    DEFAULT_DELETE_PIN_HASH,
    SIGNED_URL_FALLBACK_EXPIRES_IN,
    OnlineSettings,
    SupabaseService,
    hash_delete_pin,
    hash_password,
    prepare_image,
    prepare_pdf,
    verify_password,
)


def test_password_hash_is_salted_and_verifiable():
    first = hash_password("MatKhauAnToan2026")
    second = hash_password("MatKhauAnToan2026")

    assert first != second
    assert verify_password("MatKhauAnToan2026", first)
    assert not verify_password("MatKhauSai", first)
    assert not verify_password("MatKhauAnToan2026", "du-lieu-khong-hop-le")


def test_password_must_have_at_least_ten_characters():
    with pytest.raises(ValueError, match="10 ký tự"):
        hash_password("qua-ngan")


def test_delete_pin_hash_supports_short_pin_and_verifies_default():
    pin_hash = hash_delete_pin("2026")
    assert verify_password("2026", pin_hash)
    assert not verify_password("9999", pin_hash)
    assert verify_password("HMT2026", DEFAULT_DELETE_PIN_HASH)

    with pytest.raises(ValueError, match="4 ký tự"):
        hash_delete_pin("123")


def test_prepare_image_converts_and_resizes_to_jpeg():
    source = Image.new("RGBA", (2400, 1200), color=(30, 90, 150, 180))
    buffer = io.BytesIO()
    source.save(buffer, format="PNG")

    prepared = prepare_image(buffer.getvalue(), max_side=800)

    with Image.open(io.BytesIO(prepared)) as result:
        assert result.format == "JPEG"
        assert result.mode == "RGB"
        assert max(result.size) == 800


def test_prepare_image_rejects_invalid_bytes():
    with pytest.raises(ValueError, match="không phải ảnh hợp lệ"):
        prepare_image(b"day-khong-phai-anh")


def test_prepare_pdf_accepts_valid_pdf():
    valid_pdf = b"%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF"
    result = prepare_pdf(valid_pdf)
    assert result == valid_pdf


def test_prepare_pdf_rejects_invalid_bytes():
    with pytest.raises(ValueError, match="không phải định dạng PDF hợp lệ"):
        prepare_pdf(b"day-la-van-ban-thuong-khong-phai-pdf")


def test_prepare_pdf_rejects_empty():
    with pytest.raises(ValueError, match="Tệp PDF rỗng"):
        prepare_pdf(b"")


def test_prepare_pdf_rejects_oversized():
    fake_large_pdf = b"%PDF-1.4\n" + b"0" * (26 * 1024 * 1024)
    with pytest.raises(ValueError, match="vượt quá 25 MB"):
        prepare_pdf(fake_large_pdf)


def test_get_file_url_returns_non_expiring_public_url():
    assert SIGNED_URL_FALLBACK_EXPIRES_IN >= 315_360_000

    class DummyBucketRef:
        def get_public_url(self, path: str) -> str:
            return f"https://example.supabase.co/storage/v1/object/public/progress-photos/{path}?"

    class DummyStorage:
        def update_bucket(self, bucket: str, opts: dict) -> None:
            assert opts.get("public") is True

        def from_(self, bucket: str) -> DummyBucketRef:
            return DummyBucketRef()

    class DummyClient:
        storage = DummyStorage()

    svc = object.__new__(SupabaseService)
    svc.settings = OnlineSettings(url="https://example.supabase.co", service_role_key="dummy")
    svc.client = DummyClient()

    url = svc.get_file_url("PL-01/2026-09-04/test.pdf")
    assert url == "https://example.supabase.co/storage/v1/object/public/progress-photos/PL-01/2026-09-04/test.pdf"
    assert "token=" not in url
    assert svc.get_file_url("") is None



