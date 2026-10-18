"""Secure image processing and upload service for menu dish photos.

Supports two storage backends selected via settings:
1. **ImageKit** (preferred in production): Uploads processed WebP to ImageKit CDN.
   Requires IMAGEKIT_PUBLIC_KEY, IMAGEKIT_PRIVATE_KEY and IMAGEKIT_URL_ENDPOINT.
2. **Local filesystem** (development / fallback): Saves to ``settings.upload_dir``.
   Images are served via the ``/media/`` Caddy route or ``/static/menu/`` in dev.

Follows `docs/06-security-specification.md` (Section 26),
`docs/10-deployment-and-devops-specification.md`, and
`docs/13-final-implementation-blueprint.md`.

Enforces (both backends):
1. Max 2 MB raw size check.
2. Pillow magic-byte inspection and verification (rejecting SVG, HTML, disguised executables).
3. Whitelisted image formats: JPEG, PNG, WEBP only.
4. Complete discarding of user-supplied filenames.
5. Re-encoding to clean WebP, stripping all EXIF metadata.
6. For local: safe UUID filename in isolated non-executable upload directory.
7. For ImageKit: private key is never logged or returned to the client.
"""

from __future__ import annotations

import io
import uuid
from pathlib import Path
from typing import NamedTuple

from PIL import Image, UnidentifiedImageError

from app.config import get_settings
from app.core.exceptions import PayloadTooLargeError, UnsupportedMediaTypeError
from app.core.logging import get_logger

logger = get_logger(__name__)

ALLOWED_IMAGE_FORMATS: frozenset[str] = frozenset({"JPEG", "PNG", "WEBP"})
MAX_IMAGE_DIMENSION: int = 1200


class ImageUploadResult(NamedTuple):
    """Result of a successful image upload."""

    image_url: str
    """Publicly accessible URL — stored in ``menu_items.image_url``."""
    imagekit_file_id: str | None
    """ImageKit file ID for deletion; None when using local storage."""
    filename: str
    """Stored filename (local) or ImageKit file name."""


