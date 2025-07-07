from datetime import date
from flask import Blueprint, render_template, request, flash, redirect
from ..db.models import Artist
from ..pagination import Pager
from ..api.util import Util
from ..db import construct_item, update

artist_bp = Blueprint("artist_bp", __name__, template_folder="templates")


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

    no_end = date(9999, 12, 31)
    no_start = date(1, 1, 1)
    data = {"artist": artist_data, "no_end": no_end, "no_start": no_start}
    return render_template("artist.html", data=data)


@artist_bp.route("/artists", methods=["GET"])
def artists():
    countries = Artist.get_distinct_column_values("country")
    data = {"countries": countries}
    return render_template("artists.html", data=data, active_page="artists")


@artist_bp.route("/artist_search", methods=["POST"])
def artist_search():
    data = request.get_json()
    search_results = Artist.dynamic_search(data)
    page = Pager.get_page_param(request)
    paged_data, flask_pagination = Pager.paginate(
        per_page=15, current_page=page, data=search_results
    )
    return render_template(
        "artist_search.html",
        data=paged_data,
        data_full=search_results,
        pagination=flask_pagination,
    )


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
                Util.get_image(item_type="artist", item_id=artist_id, url=image_url)
                artist_data.image = image_url
            else:
                print("Image not a URL. Skipping.")

        country = edit_data.get("country")
        if country:
            artist_data.country = country

        update(artist_data)
        return redirect("/", 302)


# TODO: implement delete_artist
