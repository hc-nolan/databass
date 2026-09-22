"""
Explore: declarative query engine for the stats "explore" tab.

The frontend sends a validated JSON spec describing filters, a group-by
dimension, an aggregate metric, and a limit/sort (see ``run_query``). This
module translates that spec into a SQLAlchemy aggregate over the Release
fact table - one row per logged listen - joined to Artist / Label / Genre as
the filters and dimension require, and returns rows already formatted for the
frontend's hand-rolled bar/column charts.

No query language, no raw SQL: every field, operator, dimension and metric is
whitelisted and validated up front, and aggregate limits are clamped.
"""

from __future__ import annotations

from typing import Any, Callable, Optional

import pycountry
from sqlalchemy import Integer, and_, case, extract, false, func, or_

from .db import models
from .db.base import app_db
from .db.models.associations import release_genre_association

DEFAULT_LIMIT = 15
LIMIT_MIN = 1
LIMIT_MAX = 50
MIN_ITEMS_MIN = 1
MIN_ITEMS_MAX = 1_000_000

MONTH_NAMES = [
    "JAN",
    "FEB",
    "MAR",
    "APR",
    "MAY",
    "JUN",
    "JUL",
    "AUG",
    "SEP",
    "OCT",
    "NOV",
    "DEC",
]

# ---------------------------------------------------------------------------
# Whitelists (single source of truth for what the frontend may request).
# ---------------------------------------------------------------------------

# field name -> {"label": str, "kind": "text"|"enum"|"years"|"range",
#                 "options": option-key for enum fields}
FIELD_DEFS: dict[str, dict] = {
    "artist_name": {"label": "artist name", "kind": "text"},
    "artist_country": {
        "label": "artist country",
        "kind": "enum",
        "options": "artist_countries",
    },
    "artist_type": {"label": "artist type", "kind": "enum", "options": "artist_types"},
    "artist_active": {"label": "artist active years", "kind": "years"},
    "label_name": {"label": "label name", "kind": "text"},
    "label_country": {
        "label": "label country",
        "kind": "enum",
        "options": "label_countries",
    },
    "label_type": {"label": "label type", "kind": "enum", "options": "label_types"},
    "release_name": {"label": "release title", "kind": "text"},
    "release_country": {
        "label": "release country",
        "kind": "enum",
        "options": "release_countries",
    },
    "genre": {"label": "genre", "kind": "enum", "options": "genres"},
    "release_year": {"label": "release year", "kind": "range"},
    "listen_year": {"label": "listen year", "kind": "range"},
    "rating": {"label": "rating", "kind": "range"},
    "runtime": {"label": "runtime (min)", "kind": "range"},
}

GROUP_BY_DEFS: dict[str, dict] = {
    "artist": {"label": "artist"},
    "label": {"label": "label"},
    "genre": {"label": "genre"},
    "release_country": {"label": "release country"},
    "artist_country": {"label": "artist country"},
    "artist_type": {"label": "artist type"},
    "release_year": {"label": "release year"},
    "release_decade": {"label": "release decade"},
    "listen_year": {"label": "listen year"},
    "listen_month": {"label": "listen month"},
    "rating_bucket": {"label": "rating"},
}

METRIC_DEFS: dict[str, dict] = {
    "count": {"label": "releases logged"},
    "distinct_artists": {"label": "distinct artists"},
    "avg_rating": {"label": "average rating"},
    "bayes_rating": {"label": "favourites (Bayesian avg)"},
    "runtime_hours": {"label": "listening time"},
}

# Operators allowed per field kind.
_KIND_OPS = {
    "text": {"contains"},
    "enum": {"eq"},
    "years": {"overlaps"},
    "range": {"between", "gte", "lte"},
}

# Inclusive value bounds for range fields, in *display* units. These are the
# outer validation limits, deliberately wider than any realistic data so the
# data-driven bounds exposed by `explore_options` are always a subset.
_RANGE_BOUNDS: dict[str, tuple[int, int]] = {
    "release_year": (1000, 2200),
    "listen_year": (1900, 2200),
    "rating": (1, 10),
    "runtime": (5, 600),
}

