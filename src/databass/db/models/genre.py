from __future__ import annotations
from typing import Optional

from sqlalchemy import String, distinct, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..base import app_db
from ..operations import insert
from .base import Base
from .associations import (
    release_genre_association,
    artist_genre_association,
    label_genre_association,
)
from .catalog import Release


class Genre(Base):
    __tablename__ = "genre"
    name: Mapped[str] = mapped_column(String, unique=True)

    main_genres = relationship("Release", back_populates="main_genre")
    releases = relationship(
        "Release", secondary=release_genre_association, back_populates="genres"
    )
    artists = relationship(
        "Artist", secondary=artist_genre_association, back_populates="genres"
    )
    labels = relationship(
        "Label", secondary=label_genre_association, back_populates="genres"
    )

    @classmethod
    def top_by_release_count(cls, limit: int = 6) -> list[dict]:
        """
        Top genres by number of releases logged under them as their main
        genre, all-time, most-listened first.
        """
        rows = (
            app_db.session.query(cls.name, func.count(Release.id).label("count"))
            .join(Release, Release.main_genre_id == cls.id)
            .group_by(cls.name)
            .order_by(func.count(Release.id).desc())
            .limit(limit)
            .all()
        )
        return [{"name": name, "count": count} for name, count in rows]

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

    @staticmethod
    def create_genres(genres: str) -> list:
        """
        Create genres for a given release in the database, if they do not already exist.

        Args:
            genres (str): A comma-separated string of genre names to create.

        Returns:
            List of the genre objects

        This function splits the `genres` string on commas to get a list of individual genre names.
        For each genre name, it constructs a new `Genre` object with the genre name and inserts it.
        """
        out_genres = []
        for genre in genres.split(","):
            exists = Genre.exists_by_name(genre)
            if exists:
                out_genres.append(exists)
            else:
                # new genre, create and insert
                item = Genre(name=genre)
                genre_id = insert(item)
                item.id = genre_id
                out_genres.append(item)
        return out_genres

    @staticmethod
    def create_if_not_exists(name: str) -> Genre:
        """
        Create the given genre if it does not already exist

        Returns:
            Genre object; either newly created or existing
        """
        exists = Genre.exists_by_name(name)
        if exists:
            return exists

        # No existing entry; create one
        genre = Genre(name=name)
        genre_id = insert(genre)
        genre.id = genre_id
        return genre

    @classmethod
    def exists_by_name(cls, name: str) -> Optional[Genre]:
        """
        Check if an entry exists in the database by its name.
        This is separate from Base.exists_by_name because we want to match on the full genre name
        rather than partial match.

        Args:
            name (str): The name of the entry to check for.

        Returns:
            Optional[Genre]: The entry if it exists, otherwise None.
        """
        if not name or not isinstance(name, str):
            return None
        result = app_db.session.query(cls).filter(cls.name == name).one_or_none()
        return result
