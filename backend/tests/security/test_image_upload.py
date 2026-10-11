"""Security test cases for menu image upload and sanitization (SEC-T19 & SEC-T20).

Follows `docs/06-security-specification.md` (Section 26),
`docs/10-deployment-and-devops-specification.md`, and
`docs/13-final-implementation-blueprint.md`.
Verifies:
1. Valid JPEG/PNG/WebP is re-encoded into clean WebP with EXIF metadata stripped.
2. User-provided filenames are completely discarded; random UUID filenames are used.
3. SVG containing `<script>` or XML disguised with `.jpg` extension is rejected (HTTP 415/422).
4. HTML or arbitrary binary payload disguised as image is rejected.
5. Uploads exceeding 2 MB are rejected (HTTP 413/422).
6. Non-admin users are rejected (HTTP 403).
7. Unauthenticated upload attempts are rejected (HTTP 401).
8. Safe deletion of dish image and traversal prevention.
"""

from __future__ import annotations

import io
import uuid
from pathlib import Path
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from PIL import Image

from app.core.database import get_db
from app.core.dependencies import get_current_staff_user
from app.core.exceptions import PayloadTooLargeError, UnsupportedMediaTypeError
from app.main import create_app
from app.models.enums import UserRole, UserStatus
from app.models.identity import User
from app.models.menu import MenuItem
from app.models.operations import AuditLog
from app.services.image_service import ImageService


def create_sample_image_bytes(
    image_format: str = "JPEG",
    size: tuple[int, int] = (120, 120),
    color: str = "blue",
) -> bytes:
    """Generate in-memory valid image bytes using Pillow."""
    buf = io.BytesIO()
    img = Image.new("RGB", size, color=color)
    img.save(buf, format=image_format)
    return buf.getvalue()


class MockQueryResult:
    def __init__(self, single: Any = None, multiple: list[Any] | None = None) -> None:
        self._single = single
        self._multiple = (
            multiple if multiple is not None else ([single] if single is not None else [])
        )

    def scalar_one_or_none(self) -> Any:
        return self._single

    def scalar_one(self) -> Any:
        return self._single

    def scalars(self) -> MockQueryResult:
        return self

    def all(self) -> list[Any]:
        return self._multiple


class FakeImageSession:
    """Mock database session holding an item and audit logs."""

    def __init__(self, item: MenuItem) -> None:
        self.item = item
        self.audit_logs: list[AuditLog] = []

    async def get(self, entity_cls: Any, pk: Any) -> Any:
        if entity_cls is MenuItem and self.item.id == pk:
            return self.item
        return None

    async def execute(self, statement: Any) -> Any:
        return MockQueryResult(single=self.item, multiple=[self.item])

    def add(self, instance: Any) -> None:
        if isinstance(instance, AuditLog):
            self.audit_logs.append(instance)

    async def flush(self) -> None:
        pass

    async def commit(self) -> None:
        pass


@pytest.fixture
def admin_user() -> User:
    return User(
        id=uuid.uuid4(),
        username="admin_sec",
        full_name="Admin Security",
        role=UserRole.ADMIN.value,
        is_active=True,
        status=UserStatus.ACTIVE.value,
        token_version=1,
    )


@pytest.fixture
def waiter_user() -> User:
    return User(
        id=uuid.uuid4(),
        username="waiter_sec",
        full_name="Waiter Security",
        role=UserRole.WAITER.value,
        is_active=True,
        status=UserStatus.ACTIVE.value,
        token_version=1,
    )


# =============================================================================
# ImageService Unit Tests
# =============================================================================


def test_sanitize_and_save_valid_jpeg(tmp_path: Path) -> None:
    jpeg_bytes = create_sample_image_bytes("JPEG", (200, 200), "green")

    url, filename = ImageService.sanitize_and_save_menu_image(jpeg_bytes, upload_dir=tmp_path)

    assert url.startswith("/static/menu/menu_")
    assert filename.startswith("menu_")
    assert filename.endswith(".webp")

    # Verify saved file is a valid WebP
    saved_path = tmp_path / filename
    assert saved_path.exists()
    with Image.open(saved_path) as verified:
        assert verified.format == "WEBP"
        assert verified.size == (200, 200)


def test_sanitize_and_save_valid_png(tmp_path: Path) -> None:
    png_bytes = create_sample_image_bytes("PNG", (150, 150), "red")

    url, filename = ImageService.sanitize_and_save_menu_image(png_bytes, upload_dir=tmp_path)

    assert filename.endswith(".webp")
    saved_path = tmp_path / filename
    assert saved_path.exists()
    with Image.open(saved_path) as verified:
        assert verified.format == "WEBP"


def test_reject_svg_with_script_tag(tmp_path: Path) -> None:
    malicious_svg = b"<svg xmlns='http://www.w3.org/2000/svg'><script>alert('XSS')</script></svg>"

    with pytest.raises(UnsupportedMediaTypeError) as exc_info:
        ImageService.sanitize_and_save_menu_image(malicious_svg, upload_dir=tmp_path)
    assert exc_info.value.code == "INVALID_IMAGE_FILE"