# Accepted value window for the artist active-years overlap filter.
_ERA_BOUNDS = (1000, 2200)

# Maximum number of filter rows a spec may carry (guards the API against
# degenerate payloads ballooning into Postgres' bound-parameter limits).
MAX_FILTERS = 20

# Fields that require a join to the artist table.
_ARTIST_FIELDS = {"artist_name", "artist_country", "artist_type", "artist_active"}
_LABEL_FIELDS = {"label_name", "label_country", "label_type"}

_PLACEHOLDER_NAMES = ["", "[NONE]", "Various Artists", "[no label]", "Unknown"]


class ExploreError(ValueError):
    """Raised when a query spec fails validation."""


def country_name(code: Optional[str]) -> Optional[str]:
    """Two-letter country code -> full name, falling back to the code itself."""
    if not code:
        return None
    try:
        country = pycountry.countries.get(alpha_2=code.upper())
        return country.name if country else code
    except (AttributeError, KeyError):
        return code


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def _is_int(value) -> bool:
    """True for real ints only — Python's bool is a subclass of int."""
    return isinstance(value, int) and not isinstance(value, bool)


def _validate_filter(filter_: Any) -> dict:
    if not isinstance(filter_, dict):
        raise ExploreError("Each filter must be an object")
    field = filter_.get("field")
    if field not in FIELD_DEFS:
        raise ExploreError(f"Unknown filter field: {field!r}")
    kind = FIELD_DEFS[field]["kind"]
    op = filter_.get("op")
    if op not in _KIND_OPS[kind]:
        raise ExploreError(f"Operator {op!r} is not valid for field {field!r}")
    value = filter_.get("value")

    if kind == "text":
        if op != "contains" or not isinstance(value, str) or not value.strip():
            raise ExploreError(f"Filter on {field!r} needs a non-empty text value")
        return {"field": field, "op": "contains", "value": value.strip()[:100]}

    if kind == "enum":
        if op != "eq" or not isinstance(value, str) or not value.strip():
            raise ExploreError(f"Filter on {field!r} needs a non-empty value")
        return {"field": field, "op": "eq", "value": value.strip()}

    if kind == "years":
        if (
            op != "overlaps"
            or not isinstance(value, list)
            or len(value) != 2
            or not all(_is_int(v) and _ERA_BOUNDS[0] <= v <= _ERA_BOUNDS[1] for v in value)
            or value[0] > value[1]
        ):
            raise ExploreError(
                f"Filter on {field!r} needs a [start, end] inclusive year range"
            )
        return {"field": field, "op": "overlaps", "value": [value[0], value[1]]}

    # kind == "range"
    lo, hi = _RANGE_BOUNDS[field]
    if op == "between":
        if not isinstance(value, list) or len(value) != 2:
            raise ExploreError(f"Filter on {field!r} needs a [min, max] range")
        low, high = value
        if low is not None and (not _is_int(low) or not lo <= low <= hi):
            raise ExploreError(f"{low!r} out of bounds for {field!r}")
        if high is not None and (not _is_int(high) or not lo <= high <= hi):
            raise ExploreError(f"{high!r} out of bounds for {field!r}")
        if low is None and high is None:
            raise ExploreError(f"Filter on {field!r} needs at least one bound")
        if low is not None and high is not None and low > high:
            raise ExploreError(f"Filter on {field!r} has inverted bounds")
        return {"field": field, "op": "between", "value": [low, high]}
    if not _is_int(value) or not lo <= value <= hi:
        raise ExploreError(f"{value!r} out of bounds for {field!r}")
    return {"field": field, "op": op, "value": value}


def _coerce_int(value: Any, name: str, lo: int, hi: int, default: int) -> int:
    if value is None:
        return default
    if isinstance(value, bool):
        raise ExploreError(f"{name} must be an integer")
    try:
        num = int(value)
    except (TypeError, ValueError):
        raise ExploreError(f"{name} must be an integer") from None
    return max(lo, min(hi, num))


