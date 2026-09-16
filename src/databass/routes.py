"""
Implements the main routes for the databass application, including
- home page
- new release page
- stats page
- goals page
"""

from datetime import datetime, timedelta, date
from typing import Optional
from os.path import join, abspath
from glob import glob
from itertools import groupby
import flask
from flask import (
    render_template,
    request,
    redirect,
    abort,
    flash,
    make_response,
    send_file,
    jsonify,
)
from sqlalchemy.exc import IntegrityError
import pycountry
from .api import Util, MusicBrainz
from . import db
from .db import models
from .db.util import handle_submit_data
from .errors.util import friendly_message, integrity_error_message
from .pagination import Pager
from . import stats2


def image_exists(itemtype: str, itemid: int) -> bool:
    """Check whether a downloaded cover/artist/label image exists on disk."""
    img_dir = abspath(join("databass", "static", "img", itemtype))
    return bool(glob(join(img_dir, f"{itemid}.*")))


def initials(name: Optional[str], max_len: int = 4) -> str:
    """Derive an art-placeholder initials string, e.g. 'Sunn O)))' -> 'SO'."""
    if not name:
        return "?"
    letters = "".join(word[0] for word in name.split() if word)
    return letters[:max_len].upper() or "?"


def format_runtime(runtime_ms: Optional[int]) -> str:
    """Format a runtime in milliseconds as e.g. '1h 20m' or '54m'."""
    minutes = round((runtime_ms or 0) / 60000)
    hours, remainder = divmod(minutes, 60)
    if hours:
        return f"{hours}h {remainder}m" if remainder else f"{hours}h"
    return f"{minutes}m"


def day_label(day, today) -> str:
    """Format a day-group heading, e.g. 'TODAY · SAT 12 SEP'."""
    diff = (today - day).days
    weekday_month = day.strftime("%a %d %b").upper()
    if diff == 0:
        return f"TODAY · {weekday_month}"
    if diff == 1:
        return f"YESTERDAY · {weekday_month}"
    return f"{weekday_month} · {diff}D AGO"


def build_entry(release: models.Release) -> dict:
    """Build the template-ready dict for a single home-page entry row."""
    latest_review = release.reviews[0] if release.reviews else None
    subgenres = [g.name for g in release.genres if g.id != release.main_genre_id]
    return {
        "id": release.id,
        "title": release.name,
        "year": release.year,
        "artist": {"id": release.artist.id, "name": release.artist.name}
        if release.artist
        else None,
        "label": {"id": release.label.id, "name": release.label.name}
        if release.label
        else None,
        "main_genre": release.main_genre.name if release.main_genre else None,
        "subgenres": subgenres,
        "note": latest_review.text if latest_review else None,
        "rating": release.rating,
        "score": round(release.rating / 10, 1),
        "runtime": format_runtime(release.runtime),
        "track_count": release.track_count,
        "art_key": initials(release.artist.name if release.artist else release.name),
        "has_art": image_exists("release", release.id),
    }


def build_day_groups(rows: list) -> list[dict]:
    """
    Group lightweight (id, listen_date, runtime) rows by listen date (newest
    first) for the home page feed, without touching any relationships.

    Returns:
        list[dict]: Each dict has "label" (e.g. "TODAY · SAT 12 SEP"), "meta"
        (e.g. "2 releases · 1h 20m"), and "ids" (release IDs in that group).
    """
    today = datetime.now().date()
    ordered = sorted(rows, key=lambda r: (r.listen_date, r.id), reverse=True)
    groups = []
    for day, day_rows in groupby(ordered, key=lambda r: r.listen_date.date()):
        day_rows = list(day_rows)
        total_minutes = round(sum(r.runtime or 0 for r in day_rows) / 60000)
        noun = "release" if len(day_rows) == 1 else "releases"
        hours, minutes = divmod(total_minutes, 60)
        duration = f"{hours}h {minutes}m" if hours else f"{minutes}m"
        groups.append(
            {
                "label": day_label(day, today),
                "meta": f"{len(day_rows)} {noun} · {duration}",
                "ids": [r.id for r in day_rows],
            }
        )
    return groups


