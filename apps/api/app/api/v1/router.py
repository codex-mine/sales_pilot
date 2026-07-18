from fastapi import APIRouter

from app.api.v1 import ai, auth, companies, health, leads, organizations

router = APIRouter()
router.include_router(auth.router)
router.include_router(organizations.router)
router.include_router(leads.router)
router.include_router(companies.router)
router.include_router(ai.router)
router.include_router(health.router)
