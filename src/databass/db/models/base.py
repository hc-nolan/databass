from __future__ import annotations
from datetime import datetime, date
from typing import Any, Optional

import sqlalchemy.exc
from sqlalchemy import extract, distinct, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from ..base import app_db


class Base(DeclarativeBase):
    """Base class which all other database model classes are built from"""

    id: Mapped[int] = mapped_column(primary_key=True)
    date_added: Mapped[date | None] = mapped_column(default=date.today(), nullable=True)

    @classmethod
    def added_this_year(cls):
        # Returns the number of entries where date_added is within current year
        current_year = datetime.now().year
        try:
            results = (
                app_db.session.query(cls)
                .filter(extract("year", cls.date_added) == current_year)
                .count()
            )
            if current_year == 2024:
                # This section is required for backwards compatibility
                results += (
                    app_db.session.query(cls).filter(cls.date_added is None).count()
                )
        except Exception:
            results = 0
        return results

    @classmethod
    def added_per_day_this_year(cls):
        """
        Calculates the average number of listens per day so far this year.

        Returns:
            float: The average number of listens per day so far this year,
            rounded to 2 decimal places.
        """
        days_this_year: int = date.today().timetuple().tm_yday
        if days_this_year == 0:
            return 0.0
        count = cls.added_this_year()
        result = count / days_this_year
        return round(result, 2)

    @classmethod
    def exists_by_id(cls, item_id: int):
        """
        Check if an item exists in the database by its ID
        :param item_id: Item's ID (primary key)
        :return: The item, if it exists, or False if the item does not exist
        """
        try:
            result = app_db.session.query(cls).filter(cls.id == item_id).one_or_none()
            return result if result else None
        except Exception:
            return None

    @classmethod
    def exists_by_name(cls, name: str) -> Optional[Base]:
        """
        Check if an entry exists in the database by its name.

        Args:
            name (str): The name of the entry to check for.

        Returns:
            Optional[Base]: The entry if it exists, otherwise None.
        """
        if not name or not isinstance(name, str):
            return None
        try:
            result = (
                app_db.session.query(cls)
                .filter(cls.name.ilike(f"%{name}%"))
                .one_or_none()
            )
        except sqlalchemy.exc.MultipleResultsFound:
            result = (
                app_db.session.query(cls).filter(cls.name.ilike(f"%{name}%")).first()
            )
        return result


class MusicBrainzEntity(Base):
    # Release and ArtistOrLabel are built from this prototype
    __abstract__ = True

    mbid: Mapped[str | None] = mapped_column(String, unique=True, nullable=True)
    name: Mapped[str] = mapped_column(String())
    image: Mapped[str | None] = mapped_column(String(), nullable=True)
    country: Mapped[str | None] = mapped_column(String(), nullable=True)

    @classmethod
    def get_all(cls) -> list[Any]:
        # Return all database entries for this class
        results = app_db.session.query(cls).all()
        return results

    @classmethod
    def total_count(cls) -> int:
        # Return the count of all database entries for this class
        try:
            results = app_db.session.query(cls).count()
            return results if isinstance(results, int) else None
        except Exception:
            return 0

    @classmethod
    def get_distinct_column_values(cls, column: str) -> list:
        """
        Get all distinct values of a given column
        :param column: String representing the column's name
        :return: List of the unique values of the given column
        """
        try:
            attribute = getattr(cls, column)
            return [value for (value,) in app_db.session.query(distinct(attribute))]
        except AttributeError as e:
            raise e

    @classmethod
    def exists_by_mbid(cls, mbid: str) -> Optional[MusicBrainzEntity]:
        """
        Check if a MusicBrainzEntity exists in the database by its MBID (MusicBrainz ID).

        Args:
            mbid (str): The MBID of the MusicBrainzEntity to check for.

        Returns:
            Optional[MusicBrainzEntity]: The MusicBrainzEntity if it exists, otherwise None.
        """
        if not mbid or not isinstance(mbid, str):
            return None
        try:
            result = app_db.session.query(cls).filter(cls.mbid == mbid).one_or_none()
        except Exception:
            app_db.session.rollback()
            return None
        if result:
            return result
        return None

    @classmethod
    def name_from_id(cls, item_id: int) -> Optional[MusicBrainzEntity.name]:
        """
        Get the name of a MusicBrainzEntity from its database ID.

        Args:
            item_id (int): The ID of the MusicBrainzEntity to get the name of.

        Returns:
            Optional[MusicBrainzEntity.name]: The name (str) of the MusicBrainzEntity,
            or None if no entry with the specified ID is found.
        """
        if not isinstance(item_id, int) or item_id <= 0:
            return None
        result = app_db.session.query(cls.name).where(cls.id == item_id).one_or_none()
        return result[0] if result is not None else None

    @classmethod
    def id_by_matching_name(cls, name: str) -> list[MusicBrainzEntity.id]:
        """
        Get all MusicBrainzEntity IDs of a given type (Release, Artist, Label)
        where the name matches the `name` argument.

        Args:
            name (str): The name to match on.

        Returns:
            list[MusicBrainzEntity.id]: A list of MusicBrainzEntity IDs (int) with names
                                        that match the `name` argument.
        """
        if not isinstance(name, str):
            return []
        result = app_db.session.query(cls.id).filter(cls.name.ilike(f"%{name}%")).all()
        # .all() returns a list of tuples like [(1,), (2,)]
        # below list comprehension unpacks it to [1, 2]
        return [r[0] for r in result]
