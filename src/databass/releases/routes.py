from datetime import datetime
from flask import Blueprint, render_template, request, redirect, flash
from .. import db
from ..db import models
from ..api import Util
from ..detail import build_release_detail

release_bp = Blueprint("release_bp", __name__, template_folder="templates")


@release_bp.route("/release/<string:release_id>", methods=["GET"])
def release(release_id):
    # Displays all info related to a particular release
    release_data = models.Release.exists_by_id(release_id)
    if not release_data:
        error = f"No release with id {release_id} found."
        flash(error)
        return redirect("/error", code=302)
    return render_template(
        "detail.html", active_page="browse", data=build_release_detail(release_data)
    )


@release_bp.route("/release/<string:release_id>/relisten", methods=["POST"])
def relisten(release_id):
    # Logs a new listen of an existing release: bumps the listen date and
    # appends a diary entry so re-listens read as history, not an overwrite.
    release_data = models.Release.exists_by_id(int(release_id))
    if not release_data:
        error = f"No release with id {release_id} found."
        flash(error)
        return redirect("/error", code=302)
    release_data.listen_date = datetime.now()
    db.update(release_data)
    new_review = db.construct_item(
        "review", {"release_id": int(release_id), "text": "Logged another listen."}
    )
    db.insert(new_review)
    return redirect(f"/release/{release_id}", code=302)


@release_bp.route("/release/<string:release_id>/edit", methods=["GET", "POST"])
def edit(release_id):
    # Check if release exists
    release_data = models.Release.exists_by_id(int(release_id))
    if not release_data:
        error = f"No release with id {release_id} found."
        flash(error)
        return redirect("/error", code=302)

    if request.method == "GET":
        try:
            release_image = release_data.image[1:]
        except TypeError:
            release_image = None
        label_data = models.Label.exists_by_id(release_data.label_id)
        artist_data = models.Artist.exists_by_id(release_data.artist_id)
        countries = sorted(models.Release.get_distinct_column_values("country"))
        return render_template(
            "edit.html",
            release=release_data,
            artist=artist_data,
            label=label_data,
            image=release_image,
            countries=countries,
        )
    if request.method == "POST":
        edit_data = request.form.to_dict()
        submit_data = {}

        # image
        try:
            if edit_data["image"]:
                image = edit_data["image"]
                if "http" and "://" in image:
                    # If image is a URL, download it
                    new_image = Util.get_image(
                        entity_type="release", entity_id=release_id, url=image
                    )
                    submit_data["image"] = new_image
                else:
                    print("Image not a URL. Skipping.")
        except KeyError:
            pass

        # release year
        try:
            year = edit_data["year"]
            if year:
                submit_data["year"] = year
        except KeyError:
            pass

        # listen date
        try:
            listen_date = edit_data["listen_date"]
            if listen_date:
                from datetime import datetime

                submit_data["listen_date"] = datetime.strptime(listen_date, "%Y-%m-%d")
        except KeyError:
            pass

        # rating
        try:
            rating = edit_data["rating"]
            if rating:
                submit_data["rating"] = rating
        except KeyError:
            pass

        # genre
        try:
            main_genre = edit_data["main_genre"]
            if main_genre:
                genre = models.Genre.create_if_not_exists(main_genre)
                submit_data["main_genre"] = genre
        except KeyError:
            pass

        # country
        try:
            country = edit_data["country"]
            if country:
                submit_data["country"] = country
        except KeyError:
            pass

        # genres
        try:
            genres = edit_data["genres"]
            genre_objs = []
            if genres:
                for g in genres.split(","):
                    genre_objs.append(models.Genre.create_if_not_exists(g))
                submit_data["genres"] = genre_objs
        except KeyError:
            pass

        # collab artists: additional artists whose discography should
        # include this release, alongside its primary artist
        try:
            collab_artists = edit_data["collab_artists"]
            collab_objs = []
            for name in collab_artists.split(","):
                name = name.strip()
                if name:
                    collab_id = models.Artist.create_if_not_exist(name)
                    collab_objs.append(models.Artist.exists_by_id(collab_id))
            # unlike genres, an empty submission here is meaningful: it's how
            # a collab credit gets removed, so always write the (possibly
            # empty) list rather than only when non-empty
            submit_data["collab_artists"] = collab_objs
        except KeyError:
            pass

        updated_release = db.construct_item("release", submit_data)
        # construct_item() will produce a unique ID primary key, so we need to set it to the original one for update() to work
        try:
            updated_release.id = release_id
            # grab the other release so we can inject the data that doesn't change
            old_release = models.Release.exists_by_id(release_id)
            updated_release.artist_id = old_release.artist_id
            updated_release.label_id = old_release.label_id
            updated_release.runtime = old_release.runtime
            updated_release.track_count = old_release.track_count

        except KeyError:
            error = (
                "Edit data missing ID, unable to update an existing entry without ID."
            )
            flash(error)
            return redirect("/error", code=302)
        db.update(updated_release)
        return redirect("/", 302)


@release_bp.route("/delete", methods=["POST"])
def delete():
    data = request.get_json()
    try:
        deletion_id = data["id"]
        deletion_type = data["type"]
    except KeyError:
        error = "Deletion request missing one of the required variables (ID or type)"
        flash(error)
        return redirect("/error", code=302)

    if not models.Release.exists_by_id(deletion_id):
        error = f"No release with id {deletion_id} found."
        flash(error)
        return redirect("/error", code=302)
    print(f"Deleting {deletion_type} {deletion_id}")
    db.delete(item_type=deletion_type, item_id=deletion_id)
    return redirect("/", 302)


@release_bp.route("/release/<string:release_id>/add_review", methods=["POST"])
def add_review(release_id):
    # Make sure release exists before doing anything
    if not models.Release.exists_by_id(int(release_id)):
        error = f"No release with ID {release_id} found"
        flash(error)
        return redirect("/error", code=302)
    # Ensure request has required data
    review_data = request.form.to_dict()
    if "text" not in review_data.keys():
        error = "Request missing one of the required variables: text"
        flash(error)
        return redirect("/error", code=302)
    # Perform deletion
    new_review = db.construct_item("review", review_data)
    db.insert(new_review)
    return redirect(request.referrer, 302)


@release_bp.route("/releases", methods=["GET"])
def releases():
    return redirect("/browse/releases", code=301)
