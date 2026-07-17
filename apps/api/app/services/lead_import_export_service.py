"""
CSV import (preview -> commit, stateless across the two requests) and export
for the Lead Management module.

Import is a two-call flow, deliberately stateless server-side:
1. `preview()` — parse the uploaded file, auto-detect column -> field
   mapping, return headers/sample rows/suggestions. Nothing is persisted.
2. `commit()` — the frontend re-submits the *same file* plus the
   user-confirmed mapping (auto-detected or hand-edited); this parses again
   and actually creates leads. No server-side wizard session/state to manage,
   at the cost of re-uploading the file once — an acceptable tradeoff for a
   CSV that's realistically at most a few MB.
"""

import csv
import io
import uuid
from datetime import datetime, timezone

from fastapi import UploadFile
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions.errors import ValidationError
from app.models.crm.models import Activity, Lead
from app.models.enums import ActivityTypeEnum, AuditActionEnum, LeadStatusEnum
from app.models.identity.models import User
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.lead_repository import LeadRepository
from app.repositories.tag_repository import TagRepository
from app.schemas.leads import (
    ImportFailedRow,
    ImportPreviewResponse,
    ImportResultResponse,
    LeadCreateRequest,
)

# Canonical import target fields, with auto-detect synonyms. "full_name" is a
# virtual target — matched rows get split into first_name/last_name at
# import time (see _split_full_name) rather than stored directly.
IMPORTABLE_FIELDS = [
    "full_name", "first_name", "last_name", "email", "phone", "job_title",
    "company_name", "website", "industry", "source", "status", "priority",
    "country", "state", "city", "linkedin_url", "twitter_url",
    "company_size", "revenue", "employee_count", "description", "tags",
    "lead_score",
]

_SYNONYMS: dict[str, str] = {
    "name": "full_name", "fullname": "full_name", "full name": "full_name",
    "first": "first_name", "firstname": "first_name", "first name": "first_name",
    "last": "last_name", "lastname": "last_name", "last name": "last_name",
    "e-mail": "email", "email address": "email",
    "mobile": "phone", "phone number": "phone", "telephone": "phone",
    "title": "job_title", "job title": "job_title", "position": "job_title",
    "company": "company_name", "organization": "company_name", "org": "company_name",
    "url": "website", "web": "website", "domain": "website",
    "linkedin": "linkedin_url", "linked in": "linkedin_url",
    "twitter": "twitter_url", "x": "twitter_url",
    "size": "company_size", "employees": "employee_count", "headcount": "employee_count",
    "annual revenue": "revenue", "score": "lead_score",
}


def _normalize_header(header: str) -> str:
    return header.strip().lower().replace("_", " ").replace("-", " ")


