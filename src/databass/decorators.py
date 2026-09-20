"""
View decorators for cross-cutting route concerns (see Flask's own
view-decorator pattern: https://flask.palletsprojects.com/en/stable/patterns/viewdecorators/).
"""
from functools import wraps
from flask import jsonify


def load_or_404(model, url_param, inject_as=None):
    """
    Loads `model` by the ID found in the `url_param` route kwarg, replacing
    it with the loaded instance under `inject_as` (defaults to `url_param`)
    before calling the view. If no matching row exists, responds with a
    JSON 404 -- without the view itself needing to check.
    """
    inject_as = inject_as or url_param

    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            item_id = kwargs.pop(url_param)
            try:
                instance = model.exists_by_id(int(item_id))
            except (TypeError, ValueError):
                instance = None
            if not instance:
                message = f"No {model.__name__.lower()} with id {item_id} found."
                return jsonify({"error": message}), 404
            kwargs[inject_as] = instance
            return f(*args, **kwargs)

        return wrapper

    return decorator