class ImageService:
    """Secure image upload and sanitization service with ImageKit / local fallback."""

    # ─── Public API ──────────────────────────────────────────────────────────

    @classmethod
    def sanitize_and_save_menu_image(
        cls,
        file_bytes: bytes,
        *,
        upload_dir: Path | None = None,
    ) -> tuple[str, str]:
        """Validate, sanitize, re-encode to WebP, and store a menu dish image.

        Returns:
            ``(image_url, filename)`` — the URL written to the DB and the storage filename.

        Raises:
            PayloadTooLargeError: File exceeds maximum allowed bytes (2 MB).
            UnsupportedMediaTypeError: Format is invalid, malicious, or not JPEG/PNG/WebP.

        .. deprecated::
            Prefer :meth:`upload_menu_image` which returns :class:`ImageUploadResult`
            including the ImageKit file ID needed for safe remote deletion.
        """
        result = cls.upload_menu_image(file_bytes, upload_dir=upload_dir)
        return result.image_url, result.filename

    @classmethod
    def upload_menu_image(
        cls,
        file_bytes: bytes,
        *,
        upload_dir: Path | None = None,
    ) -> ImageUploadResult:
        """Validate, sanitize, and upload a menu image to ImageKit or local storage.

        Args:
            file_bytes: Raw binary content of the uploaded file.
            upload_dir: Override for local storage directory (testing / dev).

        Returns:
            :class:`ImageUploadResult` with URL, optional ImageKit file ID, and filename.
        """
        settings = get_settings()

        # 1. Enforce strict file size limit (before Pillow decoding)
        if len(file_bytes) > settings.max_upload_size_bytes:
            raise PayloadTooLargeError(
                code="PAYLOAD_TOO_LARGE",
                message=f"Uploaded file size ({len(file_bytes)} bytes) exceeds the 2 MB limit.",
                details={
                    "max_bytes": settings.max_upload_size_bytes,
                    "actual_bytes": len(file_bytes),
                },
            )

        if len(file_bytes) == 0:
            raise UnsupportedMediaTypeError(
                code="INVALID_IMAGE_FILE",
                message="Uploaded file is empty.",
            )

        # 2. Magic-byte inspection & Pillow verification
        try:
            with Image.open(io.BytesIO(file_bytes)) as test_img:
                img_format = (test_img.format or "").upper()
                if img_format not in ALLOWED_IMAGE_FORMATS:
                    raise UnsupportedMediaTypeError(
                        code="UNSUPPORTED_MEDIA_TYPE",
                        message=(
                            f"Image format '{img_format}' is not supported. "
                            "Allowed formats are JPEG, PNG, and WebP."
                        ),
                        details={"detected_format": img_format},
                    )
                test_img.verify()
        except (UnidentifiedImageError, OSError, SyntaxError) as exc:
            logger.warning("Rejected invalid or malicious image upload: %s", exc)
            raise UnsupportedMediaTypeError(
                code="INVALID_IMAGE_FILE",
                message="File is not a valid or recognizable image (JPEG, PNG, or WebP).",
            ) from exc

        # 3. Second pass: decode, resize, strip EXIF, re-encode to WebP
        webp_bytes = cls._reencode_to_webp(file_bytes)

        # 4. Generate random UUID filename (completely discard user filename)
        filename = f"menu_{uuid.uuid4().hex}.webp"

        # 5. Route to ImageKit or local storage
        if settings.imagekit_enabled:
            return cls._upload_to_imagekit(webp_bytes, filename, settings)
        else:
            return cls._save_locally(webp_bytes, filename, settings, upload_dir)

    @classmethod
    def delete_menu_image(
        cls,
        image_url: str | None,
        *,
        imagekit_file_id: str | None = None,
        upload_dir: Path | None = None,
    ) -> bool:
        """Safely delete an existing image from ImageKit or local storage.

        When ``imagekit_file_id`` is provided the file is deleted from ImageKit;
        otherwise falls back to deleting the local file matching ``image_url``.
        Returns True on success, False if nothing was deleted.
        """
        if not image_url and not imagekit_file_id:
            return False

        settings = get_settings()

        if imagekit_file_id and settings.imagekit_enabled:
            return cls._delete_from_imagekit(imagekit_file_id, settings)

        # Local deletion (pattern-guarded to prevent directory traversal)
        return cls._delete_locally(image_url, settings, upload_dir)

    # ─── Internal helpers ─────────────────────────────────────────────────────

    @classmethod
    def _reencode_to_webp(cls, file_bytes: bytes) -> bytes:
        """Decode raster, resize if needed, strip EXIF, return WebP bytes."""
        try:
            with Image.open(io.BytesIO(file_bytes)) as img:
                if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
                    clean_img = img.convert("RGBA")
                else:
                    clean_img = img.convert("RGB")

                if clean_img.width > MAX_IMAGE_DIMENSION or clean_img.height > MAX_IMAGE_DIMENSION:
                    clean_img.thumbnail(
                        (MAX_IMAGE_DIMENSION, MAX_IMAGE_DIMENSION),
                        Image.Resampling.LANCZOS,
                    )

                buf = io.BytesIO()
                clean_img.save(buf, format="WEBP", quality=85, method=6)
                return buf.getvalue()
        except Exception as exc:
            logger.error("Failed to re-encode image to WebP: %s", exc)
            raise UnsupportedMediaTypeError(
                code="IMAGE_PROCESSING_FAILED",
                message="Failed to process and re-encode image.",
            ) from exc

    @classmethod
    def _upload_to_imagekit(
        cls,
        webp_bytes: bytes,
        filename: str,
        settings: object,  # Settings
    ) -> ImageUploadResult:
        """Upload WebP bytes to ImageKit using the v5 SDK and return CDN URL + file ID.

        imagekitio v5 API:
        - ImageKit(private_key=...) — no public_key or url_endpoint in constructor.
        - ik.files.upload(file=bytes, file_name=str, folder=str, ...) — keyword-only.
        - Response: FileUploadResponse with .file_id and .url attributes.
        - Delete: ik.files.delete(file_id=str) — returns None.
        """
        try:
            from imagekitio import ImageKit  # noqa: PLC0415
        except ImportError as exc:
            raise RuntimeError(
                "imagekitio package is not installed. "
                "Add 'imagekitio>=5.10.0' to backend/requirements.txt and reinstall."
            ) from exc

        ik = ImageKit(private_key=settings.imagekit_private_key)  # never logged

        try:
            result = ik.files.upload(
                file=webp_bytes,
                file_name=filename,
                folder=settings.imagekit_upload_folder,
                use_unique_file_name=False,  # we already generated a UUID name
                tags=["menu", "food"],
            )
        except Exception as exc:
            logger.error(
                "ImageKit upload failed for %s: %s",
                filename,
                type(exc).__name__,
            )
            raise UnsupportedMediaTypeError(
                code="IMAGE_UPLOAD_FAILED",
                message="Failed to upload image to CDN. Please try again.",
            ) from exc

        image_url: str = result.url
        file_id: str = result.file_id
        logger.info("ImageKit upload successful: file_id=%s url=%s", file_id, image_url)
        return ImageUploadResult(
            image_url=image_url,
            imagekit_file_id=file_id,
            filename=filename,
        )

    @classmethod
    def _save_locally(
        cls,
        webp_bytes: bytes,
        filename: str,
        settings: object,  # Settings
        upload_dir: Path | None,
    ) -> ImageUploadResult:
        """Save WebP bytes to the local upload directory and return a /media/ URL."""
        target_dir: Path = upload_dir or settings.upload_dir
        target_dir.mkdir(parents=True, exist_ok=True)
        dest_path = target_dir / filename

        try:
            dest_path.write_bytes(webp_bytes)
        except OSError as exc:
            logger.error("Failed to write image to disk: %s", exc)
            raise UnsupportedMediaTypeError(
                code="IMAGE_PROCESSING_FAILED",
                message="Failed to save image to local storage.",
            ) from exc

        logger.info(
            "Local image saved: %s (%d bytes)",
            filename,
            len(webp_bytes),
        )
        # URL path must match the Caddy /media/* route (not /static/menu/).
        return ImageUploadResult(
            image_url=f"/media/{filename}",
            imagekit_file_id=None,
            filename=filename,
        )

    @classmethod
    def _delete_from_imagekit(cls, file_id: str, settings: object) -> bool:
        """Delete a file from ImageKit by its file ID using the v5 SDK."""
        try:
            from imagekitio import ImageKit  # noqa: PLC0415
        except ImportError:
            logger.warning("imagekitio not installed; cannot delete file_id=%s", file_id)
            return False

        ik = ImageKit(private_key=settings.imagekit_private_key)
        try:
            ik.files.delete(file_id)
            logger.info("Deleted ImageKit file: file_id=%s", file_id)
            return True
        except Exception as exc:
            logger.warning(
                "Could not delete ImageKit file file_id=%s: %s",
                file_id,
                type(exc).__name__,
            )
            return False

    @classmethod
    def _delete_locally(
        cls,
        image_url: str | None,
        settings: object,
        upload_dir: Path | None,
    ) -> bool:
        """Safely delete a local file matching the image_url pattern."""
        if not image_url:
            return False

        filename = Path(image_url).name
        # Accept both /media/ and /static/menu/ prefixed URLs for backwards compatibility.
        if not filename.startswith("menu_") or not filename.endswith(".webp"):
            return False

        target_dir: Path = upload_dir or settings.upload_dir
        dest_path = (target_dir / filename).resolve()

        # Prevent directory traversal
        try:
            if not dest_path.is_relative_to(target_dir.resolve()):
                return False
        except AttributeError:
            # Python 3.8 fallback
            if not str(dest_path).startswith(str(target_dir.resolve())):
                return False

        if dest_path.is_file():
            try:
                dest_path.unlink()
                logger.info("Deleted local menu image: %s", filename)
                return True
            except OSError as exc:
                logger.warning("Could not delete local image %s: %s", filename, exc)
                return False
        return False
