from typing import Generic, TypeVar
from pydantic import BaseModel
T = TypeVar("T")
class ApiResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T | None = None
    message: str = "OK"
    errors: dict[str, list[str]] | None = None
    meta: dict[str, object] | None = None
