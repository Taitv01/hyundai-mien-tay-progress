"""Dịch vụ lưu trữ online cho tiến độ, tài khoản và ảnh hiện trường."""

from __future__ import annotations

import base64
import datetime as dt
import hashlib
import hmac
import io
import secrets
import uuid
from dataclasses import dataclass
from typing import Any

import pandas as pd
from PIL import Image, ImageOps
from supabase import Client, create_client
from supabase.client import ClientOptions

from data_service import normalize_progress_data, normalize_qcvn_data


ALLOWED_ROLES = {"admin", "editor", "viewer"}
ROLE_LABELS = {
    "admin": "Quản trị",
    "editor": "Đại lý cập nhật",
    "viewer": "Chỉ xem",
}


@dataclass(frozen=True)
class OnlineSettings:
    url: str
    service_role_key: str
    photos_bucket: str = "progress-photos"
    bootstrap_username: str = ""
    bootstrap_password_hash: str = ""
    bootstrap_display_name: str = "Quản trị hệ thống"


@dataclass(frozen=True)
class AppUser:
    id: str
    username: str
    display_name: str
    role: str

    @property
    def can_edit(self) -> bool:
        return self.role in {"admin", "editor"}

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


def hash_password(password: str, salt: bytes | None = None) -> str:
    """Tạo chuỗi PBKDF2 có salt để không lưu mật khẩu thô."""

    if len(password) < 10:
        raise ValueError("Mật khẩu phải có ít nhất 10 ký tự.")
    salt = salt or secrets.token_bytes(16)
    iterations = 310_000
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return "pbkdf2_sha256${}${}${}".format(
        iterations,
        base64.urlsafe_b64encode(salt).decode("ascii"),
        base64.urlsafe_b64encode(digest).decode("ascii"),
    )


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt_text, digest_text = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        salt = base64.urlsafe_b64decode(salt_text.encode("ascii"))
        expected = base64.urlsafe_b64decode(digest_text.encode("ascii"))
        actual = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, int(iterations)
        )
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def prepare_image(image_bytes: bytes, max_side: int = 1920) -> bytes:
    """Xác thực, xoay đúng EXIF, thu nhỏ và chuẩn hóa ảnh thành JPEG."""

    if not image_bytes:
        raise ValueError("Tệp ảnh rỗng.")
    if len(image_bytes) > 12 * 1024 * 1024:
        raise ValueError("Mỗi ảnh không được vượt quá 12 MB.")

    try:
        with Image.open(io.BytesIO(image_bytes)) as source:
            source.verify()
        with Image.open(io.BytesIO(image_bytes)) as source:
            image = ImageOps.exif_transpose(source).convert("RGB")
            image.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
            output = io.BytesIO()
            image.save(output, format="JPEG", quality=84, optimize=True)
            return output.getvalue()
    except Exception as exc:
        raise ValueError("Tệp tải lên không phải ảnh hợp lệ.") from exc