def validate_spec(spec: Any) -> dict:
    """Validate a raw query spec; returns a normalized copy or raises ExploreError."""
    if not isinstance(spec, dict) or not spec:
        raise ExploreError("Query spec must be a non-empty object")

    group_by = spec.get("group_by", "artist")
    if group_by not in GROUP_BY_DEFS:
        raise ExploreError(f"Unknown group_by: {group_by!r}")
    metric = spec.get("metric", "count")
    if metric not in METRIC_DEFS:
        raise ExploreError(f"Unknown metric: {metric!r}")
    order = spec.get("order", "desc")
    if order not in ("desc", "asc"):
        raise ExploreError(f"Order must be 'desc' or 'asc', got {order!r}")

    filters = spec.get("filters", [])
    if not isinstance(filters, list):
        raise ExploreError("filters must be a list")
    if len(filters) > MAX_FILTERS:
        raise ExploreError(f"Too many filters (max {MAX_FILTERS})")

    return {
        "group_by": group_by,
        "metric": metric,
        "order": order,
        "min_items": _coerce_int(
            spec.get("min_items"), "min_items", MIN_ITEMS_MIN, MIN_ITEMS_MAX, MIN_ITEMS_MIN
        ),
        "limit": _coerce_int(
            spec.get("limit"), "limit", LIMIT_MIN, LIMIT_MAX, DEFAULT_LIMIT
        ),
        "filters": [_validate_filter(f) for f in filters],
    }


# ---------------------------------------------------------------------------
# Dimensions
# ---------------------------------------------------------------------------


def _dimension(group_by: str) -> dict:
    """
    Resolve a group-by key into the SQL columns to select/group and the
    metadata needed to render the result rows.

    Returns a dict with:
      cols: list of select expressions (dimension key, label, optional id)
      group_exprs: expressions to GROUP BY
      label_idx: index into cols giving the row label
      id_idx: index giving the entity id, or None
      table: "artist" | "label" | "genre" | None (which join is required)
      format: callable(raw_label) -> display label
      href: callable(id, label) -> detail href, or None
    """
    Release = models.Release
    Artist = models.Artist
    Label = models.Label
    Genre = models.Genre

    year_expr = extract("year", Release.listen_date).cast(Integer)
    month_expr = extract("month", Release.listen_date).cast(Integer)
    decade_expr = func.floor(Release.year / 10.0) * 10
    # Ratings are 0-100 (0-10 display); a perfect 100 must land in bucket 10,
    # not floor(10.0)+1 = 11. CASE is portable across Postgres and SQLite.
    bucket_expr = case((Release.rating >= 100, 9), else_=func.floor(Release.rating / 10.0)) + 1

    no_country = lambda v: country_name(v) or "—"
    identity = lambda v: v

    if group_by == "artist":
        return {
            "cols": [Artist.id, Artist.name],
            "group_exprs": [Artist.id, Artist.name],
            "label_idx": 1,
            "id_idx": 0,
            "table": "artist",
            "format": identity,
            "href": lambda id_, _label: f"/artist/{id_}",
            "placeholder_exclude": True,
        }
    if group_by == "label":
        return {
            "cols": [Label.id, Label.name],
            "group_exprs": [Label.id, Label.name],
            "label_idx": 1,
            "id_idx": 0,
            "table": "label",
            "format": identity,
            "href": lambda id_, _label: f"/label/{id_}",
            "placeholder_exclude": True,
        }
    if group_by == "genre":
        return {
            "cols": [Genre.id, Genre.name],
            "group_exprs": [Genre.id, Genre.name],
            "label_idx": 1,
            "id_idx": 0,
            "table": "genre",
            "format": identity,
            "href": None,
            "placeholder_exclude": False,
        }
    if group_by == "release_country":
        return {
            "cols": [Release.country, Release.country],
            "group_exprs": [Release.country],
            "label_idx": 1,
            "id_idx": None,
            "table": None,
            "format": no_country,
            "href": None,
            "placeholder_exclude": False,
        }
    if group_by == "artist_country":
        return {
            "cols": [Artist.country, Artist.country],
            "group_exprs": [Artist.country],
            "label_idx": 1,
            "id_idx": None,
            "table": "artist",
            "format": no_country,
            "href": None,
            "placeholder_exclude": False,
        }
    if group_by == "artist_type":
        return {
            "cols": [Artist.type, Artist.type],
            "group_exprs": [Artist.type],
            "label_idx": 1,
            "id_idx": None,
            "table": "artist",
            "format": lambda v: v or "—",
            "href": None,
            "placeholder_exclude": False,
        }
    if group_by == "release_year":
        return {
            "cols": [Release.year, Release.year],
            "group_exprs": [Release.year],
            "label_idx": 1,
            "id_idx": None,
            "table": None,
            "format": lambda v: str(int(v)),
            "href": None,
            "placeholder_exclude": False,
        }
    if group_by == "release_decade":
        return {
            "cols": [decade_expr, decade_expr],
            "group_exprs": [decade_expr],
            "label_idx": 1,
            "id_idx": None,
            "table": None,
            "format": lambda v: f"{int(v)}s",
            "href": None,
            "placeholder_exclude": False,
        }
    if group_by == "listen_year":
        return {
            "cols": [year_expr, year_expr],
            "group_exprs": [year_expr],
            "label_idx": 1,
            "id_idx": None,
            "table": None,
            "format": lambda v: str(int(v)),
            "href": None,
            "placeholder_exclude": False,
        }
    if group_by == "listen_month":
        return {
            "cols": [month_expr, month_expr],
            "group_exprs": [month_expr],
            "label_idx": 1,
            "id_idx": None,
            "table": None,
            "format": lambda v: MONTH_NAMES[int(v) - 1],
            "href": None,
            "placeholder_exclude": False,
        }
    if group_by == "rating_bucket":
        return {
            "cols": [bucket_expr, bucket_expr],
            "group_exprs": [bucket_expr],
            "label_idx": 1,
            "id_idx": None,
            "table": None,
            "format": lambda v: str(int(v)),
            "href": None,
            "placeholder_exclude": False,
        }
    raise ExploreError(f"Unreachable: unknown group_by {group_by!r}")


