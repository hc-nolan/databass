"""ListenBrainz listen import, album detection, and catalog matching."""

from __future__ import annotations

import os
import threading
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy.exc import IntegrityError

from .api import ListenBrainz
from .db.base import app_db
from .db.models import AppSetting, Artist, Listen, Release, ScrobbledAlbum


# ListenBrainz rate-limits to about one request per second; a page is up to
# 1000 listens, so 25 pages is roughly a 25k-listen slice of history per sync.
BACKFILL_PAGE_LIMIT = 25
PAGE_SIZE = 1000
# Only recent history should surface as "log this listen" suggestions; a
# full-history backfill must not dump thousands of old recommendations.
SUGGESTION_WINDOW_DAYS = 30

# A manual "sync now" can overlap the scheduler's job in the same process;
# serialise them so the check-then-insert dedupe can't race.
_sync_lock = threading.Lock()


def lb_enabled() -> bool:
    return bool(os.getenv("LISTENBRAINZ_USERNAME"))


def album_key(listen: dict) -> str:
    return (
        listen.get("release_group_mbid")
        or listen.get("release_mbid")
        or f"{_norm(listen.get('artist_name'))}::{_norm(listen.get('release_name'))}"
    )


def _norm(text: str | None) -> str:
    """Casefold and collapse whitespace/punctuation for fuzzy name matching."""
    if not text:
        return ""
    cleaned = "".join(ch if ch.isalnum() else " " for ch in text.casefold())
    return " ".join(cleaned.split())


def dedupe_key(listen: dict) -> str:
    if listen.get("recording_mbid"):
        return f"mbid:{listen['recording_mbid']}"
    return "name:{artist}|{track}|{release}".format(
        artist=_norm(listen.get("artist_name")),
        track=_norm(listen.get("track_name")),
        release=_norm(listen.get("release_name")),
    )


def detect_album_listens(listens: list[dict], gap_minutes: int = 90) -> list[dict]:
    """Group scrobbles into probable album listens.

    ListenBrainz does not expose album track counts on every listen, so three
    distinct tracks is the conservative threshold when no count is available.
    """
    groups: dict[str, list[dict]] = defaultdict(list)
    for listen in listens:
        if listen.get("listened_at") and listen.get("release_name"):
            groups[album_key(listen)].append(listen)

    detected = []
    for key, rows in groups.items():
        rows.sort(key=lambda row: row["listened_at"])
        clusters: list[list[dict]] = []
        for row in rows:
            if not clusters or row["listened_at"] - clusters[-1][-1]["listened_at"] > gap_minutes * 60:
                clusters.append([])
            clusters[-1].append(row)
        for cluster in clusters:
            tracks = list(dict.fromkeys(r.get("track_name") for r in cluster if r.get("track_name")))
            if len(tracks) < 3:
                continue
            first = cluster[0]
            detected.append(
                {
                    "album_key": key,
                    "artist_name": first.get("artist_name", "Unknown artist"),
                    "artist_mbid": first.get("artist_mbid"),
                    "release_name": first.get("release_name", "Unknown release"),
                    "release_mbid": first.get("release_mbid"),
                    "release_group_mbid": first.get("release_group_mbid"),
                    "listened_at": datetime.fromtimestamp(
                        cluster[-1]["listened_at"], timezone.utc
                    ),
                    "track_names": tracks,
                }
            )
    return detected


class CatalogIndex:
    """Resolves a scrobble to a logged Release/Artist using MBID then name.

    Built once per sync so matching is a handful of dict lookups rather than
    per-listen queries. ``release_by_group`` is seeded from previously linked
    listens, which lets a scrobble from a different pressing of an album link
    through its release-group MBID.
    """

    def __init__(self):
        releases = (
            app_db.session.query(
                Release.id,
                Release.mbid,
                Release.name,
                Release.artist_id,
                Artist.name,
            )
            .join(Artist, Release.artist_id == Artist.id, isouter=True)
            .all()
        )
        self.release_by_mbid: dict[str, int] = {}
        self.release_by_name: dict[tuple[str, str], int] = {}
        for release_id, mbid, name, artist_id, artist_name in releases:
            if mbid:
                self.release_by_mbid.setdefault(mbid, release_id)
            self.release_by_name.setdefault((_norm(artist_name), _norm(name)), release_id)

        self.artist_by_mbid: dict[str, int] = {}
        self.artist_by_name: dict[str, int] = {}
        for artist_id, mbid, name in app_db.session.query(Artist.id, Artist.mbid, Artist.name):
            if mbid:
                self.artist_by_mbid.setdefault(mbid, artist_id)
            self.artist_by_name.setdefault(_norm(name), artist_id)

        self.release_by_group: dict[str, int] = {}
        rows = (
            app_db.session.query(Listen.release_group_mbid, Listen.release_id)
            .filter(Listen.release_id.isnot(None), Listen.release_group_mbid.isnot(None))
            .distinct()
        )
        for group_mbid, release_id in rows:
            self.release_by_group.setdefault(group_mbid, release_id)

    def resolve_release(self, listen: dict) -> int | None:
        mbid = listen.get("release_mbid")
        if mbid and mbid in self.release_by_mbid:
            return self.release_by_mbid[mbid]
        group = listen.get("release_group_mbid")
        if group and group in self.release_by_group:
            return self.release_by_group[group]
        return self.release_by_name.get(
            (_norm(listen.get("artist_name")), _norm(listen.get("release_name")))
        )

    def resolve_artist(self, listen: dict) -> int | None:
        mbid = listen.get("artist_mbid")
        if mbid and mbid in self.artist_by_mbid:
            return self.artist_by_mbid[mbid]
        return self.artist_by_name.get(_norm(listen.get("artist_name")))

    def learn(self, listen: dict, release_id: int | None) -> None:
        """Remember a group→release link discovered from an exact match."""
        group = listen.get("release_group_mbid")
        if group and release_id is not None:
            self.release_by_group.setdefault(group, release_id)
        mbid = listen.get("release_mbid")
        if mbid and release_id is not None:
            self.release_by_mbid.setdefault(mbid, release_id)


