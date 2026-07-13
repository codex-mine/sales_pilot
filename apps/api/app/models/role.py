import uuid
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from app.database.base import Base
class Role(Base):
    """Catalog role retained for policy expansion; membership currently stores its stable role key."""
    __tablename__ = "roles"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(String(255))
