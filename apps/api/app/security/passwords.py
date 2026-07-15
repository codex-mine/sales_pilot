import re

from passlib.context import CryptContext

from app.core.config import get_settings

_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

_UPPER = re.compile(r"[A-Z]")
_LOWER = re.compile(r"[a-z]")
_DIGIT = re.compile(r"\d")
_SPECIAL = re.compile(r"[^A-Za-z0-9]")


def hash_password(password: str) -> str:
    return _context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return _context.verify(password, password_hash)


def validate_password_strength(password: str) -> list[str]:
    """
    Returns a list of human-readable violations (empty list == valid).
    Kept separate from the Pydantic schema so the same rule set can be reused
    by reset-password and change-password flows without re-declaring a
    field validator on every schema.
    """
    settings = get_settings()
    violations: list[str] = []

    if len(password) < settings.password_min_length:
        violations.append(
            f"Password must be at least {settings.password_min_length} characters long."
        )
    if len(password) > settings.password_max_length:
        violations.append(
            f"Password must be at most {settings.password_max_length} characters long."
        )
    if not _UPPER.search(password):
        violations.append("Password must contain at least one uppercase letter.")
    if not _LOWER.search(password):
        violations.append("Password must contain at least one lowercase letter.")
    if not _DIGIT.search(password):
        violations.append("Password must contain at least one number.")
    if not _SPECIAL.search(password):
        violations.append("Password must contain at least one special character.")

    return violations
