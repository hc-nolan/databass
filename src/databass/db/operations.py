from os import getenv
from sqlalchemy.exc import IntegrityError
from dotenv import load_dotenv
from .base import app_db


load_dotenv()
TIMEZONE = getenv("TIMEZONE")


def insert(item: app_db.Model) -> int:
    """
    Insert a new database entry.

    Args:
        item (app_db.Model): Instance of a database model class to insert.

    Returns:
        int: The ID of the newly inserted item.

    Raises:
        IntegrityError: If there is a SQLite integrity error when inserting the item.
        Exception: For any other unexpected errors.
    """
    try:
        app_db.session.add(item)
        app_db.session.commit()
        return item.id
    except IntegrityError as err:
        app_db.session.rollback()
        raise IntegrityError(
            f"SQLite Integrity Error: \n{err}\n", params=err.params, orig=err
        )
    except Exception as err:
        app_db.session.rollback()
        raise Exception(f"Unexpected error: {err}")


def update(item: app_db.Model) -> None:
    """
    Update an existing database entry.

    Args:
        item (app_db.Model): Instance of a database model class to update.

    Raises:
        Exception: For any unexpected errors that occur during the update operation.
    """
    try:
        model_class = type(item)
        existing_item = app_db.session.query(model_class).get(item.id)
        if existing_item:
            for key in item.__dict__:
                if not key.startswith("_"):  # Ignore private attributes
                    setattr(existing_item, key, getattr(item, key))
            app_db.session.commit()
        else:
            raise Exception(f"No entry found with ID {item.id}")
    except Exception as err:
        app_db.session.rollback()
        raise Exception(f"Unexpected error: {err}")


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


def get_model(model_name: str):
    """
    :param model_name: String corresponding to a database model class
    :return: Instance of that model's class if it exists; None otherwise
    """
    from .registry import MODELS

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