def get_manual_release_data(data) -> dict:
    """
    Parses search form data for release information that was manually submitted
    """
    genres = data.get("genres")
    image = data.get("image")
    runtime_ms = data.get("runtime", 0)
    runtime = int(runtime_ms) * 60000
    track_count = data.get("track_count", 0)
    track_count = int(track_count)

    country = country_code(data.get("country"))

    return {
        "name": data.get("name"),
        "mbid": None,
        "artist_name": data.get("artist"),
        "artist_mbid": None,
        "label_name": data.get("label"),
        "label_mbid": None,
        "year": data.get("year"),
        "main_genre": data.get("main_genre"),
        "rating": data.get("rating"),
        "genres": genres,
        "image": image,
        "listen_date": Util.to_date(None, data.get("listen_date") or Util.today()),
        "runtime": runtime,
        "track_count": track_count,
        "country": country,
        "release_group_mbid": None,
        "note": data.get("note") or None,
    }


def get_release_data(data) -> dict:
    """
    Parses search form data for release information returned by MusicBrainz
    """
    year = data.get("year")
    if year is None:
        year = 0

    return {
        "release_group_mbid": data.get("release_group_id"),
        "name": data.get("release_name"),
        "mbid": data.get("release_mbid"),
        "artist_name": data.get("artist"),
        "artist_mbid": data.get("artist_mbid"),
        "label_name": data.get("label"),
        "label_mbid": data.get("label_mbid"),
        "year": int(year),
        "main_genre": data.get("main_genre"),
        "rating": int(data.get("rating")),
        "track_count": data.get("track_count"),
        "listen_date": Util.to_date(None, data.get("listen_date") or Util.today()),
        "country": data.get("country"),
        "genres": data.get("genres"),
        "image": None,
        "note": data.get("note") or None,
    }


def browse_filter_options(tab: str) -> dict:
    """Distinct facet values available for the Browse page's given tab."""
    if tab == "releases":
        countries = sorted(c for c in models.Release.get_distinct_column_values("country") if c)
        genres = sorted(models.Genre.get_distinct_column_values("name"))
        return {
            "countries": [(c, country_name(c)) for c in countries],
            "genres": genres,
        }
    model = models.Artist if tab == "artists" else models.Label
    countries = sorted(c for c in model.get_distinct_column_values("country") if c)
    types = sorted(t for t in model.get_distinct_column_values("type") if t)
    return {
        "countries": [(c, country_name(c)) for c in countries],
        "types": types,
    }


def build_browse_release_item(release: models.Release) -> dict:
    """Build the template-ready dict for one Browse grid/list item (releases tab)."""
    artist_name = release.artist.name if release.artist else None
    meta = " · ".join(filter(None, [artist_name, str(release.year) if release.year else None]))
    return {
        "id": release.id,
        "href": f"/release/{release.id}",
        "name": release.name,
        "meta": meta,
        "score": round(release.rating / 10, 1),
        "art_key": initials(artist_name or release.name),
        "has_art": image_exists("release", release.id),
        "art_type": "release",
    }


def build_browse_entity_item(row, entity_type: str) -> dict:
    """Build the template-ready dict for one Browse grid/list item (artists/labels tab)."""
    return {
        "id": row.id,
        "href": f"/{entity_type}/{row.id}",
        "name": row.name,
        "meta": f"{row.release_count} release{'s' if row.release_count != 1 else ''} · {country_name(row.country) or '—'}",
        "score": round((row.average_rating or 0) / 10, 1),
        "art_key": initials(row.name),
        "has_art": image_exists(entity_type, row.id),
        "art_type": entity_type,
    }


def _home_payload() -> dict:
    """Shared data for the home page and its /api/home counterpart."""
    active_goals = models.Goal.get_incomplete()
    goal = None
    if active_goals:
        goal = process_goal_data(active_goals[0])
        current_pace = models.Release.added_per_day_this_year()
        goal["on_track"] = current_pace >= goal["target"]

    this_year = {
        "count": models.Release.added_this_year(),
        "new_artists": models.Artist.added_this_year(),
        "new_labels": models.Label.added_this_year(),
        "listening_time": models.Release.runtime_this_year(),
        "average_score": round(models.Release.average_rating_this_year() / 10, 1),
        "pace": models.Release.added_per_day_this_year(),
    }

    distribution = models.Release.rating_distribution()
    max_bucket = max(distribution["buckets"]) or 1
    score_spread = [
        {
            "pct": round((count / max_bucket) * 100),
            "is_peak": count == max_bucket and count > 0,
        }
        for count in distribution["buckets"]
    ]

    on_repeat = models.Artist.on_repeat(days=90, limit=3)
    for entity in on_repeat:
        entity["has_art"] = image_exists("artist", entity["id"])
        entity["art_key"] = initials(entity["name"])

    return {
        "this_year": this_year,
        "goal": goal,
        "score_spread": score_spread,
        "median_score": distribution["median"],
        "on_repeat": on_repeat,
    }


