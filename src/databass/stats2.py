"""
Aggregation layer for the Stats page.

Combines the period-aware query methods on `Release`/`Artist`/`Label`
with pure-Python "listening rhythm" facts (busiest day, longest streak, etc)
that are cheaper to compute in Python than in SQL.
"""

from collections import Counter
from datetime import date
from typing import Optional

from .db import models

WEEKDAY_NAMES = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]


def _resolve_year(period: str) -> Optional[int]:
    if not period or period == "all":
        return None
    try:
        return int(period)
    except ValueError:
        return None


def _busiest_weekday(dates: list[date]) -> str:
    if not dates:
        return "-"
    counts = Counter(d.weekday() for d in dates)
    top_day, _ = max(counts.items(), key=lambda kv: kv[1])
    return WEEKDAY_NAMES[top_day]


def _longest_streak(dates: list[date]) -> int:
    unique_sorted = sorted(set(dates))
    if not unique_sorted:
        return 0
    longest = current = 1
    for prev_day, curr_day in zip(unique_sorted, unique_sorted[1:]):
        if (curr_day - prev_day).days == 1:
            current += 1
            longest = max(longest, current)
        else:
            current = 1
    return longest


def _longest_gap(dates: list[date]) -> int:
    unique_sorted = sorted(set(dates))
    if len(unique_sorted) < 2:
        return 0
    return max((b - a).days for a, b in zip(unique_sorted, unique_sorted[1:]))


def _days_since_last(dates: list[date]) -> int:
    if not dates:
        return 0
    return (date.today() - max(dates)).days


def available_periods() -> list[dict]:
    """Period switcher options: the two most recent years with data, plus all time."""
    years = models.Release.listen_years()
    periods = [{"key": str(year), "label": str(year)} for year in years[:2]]
    periods.append({"key": "all", "label": "all time"})
    return periods


def get_period_stats(period: str = "all") -> dict:
    """
    Assemble every period-dependent figure shown on the Stats page:
    the KPI strip, the "when you listen" chart, rhythm facts, and the
    rating histogram/summary. Leaderboards and genre shares are all-time
    only and are not part of this function.
    """
    year = _resolve_year(period)
    Release = models.Release
    Artist = models.Artist
    Label = models.Label

    summary = Release.stats_for_year(year)
    count = summary["count"]
    days_span = Release.days_span(year)
    pace = round(count / days_span, 2)
    avg_min_per_day = round((summary["runtime_hours"] * 60) / days_span)

    artist_stats = Artist.period_counts(year)
    label_stats = Label.period_counts(year)

    dist = Release.rating_distribution(year)
    buckets = dist["buckets"]
    total_ratings = sum(buckets)
    high_share = (
        round(sum(buckets[8:]) / total_ratings * 100, 1) if total_ratings else 0.0
    )
    low_share = (
        round(sum(buckets[:4]) / total_ratings * 100, 1) if total_ratings else 0.0
    )
    hist_max = max(buckets) if buckets else 0
    histogram = [
        {
            "h": round((count_in_bucket / hist_max) * 100) if hist_max else 0,
            "is_peak": hist_max > 0 and count_in_bucket == hist_max,
        }
        for count_in_bucket in buckets
    ]

    if year is not None:
        series_raw = Release.listens_by_month(year)
        prev_count = Release.stats_for_year(year - 1)["count"]
        if prev_count:
            pct = round((count - prev_count) / prev_count * 100)
            sign = "+" if pct >= 0 else ""
            releases_sub = f"{sign}{pct}% vs {year - 1}"
        else:
            releases_sub = "first year logged" if count else "no listens logged"
        chart_note = "releases logged per month"
    else:
        series_raw = Release.listens_by_year()
        num_years = len(Release.listen_years())
        releases_sub = f"across {num_years} year{'s' if num_years != 1 else ''}"
        chart_note = "releases logged per year"

    series_values = [b["value"] for b in series_raw]
    series_max = max(series_values) if series_values else 0
    series = [
        {
            "label": b["label"],
            "value": b["value"],
            "h": round((b["value"] / series_max) * 100) if series_max else 0,
            "is_peak": series_max > 0 and b["value"] == series_max,
        }
        for b in series_raw
    ]

    dates = Release.listen_dates(year)
    peak_idx = series_values.index(series_max) if series_max else None
    if year is not None:
        busiest_label = "BUSIEST MONTH"
        busiest_value = (
            f"{series[peak_idx]['label'].title()} — {series_max}"
            if peak_idx is not None
            else "-"
        )
        gap_label = "QUIETEST STRETCH"
        gap_value = f"{_longest_gap(dates)} days"
    else:
        busiest_label = "BUSIEST YEAR"
        busiest_value = (
            f"{series[peak_idx]['label']} — {series_max}"
            if peak_idx is not None
            else "-"
        )
        gap_label = "LAST GAP"
        gap_value = f"{_days_since_last(dates)} days"

    rhythm = [
        {"label": busiest_label, "value": busiest_value},
        {"label": "BUSIEST DAY", "value": _busiest_weekday(dates)},
        {"label": "LONGEST STREAK", "value": f"{_longest_streak(dates)} days"},
        {"label": gap_label, "value": gap_value},
    ]

    kpis = [
        {"label": "RELEASES", "value": f"{count:,}", "sub": releases_sub},
        {
            "label": "ARTISTS",
            "value": f"{artist_stats['count']:,}",
            "sub": f"{artist_stats['avg_releases']:g} releases each",
        },
        {
            "label": "LABELS",
            "value": f"{label_stats['count']:,}",
            "sub": f"{label_stats['avg_releases']:g} releases each",
        },
        {
            "label": "LISTENING TIME",
            "value": f"{summary['runtime_hours']:g}h",
            "sub": f"{avg_min_per_day:g}m / day",
        },
        {
            "label": "MEAN SCORE",
            "value": f"{summary['mean_rating']:.1f}",
            "sub": f"median {dist['median']:.1f}",
        },
        {
            "label": "PACE",
            "value": f"{pace:.2f}/d",
            "sub": f"{count:,} over {days_span:,}d",
        },
    ]

    return {
        "kpis": kpis,
        "chart_note": chart_note,
        "series": series,
        "rhythm": rhythm,
        "histogram": histogram,
        "mean": f"{summary['mean_rating']:.1f}",
        "median": f"{dist['median']:.1f}",
        "high_share": f"{high_share:g}%",
        "low_share": f"{low_share:g}%",
    }


