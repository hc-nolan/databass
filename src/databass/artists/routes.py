from flask import Blueprint, render_template, request, flash, redirect, jsonify
from ..db.models import Artist
from ..api.util import Util
from ..db import update
from ..detail import build_artist_detail

artist_bp = Blueprint("artist_bp", __name__, template_folder="templates")


def _apply_artist_edit(artist_id, edit_data: dict) -> Artist:
    artist_data = Artist.exists_by_id(artist_id)
    start = edit_data.get("start")
    if start:
        artist_data.begin = start
    end = edit_data.get("end")
    if end:
        artist_data.end = end

    image_url = edit_data.get("image")
    if image_url is not None:
        if "http" and "://" in image_url:
            Util.get_image(entity_type="artist", entity_id=artist_id, url=image_url)
            artist_data.image = image_url
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
    artist_data = Artist.exists_by_id(item_id=artist_id)
    if not artist_data:
        error = f"No release with id {artist_id} found."
        flash(error)
        return redirect("/error", code=302)

    return render_template(
        "detail.html", active_page="browse", data=build_artist_detail(artist_data)
    )


@artist_bp.route("/artists", methods=["GET"])
def artists():
    return redirect("/browse/artists", code=301)


@artist_bp.route("/artist/<string:artist_id>/edit", methods=["GET", "POST"])
def edit_artist(artist_id):
    # Check if artist exists
    artist_data = Artist.exists_by_id(int(artist_id))
    if not artist_data:
        error = f"No artist with id {artist_id} found."
        flash(error)
        return redirect("/error", code=302)

    if request.method == "GET":
        countries = Artist.get_distinct_column_values("country")
        countries = sorted([c for c in countries if c is not None])
        return render_template(
            "edit_artist.html", artist=artist_data, countries=countries
        )

    elif request.method == "POST":
        edit_data = request.form.to_dict()

        artist_data = Artist.exists_by_id(artist_id)
        start = edit_data.get("start")
        if start:
            artist_data.begin = start
        end = edit_data.get("end")
        if end:
            artist_data.end = end

        image_url = edit_data.get("image")
        if image_url is not None:
            if "http" and "://" in image_url:
                # If image is a URL, download it
                Util.get_image(entity_type="artist", entity_id=artist_id, url=image_url)
                artist_data.image = image_url
            else:
                print("Image not a URL. Skipping.")

        country = edit_data.get("country")
        if country:
            artist_data.country = country

        update(artist_data)
        return redirect("/", 302)


# TODO: implement delete_artist


@artist_bp.route("/api/artist/<int:artist_id>", methods=["GET"])
def api_artist(artist_id):
    artist_data = Artist.exists_by_id(artist_id)
    if not artist_data:
        return jsonify({"error": f"No artist with id {artist_id} found."}), 404
    return jsonify(build_artist_detail(artist_data))


@artist_bp.route("/api/artist/<int:artist_id>/edit", methods=["GET"])
def api_edit_artist_get(artist_id):
    artist_data = Artist.exists_by_id(artist_id)
    if not artist_data:
        return jsonify({"error": f"No artist with id {artist_id} found."}), 404
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
def api_edit_artist(artist_id):
    if not Artist.exists_by_id(artist_id):
        return jsonify({"error": f"No artist with id {artist_id} found."}), 404
    edit_data = request.get_json() or {}
    _apply_artist_edit(artist_id, edit_data)
    return jsonify(build_artist_detail(Artist.exists_by_id(artist_id)))