def _home_entries_payload() -> tuple[list[dict], "Pager"]:
    """Shared data for the home release feed and its /api/home/entries counterpart."""
    rows = models.Release.home_data_light()
    groups = build_day_groups(rows)

    page = Pager.get_page_param(request)
    paged_groups, flask_pagination = Pager.paginate(
        per_page=4, current_page=page, data=groups
    )

    # Only hydrate full entries (with relationships + art lookups) for
    # releases on the current page, rather than the whole library.
    page_ids = [id_ for group in paged_groups for id_ in group["ids"]]
    releases_by_id = {r.id: r for r in models.Release.by_ids(page_ids)}
    for group in paged_groups:
        group["items"] = [
            build_entry(releases_by_id[id_])
            for id_ in group["ids"]
            if id_ in releases_by_id
        ]

    return paged_groups, flask_pagination


def _new_payload() -> dict:
    """Shared data for the new-release page and its /api/new counterpart."""
    all_genres = sorted(models.Genre.get_distinct_column_values("name"))
    goal_nudge = None
    active_goals = models.Goal.get_incomplete()
    if active_goals:
        g_data = process_goal_data(active_goals[0])
        remaining = max(g_data["amount"] - g_data["current"], 0)
        goal_nudge = f"{remaining} to go on your {g_data['end'].year} {g_data['type']} goal"
    return {"all_genres": all_genres, "goal_nudge": goal_nudge}


def _search_results(data: dict) -> list[dict] | None:
    """
    Shared search logic for /search and /api/search: returns the annotated
    MusicBrainz results, or None if the request didn't include a search term.
    """
    search_release = data.get("release")
    search_artist = data.get("artist")
    search_label = data.get("label")
    if search_release is None and search_artist is None and search_label is None:
        return None

    release_data = MusicBrainz.release_search(
        release=search_release, artist=search_artist, label=search_label
    )
    results = []
    for item in release_data:
        mbid = item["release"].get("mbid")
        logged = bool(mbid and models.Release.exists_by_mbid(mbid))
        artist_name = item["artist"].get("name") or item["release"].get("name") or ""
        results.append({**item, "logged": logged, "initials": initials(artist_name)})
    return results


