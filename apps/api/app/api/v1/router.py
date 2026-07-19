from fastapi import APIRouter

from app.api.v1 import (
    ai,
    analytics,
    auth,
    companies,
    email_sender_settings,
    email_templates,
    emails,
    health,
    leads,
    organizations,
    track,
    unsubscribe,
    webhooks,
)

router = APIRouter()
router.include_router(auth.router)
router.include_router(organizations.router)
router.include_router(leads.router)
router.include_router(companies.router)
router.include_router(ai.router)
router.include_router(email_templates.router)
router.include_router(emails.router)
router.include_router(email_sender_settings.router)
router.include_router(unsubscribe.router)
router.include_router(track.router)
router.include_router(webhooks.router)
router.include_router(analytics.router)
router.include_router(health.router)
