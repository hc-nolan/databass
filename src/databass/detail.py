"""
Aggregation layer for the release/artist/label Detail page.

Builds the view-model dicts consumed by `templates/detail.html`, shared by
the three entity-specific routes in `releases/routes.py`, `artists/routes.py`,
and `labels/routes.py`.
"""

from datetime import date
from sqlalchemy import func, extract

from .db import models
from .db.base import app_db
from .routes import initials, image_exists, country_name, format_runtime

EXCLUDED_NAMES = ["[NONE]", "Various Artists", "", "[no label]"]


def _score(rating) -> float:
    return round((rating or 0) / 10, 1)


def _fmt_diff(diff_0_100: float) -> str:
    diff = diff_0_100 / 10
    sign = "+" if diff >= 0 else "−"
    return f"{sign}{abs(diff):.1f}"


def _fmt_date(value) -> str:
    if not value:
        return "—"
    return value.strftime("%Y-%m-%d") if hasattr(value, "strftime") else str(value)


def rail_item(name: str, meta: str, rating, href: str, art_type: str, entity_id: int) -> dict:
    return {
        "id": entity_id,
        "href": href,
        "name": name,
        "meta": meta,
        "score": _score(rating),
        "art_key": initials(name),
        "has_art": image_exists(art_type, entity_id),
        "art_type": art_type,
    }


def _release_rail_items(releases, meta_fn) -> list[dict]:
    return [
        rail_item(r.name, meta_fn(r), r.rating, f"/release/{r.id}", "release", r.id)
        for r in releases
    ]


def _entity_rail_items(rows, entity_type: str) -> list[dict]:
    href_prefix = "artist" if entity_type == "artist" else "label"
    return [
        rail_item(
            row.name,
            f"{row.count} logged · avg {_score(row.avg_rating)}",
            row.avg_rating,
            f"/{href_prefix}/{row.id}",
            entity_type,
            row.id,
        )
        for row in rows
    ]


def build_breadcrumb(kind: str, name: str) -> dict:
    crumb_label = {"release": "releases", "artist": "artists", "label": "labels"}[kind]
    return {"crumb_label": crumb_label, "crumb_href": f"/browse/{crumb_label}", "name": name}


def build_release_detail(release: models.Release) -> dict:
    artist = release.artist
    label = release.label
    has_artist = artist and artist.name not in EXCLUDED_NAMES
    has_label = label and label.name not in EXCLUDED_NAMES

    links = []
    if has_artist:
        links.append({"name": artist.name, "href": f"/artist/{artist.id}"})
    if has_label:
        links.append({"name": label.name, "href": f"/label/{label.id}"})

    subline_parts = [str(release.year) if release.year else None, country_name(release.country)]
    subline = " · ".join(p for p in subline_parts if p)

    tags = []
    if release.main_genre:
        tags.append(release.main_genre.name)
    for g in release.genres:
        if g.name not in tags:
            tags.append(g.name)

    reviews = list(release.reviews)
    times_listened = max(len(reviews), 1)

    facts = [
        {"label": "YOUR SCORE", "value": _score(release.rating), "tone": "amber"},
        {"label": "LISTENED", "value": _fmt_date(release.listen_date), "tone": "ink"},
        {"label": "TIMES", "value": times_listened, "tone": "ink"},
        {"label": "RUNTIME", "value": format_runtime(release.runtime), "tone": "ink"},
        {"label": "TRACKS", "value": release.track_count, "tone": "ink"},
    ]

    entries = [{"date": r.timestamp.strftime("%Y-%m-%d"), "text": r.text} for r in reviews]
    if reviews:
        earliest = reviews[-1].timestamp.strftime("%Y-%m-%d")
        noun = "entry" if len(reviews) == 1 else "entries"
        diary_meta = f"{len(reviews)} {noun} · first logged {earliest}"
    else:
        diary_meta = "no diary entries yet"

    context = [
        {
            "label": "vs your average",
            "value": _fmt_diff(release.rating - models.Release.ratings_average()),
        }
    ]
    if has_artist:
        artist_avg = (
            app_db.session.query(func.avg(models.Release.rating))
            .filter(models.Release.artist_id == artist.id)
            .scalar()
            or 0
        )
        context.append(
            {"label": "vs this artist", "value": _fmt_diff(release.rating - artist_avg)}
        )
    if release.main_genre:
        genre_avg = (
            app_db.session.query(func.avg(models.Release.rating))
            .filter(models.Release.main_genre_id == release.main_genre_id)
            .scalar()
            or 0
        )
        context.append(
            {
                "label": f"vs {release.main_genre.name}",
                "value": _fmt_diff(release.rating - genre_avg),
            }
        )
    if release.listen_date:
        year = release.listen_date.year
        year_rows = (
            app_db.session.query(models.Release.id, models.Release.rating)
            .filter(extract("year", models.Release.listen_date) == year)
            .order_by(models.Release.rating.desc())
            .all()
        )
        total = len(year_rows)
        rank = next(
            (i + 1 for i, (rid, _) in enumerate(year_rows) if rid == release.id), None
        )
        if rank:
            context.append({"label": f"rank in {year}", "value": f"#{rank} of {total}"})
        days_since = (date.today() - release.listen_date.date()).days
        context.append({"label": "days since last listen", "value": str(days_since)})

    rails = []
    if has_artist:
        artist_items = [r for r in artist.releases if r.id != release.id]
        items = _release_rail_items(artist_items, lambda r: f"{r.year} · {_score(r.rating)}")
        if items:
            noun = "release" if len(items) == 1 else "releases"
            rails.append(
                {
                    "title": f"ALSO BY {artist.name.upper()}",
                    "note": f"{len(items)} {noun} logged",
                    "items": items,
                }
            )
    if has_label:
        label_items = [r for r in label.releases if r.id != release.id]
        items = _release_rail_items(
            label_items,
            lambda r: f"{r.artist.name if r.artist else '?'} · {_score(r.rating)}",
        )
        if items:
            avg = sum(r.rating for r in label_items) / len(label_items) if label_items else 0
            noun = "release" if len(items) == 1 else "releases"
            rails.append(
                {
                    "title": f"ALSO ON {label.name.upper()}",
                    "note": f"{len(items)} {noun} logged · avg {_score(avg)}",
                    "items": items,
                }
            )

    return {
        "kind": "release",
        "id": release.id,
        "eyebrow": "RELEASE",
        "name": release.name,
        "art_key": initials(artist.name if has_artist else release.name),
        "has_art": image_exists("release", release.id),
        **build_breadcrumb("release", release.name),
        "links": links,
        "subline": subline,
        "tags": tags,
        "facts": facts,
        "is_release": True,
        "relisten_href": f"/release/{release.id}/relisten",
        "edit_href": f"/release/{release.id}/edit",
        "delete_id": release.id,
        "delete_type": "release",
        "show_delete": True,
        "source_href": f"https://musicbrainz.org/release/{release.mbid}" if release.mbid else None,
        "diary_meta": diary_meta,
        "entries": entries,
        "context": context,
        "rails": rails,
    }


