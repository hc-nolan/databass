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


def register_routes(app):
    @app.route("/", methods=["GET"])
    @app.route("/home", methods=["GET"])
    def home() -> str:
        stats_data = get_all_stats()
        active_goals = models.Goal.get_incomplete()
        if active_goals is not None:
            goal_data = [process_goal_data(goal) for goal in active_goals]
        else:
            goal_data = []
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
        try:
            search_release = data["release"]
            search_artist = data["artist"]
            search_label = data["label"]
        except KeyError:
            error = "Request missing one of the expected keys"
            flash(error)
            # TODO: move this error handling into errors/routes.py
            return redirect("/error")
        if not search_release and not search_artist and not search_label:
            error = "ERROR: Search requires at least one search term"
            return error
        app.logger.info(
            "Searching MusicBrainz for: %s - %s - %s",
            search_release,
            search_artist,
            search_label,
        )
        release_data = MusicBrainz.release_search(
            release=search_release, artist=search_artist, label=search_label
        )
        page = Pager.get_page_param(request)
        if all(var is not None for var in [page, release_data]):
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
        app.logger.info("Displaying search results.")
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
        app.logger.info("Submitting new release data.")
        data = request.form.to_dict()
        try:
            release_data = {}
            # Check if this is a manual submission
            if data["manual_submit"] == "true":
                app.logger.info("Got a manual submission - parsing fields.")
                # try to grab optional fields
                try:
                    genres = data["genres"]
                except KeyError:
                    genres = []
                try:
                    image = data["image"]
                except KeyError:
                    image = ""

                try:
                    # convert minutes to ms
                    runtime = int(data["runtime"]) * 60000
                except (KeyError, ValueError):
                    runtime = 0

                try:
                    track_count = int(data["track_count"])
                except (KeyError, ValueError):
                    track_count = 0

                try:
                    country = country_code(data["country"])
                except KeyError:
                    country = "?"

                release_data = {
                    "name": data["name"],
                    "mbid": None,
                    "artist_name": data["artist"],
                    "artist_mbid": None,
                    "label_name": data["label"],
                    "label_mbid": None,
                    "year": data["year"],
                    "main_genre": data["main_genre"],
                    "rating": data["rating"],
                    "genres": genres,
                    "image": image,
                    "listen_date": Util.today(),
                    "runtime": runtime,
                    "track_count": track_count,
                    "country": country,
                    "release_group_mbid": None,
                }
            elif data["manual_submit"] == "false":
                # Grab variables from request
                release_data = {
                    "release_group_mbid": data["release_group_id"],
                    "name": data["release_name"],
                    "mbid": data["release_mbid"],
                    "artist_name": data["artist"],
                    "artist_mbid": data["artist_mbid"],
                    "label_name": data["label"],
                    "label_mbid": data["label_mbid"],
                    "year": int(data["year"]),
                    "main_genre": data["main_genre"],
                    "rating": int(data["rating"]),
                    "track_count": data["track_count"],
                    "listen_date": Util.today(),
                    "country": data["country"],
                    "genres": data["genres"],
                    "image": None,
                }
            app.logger.info("Submitting release data: %s", release_data)
            try:
                handle_submit_data(release_data)
            except IntegrityError as err:
                flash(str(err))
                return redirect("/error")
        except KeyError as err:
            error = f"Request missing one of the expected keys: {err}"
            flash(error)
            return redirect("/error")
        return redirect("/", code=302)

    @app.route("/stats", methods=["GET"])
    def stats():
        app.logger.info("Fetching all statistics.")
        statistics = get_all_stats()
        return render_template("stats.html", data=statistics, active_page="stats")

    @app.route("/stats/get/<string:stats_type>", methods=["GET"])
    def stats_get(stats_type):
        statistics = get_all_stats()
        data = ""
        msg = "Fetching statistics for "
        if stats_type == "labels":
            msg += "labels"
            data = {
                "most_frequent": statistics["top_frequent_labels"],
                "highest_average": statistics["top_average_labels"],
                "favourite": statistics["top_rated_labels"],
            }
        if stats_type == "artists":
            msg += "artists"
            data = {
                "most_frequent": statistics["top_frequent_artists"],
                "highest_average": statistics["top_average_artists"],
                "favourite": statistics["top_rated_artists"],
            }
        app.logger.info("%s", msg)
        return render_template("stats_data.html", type=stats_type, stats=data)

    @app.route("/goals", methods=["GET"])
    def goals():
        app.logger.info("Displaying goals.")
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
            app.logger.error("%s", error)
            # TODO: move this error handling into errors/routes.py
            flash(error)
            return redirect("/error")
        try:
            goal = db.construct_item(model_name="goal", data_dict=data)
            if not goal:
                raise NameError("Construction of Goal object failed")
        except Exception as e:
            # TODO: move this error handling into errors/routes.py
            app.logger.error("%s", e)
            flash(str(e))
            return redirect("/error")

        app.logger.info("Adding new goal: %s", data)
        db.insert(goal)
        return redirect("/goals", 302)

    @app.route("/img/<string:itemtype>/<int:itemid>", methods=["GET"])
    def serve_image(itemtype: str, itemid: int):
        app.logger.info("Attempting to serve image for %s %s", itemtype, itemid)
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
            return country
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