def _as_utc(epoch: int) -> datetime:
    return datetime.fromtimestamp(epoch, timezone.utc).replace(tzinfo=None)


def _existing_listen_keys(timestamps: set) -> set:
    """Already-stored (listened_at, dedupe_key) pairs for the given timestamps."""
    if not timestamps:
        return set()
    rows = app_db.session.query(Listen.listened_at, Listen.dedupe_key).filter(
        Listen.listened_at.in_(timestamps)
    )
    return {(row[0], row[1]) for row in rows}


def _import_batch(batch: list[dict], index: CatalogIndex) -> tuple[int, int]:
    """Store new scrobbles and detect album listens. Returns (imported, suggestions)."""
    if not batch:
        return 0, 0

    timestamps = {_as_utc(item["listened_at"]) for item in batch if item.get("listened_at")}
    existing = _existing_listen_keys(timestamps)

    imported = 0
    for item in batch:
        if not item.get("listened_at"):
            continue
        listened_at = _as_utc(item["listened_at"])
        key = dedupe_key(item)
        if (listened_at, key) in existing:
            continue
        release_id = index.resolve_release(item)
        index.learn(item, release_id)
        try:
            # Savepoint per row: a duplicate (e.g. a concurrent sync) only
            # rolls back its own insert, so the rest of the batch — and the
            # cursor the caller advances afterwards — stays consistent.
            with app_db.session.begin_nested():
                app_db.session.add(
                    Listen(
                        listened_at=listened_at,
                        dedupe_key=key,
                        track_name=item.get("track_name"),
                        artist_name=item.get("artist_name"),
                        artist_mbid=item.get("artist_mbid"),
                        release_name=item.get("release_name"),
                        release_mbid=item.get("release_mbid"),
                        release_group_mbid=item.get("release_group_mbid"),
                        recording_mbid=item.get("recording_mbid"),
                        release_id=release_id,
                        artist_id=index.resolve_artist(item),
                    )
                )
        except IntegrityError:
            continue
        existing.add((listened_at, key))
        imported += 1

    suggestions = _store_suggestions(batch)
    app_db.session.commit()
    return imported, suggestions


def _store_suggestions(batch: list[dict]) -> int:
    tz = _local_tz()
    cutoff = datetime.now(timezone.utc) - timedelta(days=SUGGESTION_WINDOW_DAYS)
    cutoff_epoch = int(cutoff.timestamp())
    created = 0
    for item in detect_album_listens(
        [row for row in batch if row.get("listened_at", 0) >= cutoff_epoch]
    ):
        local_date = item["listened_at"].astimezone(tz).replace(tzinfo=None)
        exists = (
            app_db.session.query(ScrobbledAlbum)
            .filter_by(album_key=item["album_key"], listened_at=local_date)
            .one_or_none()
        )
        if exists:
            continue
        if item.get("release_mbid") and Release.exists_by_mbid(item["release_mbid"]):
            continue
        try:
            with app_db.session.begin_nested():
                app_db.session.add(ScrobbledAlbum(**{**item, "listened_at": local_date}))
        except IntegrityError:
            continue
        created += 1
    return created


def _local_tz():
    try:
        return ZoneInfo(os.getenv("TIMEZONE") or "UTC")
    except Exception:
        return ZoneInfo("UTC")


