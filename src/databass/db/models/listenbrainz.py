from __future__ import annotations

from datetime import datetime, time, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

from sqlalchemy import DateTime, ForeignKey, JSON, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from ..base import app_db
from .base import Base
from .catalog import Release


class AppSetting(Base):
    __tablename__ = "app_setting"
    key: Mapped[str] = mapped_column(String, unique=True)
    value: Mapped[dict | list | str | int | float | None] = mapped_column(JSON, nullable=True)


class ScrobbledAlbum(Base):
    __tablename__ = "scrobbled_album"
    __table_args__ = (UniqueConstraint("album_key", "listened_at", name="uq_scrobbled_album_key_date"),)

    album_key: Mapped[str] = mapped_column(String, index=True)
    artist_name: Mapped[str] = mapped_column(String)
    artist_mbid: Mapped[str | None] = mapped_column(String, nullable=True)
    release_name: Mapped[str] = mapped_column(String)
    release_mbid: Mapped[str | None] = mapped_column(String, nullable=True)
    release_group_mbid: Mapped[str | None] = mapped_column(String, nullable=True)
    listened_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    track_names: Mapped[list[str]] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String, default="pending", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Listen(Base):
    """One row per ListenBrainz scrobble.

    Scrobbles are the raw fact table that backs per-release/artist/label listen
    counts and the favourites metric. ``release_id``/``artist_id`` are resolved
    lazily at import time (and re-resolved by a relink pass) so a scrobble that
    arrives before its release is logged still gets linked later. Unmatched
    listens keep NULL links and only count toward global figures.
    """

    __tablename__ = "listen"
    __table_args__ = (
        UniqueConstraint("listened_at", "dedupe_key", name="uq_listen_identity"),
    )

    listened_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    # recording MBID when known, otherwise a normalized name triple, so the
    # same scrobble is not stored twice across overlapping incremental fetches.
    dedupe_key: Mapped[str] = mapped_column(String, index=True)
    track_name: Mapped[str | None] = mapped_column(String, nullable=True)
    artist_name: Mapped[str | None] = mapped_column(String, nullable=True)
    artist_mbid: Mapped[str | None] = mapped_column(String, nullable=True)
    release_name: Mapped[str | None] = mapped_column(String, nullable=True)
    release_mbid: Mapped[str | None] = mapped_column(String, nullable=True)
    release_group_mbid: Mapped[str | None] = mapped_column(String, nullable=True)
    recording_mbid: Mapped[str | None] = mapped_column(String, nullable=True)
    release_id: Mapped[int | None] = mapped_column(
        ForeignKey("release.id"), index=True, nullable=True
    )
    artist_id: Mapped[int | None] = mapped_column(
        ForeignKey("artist.id"), index=True, nullable=True
    )

    @classmethod
    def total(cls) -> int:
        try:
            return app_db.session.query(func.count(cls.id)).scalar() or 0
        except Exception:
            return 0

    @classmethod
    def for_release(cls, release_ids: list[int]) -> int:
        if not release_ids:
            return 0
        return (
            app_db.session.query(func.count(cls.id))
            .filter(cls.release_id.in_(release_ids))
            .scalar()
            or 0
        )

    @classmethod
    def last_for_release(cls, release_ids: list[int]) -> Optional[datetime]:
        if not release_ids:
            return None
        return (
            app_db.session.query(func.max(cls.listened_at))
            .filter(cls.release_id.in_(release_ids))
            .scalar()
        )

    @classmethod
    def for_artist(cls, artist_id: int) -> int:
        return (
            app_db.session.query(func.count(cls.id))
            .filter(cls.artist_id == artist_id)
            .scalar()
            or 0
        )

    @classmethod
    def for_label(cls, label_id: int) -> int:
        """Scrobbles linked to releases on this label (catalog-matched only)."""
        return (
            app_db.session.query(func.count(cls.id))
            .join(Release, cls.release_id == Release.id)
            .filter(Release.label_id == label_id)
            .scalar()
            or 0
        )

    @classmethod
    def today_summary(cls, timezone_name: str | None = None) -> dict:
        """Scrobbles and distinct albums so far today, in the user's timezone."""
        try:
            tz = ZoneInfo(timezone_name or "UTC")
        except Exception:
            tz = ZoneInfo("UTC")
        now_local = datetime.now(tz)
        start = datetime.combine(now_local.date(), time.min)
        start_utc = start.replace(tzinfo=tz).astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
        end_utc = start_utc + timedelta(days=1)
        return {
            "listens": cls._count_between(start_utc, end_utc),
            "albums": cls._distinct_releases_between(start_utc, end_utc),
        }

    @classmethod
    def _count_between(cls, start: datetime, end: datetime) -> int:
        return (
            app_db.session.query(func.count(cls.id))
            .filter(cls.listened_at >= start, cls.listened_at < end)
            .scalar()
            or 0
        )

    @classmethod
    def _distinct_releases_between(cls, start: datetime, end: datetime) -> int:
        return (
            app_db.session.query(func.count(func.distinct(cls.release_id)))
            .filter(
                cls.listened_at >= start,
                cls.listened_at < end,
                cls.release_id.isnot(None),
            )
            .scalar()
            or 0
        )
