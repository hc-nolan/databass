"""
Implements the main routes for the databass application, including
- home page
- new release page
- stats page
- goals page
"""

from datetime import datetime
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
)
from sqlalchemy.exc import IntegrityError
import pycountry
from .api import Util, MusicBrainz
from . import db
from .db import models
from .db.util import get_all_stats, handle_submit_data
from .pagination import Pager


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
        "artist": release.artist,
        "label": release.label,
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


def build_day_groups(releases: list[models.Release]) -> list[dict]:
    """
    Group releases by listen date (newest first) for the home page feed.

    Returns:
        list[dict]: Each dict has "label" (e.g. "TODAY · SAT 12 SEP"), "meta"
        (e.g. "2 releases · 1h 20m"), and "items" (list of entry dicts).
    """
    today = datetime.now().date()
    ordered = sorted(releases, key=lambda r: r.listen_date, reverse=True)
    groups = []
    for day, day_releases in groupby(ordered, key=lambda r: r.listen_date.date()):
        day_releases = list(day_releases)
        total_minutes = round(sum(r.runtime or 0 for r in day_releases) / 60000)
        noun = "release" if len(day_releases) == 1 else "releases"
        hours, minutes = divmod(total_minutes, 60)
        duration = f"{hours}h {minutes}m" if hours else f"{minutes}m"
        groups.append(
            {
                "label": day_label(day, today),
                "meta": f"{len(day_releases)} {noun} · {duration}",
                "items": [build_entry(r) for r in day_releases],
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
        "listen_date": Util.today(),
        "runtime": runtime,
        "track_count": track_count,
        "country": country,
        "release_group_mbid": None,
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
        "listen_date": Util.today(),
        "country": data.get("country"),
        "genres": data.get("genres"),
        "image": None,
    }


def register_routes(app):
    @app.route("/", methods=["GET"])
    @app.route("/home", methods=["GET"])
    def home() -> str:
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

        return render_template(
            "index.html",
            this_year=this_year,
            goal=goal,
            score_spread=score_spread,
            median_score=distribution["median"],
            on_repeat=on_repeat,
            active_page="home",
        )

    @app.route("/home_release_table")
    def home_release_table():
        groups = models.Release.home_data()
        groups = build_day_groups(groups)

        page = Pager.get_page_param(request)
        paged_groups, flask_pagination = Pager.paginate(
            per_page=4, current_page=page, data=groups
        )

        return render_template(
            "home_release_table.html",
            groups=paged_groups,
            pagination=flask_pagination,
        )

    @app.route("/new")
    def new():
        return render_template("new.html", active_page="new")

    @app.route("/search", methods=["POST", "GET"])
    def search() -> str | flask.Response:
        page = paged_data = release_data = per_page = None

        if request.method == "GET":
            return render_template(
                "search.html",
                page=page,
                data=paged_data,
                pagination=None,
                data_full=release_data,
                per_page=per_page,
            )

        data = request.get_json()
        search_release = data.get("release")
        search_artist = data.get("artist")
        search_label = data.get("label")

        if search_release is None and search_artist is None and search_label is None:
            error = "ERROR: Search requires at least one search term"
            flash(error)
            return redirect("/error")

        release_data = MusicBrainz.release_search(
            release=search_release, artist=search_artist, label=search_label
        )
        page = Pager.get_page_param(request)
        paged_data, flask_pagination = Pager.paginate(
            per_page=10, current_page=page, data=release_data
        )
        return render_template(
            "search.html",
            page=page,
            data=paged_data,
            pagination=flask_pagination,
            data_full=release_data,
            per_page=per_page,
        )

    @app.route("/search_results", methods=["POST"])
    def search_results():
        data = request.get_json()
        per_page = 10
        page = Pager.get_page_param(request)
        paged_data, flask_pagination = Pager.paginate(
            per_page=per_page, current_page=page, data=data
        )
        return render_template(
            "search.html",
            page=page,
            data=paged_data,
            pagination=flask_pagination,
            data_full=data,
            per_page=per_page,
        )

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
            handle_submit_data(release_data)
        except IntegrityError as err:
            flash(str(err))
            return redirect("/error")

        return redirect("/", code=302)

    @app.route("/stats", methods=["GET"])
    def stats():
        statistics = get_all_stats()
        return render_template("stats.html", data=statistics, active_page="stats")

    @app.route("/stats/get/<string:stats_type>", methods=["GET"])
    def stats_get(stats_type):
        statistics = get_all_stats()
        data = ""
        match stats_type:
            case "labels":
                most_freq = statistics.get("top_frequent_labels")
                highest_avg = statistics.get("top_average_labels")
                fav = statistics.get("top_rated_labels")
            case "artists":
                most_freq = statistics.get("top_frequent_artists")
                highest_avg = statistics.get("top_average_artists")
                fav = statistics.get("top_rated_artists")
            case _:
                most_freq = None
                highest_avg = None
                fav = None
        data = {
            "most_frequent": most_freq,
            "highest_average": highest_avg,
            "favourite": fav,
        }
        return render_template("stats_data.html", type=stats_type, stats=data)

    @app.route("/goals", methods=["GET"])
    def goals():
        if request.method != "GET":
            abort(405)
        existing_goals = models.Goal.get_incomplete()
        if existing_goals is None:
            existing_goals = []
        data = {"today": Util.today(), "existing_goals": existing_goals}
        return render_template("goals.html", active_page="goals", data=data)

    @app.route("/add_goal", methods=["POST"])
    def add_goal():
        data = request.form.to_dict()
        if not data:
            error = "/add_goal received an empty payload"
            # TODO: move this error handling into errors/routes.py
            flash(error)
            return redirect("/error")
        try:
            goal = db.construct_item(model_name="goal", data_dict=data)
            if not goal:
                raise NameError("Construction of Goal object failed")
        except Exception as e:
            # TODO: move this error handling into errors/routes.py
            flash(str(e))
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

    @app.route("/new_release", methods=["POST"])
    def new_release_popup():
        data = request.get_json()
        return render_template("new_release_popup.html", data=data)

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
