from flask import Blueprint, render_template, request, flash, redirect, jsonify
from sqlalchemy.exc import IntegrityError
from ..db.models import Label
from ..db import update
from ..api.util import Util
from ..detail import build_label_detail
from ..errors.util import friendly_message, integrity_error_message

label_bp = Blueprint("label_bp", __name__, template_folder="templates")


def _apply_label_edit(label_id, edit_data: dict) -> Label:
    label_data = Label.exists_by_id(label_id)
    start = edit_data.get("start")
    if start:
        label_data.begin = start
    end = edit_data.get("end")
    if end:
        label_data.end = end

    image = edit_data.get("image")
    if image:
        if "http" and "://" in image:
            new_image = Util.get_image(entity_type="label", entity_id=label_id, url=image)
            label_data.image = new_image
        else:
            print("Image not a URL. Skipping.")

    country = edit_data.get("country")
    if country:
        label_data.country = country

    update(label_data)
    return label_data


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
        try:
            _apply_label_edit(label_id, edit_data)
        except IntegrityError as err:
            flash(integrity_error_message(err))
            return redirect("/error", code=302)
        except Exception as err:
            flash(friendly_message(err))
            return redirect("/error", code=302)
        return redirect("/", 302)


# TODO: implement edit_label
# @label_bp.route('/label/<string:label_id>', methods=['GET', 'POST'])
# def edit_label(label_id):
#     if request.method == 'GET':
#         pass
#     elif request.method == 'POST':
#         pass
# TODO: implement delete_label


@label_bp.route("/api/label/<int:label_id>", methods=["GET"])
def api_label(label_id):
    label_data = Label.exists_by_id(label_id)
    if not label_data:
        return jsonify({"error": f"No label with id {label_id} found."}), 404
    return jsonify(build_label_detail(label_data))


@label_bp.route("/api/label/<int:label_id>/edit", methods=["GET"])
def api_edit_label_get(label_id):
    label_data = Label.exists_by_id(label_id)
    if not label_data:
        return jsonify({"error": f"No label with id {label_id} found."}), 404
    countries = Label.get_distinct_column_values("country")
    countries = sorted([c for c in countries if c is not None])
    return jsonify(
        {
            "id": label_data.id,
            "name": label_data.name,
            "begin": label_data.begin,
            "end": label_data.end,
            "country": label_data.country,
            "image": label_data.image[1:] if label_data.image else None,
            "countries": countries,
        }
    )


@label_bp.route("/api/label/<int:label_id>", methods=["PUT"])
def api_edit_label(label_id):
    if not Label.exists_by_id(label_id):
        return jsonify({"error": f"No label with id {label_id} found."}), 404
    edit_data = request.get_json() or {}
    try:
        _apply_label_edit(label_id, edit_data)
    except IntegrityError as err:
        return jsonify({"error": integrity_error_message(err)}), 400
    except Exception as err:
        return jsonify({"error": friendly_message(err)}), 400
    return jsonify(build_label_detail(Label.exists_by_id(label_id)))