# ---------------------------------------------------------------------------
# Query building
# ---------------------------------------------------------------------------


def _rescale(value, multiplier: int):
    """Scale a display-unit range bound to storage units (rating, runtime)."""
    if isinstance(value, list):
        return [(v * multiplier) if v is not None else None for v in value]
    return value * multiplier


def _contains(value: str) -> str:
    """Escape a contains-filter so user %/_ are literal, not SQL wildcards."""
    escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _range_filter(query, column, value, op):
    if op == "between":
        lo, hi = value
        if lo is not None:
            query = query.filter(column >= lo)
        if hi is not None:
            query = query.filter(column <= hi)
        return query
    if op == "gte":
        return query.filter(column >= value)
    return query.filter(column <= value)


def _apply_filter(query, filter_: dict):
    """Add one validated filter to a Release-rooted query (joins pre-applied)."""
    Release = models.Release
    Artist = models.Artist
    Label = models.Label
    Genre = models.Genre
    field = filter_["field"]
    op = filter_["op"]
    value = filter_["value"]

    if field == "artist_name":
        return query.filter(Artist.name.ilike(_contains(value), escape="\\"))
    if field == "artist_country":
        return query.filter(Artist.country == value)
    if field == "artist_type":
        return query.filter(Artist.type == value)
    if field == "artist_active":
        start, end = value
        return query.filter(
            and_(
                extract("year", Artist.begin).cast(Integer) <= end,
                or_(
                    Artist.end.is_(None),
                    extract("year", Artist.end).cast(Integer) >= start,
                ),
            )
        )
    if field == "label_name":
        return query.filter(Label.name.ilike(_contains(value), escape="\\"))
    if field == "label_country":
        return query.filter(Label.country == value)
    if field == "label_type":
        return query.filter(Label.type == value)
    if field == "release_name":
        return query.filter(Release.name.ilike(_contains(value), escape="\\"))
    if field == "release_country":
        return query.filter(Release.country == value)
    if field == "genre":
        genre_ids = [
            rid
            for (rid,) in app_db.session.query(Genre.id).filter(Genre.name == value).all()
        ]
        if not genre_ids:
            # No genre matches, so nothing can satisfy this filter.
            return query.filter(false())
        return query.filter(
            or_(
                Release.main_genre_id.in_(genre_ids),
                Release.id.in_(
                    app_db.session.query(release_genre_association.c.release_id).filter(
                        release_genre_association.c.genre_id.in_(genre_ids)
                    )
                ),
            )
        )
    if field == "release_year":
        return _range_filter(query, Release.year, value, op)
    if field == "listen_year":
        return _range_filter(
            query, extract("year", Release.listen_date).cast(Integer), value, op
        )
    if field == "rating":
        # UI communicates in 0-10, storage is 0-100.
        return _range_filter(query, Release.rating, _rescale(value, 10), op)
    if field == "runtime":
        # UI communicates in minutes, storage is milliseconds.
        return _range_filter(query, Release.runtime, _rescale(value, 60000), op)
    raise ExploreError(f"Unreachable: unknown filter field {field!r}")


