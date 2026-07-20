"""
`Campaign.settings` JSONB packing for fields with no dedicated column — same
reasoning as `sequence_service.py`'s `content_source`-inside-`condition`
packing: V1 reuses the existing schema only, no migration. This is the only
place that packs/unpacks these keys; every other caller sees
`requires_approval` as a plain, explicit field.
"""

from app.models.campaigns.models import Campaign

_REQUIRES_APPROVAL_KEY = "requires_approval"


def get_requires_approval(campaign: Campaign) -> bool:
    return bool((campaign.settings or {}).get(_REQUIRES_APPROVAL_KEY, True))


def pack_requires_approval(settings: dict | None, requires_approval: bool) -> dict:
    merged = dict(settings or {})
    merged[_REQUIRES_APPROVAL_KEY] = requires_approval
    return merged