def relink_unmatched(limit: int = 5000) -> int:
    """Re-resolve scrobbles stored before their release/artist was logged."""
    pending = (
        app_db.session.query(Listen)
        .filter((Listen.release_id.is_(None)) | (Listen.artist_id.is_(None)))
        .limit(limit)
        .all()
    )
    if not pending:
        return 0
    index = CatalogIndex()
    updated = 0
    for listen in pending:
        item = {
            "release_mbid": listen.release_mbid,
            "release_group_mbid": listen.release_group_mbid,
            "artist_name": listen.artist_name,
            "release_name": listen.release_name,
            "artist_mbid": listen.artist_mbid,
        }
        changed = False
        if listen.release_id is None:
            release_id = index.resolve_release(item)
            if release_id is not None:
                listen.release_id = release_id
                index.learn(item, release_id)
                changed = True
        if listen.artist_id is None:
            artist_id = index.resolve_artist(item)
            if artist_id is not None:
                listen.artist_id = artist_id
                changed = True
        updated += 1 if changed else 0
    app_db.session.commit()
    return updated


def _get_setting(key: str):
    return app_db.session.query(AppSetting).filter_by(key=key).one_or_none()


def _set_setting(key: str, value) -> None:
    setting = _get_setting(key)
    if not setting:
        setting = AppSetting(key=key)
        app_db.session.add(setting)
    setting.value = value


def _get_int_setting(key: str) -> int | None:
    setting = _get_setting(key)
    if not setting or setting.value in (None, ""):
        return None
    try:
        return int(setting.value)
    except (TypeError, ValueError):
        return None


def _backfill_cutoff() -> int | None:
    """Optional lower bound (epoch seconds) from LISTENBRAINZ_BACKFILL_DAYS."""
    days = os.getenv("LISTENBRAINZ_BACKFILL_DAYS", "0")
    try:
        days = int(days)
    except ValueError:
        days = 0
    if days <= 0:
        return None
    return int(datetime.now(timezone.utc).timestamp()) - days * 86400


def _run_backfill(username: str, page_limit: int) -> tuple[int, int]:
    index = CatalogIndex()
    imported = suggestions = 0

    # Keep the head of the history current while older pages are still being
    # filled in, so today's listens aren't held up by a multi-run backfill.
    head_cursor = _get_int_setting("lb_last_sync_ts")
    if head_cursor is not None:
        head = ListenBrainz.fetch_listens(username, min_ts=head_cursor, count=PAGE_SIZE)
        if head:
            page_imported, page_suggestions = _import_batch(head, index)
            imported += page_imported
            suggestions += page_suggestions
            _set_setting("lb_last_sync_ts", max(item["listened_at"] for item in head))

    cursor = _get_int_setting("lb_backfill_min_ts")
    cutoff = _backfill_cutoff()
    done = False

    for _ in range(page_limit):
        batch = ListenBrainz.fetch_listens(username, max_ts=cursor, count=PAGE_SIZE)
        if not batch:
            done = True
            break
        page_imported, page_suggestions = _import_batch(batch, index)
        imported += page_imported
        suggestions += page_suggestions
        if _get_int_setting("lb_last_sync_ts") is None:
            _set_setting("lb_last_sync_ts", max(item["listened_at"] for item in batch))
        oldest = min(item["listened_at"] for item in batch)
        cursor = oldest
        _set_setting("lb_backfill_min_ts", cursor)
        if len(batch) < PAGE_SIZE:
            done = True
            break
        if cutoff is not None and oldest < cutoff:
            done = True
            break

    _set_setting("lb_backfill_done", done)
    app_db.session.commit()
    return imported, suggestions


def _run_incremental(username: str, page_limit: int) -> tuple[int, int]:
    index = CatalogIndex()
    cursor = _get_int_setting("lb_last_sync_ts")
    imported = suggestions = 0
    for _ in range(page_limit):
        batch = ListenBrainz.fetch_listens(username, min_ts=cursor, count=PAGE_SIZE)
        if not batch:
            break
        page_imported, page_suggestions = _import_batch(batch, index)
        imported += page_imported
        suggestions += page_suggestions
        cursor = max(item["listened_at"] for item in batch)
        _set_setting("lb_last_sync_ts", cursor)
        if len(batch) < PAGE_SIZE:
            break
    app_db.session.commit()
    return imported, suggestions


def sync_listens(page_limit: int = BACKFILL_PAGE_LIMIT) -> dict:
    """Import listens (backfilling history first, then incrementally)."""
    username = os.getenv("LISTENBRAINZ_USERNAME")
    if not username:
        return {"imported": 0, "suggestions": 0, "backfill_done": False}

    # Non-blocking: if a sync is already running (scheduler vs "sync now"),
    # skip this one rather than racing on the same unique listens.
    if not _sync_lock.acquire(blocking=False):
        return {
            "imported": 0,
            "suggestions": 0,
            "backfill_done": _backfill_done(),
            "total": Listen.total(),
            "busy": True,
        }
    try:
        if _backfill_done():
            imported, suggestions = _run_incremental(username, page_limit)
        else:
            imported, suggestions = _run_backfill(username, page_limit)

        relink_unmatched()
        return {
            "imported": imported,
            "suggestions": suggestions,
            "backfill_done": _backfill_done(),
            "total": Listen.total(),
        }
    finally:
        _sync_lock.release()


def _backfill_done() -> bool:
    setting = _get_setting("lb_backfill_done")
    return bool(setting and setting.value)
