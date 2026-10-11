"""Secure image processing and upload service for menu dish photos.

Follows `docs/06-security-specification.md` (Section 26),
`docs/10-deployment-and-devops-specification.md`, and
`docs/13-final-implementation-blueprint.md`.
Enforces:
1. Max 2 MB raw size check.
2. Pillow magic-byte inspection and verification (rejecting SVG, HTML, and disguised executables).
3. Whitelisted image formats: JPEG, PNG, WEBP only.
4. Complete discarding of user-supplied filenames.
5. Re-encoding to clean WebP, stripping all EXIF metadata.
6. Safe UUID filename storage in isolated non-executable upload directory.
"""

from __future__ import annotations

import io
import uuid
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from app.config import get_settings
from app.core.exceptions import PayloadTooLargeError, UnsupportedMediaTypeError
from app.core.logging import get_logger

logger = get_logger(__name__)

ALLOWED_IMAGE_FORMATS: frozenset[str] = frozenset({"JPEG", "PNG", "WEBP"})
MAX_IMAGE_DIMENSION: int = 1200


class ImageService:
    """Zero-cost, secure image upload and sanitization service."""

    @classmethod
    def sanitize_and_save_menu_image(
        cls,
        file_bytes: bytes,
        *,
        upload_dir: Path | None = None,
    ) -> tuple[str, str]:
        """Validate, sanitize, re-encode to WebP, and save a menu dish image.

        Args:
            file_bytes: Raw binary content of the uploaded file.
            upload_dir: Directory where the image should be saved.

        Returns:
            Tuple of (relative_url, saved_filename)
            e.g., ("/static/menu/menu_123e4567.webp", "menu_123e4567.webp")

        Raises:
            PayloadTooLargeError: If file exceeds maximum allowed bytes (2 MB).
            UnsupportedMediaTypeError: If format is invalid, malicious, or not JPEG/PNG/WebP.
        """
        settings = get_settings()
        target_dir = upload_dir or settings.upload_dir

        # 1. Enforce strict file size limit
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
            # First pass: verify integrity and format
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
                # verify() checks stream integrity without decoding full raster
                test_img.verify()
        except (UnidentifiedImageError, OSError, SyntaxError) as exc:
            logger.warning("Rejected invalid or malicious image upload: %s", exc)
            raise UnsupportedMediaTypeError(
                code="INVALID_IMAGE_FILE",
                message="File is not a valid or recognizable image (JPEG, PNG, or WebP).",
            ) from exc

        # 3. Second pass: decode raster, resize if oversized, strip EXIF metadata
        try:
            with Image.open(io.BytesIO(file_bytes)) as img:
                # Discard all EXIF / ICC / metadata by copying raw pixel buffer
                if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
                    clean_img = img.convert("RGBA")
                else:
                    clean_img = img.convert("RGB")

                # Downscale if dimensions exceed reasonable maximum (1200px)
                if clean_img.width > MAX_IMAGE_DIMENSION or clean_img.height > MAX_IMAGE_DIMENSION:
                    clean_img.thumbnail(
                        (MAX_IMAGE_DIMENSION, MAX_IMAGE_DIMENSION),
                        Image.Resampling.LANCZOS,
                    )

                # 4. Generate random UUID filename (completely discard user filename)
                target_dir.mkdir(parents=True, exist_ok=True)
                filename = f"menu_{uuid.uuid4().hex}.webp"
                dest_path = target_dir / filename

                # 5. Save as clean WebP (strips EXIF metadata automatically)
                clean_img.save(
                    dest_path,
                    format="WEBP",
                    quality=85,
                    method=6,
                )

                logger.info(
                    "Sanitized menu image saved: %s (%dx%d, %d bytes)",
                    filename,
                    clean_img.width,
                    clean_img.height,
                    dest_path.stat().st_size,
                )
                return f"/static/menu/{filename}", filename
        except Exception as exc:
            logger.error("Failed to re-encode and save image: %s", exc)
            raise UnsupportedMediaTypeError(
                code="IMAGE_PROCESSING_FAILED",
                message="Failed to process and re-encode image.",
            ) from exc

    @classmethod
    def delete_menu_image(cls, image_url: str | None, *, upload_dir: Path | None = None) -> bool:
        """Safely delete an existing image file from the uploads directory.

        Only deletes files matching the pattern 'menu_*.webp' within the target directory
        to prevent directory traversal attacks.
        """
        if not image_url:
            return False

        filename = Path(image_url).name
        if not filename.startswith("menu_") or not filename.endswith(".webp"):
            return False

        settings = get_settings()
        target_dir = upload_dir or settings.upload_dir
        dest_path = (target_dir / filename).resolve()

        # Prevent directory traversal
        try:
            if not dest_path.is_relative_to(target_dir.resolve()):
                return False
        except AttributeError:
            # Python 3.8 fallback
            if str(dest_path).find(str(target_dir.resolve())) != 0:
                return False

        if dest_path.is_file():
            try:
                dest_path.unlink()
                logger.info("Deleted menu image: %s", filename)
                return True
            except OSError as exc:
                logger.warning("Could not delete menu image %s: %s", filename, exc)
                return False
        return False