def _browse_results_payload(tab: str) -> dict:
    """Shared data for /browse/<tab>/results and its /api counterpart."""
    q = request.args.get("q", "").strip()
    country = request.args.get("country", "")
    rating_min = request.args.get("rating_min", type=int)
    page = max(request.args.get("page", 1, type=int), 1)
    per_page = 30

    if tab == "releases":
        sort = request.args.get("sort", "listened")
        genre = request.args.get("genre", "")
        year_min = request.args.get("year_min", type=int)
        rows, total = models.Release.browse_search(
            q=q,
            country=country,
            genre=genre,
            year_min=year_min,
            rating_min=rating_min * 10 if rating_min else None,
            sort=sort,
            page=page,
            per_page=per_page,
        )
        items = [build_browse_release_item(r) for r in rows]
    else:
        model = models.Artist if tab == "artists" else models.Label
        sort = request.args.get("sort", "releases")
        type_ = request.args.get("type", "")
        releases_min = request.args.get("releases_min", type=int)
        rows, total = model.browse_search(
            q=q,
            country=country,
            type_=type_,
            releases_min=releases_min,
            rating_min=rating_min * 10 if rating_min else None,
            sort=sort,
            page=page,
            per_page=per_page,
        )
        items = [build_browse_entity_item(r, tab[:-1]) for r in rows]

    total_pages = max(-(-total // per_page), 1)
    return {"items": items, "total": total, "page": page, "total_pages": total_pages}


def _goals_payload() -> dict:
    """Shared data for the goals page and its /api/goals counterpart."""
    incomplete_goals = models.Goal.get_incomplete() or []
    # An incomplete goal past its end date is missed, not active; get_past()
    # already surfaces it there, so exclude it here to avoid double-counting
    # it as an in-progress goal with no upper bound on its current_amount.
    current_incomplete_goals = [
        g for g in incomplete_goals if g.end >= datetime.now()
    ]
    active_goal = (
        build_active_goal_view(current_incomplete_goals[0])
        if current_incomplete_goals
        else None
    )
    past_goals = [build_past_goal_view(g) for g in models.Goal.get_past()]

    today_date = datetime.now().date()
    next_new_year = date(today_date.year + 1, 1, 1)
    goal_presets = [
        {
            "label": "365 in a year",
            "amount": 365,
            "end": (today_date + timedelta(days=365)).isoformat(),
        },
        {
            "label": "100 by new year",
            "amount": 100,
            "end": next_new_year.isoformat(),
        },
        {
            "label": "1000 in a year",
            "amount": 1000,
            "end": (today_date + timedelta(days=365)).isoformat(),
        },
    ]
    goal_types = [
        {"value": "release", "label": "releases"},
        {"value": "artist", "label": "artists"},
        {"value": "label", "label": "labels"},
    ]

    return {
        "active_goal": active_goal,
        "past_goals": past_goals,
        "current_pace": models.Release.added_per_day_this_year(),
        "today": Util.today(),
        "default_amount": 100,
        "default_end": (today_date + timedelta(days=90)).isoformat(),
        "goal_presets": goal_presets,
        "goal_types": goal_types,
    }


def _construct_goal_or_error(data: dict) -> tuple["models.Goal | None", str | None]:
    """Shared goal-construction logic for /add_goal and /api/goals (POST)."""
    try:
        goal = db.construct_item(model_name="goal", data_dict=data)
        if not goal:
            raise NameError("Construction of Goal object failed")
    except Exception as e:  # pylint: disable=broad-exception-caught
        return None, friendly_message(e)
    return goal, None


def register_routes(app):
    @app.route("/", methods=["GET"])
    @app.route("/home", methods=["GET"])
    def home() -> str:
        return render_template("index.html", active_page="home", **_home_payload())

    @app.route("/home_release_table")
    def home_release_table():
        paged_groups, flask_pagination = _home_entries_payload()
        return render_template(
            "home_release_table.html",
            groups=paged_groups,
            pagination=flask_pagination,
        )

    @app.route("/new")
    def new():
        q = request.args.get("q", "").strip()
        return render_template(
            "new.html",
            active_page="new",
            q=q,
            today=Util.today(),
            **_new_payload(),
        )

    @app.route("/search", methods=["POST", "GET"])
    def search() -> str | flask.Response:
        if request.method == "GET":
            return render_template("new_manual_entry.html")

        results = _search_results(request.get_json())
        if results is None:
            flash("ERROR: Search requires at least one search term")
            return redirect("/error")

        return render_template("new_search_results.html", data=results)

    @app.route("/submit", methods=["POST"])
    def submit():
        data = request.form.to_dict()
        release_data = {}
        match data.get("manual_submit"):
            case "true":
                release_data = get_manual_release_data(data)
            case "false":
                release_data = get_release_data(data)

        try:
            completed_goals = handle_submit_data(release_data)
        except IntegrityError as err:
            flash(integrity_error_message(err))
            return redirect("/error")
        except Exception as err:
            flash(friendly_message(err))
            return redirect("/error")

        if completed_goals:
            flash(
                f"Goal completed: {completed_goals[0].amount} "
                f"{_goal_type_label(completed_goals[0].type)} in {completed_goals[0].end.year}"
            )
        return redirect("/", code=302)

    @app.route("/browse")
    @app.route("/browse/<string:tab>")
    def browse(tab="releases"):
        if tab not in ("releases", "artists", "labels"):
            abort(404)
        counts = {
            "releases": models.Release.total_count(),
            "artists": models.Artist.total_count(),
            "labels": models.Label.total_count(),
        }
        return render_template(
            "browse.html",
            active_page="browse",
            tab=tab,
            counts=counts,
            filters=browse_filter_options(tab),
        )

    @app.route("/browse/<string:tab>/results")
    def browse_results(tab):
        if tab not in ("releases", "artists", "labels"):
            abort(404)
        return render_template(
            "browse_results.html", tab=tab, **_browse_results_payload(tab)
        )

    @app.route("/stats", methods=["GET"])
    def stats():
        periods = stats2.available_periods()
        period = request.args.get("period") or (periods[0]["key"] if periods else "all")
        return render_template(
            "stats.html",
            periods=periods,
            active_period=period,
            stats=stats2.get_period_stats(period),
            genres=stats2.get_genre_shares(),
            active_page="stats",
        )

    @app.route("/stats/period/<string:period>", methods=["GET"])
    def stats_period(period):
        return render_template("stats_period.html", stats=stats2.get_period_stats(period))

    @app.route("/stats/get/<string:stats_type>", methods=["GET"])
    def stats_get(stats_type):
        entity = models.Label if stats_type == "labels" else models.Artist
        boards = stats2.build_leaderboards(entity)
        return render_template("stats_data.html", type=stats_type, boards=boards)

    @app.route("/goals", methods=["GET"])
    def goals():
        if request.method != "GET":
            abort(405)
        return render_template("goals.html", active_page="goals", **_goals_payload())

    @app.route("/add_goal", methods=["POST"])
    def add_goal():
        data = request.form.to_dict()
        if not data:
            # TODO: move this error handling into errors/routes.py
            flash("/add_goal received an empty payload")
            return redirect("/error")
        goal, error = _construct_goal_or_error(data)
        if error:
            # TODO: move this error handling into errors/routes.py
            flash(error)
            return redirect("/error")

        db.insert(goal)
        return redirect("/goals", 302)

    @app.route("/img/<string:itemtype>/<int:itemid>", methods=["GET"])
    def serve_image(itemtype: str, itemid: int):
        match itemtype:
            case "artist":
                item = models.Artist.exists_by_id(itemid)
            case "label":
                item = models.Label.exists_by_id(itemid)
            case "release":
                item = models.Release.exists_by_id(itemid)
            case _:
                return
        img_dir = abspath(join("databass", "static", "img", itemtype))
        img_pattern = join(img_dir, f"{item.id}.*")
        img_match = glob(img_pattern)
        if img_match:
            img_path = img_match[0]
        else:
            img_path = "./static/img/none.png"
        resp = make_response(send_file(img_path))
        resp.headers["Cache-Control"] = "max-age=600"
        return resp

    # ---------------------------------------------------------------
    # JSON API for the SvelteKit frontend. Mirrors the routes above;
    # once the frontend migration is complete, the render_template
    # routes above (and their fragment/htmx-style endpoints) will be
    # removed in favour of these.
    # ---------------------------------------------------------------

    @app.route("/api/home", methods=["GET"])
    def api_home():
        payload = _home_payload()
        if payload["goal"]:
            payload["goal"]["start"] = payload["goal"]["start"].isoformat()
            payload["goal"]["end_year"] = payload["goal"]["end"].year
            payload["goal"]["end"] = payload["goal"]["end"].isoformat()

        return jsonify(
            {
                **payload,
                "total_logged": flask.g.total_logged,
                "day_of_year": flask.g.day_of_year,
                "current_year": flask.g.current_year,
            }
        )

    @app.route("/api/home/entries", methods=["GET"])
    def api_home_entries():
        page = Pager.get_page_param(request)
        paged_groups, flask_pagination = _home_entries_payload()
        for group in paged_groups:
            del group["ids"]

        return jsonify(
            {
                "groups": paged_groups,
                "has_next": flask_pagination.has_next,
                "page": page,
            }
        )

    @app.route("/api/new", methods=["GET"])
    def api_new():
        return jsonify(
            {
                **_new_payload(),
                "today": Util.today(),
                "total_logged": flask.g.total_logged,
            }
        )

    @app.route("/api/search", methods=["POST"])
    def api_search():
        data = request.get_json() or {}
        results = _search_results(data)
        if results is None:
            return jsonify({"error": "Search requires at least one search term"}), 400

        return jsonify({"results": results})

    @app.route("/api/submit", methods=["POST"])
    def api_submit():
        data = request.get_json() or {}
        release_data = {}
        if data.get("manual_submit"):
            release_data = get_manual_release_data(data)
        else:
            release_data = get_release_data(data)

        try:
            completed_goals = handle_submit_data(release_data)
        except IntegrityError as err:
            return jsonify({"error": integrity_error_message(err)}), 400
        except Exception as err:
            return jsonify({"error": friendly_message(err)}), 400

        return jsonify(
            {
                "ok": True,
                "completed_goals": [build_completed_goal_notice(g) for g in completed_goals],
            }
        ), 201

    @app.route("/api/browse/<string:tab>", methods=["GET"])
    def api_browse(tab):
        if tab not in ("releases", "artists", "labels"):
            abort(404)
        counts = {
            "releases": models.Release.total_count(),
            "artists": models.Artist.total_count(),
            "labels": models.Label.total_count(),
        }
        return jsonify({"counts": counts, "filters": browse_filter_options(tab)})

    @app.route("/api/browse/<string:tab>/results", methods=["GET"])
    def api_browse_results(tab):
        if tab not in ("releases", "artists", "labels"):
            abort(404)
        return jsonify(_browse_results_payload(tab))

    @app.route("/api/stats", methods=["GET"])
    def api_stats():
        periods = stats2.available_periods()
        period = request.args.get("period") or (periods[0]["key"] if periods else "all")
        first_listen = models.Release.first_listen_date()
        return jsonify(
            {
                "periods": periods,
                "active_period": period,
                "stats": stats2.get_period_stats(period),
                "genres": stats2.get_genre_shares(),
                "since": first_listen.isoformat() if first_listen else None,
            }
        )

    @app.route("/api/stats/period/<string:period>", methods=["GET"])
    def api_stats_period(period):
        return jsonify({"stats": stats2.get_period_stats(period)})

    @app.route("/api/stats/leaderboards/<string:stats_type>", methods=["GET"])
    def api_stats_leaderboards(stats_type):
        entity = models.Label if stats_type == "labels" else models.Artist
        return jsonify({"boards": stats2.build_leaderboards(entity)})

    @app.route("/api/goals", methods=["GET"])
    def api_goals():
        return jsonify(_goals_payload())

    @app.route("/api/goals", methods=["POST"])
    def api_add_goal():
        data = request.get_json() or {}
        if not data:
            return jsonify({"error": "/api/goals received an empty payload"}), 400
        goal, error = _construct_goal_or_error(data)
        if error:
            return jsonify({"error": error}), 400

        db.insert(goal)
        return jsonify({"ok": True}), 201

    @app.route("/api/<string:item_type>/<int:item_id>", methods=["DELETE"])
    def api_delete(item_type, item_id):
        if item_type not in ("release", "artist", "label", "review"):
            abort(404)
        if not db.get_model(item_type).exists_by_id(item_id):
            return jsonify({"error": f"No {item_type} with id {item_id} found."}), 404
        db.delete(item_type=item_type, item_id=item_id)
        return jsonify({"ok": True})

    @app.template_filter("country_name")
    def country_name_filter(code: Optional[str]) -> Optional[str]:
        return country_name(code)

    @app.template_filter("country_code")
    def country_code_filter(country: str) -> Optional[str]:
        return country_code(country)


def country_name(code: Optional[str]) -> Optional[str]:
    """
    Converts a two-letter country code to the full country name.
    If the country code is `None` or not found in the `pycountry` library,
    the original country code is returned.
    """
    try:
        country = pycountry.countries.get(alpha_2=code.upper())
        return country.name if country else code
    except AttributeError:
        return code


def country_code(country: str) -> Optional[str]:
    """
    Converts a country string to the corresponding two-letter country code
    If country is `None` or not found in `pycountry`, original value is returned.
    """
    if country is None:
        return None
    try:
        code = pycountry.countries.lookup(country)
        return code.alpha_2 if code else None
    except (KeyError, LookupError):
        return country


def process_goal_data(goal: models.Goal):
    """
    Processes the data for a given goal, calculating the current progress,
    remaining amount, and daily target.

    Args:
        goal (models.Goal): The goal object to process.

    Returns:
        dict: A dictionary containing the following keys:
            - start (datetime): The start date of the goal.
            - end (datetime): The end date of the goal.
            - type (str): The type of the goal.
            - amount (int): The total amount of the goal.
            - progress (float): The current progress of the goal as a percentage.
            - target (float): The daily target amount needed to reach the goal.
            - current (int): The current amount achieved for the goal.
    """
    current = goal.new_releases_since_start_date
    remaining = goal.amount - current
    days_left = (goal.end - datetime.today()).days
    try:
        target = round((remaining / days_left), 2)
    except ZeroDivisionError:
        target = 0
    return {
        "start": goal.start,
        "end": goal.end,
        "type": goal.type,
        "amount": goal.amount,
        "progress": round((current / goal.amount) * 100),
        "target": target,
        "current": current,
        "days_left": days_left,
    }


GOAL_TYPE_LABELS = {"release": "releases", "artist": "artists", "label": "labels"}


def _goal_type_label(goal_type: str) -> str:
    return GOAL_TYPE_LABELS.get(goal_type, "releases")


def build_completed_goal_notice(goal: "models.Goal") -> dict:
    """Builds the payload describing a just-completed goal, for the submit response."""
    return {
        "type": goal.type,
        "amount": goal.amount,
        "end_year": goal.end.year,
    }


def build_active_goal_view(goal: "models.Goal") -> dict:
    """
    Builds the view model for the "active goal" hero card on the Goals page,
    covering progress-to-date, pace, and a plain-language projection of
    where the goal will land if the current pace holds.
    """
    today = datetime.now()
    start, end = goal.start, goal.end
    actual = goal.current_amount
    target = goal.amount
    type_label = _goal_type_label(goal.type)

    days_total = max((end - start).days, 1)
    days_elapsed = min(max((today - start).days, 1), days_total)
    days_left = max((end - today).days, 0)

    pace = actual / days_elapsed if days_elapsed else 0
    expected = round(target * (days_elapsed / days_total))
    behind = expected - actual
    needed = (target - actual) / days_left if days_left else 0
    projected = round(actual + pace * days_left)

    if projected >= target:
        spare = projected - target
        projection = (
            f"At {pace:.2f} / day you're on pace to clear this goal"
            + (f", with {spare} to spare." if spare > 0 else ".")
        )
    else:
        shortfall = target - projected
        if pace > 0:
            new_deadline = today + timedelta(days=(target - actual) / pace)
            deadline_text = (
                f"moving the deadline to {new_deadline:%d %b %Y} keeps the pace "
                "you actually have."
            )
        else:
            deadline_text = "you'll need to start logging to make any progress."
        projection = (
            f"At {pace:.2f} / day you finish on {projected} — {shortfall} short. "
            f"Picking up the pace on {shortfall} of the remaining {days_left} days "
            f"closes the gap; otherwise {deadline_text}"
        )

    return {
        "status": "BEHIND PACE" if behind > 0 else "ON TRACK",
        "on_track": behind <= 0,
        "window": f"{start:%d %b %Y} → {end:%d %b %Y} · {days_left} days left",
        "actual": actual,
        "target": target,
        "type_label": type_label,
        "percent": round((actual / target) * 100) if target else 0,
        "progress_w": min(round((actual / target) * 100), 100) if target else 0,
        "pace_w": min(round((days_elapsed / days_total) * 100), 100),
        "progress_label": f"{actual} logged",
        "pace_label": (
            f"even pace would be {expected} by today — you're {abs(behind)} "
            f"{'behind' if behind > 0 else 'ahead'}"
        ),
        "metrics": [
            {
                "label": "REMAINING",
                "value": max(target - actual, 0),
                "sub": type_label,
                "tone": "ink",
            },
            {
                "label": "DAYS LEFT",
                "value": days_left,
                "sub": f"to {end:%d %b}",
                "tone": "ink",
            },
            {
                "label": "NEEDED / DAY",
                "value": f"{needed:.2f}",
                "sub": "from here on",
                "tone": "amber",
            },
            {
                "label": "CURRENT PACE",
                "value": f"{pace:.2f}",
                "sub": "since goal start",
                "tone": "ink",
            },
            {
                "label": "PROJECTED",
                "value": projected,
                "sub": "clears the goal" if projected >= target else f"{target - projected} short",
                "tone": "cyan" if projected >= target else "red",
            },
        ],
        "projection": projection,
    }


def build_past_goal_view(goal: "models.Goal") -> dict:
    """Builds the view model for a single row in the Goals page's "past goals" list."""
    actual = goal.current_amount
    target = goal.amount
    pct = round((actual / target) * 100) if target else 0
    type_label = _goal_type_label(goal.type)

    if goal.completed:
        days_early = (goal.end - goal.completed).days
        result = f"hit on {goal.completed:%d %b %Y}" + (
            f" · {days_early} days early" if days_early > 0 else ""
        )
        badge, tone = "COMPLETE", "cyan"
    else:
        result = f"{actual:,} of {target:,} · {pct}%"
        badge, tone = "MISSED", "red"

    return {
        "title": f"{target:,} {type_label}",
        "window": f"{goal.start:%d %b %Y} → {goal.end:%d %b %Y}",
        "w": min(pct, 100),
        "result": result,
        "badge": badge,
        "tone": tone,
    }
