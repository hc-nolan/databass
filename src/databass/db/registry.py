from .base import app_db
from .models import Release, Artist, Label, Goal, Genre, Review

MODELS = {
    "artist": Artist,
    "release": Release,
    "label": Label,
    "goal": Goal,
    "genre": Genre,
    "review": Review,
}


def get_model(model_name: str):
    """
    :param model_name: String corresponding to a database model class
    :return: Instance of that model's class if it exists; None otherwise
    """
    if not isinstance(model_name, str):
        raise ValueError("model_name must be a string")
    instance = MODELS.get(model_name)
    if not instance:
        raise NameError(
            f"No model with the name '{model_name}' found in MODELS."
            "Ensure all valid models are imported in databass.db.util.py and "
            "reflect existing models as defined in models.py"
        )
    return instance


def construct_item(model_name: str, data_dict: dict):
    """
    Construct an instance of a model from a dictionary
    :param model_name: String corresponding to SQLAlchemy model class from models.py
    :param data_dict: Dictionary containing keys corresponding to the database model class
    :return: The newly constructed instance of the model class.
    """
    model = get_model(model_name)
    if model is not None:
        item = model(**data_dict)
        return item
    raise NameError(
        f"No model with the name '{model_name}' found in globals(). Ensure all "
        f"valid models are imported and reflect existing models as defined in models.py."
        f"Globals: {globals()}"
    )


def delete(item_type: str, item_id: str) -> None:
    """
    Delete a database entry by its type and ID.

    Args:
        item_type (str): The type of the database item to delete (e.g. 'label', 'artist').
        item_id (str): The ID of the database item to delete.

    Raises:
        Exception: If no model is found for the given item_type, or if an unexpected error occurs during the delete operation.
    """
    try:
        model = get_model(item_type)
        to_delete = app_db.session.query(model).where(model.id == item_id).one()
        if to_delete:
            app_db.session.delete(to_delete)
            app_db.session.commit()
        else:
            raise ValueError(f"No {item_type} entry found for {item_id}")
    except Exception as err:
        app_db.session.rollback()
        raise err
