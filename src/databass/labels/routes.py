from flask import Blueprint, render_template, request, flash, redirect
from ..db.models import Label
from ..db import update
from ..api.util import Util
from ..detail import build_label_detail

label_bp = Blueprint("label_bp", __name__, template_folder="templates")


@label_bp.route("/label/<int:label_id>", methods=["GET"])
def label(label_id):
    if label_id == 0:
        return redirect("/")
    label_data = Label.exists_by_id(label_id)
    if not label_data:
        error = f"No label with ID {label_id} found."
        flash(error)
        return redirect("/error", code=302)
    return render_template(
        "detail.html", active_page="browse", data=build_label_detail(label_data)
    )


@label_bp.route("/labels", methods=["GET"])
def labels():
    return redirect("/browse/labels", code=301)


@label_bp.route("/label/<string:label_id>/edit", methods=["GET", "POST"])
def edit_label(label_id):
    # Check if label exists
    label_data = Label.exists_by_id(int(label_id))
    if not label_data:
        error = f"No label with id {label_id} found."
        flash(error)
        return redirect("/error", code=302)

    if request.method == "GET":
        countries = Label.get_distinct_column_values("country")
        countries = sorted([c for c in countries if c is not None])
        return render_template("edit_label.html", label=label_data, countries=countries)

    elif request.method == "POST":
        edit_data = request.form.to_dict()

        label_data = Label.exists_by_id(label_id)
        try:
            start = edit_data["start"]
            if start:
                label_data.begin = start
        except KeyError:
            pass

        try:
            end = edit_data["end"]
            if end:
                label_data.end = end
        except KeyError:
            pass

        try:
            if edit_data["image"]:
                image = edit_data["image"]
                if "http" and "://" in image:
                    # If image is a URL, download it
                    new_image = Util.get_image(
                        entity_type="release", entity_id=label_id, url=image
                    )
                    label_data.image = image
                else:
                    print("Image not a URL. Skipping.")
        except KeyError:
            pass

        try:
            country = edit_data["country"]
            if country:
                label_data.country = country
        except KeyError:
            pass

        update(label_data)
        return redirect("/", 302)


# TODO: implement edit_label
# @label_bp.route('/label/<string:label_id>', methods=['GET', 'POST'])
# def edit_label(label_id):
#     if request.method == 'GET':
#         pass
#     elif request.method == 'POST':
#         pass
# TODO: implement delete_label
