from fastapi import APIRouter
from app.schemas.common import ApiResponse
router = APIRouter(tags=["health"])
@router.get("/health/live", response_model=ApiResponse[dict[str, str]])
async def live() -> ApiResponse[dict[str, str]]: return ApiResponse(data={"status": "ok"})
@router.get("/health/ready", response_model=ApiResponse[dict[str, str]])
async def ready() -> ApiResponse[dict[str, str]]: return ApiResponse(data={"status": "ready"})
