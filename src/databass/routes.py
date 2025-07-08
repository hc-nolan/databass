"""
Implements the main routes for the databass application, including
- home page
- new release page
- stats page
- goals page
"""

from datetime import datetime
from os.path import join, abspath
from glob import glob
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


def get_manual_release_data(data) -> dict:
    """
    Parses search form data for release information that was manually submitted
    """
    genres = data.get("genres")
    image = data.get("image")
    runtime_ms = data.get("runtime")
    try:
        runtime = int(runtime_ms) * 60000
    except ValueError:
        runtime = 0

    track_count = data.get("track_count")
    try:
        track_count = int(track_count)
    except ValueError:
        track_count = 0

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
        stats_data = get_all_stats()
        active_goals = models.Goal.get_incomplete()
        goal_data = []
        if active_goals is not None:
            goal_data = [process_goal_data(goal) for goal in active_goals]
        year = datetime.now().year
        return render_template(
            "index.html",
            stats=stats_data,
            goals=goal_data,
            year=year,
            active_page="home",
        )

    @app.route("/home_release_table")
    def home_release_table():
        data = models.Release.home_data()

        page = Pager.get_page_param(request)
        paged_data, flask_pagination = Pager.paginate(
            per_page=5, current_page=page, data=data
        )

        return render_template(
            "home_release_table.html",
            data=paged_data,
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

        if not search_release and not search_artist and not search_label:
            error = "ERROR: Search requires at least one search term"
            return error

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
        item = ""
        if itemtype == "artist":
            item = models.Artist.exists_by_id(itemid)
        if itemtype == "label":
            item = models.Label.exists_by_id(itemid)
        if itemtype == "release":
            item = models.Release.exists_by_id(itemid)

        try:
            img_dir = abspath(join("databass", "static", "img", itemtype))
            img_pattern = join(img_dir, f"{item.id}.*")
            match = glob(img_pattern)
            if match:
                img_path = match[0]
            else:
                img_path = "./static/img/none.png"
        except KeyError:
            img_path = "./static/img/none.png"
        try:
            resp = make_response(send_file(img_path))
        except TypeError:
            img_path = "./static/img/none.png"
            resp = make_response(send_file(img_path))
        resp.headers["Cache-Control"] = "max-age"
        return resp

    # TODO: see if still needed
    @app.route("/stats_search", methods=["GET"])
    def stats_search():
        data = request.get_json()
        sort = data["sort"]
        metric = data["metric"]
        item_type = data["item_type"]
        item_property = data["item_property"]
        stats.search(
            sort=sort, metric=metric, item_type=item_type, item_property=item_property
        )

    # TODO: see if still needed
    @app.route("/imgupdate/<item_type>/<item_id>")
    def imgupdate(item_type, item_id):
        print(f"Checking: {item_type} {item_id}")
        item_id = int(item_id)
        if item_type == "release":
            item = models.Release.exists_by_id(item_id)
        elif item_type == "artist":
            item = models.Artist.exists_by_id(item_id)
        elif item_type == "label":
            item = models.Label.exists_by_id(item_id)
        else:
            raise ValueError(f"Unexpected item_type: {item_type}")
        try:
            img_path = "." + Util.img_exists(item_id=item_id, item_type=item_type)
            print(f"Local image already exists: {img_path}")
        except TypeError:
            print("Local image not found, attempting to grab from external sources.")
            # No local image exists, grab it
            if item_type == "release":
                release_name = item.name
                release_artist = models.Artist.exists_by_id(item.artist_id)
                artist_name = release_artist.name
                img_path = Util.get_image(
                    item_type=item_type,
                    item_id=item_id,
                    mbid=item.mbid,
                    release_name=release_name,
                    artist_name=artist_name,
                )
            elif item_type == "artist":
                artist_name = item.name
                img_path = Util.get_image(
                    item_type=item_type,
                    item_id=item_id,
                    mbid=item.mbid,
                    artist_name=artist_name,
                )
            elif item_type == "label":
                label_name = item.name
                img_path = Util.get_image(
                    item_type=item_type,
                    item_id=item_id,
                    mbid=item.mbid,
                    label_name=label_name,
                )
        if item.image != img_path:
            item.image = img_path
            print(f"Updating database entry: {item_type}.image => {img_path}")
            db.update(item)
        # Define the mappings for the order of items.
        # All releases are fixed 1 by 1, then artists, then labels
        next_type = {"release": "artist", "artist": "label", "label": None}
        next_item = db.util.next_item(item_type=item_type, prev_id=item_id)
        if next_item:
            return redirect(f"/imgupdate/{item_type}/{next_item.id}")

        # No next item; move onto next item type
        next_item = next_type.get(item_type)
        if next_item:
            return redirect(f"/imgupdate/{next_item}/0")
        # Complete, redirect to home
        return redirect("/", code=302)

    # TODO: see if still needed
    @app.route("/fix_images")
    def fix_images():
        print("Fixing images.")
        # Starts the imgupdate process; recursively calls itself and update all images 1 by 1
        return redirect("/imgupdate/release/1")

    @app.route("/new_release", methods=["POST"])
    def new_release_popup():
        data = request.get_json()
        return render_template("new_release_popup.html", data=data)

    @app.template_filter("country_name")
    def country_name(code: str) -> str | None:
        """
        Converts a two-letter country code to the full country name.
        If the country code is `None` or not found in the `pycountry` library,
        the original country code is returned.

        Args:
            code (str): The two-letter ISO 3166-1 alpha-2 country code.

        Returns:
            str | None: The full country name if found, otherwise the original country code.
        """
        if code is None:
            return code
        try:
            country = pycountry.countries.get(alpha_2=code.upper())
            return country.name if country else code
        except KeyError:
            return code

    @app.template_filter("country_code")
    def country_code(country: str) -> str | None:
        """
        Converts a country string to the corresponding two-letter country code
        If country is `None` or not found in `pycountry`, original value is returned.
        """
        if country is None:
            return "?"
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
    }
