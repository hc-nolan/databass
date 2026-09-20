from datetime import datetime
from flask import Blueprint, request, redirect, jsonify
from .. import db
from ..db import models
from ..api import Util
from ..decorators import load_or_404
from ..detail import build_release_detail
from ..errors.util import friendly_message

release_bp = Blueprint("release_bp", __name__)


def _release_edit_data(release_data: models.Release) -> dict:
    label_data = models.Label.exists_by_id(release_data.label_id)
    artist_data = models.Artist.exists_by_id(release_data.artist_id)
    countries = sorted(models.Release.get_distinct_column_values("country"))
    return {
        "id": release_data.id,
        "name": release_data.name,
        "year": release_data.year,
        "main_genre": release_data.main_genre.name if release_data.main_genre else None,
        "genres": [g.name for g in release_data.genres],
        "rating": release_data.rating,
        "image": release_data.image[1:] if release_data.image else None,
        "listen_date": release_data.listen_date.strftime("%Y-%m-%d")
        if release_data.listen_date
        else None,
        "country": release_data.country,
        "artist": artist_data.name if artist_data else None,
        "label": label_data.name if label_data else None,
        "collab_artists": [a.name for a in release_data.collab_artists],
        "countries": countries,
    }


def _apply_release_edit(release_data: models.Release, edit_data: dict) -> models.Release:
    """Shared edit logic for the release edit endpoint."""
    submit_data = {}

    image = edit_data.get("image")
    if image:
        if "://" in image:
            new_image = Util.get_image_from_url(entity_type="release", url=image)
            submit_data["image"] = new_image
        else:
            print("Image not a URL. Skipping.")

    year = edit_data.get("year")
    if year:
        submit_data["year"] = year

    listen_date = edit_data.get("listen_date")
    if listen_date:
        submit_data["listen_date"] = datetime.strptime(listen_date, "%Y-%m-%d")

    rating = edit_data.get("rating")
    if rating:
        submit_data["rating"] = rating

    main_genre = edit_data.get("main_genre")
    if main_genre:
        submit_data["main_genre"] = models.Genre.create_if_not_exists(main_genre)

    country = edit_data.get("country")
    if country:
        submit_data["country"] = country

    genres = edit_data.get("genres")
    if genres:
        genre_names = genres if isinstance(genres, list) else genres.split(",")
        submit_data["genres"] = [
            models.Genre.create_if_not_exists(g.strip())
            for g in genre_names
            if g.strip()
        ]

    if "collab_artists" in edit_data:
        collab_artists = edit_data["collab_artists"]
        collab_names = (
            collab_artists if isinstance(collab_artists, list) else collab_artists.split(",")
        )
        collab_objs = []
        for name in collab_names:
            name = name.strip()
            if name:
                collab_id = models.Artist.create_if_not_exist(name)
                collab_objs.append(models.Artist.exists_by_id(collab_id))
        # unlike genres, an empty submission here is meaningful: it's how
        # a collab credit gets removed, so always write the (possibly
        # empty) list rather than only when non-empty
        submit_data["collab_artists"] = collab_objs

    updated_release = db.construct_item("release", submit_data)
    # construct_item() will produce a unique ID primary key, so we need to set it to the original one for update() to work
    updated_release.id = release_data.id
    # carry over the fields that don't change from the release we already loaded
    updated_release.artist_id = release_data.artist_id
    updated_release.label_id = release_data.label_id
    updated_release.runtime = release_data.runtime
    updated_release.track_count = release_data.track_count
    db.update(updated_release)
    return updated_release


@release_bp.route("/releases", methods=["GET"])
def releases():
    return redirect("/browse/releases", code=301)


@release_bp.route("/api/release/<int:release_id>", methods=["GET"])
@load_or_404(models.Release, "release_id", inject_as="release_data")
def api_release(release_data):
    return jsonify(build_release_detail(release_data))


@release_bp.route("/api/release/<int:release_id>/relisten", methods=["POST"])
@load_or_404(models.Release, "release_id", inject_as="release_data")
def api_relisten(release_data):
    release_data.listen_date = datetime.now()
    db.update(release_data)
    new_review = db.construct_item(
        "review", {"release_id": release_data.id, "text": "Logged another listen."}
    )
    db.insert(new_review)
    return jsonify(build_release_detail(release_data))


@release_bp.route("/api/release/<int:release_id>/edit", methods=["GET"])
@load_or_404(models.Release, "release_id", inject_as="release_data")
def api_edit_release_get(release_data):
    return jsonify(_release_edit_data(release_data))


@release_bp.route("/api/release/<int:release_id>", methods=["PUT"])
@load_or_404(models.Release, "release_id", inject_as="release_data")
def api_edit_release(release_data):
    edit_data = request.get_json() or {}
    try:
        updated_release = _apply_release_edit(release_data, edit_data)
    except Exception as e:
        return jsonify({"error": friendly_message(e)}), 400
    return jsonify(build_release_detail(updated_release))


@release_bp.route("/api/release/<int:release_id>/reviews", methods=["POST"])
@load_or_404(models.Release, "release_id", inject_as="release_data")
def api_add_review(release_data):
    review_data = request.get_json() or {}
    if "text" not in review_data:
        return jsonify({"error": "Request missing required field: text"}), 400
    new_review = db.construct_item(
        "review", {"release_id": release_data.id, "text": review_data["text"]}
    )
    db.insert(new_review)
    return jsonify(build_release_detail(release_data)), 201


@release_bp.route("/api/release/<int:release_id>/reviews/<int:review_id>", methods=["PUT"])
@load_or_404(models.Release, "release_id", inject_as="release_data")
def api_edit_review(release_data, review_id):
    review_data = request.get_json() or {}
    if "text" not in review_data:
        return jsonify({"error": "Request missing required field: text"}), 400
    review = models.Review.exists_by_id(review_id)
    if not review or review.release_id != release_data.id:
        return (
            jsonify(
                {
                    "error": f"No review with ID {review_id} found for release {release_data.id}"
                }
            ),
            404,
        )
    review.text = review_data["text"]
    db.update(review)
    return jsonify(build_release_detail(release_data))
