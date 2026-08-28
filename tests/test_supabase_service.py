import io

import pytest
from PIL import Image

from supabase_service import hash_password, prepare_image, verify_password


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