def _apply_dim_joins_and_filters(query, dim, filters: list[dict]):
    """Apply the dimension's join(s) + every filter to an aggregate query."""
    Release = models.Release
    Artist = models.Artist
    Label = models.Label
    Genre = models.Genre
    needs_artist = dim["table"] == "artist" or any(
        f["field"] in _ARTIST_FIELDS for f in filters
    )
    needs_label = dim["table"] == "label" or any(
        f["field"] in _LABEL_FIELDS for f in filters
    )
    needs_genre = dim["table"] == "genre"
    if needs_artist:
        query = query.join(Artist, Artist.id == Release.artist_id)
    if needs_label:
        query = query.join(Label, Label.id == Release.label_id)
    if needs_genre:
        query = query.join(Genre, Genre.id == Release.main_genre_id)
    for filter_ in filters:
        query = _apply_filter(query, filter_)
    if dim.get("placeholder_exclude"):
        model = Artist if dim["table"] == "artist" else Label
        query = query.filter(model.name.notin_(_PLACEHOLDER_NAMES))
    return query


def _period_count(filters: list[dict]) -> int:
    """Total releases matching the filters (no grouping), for share subtitles."""
    Release = models.Release
    query = app_db.session.query(Release.id)
    needs_artist = any(f["field"] in _ARTIST_FIELDS for f in filters)
    needs_label = any(f["field"] in _LABEL_FIELDS for f in filters)
    if needs_artist:
        query = query.join(models.Artist, models.Artist.id == Release.artist_id)
    if needs_label:
        query = query.join(models.Label, models.Label.id == Release.label_id)
    for filter_ in filters:
        query = _apply_filter(query, filter_)
    return query.count() or 0


# ---------------------------------------------------------------------------
# Row formatting
# ---------------------------------------------------------------------------


def _fmt_hours(hours: float) -> str:
    """Format a duration (in hours) as e.g. '1h 30m' or '45m'."""
    minutes = round(float(hours) * 60)
    h, m = divmod(minutes, 60)
    if h and m:
        return f"{h}h {m}m"
    if h:
        return f"{h}h"
    return f"{m}m"


def _build_row(metric, value, count, total, label, id_, href) -> dict:
    """Format one result row consistently with the existing stats aesthetic."""
    row = {
        "label": label or "—",
        "value": _metric_value(metric, value),
        "count": count or 0,
    }
    if id_ is not None and href is not None:
        row["id"] = id_
        row["href"] = href(id_, label)
    row["display"] = _metric_display(metric, value, count)
    row["sub"] = _metric_sub(metric, count, total)
    return row


