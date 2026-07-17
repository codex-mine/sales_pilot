"""
Local-disk file storage for the Organization module's logo upload and the
Lead Management module's attachments.

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

# Lead attachments accept a broader set of everyday business-document types.
# Unlike the logo path, these aren't necessarily images, so there's no
# decode-and-verify step — validation is by declared content-type/extension.
_ATTACHMENT_EXTENSIONS_BY_CONTENT_TYPE = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/msword": "doc",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
    "application/vnd.ms-excel": "xls",
    "text/csv": "csv",
    "application/zip": "zip",
    "application/x-zip-compressed": "zip",
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/webp": "webp",
    "image/gif": "gif",
}


class StorageService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def _org_dir(self, organization_id: uuid.UUID) -> Path:
        return Path(self.settings.upload_dir) / "organizations" / str(organization_id)

    def _attachments_dir(self, organization_id: uuid.UUID, lead_id: uuid.UUID) -> Path:
        return Path(self.settings.upload_dir) / "organizations" / str(organization_id) / "leads" / str(lead_id)

    def _company_dir(self, organization_id: uuid.UUID, company_id: uuid.UUID) -> Path:
        return Path(self.settings.upload_dir) / "organizations" / str(organization_id) / "companies" / str(company_id)

    def _company_attachments_dir(self, organization_id: uuid.UUID, company_id: uuid.UUID) -> Path:
        return self._company_dir(organization_id, company_id) / "attachments"

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

    async def save_lead_attachment(
        self, organization_id: uuid.UUID, lead_id: uuid.UUID, file: UploadFile
    ) -> tuple[str, str, int]:
        """Validates and persists a lead attachment. Returns
        (file_key, public_url, file_size) — `file_key` is what's stored on
        `Attachment.file_key`; multiple attachments per lead coexist (unlike
        the single-slot logo), each under its own generated filename so
        same-named uploads never collide."""
        extension = _ATTACHMENT_EXTENSIONS_BY_CONTENT_TYPE.get(file.content_type or "")
        if extension is None:
            raise ValidationError(
                "Unsupported file type. Allowed: PDF, DOCX, XLSX, CSV, images, ZIP.",
                errors={"file": ["Unsupported file type."]},
            )

        content = await file.read()
        max_bytes = self.settings.max_attachment_size_mb * 1024 * 1024
        if len(content) > max_bytes:
            raise ValidationError(
                f"File too large. Maximum size is {self.settings.max_attachment_size_mb}MB.",
                errors={"file": ["File too large."]},
            )

        lead_dir = self._attachments_dir(organization_id, lead_id)
        lead_dir.mkdir(parents=True, exist_ok=True)

        stored_name = f"{uuid.uuid4().hex}.{extension}"
        (lead_dir / stored_name).write_bytes(content)

        file_key = f"organizations/{organization_id}/leads/{lead_id}/{stored_name}"
        public_url = f"/media/organizations/{organization_id}/leads/{lead_id}/{stored_name}"
        return file_key, public_url, len(content)

    def delete_lead_attachment(self, organization_id: uuid.UUID, lead_id: uuid.UUID, file_key: str) -> None:
        stored_name = file_key.rsplit("/", 1)[-1]
        path = self._attachments_dir(organization_id, lead_id) / stored_name
        path.unlink(missing_ok=True)

    async def save_company_logo(self, organization_id: uuid.UUID, company_id: uuid.UUID, file: UploadFile) -> str:
        """Validates and persists a company logo, replacing any existing one.
        Mirrors `save_logo` (organization logos) — same validation, same
        single-slot-per-entity replace semantics, different directory."""
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

        company_dir = self._company_dir(organization_id, company_id)
        company_dir.mkdir(parents=True, exist_ok=True)
        self._delete_existing_logo_files(company_dir)

        destination = company_dir / f"logo.{extension}"
        destination.write_bytes(content)

        version = int(time.time())
        return f"/media/organizations/{organization_id}/companies/{company_id}/logo.{extension}?v={version}"

    def delete_company_logo(self, organization_id: uuid.UUID, company_id: uuid.UUID) -> None:
        self._delete_existing_logo_files(self._company_dir(organization_id, company_id))

    async def save_company_attachment(
        self, organization_id: uuid.UUID, company_id: uuid.UUID, file: UploadFile
    ) -> tuple[str, str, int]:
        """Validates and persists a company attachment. Mirrors `save_lead_attachment`."""
        extension = _ATTACHMENT_EXTENSIONS_BY_CONTENT_TYPE.get(file.content_type or "")
        if extension is None:
            raise ValidationError(
                "Unsupported file type. Allowed: PDF, DOCX, XLSX, CSV, images, ZIP.",
                errors={"file": ["Unsupported file type."]},
            )

        content = await file.read()
        max_bytes = self.settings.max_attachment_size_mb * 1024 * 1024
        if len(content) > max_bytes:
            raise ValidationError(
                f"File too large. Maximum size is {self.settings.max_attachment_size_mb}MB.",
                errors={"file": ["File too large."]},
            )

        company_dir = self._company_attachments_dir(organization_id, company_id)
        company_dir.mkdir(parents=True, exist_ok=True)

        stored_name = f"{uuid.uuid4().hex}.{extension}"
        (company_dir / stored_name).write_bytes(content)

        file_key = f"organizations/{organization_id}/companies/{company_id}/attachments/{stored_name}"
        public_url = f"/media/{file_key}"
        return file_key, public_url, len(content)

    def delete_company_attachment(self, organization_id: uuid.UUID, company_id: uuid.UUID, file_key: str) -> None:
        stored_name = file_key.rsplit("/", 1)[-1]
        path = self._company_attachments_dir(organization_id, company_id) / stored_name
        path.unlink(missing_ok=True)