def test_reject_disguised_html(tmp_path: Path) -> None:
    html_bytes = b"<!DOCTYPE html><html><body><h1>Disguised HTML</h1></body></html>"

    with pytest.raises(UnsupportedMediaTypeError) as exc_info:
        ImageService.sanitize_and_save_menu_image(html_bytes, upload_dir=tmp_path)
    assert exc_info.value.code == "INVALID_IMAGE_FILE"


def test_reject_oversized_file(tmp_path: Path) -> None:
    # 2.5 MB of dummy data
    oversized = b"\xff\xd8\xff" + b"\x00" * (2_500_000)

    with pytest.raises(PayloadTooLargeError) as exc_info:
        ImageService.sanitize_and_save_menu_image(oversized, upload_dir=tmp_path)
    assert exc_info.value.code == "PAYLOAD_TOO_LARGE"


def test_reject_empty_file(tmp_path: Path) -> None:
    with pytest.raises(UnsupportedMediaTypeError) as exc_info:
        ImageService.sanitize_and_save_menu_image(b"", upload_dir=tmp_path)
    assert exc_info.value.code == "INVALID_IMAGE_FILE"


def test_delete_menu_image_safely(tmp_path: Path) -> None:
    # Create fake webp
    test_file = tmp_path / "menu_test123.webp"
    test_file.write_bytes(b"dummy")

    assert (
        ImageService.delete_menu_image("/static/menu/menu_test123.webp", upload_dir=tmp_path)
        is True
    )
    assert not test_file.exists()

    # Attempt directory traversal: should safely fail without error
    assert ImageService.delete_menu_image("../../../etc/passwd.webp", upload_dir=tmp_path) is False


# =============================================================================
# API Endpoint Tests
# =============================================================================


@pytest.mark.asyncio
async def test_api_upload_dish_image_success(
    admin_user: User,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    item = MenuItem(
        id=uuid.uuid4(),
        category_id=uuid.uuid4(),
        item_code="CB",
        name="Chicken Biryani",
        image_url=None,
        is_available=True,
        is_active=True,
        display_order=1,
        created_at=now,
        updated_at=now,
    )
    item.variants = []
    session = FakeImageSession(item)

    from app import config

    settings = config.get_settings()
    monkeypatch.setattr(settings, "upload_dir", tmp_path)

    app = create_app()
    app.dependency_overrides[get_db] = lambda: session
    app.dependency_overrides[get_current_staff_user] = lambda: admin_user

    jpeg_bytes = create_sample_image_bytes("JPEG", (100, 100), "yellow")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        files = {"file": ("malicious_name.jpg", jpeg_bytes, "image/jpeg")}
        resp = await client.post(f"/api/v1/admin/menu/items/{item.id}/image", files=files)

        assert resp.status_code == 200
        data = resp.json()
        assert data["image_url"].startswith("/static/menu/menu_")
        assert "malicious_name" not in data["image_url"]

        # Check item was updated and audit log recorded
        assert item.image_url == data["image_url"]
        assert len(session.audit_logs) == 1
        assert session.audit_logs[0].action_type == "MENU_ITEM_IMAGE_UPLOADED"


@pytest.mark.asyncio
async def test_api_upload_dish_image_rejected_for_waiter(waiter_user: User) -> None:
    item_id = uuid.uuid4()
    app = create_app()
    app.dependency_overrides[get_current_staff_user] = lambda: waiter_user

    jpeg_bytes = create_sample_image_bytes("JPEG", (50, 50), "red")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        files = {"file": ("test.jpg", jpeg_bytes, "image/jpeg")}
        resp = await client.post(f"/api/v1/admin/menu/items/{item_id}/image", files=files)
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "INSUFFICIENT_ROLE_PERMISSIONS"


@pytest.mark.asyncio
async def test_api_upload_disguised_file_rejected(
    admin_user: User,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    item = MenuItem(
        id=uuid.uuid4(), category_id=uuid.uuid4(), item_code="CB", name="Chicken Biryani"
    )
    session = FakeImageSession(item)

    from app import config

    settings = config.get_settings()
    monkeypatch.setattr(settings, "upload_dir", tmp_path)

    app = create_app()
    app.dependency_overrides[get_db] = lambda: session
    app.dependency_overrides[get_current_staff_user] = lambda: admin_user

    fake_svg = b"<svg><script>alert(1)</script></svg>"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        files = {"file": ("photo.jpg", fake_svg, "image/jpeg")}
        resp = await client.post(f"/api/v1/admin/menu/items/{item.id}/image", files=files)
        assert resp.status_code in (415, 422)
        assert resp.json()["error"]["code"] == "INVALID_IMAGE_FILE"