def _metric_value(metric: str, value) -> float | int:
    if value is None:
        value = 0
    if metric in ("count", "distinct_artists"):
        return int(value)
    if metric == "runtime_hours":
        return round(float(value) / 3600000, 1)
    # avg_rating / bayes_rating are stored 0-100; present on the 0-10 scale.
    return round(float(value) / 10, 1)


def _metric_display(metric: str, value, count) -> str:
    if value is None:
        value = 0
    if metric in ("count", "distinct_artists"):
        return f"{int(value):,}"
    if metric == "runtime_hours":
        return _fmt_hours(float(value) / 3600000)
    return f"{round(float(value) / 10, 1):.1f} / 10"


def _metric_sub(metric: str, count: int, total: int) -> Optional[str]:
    if metric == "count":
        return f"{round(count / total * 100) if total else 0}% of matched"
    if metric == "distinct_artists":
        return f"{count:,} release{'s' if count != 1 else ''}"
    return f"{count:,} release{'s' if count != 1 else ''}"


def _meta(spec: dict, total: int, group_total: int) -> dict:
    return {
        "total_matched": total,
        "total_groups": group_total,
        "dimension_label": GROUP_BY_DEFS[spec["group_by"]]["label"],
        "metric_label": METRIC_DEFS[spec["metric"]]["label"],
        "order": spec["order"],
        "group_by": spec["group_by"],
        "metric": spec["metric"],
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def run_query(spec: dict) -> dict:
    """Run a validated query spec and produce rows for the frontend charts."""
    spec = validate_spec(spec)
    metric = spec["metric"]
    total = _period_count(spec["filters"])

    if metric == "bayes_rating":
        return _run_bayes(spec, total)
    return _run_sql(spec, total)


def _run_sql(spec: dict, total: int) -> dict:
    """SQL path for every metric except bayes_rating."""
    Release = models.Release
    dim = _dimension(spec["group_by"])
    metric_cols, count_idx = _metric_cols(spec["metric"])

    query = app_db.session.query(*dim["cols"], *metric_cols)
    query = _apply_dim_joins_and_filters(query, dim, spec["filters"])
    query = query.group_by(*dim["group_exprs"])
    if spec["min_items"] > MIN_ITEMS_MIN:
        query = query.having(func.count(Release.id) >= spec["min_items"])

    # True group count (after filters + HAVING, before LIMIT) for the meta.
    group_total = query.count()

    sort_col = metric_cols[0]
    order = sort_col.desc() if spec["order"] == "desc" else sort_col.asc()
    rows = (
        query.order_by(order, dim["cols"][dim["label_idx"]].asc())
        .limit(spec["limit"])
        .all()
    )

    out = []
    for row in rows:
        label = dim["format"](row[dim["label_idx"]])
        metric_value = row[len(dim["cols"])]
        count = (
            row[len(dim["cols"]) + count_idx]
            if count_idx is not None
            else metric_value
        )
        out.append(
            _build_row(
                metric=spec["metric"],
                value=metric_value,
                count=count,
                total=total,
                label=label,
                id_=row[dim["id_idx"]] if dim["id_idx"] is not None else None,
                href=dim["href"],
            )
        )
    return {"rows": out, "meta": _meta(spec, total, group_total)}


def _run_bayes(spec: dict, total: int) -> dict:
    """Bayesian-average path: per-group count+avg in SQL, weighting in Python."""
    Release = models.Release
    dim = _dimension(spec["group_by"])
    query = app_db.session.query(
        *dim["cols"], func.count(Release.id), func.avg(Release.rating)
    )
    query = _apply_dim_joins_and_filters(query, dim, spec["filters"])
    query = query.group_by(*dim["group_exprs"])
    if spec["min_items"] > MIN_ITEMS_MIN:
        query = query.having(func.count(Release.id) >= spec["min_items"])

    groups = []
    for row in query.all():
        label = dim["format"](row[dim["label_idx"]])
        count = row[len(dim["cols"])]
        avg = row[len(dim["cols"]) + 1]
        if count and avg is not None:
            groups.append(
                {
                    "label": label,
                    "count": int(count),
                    "avg": float(avg),  # Postgres returns Decimal
                    "id": row[dim["id_idx"]] if dim["id_idx"] is not None else None,
                }
            )

    if not groups:
        return {"rows": [], "meta": _meta(spec, total, 0)}
    group_total = len(groups)

    mean_avg = sum(g["avg"] for g in groups) / len(groups)
    mean_count = sum(g["count"] for g in groups) / len(groups)
    for g in groups:
        weight = g["count"] / (g["count"] + mean_count)
        g["bayes"] = weight * g["avg"] + (1 - weight) * mean_avg

    groups.sort(
        key=lambda g: (g["bayes"], g["label"]),
        reverse=spec["order"] == "desc",
    )
    groups = groups[: spec["limit"]]

    out = [
        _build_row(
            metric="bayes_rating",
            value=g["bayes"],
            count=g["count"],
            total=total,
            label=g["label"],
            id_=g["id"],
            href=dim["href"],
        )
        for g in groups
    ]
    return {"rows": out, "meta": _meta(spec, total, group_total)}


def _metric_cols(metric: str) -> tuple[list, Optional[int]]:
    """
    Aggregate expressions for a non-Bayesian metric, plus the index of the
    per-group release count within them (for the row subtitle). The count
    column is omitted when the metric is itself a count.
    """
    Release = models.Release
    if metric == "count":
        return [func.count(Release.id)], None
    if metric == "distinct_artists":
        return [func.count(func.distinct(Release.artist_id)), func.count(Release.id)], 1
    if metric == "avg_rating":
        return [func.avg(Release.rating), func.count(Release.id)], 1
    if metric == "runtime_hours":
        return [func.sum(Release.runtime), func.count(Release.id)], 1
    raise ExploreError(f"Unreachable: unknown metric {metric!r}")


# ---------------------------------------------------------------------------
# Builder options (facet values + field/dimension/metric descriptors)
# ---------------------------------------------------------------------------


def explore_options() -> dict:
    """Everything the query builder needs: field descriptors + option lists."""
    Release = models.Release
    Artist = models.Artist
    Label = models.Label
    Genre = models.Genre

    def country_pairs(model) -> list[list[str]]:
        codes = sorted(c for c in model.get_distinct_column_values("country") if c)
        return [[c, country_name(c)] for c in codes]

    release_years = (
        app_db.session.query(func.min(Release.year), func.max(Release.year)).one()
    )
    listen_row = (
        app_db.session.query(
            func.min(extract("year", Release.listen_date).cast(Integer)),
            func.max(extract("year", Release.listen_date).cast(Integer)),
        ).one()
    )

    fields = [
        {
            "value": key,
            "label": info["label"],
            "kind": info["kind"],
            "options": info.get("options"),
        }
        for key, info in FIELD_DEFS.items()
    ]

    return {
        "fields": fields,
        "group_bys": [
            {"value": key, "label": info["label"]} for key, info in GROUP_BY_DEFS.items()
        ],
        "metrics": [
            {"value": key, "label": info["label"]} for key, info in METRIC_DEFS.items()
        ],
        "options": {
            "artist_countries": country_pairs(Artist),
            "label_countries": country_pairs(Label),
            "release_countries": country_pairs(Release),
            "artist_types": sorted(
                t for t in Artist.get_distinct_column_values("type") if t
            ),
            "label_types": sorted(
                t for t in Label.get_distinct_column_values("type") if t
            ),
            "genres": sorted(Genre.get_distinct_column_values("name")),
        },
        "bounds": {
            "release_year": [release_years[0] or 1500, release_years[1] or 2100],
            "listen_year": [listen_row[0] or 1970, listen_row[1] or 2100],
            "rating": [1, 10],
            "runtime": [5, 600],
        },
        "defaults": {
            "group_by": "artist",
            "metric": "bayes_rating",
            "min_items": 2,
            "order": "desc",
            "limit": DEFAULT_LIMIT,
        },
    }