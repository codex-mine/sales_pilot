"""
Local-disk file storage for the Organization module's logo upload.

No cloud storage (S3/GCS) credentials exist anywhere in this project yet, so
this stores files on a Docker-volume-backed local path and serves them via a
StaticFiles mount (see app/main.py). The interface is narrow and swappable —
if cloud storage is introduced later, only this file needs to change.
"""

import io
import time
import uuid
from pathlib import Path

from fastapi import UploadFile
from PIL import Image, UnidentifiedImageError

from app.core.config import Settings, get_settings
from app.exceptions.errors import ValidationError

_ALLOWED_FORMATS = {"PNG": "png", "JPEG": "jpg", "WEBP": "webp"}
_ALLOWED_CONTENT_TYPES = {"image/png", "image/jpeg", "image/webp"}


class StorageService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def _org_dir(self, organization_id: uuid.UUID) -> Path:
        return Path(self.settings.upload_dir) / "organizations" / str(organization_id)

    async def save_logo(self, organization_id: uuid.UUID, file: UploadFile) -> str:
        """Validates and persists an organization logo, replacing any existing
        one (including a stale file left over from a different extension).
        Returns the URL to store on `Organization.logo_url`."""
        if file.content_type not in _ALLOWED_CONTENT_TYPES:
            raise ValidationError(
                "Unsupported file type. Upload a PNG, JPEG, or WEBP image.",
                errors={"file": ["Unsupported file type."]},
            )

        content = await file.read()
        max_bytes = self.settings.max_logo_size_mb * 1024 * 1024
        if len(content) > max_bytes:
            raise ValidationError(
                f"File too large. Maximum size is {self.settings.max_logo_size_mb}MB.",
                errors={"file": ["File too large."]},
            )

        try:
            image = Image.open(io.BytesIO(content))
            image.verify()
            # `verify()` leaves the Image unusable for further reads — reopen
            # to actually inspect the format now that we know it's decodable.
            image = Image.open(io.BytesIO(content))
            image_format = image.format
        except (UnidentifiedImageError, OSError) as exc:
            raise ValidationError(
                "The uploaded file is not a valid image.",
                errors={"file": ["Not a valid image."]},
            ) from exc

        extension = _ALLOWED_FORMATS.get(image_format or "")
        if extension is None:
            raise ValidationError(
                "Unsupported image format. Upload a PNG, JPEG, or WEBP image.",
                errors={"file": ["Unsupported image format."]},
            )

        org_dir = self._org_dir(organization_id)
        org_dir.mkdir(parents=True, exist_ok=True)
        self._delete_existing_logo_files(org_dir)

        destination = org_dir / f"logo.{extension}"
        destination.write_bytes(content)

        # Cache-bust: a "replace" that keeps the same extension would
        # otherwise produce an identical URL, and browsers/CDNs would keep
        # showing the old cached image.
        version = int(time.time())
        return f"/media/organizations/{organization_id}/logo.{extension}?v={version}"

    def delete_logo(self, organization_id: uuid.UUID) -> None:
        self._delete_existing_logo_files(self._org_dir(organization_id))

    def _delete_existing_logo_files(self, org_dir: Path) -> None:
        if not org_dir.exists():
            return
        for existing in org_dir.glob("logo.*"):
            existing.unlink(missing_ok=True)
