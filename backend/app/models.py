# Create models like (id , short_code , url , created_at ,clicks )
from datetime import datetime
import uuid
from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from .database import Base 

class Url(Base):
    __tablename__ = "urls"
    __table_args__ = (UniqueConstraint("short_code", name="uq_urls_short_code"),)

    id : Mapped[uuid.UUID] = mapped_column(
        default = uuid.uuid4,
        primary_key=True
        )
    short_code : Mapped[str] = mapped_column(
        String(10),
        nullable=False
    )
    original_url : Mapped[str] = mapped_column(
        Text,
        nullable=False 
    ) 
    created_at : Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    clicks : Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False 
    )


