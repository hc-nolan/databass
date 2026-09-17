from datetime import date

from sqlalchemy import String, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Review(Base):
    __tablename__ = "review"
    timestamp: Mapped[date] = mapped_column(DateTime, default=func.now())
    text: Mapped[str] = mapped_column(String)
    release_id: Mapped[int] = mapped_column(ForeignKey("release.id"))

    release = relationship("Release", back_populates="reviews")