def build_artist_detail(artist: models.Artist) -> dict:
    releases = list(artist.releases)
    ratings = [r.rating for r in releases]
    listen_dates = [r.listen_date for r in releases if r.listen_date]

    if artist.type == "person":
        span = f"born {artist.begin or '?'}"
        if artist.end:
            span += f" · died {artist.end}"
    elif artist.type == "group":
        span = f"active {artist.begin or '?'} – {artist.end or 'present'}"
    else:
        span = ""

    links = [n for n in [country_name(artist.country), artist.type] if n]

    tags = _genres_for_releases(releases)

    facts = [
        {"label": "LOGGED", "value": len(releases), "tone": "ink"},
        {
            "label": "AVG SCORE",
            "value": _score(sum(ratings) / len(ratings)) if ratings else "—",
            "tone": "amber",
        },
        {"label": "BEST", "value": _score(max(ratings)) if ratings else "—", "tone": "ink"},
        {"label": "FIRST", "value": _fmt_date(min(listen_dates)) if listen_dates else "—", "tone": "ink"},
        {"label": "LAST", "value": _fmt_date(max(listen_dates)) if listen_dates else "—", "tone": "ink"},
    ]

    release_items = _release_rail_items(
        releases,
        lambda r: f"{r.year} · {r.label.name if r.label else '?'}",
    )
    rails = []
    if release_items:
        noun = "release" if len(release_items) == 1 else "releases"
        rails.append(
            {
                "title": "RELEASES YOU'VE LOGGED",
                "note": f"{len(release_items)} {noun} logged",
                "items": release_items,
            }
        )

    genre_ids = {r.main_genre_id for r in releases if r.main_genre_id}
    if genre_ids:
        rows = (
            app_db.session.query(
                models.Artist.id,
                models.Artist.name,
                func.count(models.Release.id).label("count"),
                func.avg(models.Release.rating).label("avg_rating"),
            )
            .join(models.Release, models.Release.artist_id == models.Artist.id)
            .filter(models.Release.main_genre_id.in_(genre_ids))
            .filter(models.Artist.id != artist.id)
            .filter(models.Artist.name.notin_(EXCLUDED_NAMES))
            .group_by(models.Artist.id, models.Artist.name)
            .order_by(func.avg(models.Release.rating).desc())
            .limit(6)
            .all()
        )
        similar_items = _entity_rail_items(rows, "artist")
        if similar_items:
            rails.append(
                {
                    "title": "IF YOU LIKE THIS",
                    "note": "artists with overlapping genres in your library",
                    "items": similar_items,
                }
            )

    return {
        "kind": "artist",
        "id": artist.id,
        "eyebrow": "ARTIST",
        "name": artist.name,
        "art_key": initials(artist.name),
        "has_art": image_exists("artist", artist.id),
        **build_breadcrumb("artist", artist.name),
        "links": [{"name": n} for n in links],
        "subline": span,
        "tags": tags,
        "facts": facts,
        "is_release": False,
        "edit_href": f"/artist/{artist.id}/edit",
        "show_delete": False,
        "source_href": f"https://musicbrainz.org/artist/{artist.mbid}" if artist.mbid else None,
        "rails": rails,
    }