def _auto_detect_mapping(headers: list[str]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    canonical_by_normalized = {_normalize_header(f): f for f in IMPORTABLE_FIELDS}
    for header in headers:
        normalized = _normalize_header(header)
        if normalized in canonical_by_normalized:
            mapping[header] = canonical_by_normalized[normalized]
        elif normalized in _SYNONYMS:
            mapping[header] = _SYNONYMS[normalized]
    return mapping


def _split_full_name(value: str) -> tuple[str | None, str | None]:
    parts = value.strip().split(maxsplit=1)
    if not parts:
        return None, None
    if len(parts) == 1:
        return parts[0], None
    return parts[0], parts[1]


def _read_rows(raw: bytes) -> tuple[list[str], list[dict[str, str]]]:
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValidationError(
            "The file isn't valid UTF-8 text. Export it as UTF-8 CSV and try again.",
            errors={"file": ["Invalid encoding."]},
        ) from exc
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        raise ValidationError("The CSV file has no header row.", errors={"file": ["Empty file."]})
    rows = list(reader)
    return list(reader.fieldnames), rows


class LeadImportExportService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.leads = LeadRepository(db)
        self.tags = TagRepository(db)
        self.audit_log = AuditLogRepository(db)

    async def preview(self, file: UploadFile) -> ImportPreviewResponse:
        raw = await file.read()
        headers, rows = _read_rows(raw)
        return ImportPreviewResponse(
            headers=headers,
            sample_rows=[{h: (row.get(h) or "") for h in headers} for row in rows[:5]],
            suggested_mapping=_auto_detect_mapping(headers),
            total_rows=len(rows),
            available_fields=IMPORTABLE_FIELDS,
        )

    async def commit(
        self, *, organization_id: uuid.UUID, file: UploadFile, mapping: dict[str, str], actor: User
    ) -> ImportResultResponse:
        raw = await file.read()
        _headers, rows = _read_rows(raw)

        if not any(field in mapping.values() for field in ("email", "company_name", "full_name", "first_name")):
            raise ValidationError(
                "Map at least one identifying column (name, email, or company).",
                errors={"mapping": ["No identifying field mapped."]},
            )

        seen_emails: set[str] = set()
        failed_rows: list[ImportFailedRow] = []
        duplicate_count = 0
        to_create: list[dict] = []
        tag_assignments: list[list[str]] = []

        for index, row in enumerate(rows, start=2):  # header is row 1
            try:
                fields = self._row_to_fields(row, mapping)
            except ValidationError as exc:
                failed_rows.append(ImportFailedRow(row_number=index, errors=exc.errors.get("row", [exc.message]) if exc.errors else [exc.message], data=row))
                continue

            email = fields.get("email")
            if email:
                email_lower = email.lower()
                if email_lower in seen_emails or await self.leads.get_by_email(organization_id, email_lower):
                    duplicate_count += 1
                    continue
                seen_emails.add(email_lower)

            if not any([fields.get("first_name"), fields.get("last_name"), fields.get("email"), fields.get("company_name")]):
                failed_rows.append(
                    ImportFailedRow(row_number=index, errors=["Row has no name, email, or company."], data=row)
                )
                continue

            tags = fields.pop("tags", [])
            fields.setdefault("source", "csv_import")
            fields.setdefault("status", LeadStatusEnum.NEW.value)
            to_create.append(fields)
            tag_assignments.append(tags)

        created_ids: list[uuid.UUID] = []
        for fields, tags in zip(to_create, tag_assignments):
            lead = await self.leads.create(organization_id=organization_id, created_by=actor.id, **fields)
            if tags:
                tag_rows = await self.tags.get_or_create_many(organization_id, tags)
                await self.tags.set_tags_for_lead(lead, tag_rows)
            created_ids.append(lead.id)

        if created_ids:
            now = datetime.now(timezone.utc)
            await self.db.execute(
                insert(Activity),
                [
                    {
                        "organization_id": organization_id,
                        "lead_id": lead_id,
                        "actor_id": actor.id,
                        "activity_type": ActivityTypeEnum.LEAD_IMPORTED.value,
                        "summary": f"Imported via CSV by {actor.full_name}",
                        "occurred_at": now,
                    }
                    for lead_id in created_ids
                ],
            )

        await self.audit_log.record(
            organization_id=organization_id, actor_id=actor.id, actor_email=actor.email,
            action=AuditActionEnum.IMPORT, resource_type="lead", resource_id=None,
            changes={"created": len(created_ids), "failed": len(failed_rows), "duplicates": duplicate_count},
        )
        await self.db.commit()

        return ImportResultResponse(
            total_rows=len(rows),
            successful_count=len(created_ids),
            failed_count=len(failed_rows),
            duplicate_count=duplicate_count,
            failed_rows=failed_rows[:200],  # cap the payload for very large failed batches
        )

    def _row_to_fields(self, row: dict[str, str], mapping: dict[str, str]) -> dict:
        fields: dict = {}
        for header, target in mapping.items():
            raw_value = (row.get(header) or "").strip()
            if not raw_value:
                continue
            if target == "full_name":
                first, last = _split_full_name(raw_value)
                if first:
                    fields["first_name"] = first
                if last:
                    fields["last_name"] = last
            elif target == "tags":
                fields["tags"] = [t.strip() for t in raw_value.split(",") if t.strip()]
            elif target in ("priority", "employee_count"):
                try:
                    fields[target] = int(float(raw_value))
                except ValueError as exc:
                    raise ValidationError(
                        f"'{raw_value}' is not a number.",
                        errors={"row": [f"Invalid {target}: '{raw_value}'."]},
                    ) from exc
            elif target in ("revenue", "lead_score"):
                try:
                    fields[target] = float(raw_value)
                except ValueError as exc:
                    raise ValidationError(
                        f"'{raw_value}' is not a number.",
                        errors={"row": [f"Invalid {target}: '{raw_value}'."]},
                    ) from exc
            else:
                fields[target] = raw_value

        try:
            LeadCreateRequest.model_validate(fields)
        except PydanticValidationError as exc:
            messages = [f"{'.'.join(str(p) for p in err['loc'])}: {err['msg']}" for err in exc.errors()]
            raise ValidationError("Row failed validation.", errors={"row": messages}) from exc

        return fields

    # ─── Export ─────────────────────────────────────────────────────────────────

    async def export_csv(self, *, organization_id: uuid.UUID, leads: list[Lead]) -> str:
        buffer = io.StringIO()
        columns = [
            "first_name", "last_name", "email", "phone", "job_title", "company_name",
            "website", "industry", "source", "status", "priority", "country", "state",
            "city", "linkedin_url", "twitter_url", "company_size", "revenue",
            "employee_count", "lead_score", "tags", "is_favorite", "is_archived",
            "owner_email", "created_at", "updated_at",
        ]
        writer = csv.DictWriter(buffer, fieldnames=columns)
        writer.writeheader()
        for lead in leads:
            writer.writerow(
                {
                    "first_name": lead.first_name or "",
                    "last_name": lead.last_name or "",
                    "email": lead.email or "",
                    "phone": lead.phone or "",
                    "job_title": lead.job_title or "",
                    "company_name": lead.company_name or "",
                    "website": lead.website or "",
                    "industry": lead.industry or "",
                    "source": lead.source or "",
                    "status": lead.status,
                    "priority": lead.priority,
                    "country": lead.country or "",
                    "state": lead.state or "",
                    "city": lead.city or "",
                    "linkedin_url": lead.linkedin_url or "",
                    "twitter_url": lead.twitter_url or "",
                    "company_size": lead.company_size or "",
                    "revenue": lead.revenue if lead.revenue is not None else "",
                    "employee_count": lead.employee_count if lead.employee_count is not None else "",
                    "lead_score": lead.lead_score if lead.lead_score is not None else "",
                    "tags": ",".join(tag.name for tag in lead.tags),
                    "is_favorite": lead.is_favorite,
                    "is_archived": lead.is_archived,
                    "owner_email": lead.owner.email if lead.owner else "",
                    "created_at": lead.created_at.isoformat(),
                    "updated_at": lead.updated_at.isoformat(),
                }
            )
        return buffer.getvalue()
