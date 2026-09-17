from flask import Blueprint, render_template, request, flash, redirect, jsonify
from sqlalchemy.exc import IntegrityError
from ..db.models import Artist
from ..api import Util
from ..db import update
from ..decorators import load_or_404
from ..detail import build_artist_detail
from ..errors.util import friendly_message, integrity_error_message

artist_bp = Blueprint("artist_bp", __name__, template_folder="templates")


def _apply_artist_edit(artist_data: Artist, edit_data: dict) -> Artist:
    start = edit_data.get("start")
    if start:
        artist_data.begin = start
    end = edit_data.get("end")
    if end:
        artist_data.end = end

    image_url = edit_data.get("image")
    if image_url is not None:
        if "://" in image_url:
            new_image = Util.get_image_from_url(entity_type="artist", url=image_url)
            artist_data.image = new_image
        else:
            print("Image not a URL. Skipping.")

    country = edit_data.get("country")
    if country:
        artist_data.country = country

    update(artist_data)
    return artist_data


@artist_bp.route("/artist/<int:artist_id>", methods=["GET"])
def artist(artist_id):
    # Displays all info related to a particular artist
    if artist_id == 0:
        return redirect("/")
    return _artist_detail(artist_id=artist_id)


@load_or_404(Artist, "artist_id", inject_as="artist_data")
def _artist_detail(artist_data):
    return render_template(
        "detail.html", active_page="browse", data=build_artist_detail(artist_data)
    )


@artist_bp.route("/artists", methods=["GET"])
def artists():
    return redirect("/browse/artists", code=301)


@artist_bp.route("/artist/<string:artist_id>/edit", methods=["GET", "POST"])
@load_or_404(Artist, "artist_id", inject_as="artist_data")
def edit_artist(artist_data):
    if request.method == "GET":
        countries = Artist.get_distinct_column_values("country")
        countries = sorted([c for c in countries if c is not None])
        return render_template(
            "edit_artist.html", artist=artist_data, countries=countries
        )

    elif request.method == "POST":
        edit_data = request.form.to_dict()
        try:
            _apply_artist_edit(artist_data, edit_data)
        except IntegrityError as err:
            flash(integrity_error_message(err))
            return redirect("/error", code=302)
        except Exception as err:
            flash(friendly_message(err))
            return redirect("/error", code=302)
        return redirect(f"/artist/{artist_data.id}", code=302)


# TODO: implement delete_artist


@artist_bp.route("/api/artist/<int:artist_id>", methods=["GET"])
@load_or_404(Artist, "artist_id", inject_as="artist_data")
def api_artist(artist_data):
    return jsonify(build_artist_detail(artist_data))


@artist_bp.route("/api/artist/<int:artist_id>/edit", methods=["GET"])
@load_or_404(Artist, "artist_id", inject_as="artist_data")
def api_edit_artist_get(artist_data):
    countries = Artist.get_distinct_column_values("country")
    countries = sorted([c for c in countries if c is not None])
    return jsonify(
        {
            "id": artist_data.id,
            "name": artist_data.name,
            "begin": artist_data.begin,
            "end": artist_data.end,
            "country": artist_data.country,
            "image": artist_data.image[1:] if artist_data.image else None,
            "countries": countries,
        }
    )


@artist_bp.route("/api/artist/<int:artist_id>", methods=["PUT"])
@load_or_404(Artist, "artist_id", inject_as="artist_data")
def api_edit_artist(artist_data):
    edit_data = request.get_json() or {}
    try:
        _apply_artist_edit(artist_data, edit_data)
    except IntegrityError as err:
        return jsonify({"error": integrity_error_message(err)}), 400
    except Exception as err:
        return jsonify({"error": friendly_message(err)}), 400
    return jsonify(build_artist_detail(artist_data))
