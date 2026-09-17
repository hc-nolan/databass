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
        IntegrityError: If there is a database integrity error when inserting the item.
        Exception: For any other unexpected errors.
    """
    try:
        app_db.session.add(item)
        app_db.session.commit()
        return item.id
    except IntegrityError as err:
        app_db.session.rollback()
        raise IntegrityError(
            f"Database integrity error: \n{err}\n", params=err.params, orig=err.orig
        ) from err
    except Exception as err:
        app_db.session.rollback()
        raise RuntimeError(f"Unexpected error: {err}") from err


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
    except IntegrityError as err:
        app_db.session.rollback()
        raise IntegrityError(
            f"Database integrity error: \n{err}\n", params=err.params, orig=err.orig
        ) from err
    except Exception as err:
        app_db.session.rollback()
        raise RuntimeError(f"Unexpected error: {err}") from err