class SupabaseService:
    def __init__(self, settings: OnlineSettings):
        self.settings = settings
        self.client: Client = create_client(
            settings.url,
            settings.service_role_key,
            options=ClientOptions(
                auto_refresh_token=False,
                persist_session=False,
                postgrest_client_timeout=20,
                storage_client_timeout=30,
            ),
        )

    def bootstrap_admin(self) -> None:
        if not self.settings.bootstrap_username or not self.settings.bootstrap_password_hash:
            return
        response = self.client.table("app_users").select("id").limit(1).execute()
        if response.data:
            return
        self.client.table("app_users").insert(
            {
                "username": self.settings.bootstrap_username.strip().lower(),
                "display_name": self.settings.bootstrap_display_name.strip(),
                "password_hash": self.settings.bootstrap_password_hash,
                "role": "admin",
                "is_active": True,
            }
        ).execute()

    def authenticate(self, username: str, password: str) -> AppUser | None:
        normalized = username.strip().lower()
        if not normalized or not password:
            return None
        response = (
            self.client.table("app_users")
            .select("id,username,display_name,password_hash,role,is_active")
            .eq("username", normalized)
            .limit(1)
            .execute()
        )
        if not response.data:
            return None
        row = response.data[0]
        if not row.get("is_active") or not verify_password(password, row["password_hash"]):
            return None
        return AppUser(
            id=str(row["id"]),
            username=row["username"],
            display_name=row["display_name"],
            role=row["role"],
        )

    def create_user(
        self,
        actor: AppUser,
        username: str,
        display_name: str,
        password: str,
        role: str,
    ) -> None:
        if not actor.is_admin:
            raise PermissionError("Chỉ quản trị viên được tạo tài khoản.")
        username = username.strip().lower()
        if len(username) < 3 or not username.replace("-", "").replace("_", "").isalnum():
            raise ValueError("Tên đăng nhập chỉ gồm chữ, số, dấu gạch ngang hoặc gạch dưới.")
        if role not in ALLOWED_ROLES:
            raise ValueError("Vai trò không hợp lệ.")
        self.client.table("app_users").insert(
            {
                "username": username,
                "display_name": display_name.strip() or username,
                "password_hash": hash_password(password),
                "role": role,
                "is_active": True,
            }
        ).execute()

    def change_password(self, actor: AppUser, current_password: str, new_password: str) -> None:
        if self.authenticate(actor.username, current_password) is None:
            raise ValueError("Mật khẩu hiện tại không đúng.")
        self.client.table("app_users").update(
            {"password_hash": hash_password(new_password), "updated_at": dt.datetime.now(dt.UTC).isoformat()}
        ).eq("id", actor.id).execute()

    def list_users(self, actor: AppUser) -> pd.DataFrame:
        if not actor.is_admin:
            raise PermissionError("Chỉ quản trị viên được xem danh sách tài khoản.")
        rows = (
            self.client.table("app_users")
            .select("id,username,display_name,role,is_active,created_at,last_login_at")
            .order("created_at")
            .execute()
            .data
        )
        return pd.DataFrame(rows)

    def set_user_active(self, actor: AppUser, user_id: str, active: bool) -> None:
        if not actor.is_admin:
            raise PermissionError("Chỉ quản trị viên được khóa tài khoản.")
        if user_id == actor.id and not active:
            raise ValueError("Không thể tự khóa tài khoản đang sử dụng.")
        self.client.table("app_users").update({"is_active": bool(active)}).eq("id", user_id).execute()

    def mark_login(self, user: AppUser) -> None:
        self.client.table("app_users").update(
            {"last_login_at": dt.datetime.now(dt.UTC).isoformat()}
        ).eq("id", user.id).execute()

    def seed_if_empty(self, progress_df: pd.DataFrame, qcvn_df: pd.DataFrame) -> None:
        tasks = self.client.table("tasks").select("code").limit(1).execute().data
        if not tasks:
            self.save_progress(progress_df, actor=None)
        qcvn = self.client.table("qcvn_items").select("stt").limit(1).execute().data
        if not qcvn:
            self.save_qcvn(qcvn_df, actor=None)

    def load_progress(self, current_date: dt.date | None = None) -> pd.DataFrame:
        rows = self.client.table("tasks").select("*").order("sort_order").execute().data
        df = pd.DataFrame(rows)
        if df.empty:
            return df
        renamed = df.rename(
            columns={
                "code": "Mã",
                "name": "Hạng mục công việc",
                "area": "Phân khu",
                "start_date": "Bắt đầu",
                "end_date": "Hoàn thành",
                "progress": "Tiến độ (%)",
                "status": "Trạng thái",
                "assignee": "Người phụ trách",
                "notes": "Ghi chú",
            }
        )
        return normalize_progress_data(renamed, current_date=current_date)

    def load_qcvn(self) -> pd.DataFrame:
        rows = self.client.table("qcvn_items").select("*").order("stt").execute().data
        df = pd.DataFrame(rows)
        if df.empty:
            return df
        renamed = df.rename(
            columns={
                "stt": "STT",
                "group_name": "Nhóm",
                "item_name": "Hạng mục",
                "is_ev": "Đặc thù EV",
                "assessment": "Đánh giá",
                "notes": "Ghi chú",
            }
        )
        return normalize_qcvn_data(renamed)

    def save_progress(self, df: pd.DataFrame, actor: AppUser | None) -> None:
        if actor is not None and not actor.can_edit:
            raise PermissionError("Tài khoản chỉ có quyền xem.")
        normalized = normalize_progress_data(df)
        rows = []
        for sort_order, row in normalized.iterrows():
            rows.append(
                {
                    "code": row["Mã"],
                    "name": row["Hạng mục công việc"],
                    "area": row["Phân khu"],
                    "start_date": row["Bắt đầu"].isoformat(),
                    "end_date": row["Hoàn thành"].isoformat(),
                    "progress": int(row["Tiến độ (%)"]),
                    "status": row["Trạng thái"],
                    "assignee": row["Người phụ trách"],
                    "notes": row["Ghi chú"],
                    "sort_order": int(sort_order),
                    "updated_by": actor.id if actor else None,
                    "updated_at": dt.datetime.now(dt.UTC).isoformat(),
                }
            )
        self.client.table("tasks").upsert(rows, on_conflict="code").execute()

    def save_qcvn(self, df: pd.DataFrame, actor: AppUser | None) -> None:
        if actor is not None and not actor.can_edit:
            raise PermissionError("Tài khoản chỉ có quyền xem.")
        normalized = normalize_qcvn_data(df)
        rows = [
            {
                "stt": int(row["STT"]),
                "group_name": row["Nhóm"],
                "item_name": row["Hạng mục"],
                "is_ev": bool(row["Đặc thù EV"]),
                "assessment": row["Đánh giá"],
                "notes": row["Ghi chú"],
                "updated_by": actor.id if actor else None,
                "updated_at": dt.datetime.now(dt.UTC).isoformat(),
            }
            for _, row in normalized.iterrows()
        ]
        self.client.table("qcvn_items").upsert(rows, on_conflict="stt").execute()

    def create_field_update(
        self,
        actor: AppUser,
        task_code: str,
        progress: int,
        status: str,
        note: str,
        images: list[tuple[str, bytes]],
    ) -> str:
        if not actor.can_edit:
            raise PermissionError("Tài khoản chỉ có quyền xem.")
        progress = max(0, min(100, int(progress)))
        if progress == 100:
            status = "Đã hoàn thiện"
        elif progress > 0 and status == "Chưa thực hiện":
            status = "Đang thi công"

        now = dt.datetime.now(dt.UTC).isoformat()
        self.client.table("tasks").update(
            {
                "progress": progress,
                "status": status,
                "notes": note.strip(),
                "updated_by": actor.id,
                "updated_at": now,
            }
        ).eq("code", task_code).execute()
        update_row = (
            self.client.table("progress_updates")
            .insert(
                {
                    "task_code": task_code,
                    "progress": progress,
                    "status": status,
                    "note": note.strip(),
                    "updated_by": actor.id,
                    "updated_by_name": actor.display_name,
                }
            )
            .execute()
            .data[0]
        )
        update_id = str(update_row["id"])

        for original_name, image_bytes in images:
            prepared = prepare_image(image_bytes)
            storage_path = (
                f"{task_code}/{dt.date.today().isoformat()}/"
                f"{uuid.uuid4().hex}.jpg"
            )
            self.client.storage.from_(self.settings.photos_bucket).upload(
                storage_path,
                prepared,
                {"content-type": "image/jpeg", "upsert": "false"},
            )
            self.client.table("progress_photos").insert(
                {
                    "update_id": update_id,
                    "task_code": task_code,
                    "storage_path": storage_path,
                    "original_name": original_name[:255],
                    "uploaded_by": actor.id,
                }
            ).execute()
        return update_id

    def recent_updates(self, limit: int = 30, task_code: str | None = None) -> list[dict[str, Any]]:
        query = (
            self.client.table("progress_updates")
            .select("id,task_code,progress,status,note,updated_by_name,created_at")
            .order("created_at", desc=True)
            .limit(limit)
        )
        if task_code:
            query = query.eq("task_code", task_code)
        updates = query.execute().data
        if not updates:
            return []
        update_ids = [row["id"] for row in updates]
        photos = (
            self.client.table("progress_photos")
            .select("id,update_id,storage_path,original_name,created_at")
            .in_("update_id", update_ids)
            .order("created_at")
            .execute()
            .data
        )
        by_update: dict[str, list[dict[str, Any]]] = {}
        for photo in photos:
            signed = self.client.storage.from_(self.settings.photos_bucket).create_signed_url(
                photo["storage_path"], 3600
            )
            photo["url"] = signed.get("signedURL") or signed.get("signedUrl")
            by_update.setdefault(str(photo["update_id"]), []).append(photo)
        for update in updates:
            update["photos"] = by_update.get(str(update["id"]), [])
        return updates