def build_label_detail(label: models.Label) -> dict:
    releases = list(label.releases)
    ratings = [r.rating for r in releases]
    listen_dates = [r.listen_date for r in releases if r.listen_date]
    artist_ids = {r.artist_id for r in releases if r.artist_id}

    span = f"founded {label.begin}" if label.begin else ""
    if label.begin and label.end:
        span += f" · closed {label.end}"

    links = [n for n in [country_name(label.country), label.type] if n]
    tags = _genres_for_releases(releases)

    rank = _label_rank(label.id)

    facts = [
        {"label": "LOGGED", "value": len(releases), "tone": "ink"},
        {
            "label": "AVG SCORE",
            "value": _score(sum(ratings) / len(ratings)) if ratings else "—",
            "tone": "amber",
        },
        {"label": "ARTISTS", "value": len(artist_ids), "tone": "ink"},
        {"label": "FIRST", "value": _fmt_date(min(listen_dates)) if listen_dates else "—", "tone": "ink"},
        {"label": "RANK", "value": f"#{rank}" if rank else "—", "tone": "ink"},
    ]

    release_items = _release_rail_items(
        releases,
        lambda r: f"{r.artist.name if r.artist else '?'} · {r.year}",
    )
    rails = []
    if release_items:
        avg = sum(ratings) / len(ratings) if ratings else 0
        rails.append(
            {
                "title": "RELEASES YOU'VE LOGGED",
                "note": f"{len(release_items)} releases · avg {_score(avg)}",
                "items": release_items,
            }
        )

    artist_rows = (
        app_db.session.query(
            models.Artist.id,
            models.Artist.name,
            func.count(models.Release.id).label("count"),
            func.avg(models.Release.rating).label("avg_rating"),
        )
        .join(models.Release, models.Release.artist_id == models.Artist.id)
        .filter(models.Release.label_id == label.id)
        .filter(models.Artist.name.notin_(EXCLUDED_NAMES))
        .group_by(models.Artist.id, models.Artist.name)
        .order_by(func.count(models.Release.id).desc())
        .limit(8)
        .all()
    )
    artist_items = _entity_rail_items(artist_rows, "artist")
    if artist_items:
        rails.append(
            {
                "title": "ARTISTS ON THIS LABEL",
                "note": "in your library",
                "items": artist_items,
            }
        )

    return {
        "kind": "label",
        "id": label.id,
        "eyebrow": "LABEL",
        "name": label.name,
        "art_key": initials(label.name),
        "has_art": image_exists("label", label.id),
        **build_breadcrumb("label", label.name),
        "links": [{"name": n} for n in links],
        "subline": span,
        "tags": tags,
        "facts": facts,
        "is_release": False,
        "edit_href": f"/label/{label.id}/edit",
        "show_delete": False,
        "source_href": f"https://musicbrainz.org/label/{label.mbid}" if label.mbid else None,
        "rails": rails,
    }


def _genres_for_releases(releases, limit: int = 5) -> list[str]:
    counts: dict[str, int] = {}
    for r in releases:
        if r.main_genre:
            counts[r.main_genre.name] = counts.get(r.main_genre.name, 0) + 1
    return [name for name, _ in sorted(counts.items(), key=lambda kv: kv[1], reverse=True)][:limit]


def _label_rank(label_id: int) -> int | None:
    rows = (
        app_db.session.query(models.Label.id, func.count(models.Release.id).label("count"))
        .join(models.Release, models.Release.label_id == models.Label.id)
        .filter(models.Label.name.notin_(EXCLUDED_NAMES))
        .group_by(models.Label.id)
        .order_by(func.count(models.Release.id).desc())
        .all()
    )
    return next((i + 1 for i, (lid, _) in enumerate(rows) if lid == label_id), None)