def _bar_rows(names: list[str], values: list[float], formatter) -> list[dict]:
    top = max(values) if values else 0
    return [
        {
            "rank": i + 1,
            "name": name,
            "w": round(value / top * 100) if top else 0,
            "value": formatter(value),
        }
        for i, (name, value) in enumerate(zip(names, values))
    ]


def build_leaderboards(entity, limit: int = 8) -> list[dict]:
    """
    All-time leaderboards ("most frequent", "highest average", "favourites")
    for the given entity class (Artist or Label).
    """
    frequent = entity.frequency_highest(limit)
    highest_avg = entity.average_ratings_and_total_counts()[:limit]
    favourites = entity.average_ratings_bayesian()[:limit]

    return [
        {
            "title": "Most frequent",
            "note": "by releases logged",
            "rows": _bar_rows(
                [item["name"] for item in frequent],
                [item["count"] for item in frequent],
                lambda v: f"{v} rel",
            ),
        },
        {
            "title": "Highest average",
            "note": "simple mean of your scores — thin on low-release entries",
            "rows": _bar_rows(
                [row.name for row in highest_avg],
                [row.average_rating for row in highest_avg],
                lambda v: f"{v / 10:.1f} / 10",
            ),
        },
        {
            "title": "Favourites",
            "note": "Bayesian average — weights score by how much you've actually logged",
            "rows": _bar_rows(
                [item["name"] for item in favourites],
                [item["rating"] for item in favourites],
                lambda v: f"{v / 10:.1f} / 10",
            ),
        },
    ]


def get_genre_shares(limit: int = 6) -> list[dict]:
    """All-time genre shares for the "what you listen to" section."""
    top = models.Genre.top_by_release_count(limit)
    if not top:
        return []
    total = models.Release.total_count()
    max_count = top[0]["count"]
    return [
        {
            "name": genre["name"],
            "value": f"{genre['count']:,} · {round(genre['count'] / total * 100) if total else 0}%",
            "w": round(genre["count"] / max_count * 100) if max_count else 0,
        }
        for genre in top
    ]
