"""
Release, ArtistOrLabel, Label, and Artist are kept together in one module
rather than split further: Artist/Label subclass ArtistOrLabel (a hard,
non-deferrable module-level dependency), ArtistOrLabel's stats methods
(frequency_highest, average_ratings_bayesian, etc.) query Release columns
extensively, and Release.dynamic_search looks up Artist/Label by name. These
four classes form a single mutually-dependent unit reflecting the relational
schema itself, not a design flaw - splitting them further would require
either a deferred-import workaround or reintroducing a real cyclic import.
"""

from __future__ import annotations
from datetime import datetime, date
from typing import Any, Optional, List

from sqlalchemy import (
    String,
    Integer,
    ForeignKey,
    DateTime,
    Date,
    func,
    extract,
    or_,
    CheckConstraint,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
    joinedload,
    selectinload,
)
from sqlalchemy.engine.row import Row

from ..base import app_db
from ..operations import insert, update
from .base import MusicBrainzEntity
from .associations import (
    label_artist_association,
    label_genre_association,
    artist_genre_association,
    release_genre_association,
    release_collab_association,
)
from .query_utils import apply_comparison_filter, mean_avg_and_count, bayesian_avg
from .review import Review


class Release(MusicBrainzEntity):
    __tablename__ = "release"
    # Overrides MusicBrainzEntity.mbid: unlike Artist/Label, the same release
    # can legitimately be logged (relistened to) more than once, so its MBID
    # must not be unique here.
    mbid: Mapped[str | None] = mapped_column(String, unique=False, nullable=True)
    artist_id: Mapped[int] = mapped_column(ForeignKey("artist.id"))
    label_id: Mapped[int] = mapped_column(ForeignKey("label.id"))
    year: Mapped[int] = mapped_column(Integer)
    runtime: Mapped[int] = mapped_column(Integer)
    rating: Mapped[int] = mapped_column(
        Integer, CheckConstraint("rating >= 0 AND rating <= 100")
    )
    listen_date: Mapped[datetime] = mapped_column(DateTime)
    track_count: Mapped[int] = mapped_column(Integer)
    main_genre_id: Mapped[int] = mapped_column(ForeignKey("genre.id"))

    artist = relationship("Artist", back_populates="releases")
    label = relationship("Label", back_populates="releases")
    main_genre = relationship("Genre", back_populates="main_genres")
    genres = relationship(
        "Genre", secondary=release_genre_association, back_populates="releases"
    )
    collab_artists = relationship(
        "Artist",
        secondary=release_collab_association,
        back_populates="collab_releases",
    )
    reviews = relationship(
        "Review",
        cascade="all, delete-orphan",
        back_populates="release",
        order_by="Review.timestamp.desc()",
    )

    def __init__(
        self, mbid: str | None = None, artist_id: int = 0, label_id: int = 0, **kwargs
    ):
        super().__init__()
        self.mbid = mbid
        self.artist_id = artist_id
        self.label_id = label_id
        for key, value in kwargs.items():
            setattr(self, key, value)

    @classmethod
    def average_runtime(cls) -> float:
        """
        Calculate the average runtime of all Release entries.

        Returns:
            float: The average runtime of all Release entries,
                    rounded to 2 decimal places. If there are no Release entries, returns 0.
        """
        try:
            avg_runtime_ms = app_db.session.query(func.avg(cls.runtime)).scalar()
            avg_runtime_min = avg_runtime_ms / 60000
            result = round(avg_runtime_min, 2)
        except TypeError:
            result = 0
        except Exception:
            result = 0
        return result

    @classmethod
    def total_runtime(cls) -> float:
        """
        Calculate the total runtime of all Release entries.

        Returns:
            float: The total runtime of all Release entries, rounded to 2 decimal places.
                    If there are no Release entries, returns 0.
        """
        try:
            total_runtime_ms = app_db.session.query(func.sum(cls.runtime)).scalar()
            total_runtime_hours = total_runtime_ms / 3600000
            result = round(total_runtime_hours, 2)
        except Exception:
            result = 0
        return result

    @classmethod
    def ratings_lowest(cls, limit: int = 10) -> list[Release | None]:
        """
        Return a list of the lowest rated releases, up to the specified limit.

        Args:
            limit (int, optional): The maximum number of releases to return.
            If not provided, the default is 10. Must be a positive integer.

        Returns:
            list[Release | None]: A list of Release objects, ordered by rating in ascending order.

        Raises:
            ValueError: If the `limit` parameter is not a positive integer.
        """
        if not isinstance(limit, int) or limit <= 0:
            raise ValueError("Limit must be a positive integer.")
        result = (
            app_db.session.query(
                cls.id, cls.name, cls.rating, cls.artist_id, cls.label_id
            )
            .limit(limit)
            .order_by(cls.rating.asc())
            .all()
        )
        return result

    @classmethod
    def ratings_highest(cls, limit: int = 10) -> list[Release | None]:
        """
        Return a list of the highest rated releases, up to the specified limit.

        Args:
            limit (int, optional): The maximum number of releases to return.
            If not provided, the default is 10. Must be a positive integer.

        Returns:
            list[Release | None]: A list of Release objects, ordered by rating in descending order.

        Raises:
            ValueError: If the `limit` parameter is not a positive integer.
        """
        if not isinstance(limit, int) or limit <= 0:
            raise ValueError("Limit must be a positive integer.")
        result = (
            app_db.session.query(
                cls.id, cls.name, cls.rating, cls.artist_id, cls.label_id
            )
            .limit(limit)
            .order_by(cls.rating.desc())
            .all()
        )
        return result

    @classmethod
    def ratings_average(cls) -> float:
        """
        Retrieves the average rating for all releases.

        Returns:
            float: The average rating for all releases, rounded to 2 decimal places.
                   Returns 0.0 if no release exists or an exception is raised.
        """
        try:
            ratings = app_db.session.query(func.avg(cls.rating)).scalar()
            result = round(ratings or 0, 2)
        except Exception:
            result = 0.0
        return result

    @classmethod
    def home_data(cls) -> list[Row]:
        """
        Retrieves a list of data for the home page, including artist information,
        release information, and associated genres.

        Returns:
            list[Row]: A list of Release database entries

        The data is ordered by the release ID in descending order.
        """
        try:
            results = (app_db.session.query(cls).order_by(cls.id.desc())).all()
        except Exception:
            return []
        return results

    @classmethod
    def home_data_light(cls) -> list[Row]:
        """
        Retrieves lightweight (id, listen_date, runtime) rows for every release,
        ordered by listen date descending, then id descending.

        listen_date has no time component when set from the "log a listen" form
        (only edited manually), so most same-day rows tie on listen_date alone;
        breaking ties by id keeps same-day entries in the order they were logged.

        Cheap enough to run on every home page request even for large libraries,
        since it does not touch any relationships. Used to compute day-group
        pagination before hydrating only the current page's releases via `by_ids`.
        """
        try:
            results = (
                app_db.session.query(cls.id, cls.listen_date, cls.runtime)
                .order_by(cls.listen_date.desc(), cls.id.desc())
                .all()
            )
        except Exception:
            return []
        return results

    @classmethod
    def by_ids(cls, ids: list[int]) -> list[Release]:
        """
        Retrieves full Release objects for the given IDs, with the relationships
        needed to build a home-page entry (artist, label, main_genre, genres,
        reviews) eagerly loaded to avoid N+1 queries.
        """
        if not ids:
            return []
        return (
            app_db.session.query(cls)
            .filter(cls.id.in_(ids))
            .options(
                joinedload(cls.artist),
                joinedload(cls.label),
                joinedload(cls.main_genre),
                selectinload(cls.genres),
                selectinload(cls.reviews),
            )
            .all()
        )

    @classmethod
    def exists_by_mbid(cls, mbid: str) -> Optional[Release]:
        """
        Overrides MusicBrainzEntity.exists_by_mbid: since a release's MBID is
        no longer unique (the same release can be logged/relistened to more
        than once), use `.first()` instead of `.one_or_none()` so a second
        logged listen of the same release doesn't raise MultipleResultsFound.
        """
        if not mbid or not isinstance(mbid, str):
            return None
        try:
            result = app_db.session.query(cls).filter(cls.mbid == mbid).first()
        except Exception:
            app_db.session.rollback()
            return None
        return result or None

    @classmethod
    def listens_this_year(cls) -> int:
        """
        Counts the number of releases listened to during the current year.

        Returns:
            int: The total number of releases listened to during the current year.
                 Returns 0 if an exception is encountered.
        """
        try:
            current_year = datetime.now().year
            results = (
                app_db.session.query(func.count(Release.id))
                .filter(extract("year", Release.listen_date) == current_year)
                .scalar()
            )
        except Exception:
            return 0
        return results

    @classmethod
    def runtime_this_year(cls) -> float:
        """
        Total listening time, in hours, for releases added this year.

        Returns:
            float: Total hours, rounded to 1 decimal place. Returns 0.0 on error
            or if no releases have been added this year.
        """
        try:
            current_year = datetime.now().year
            total_ms = (
                app_db.session.query(func.sum(cls.runtime))
                .filter(extract("year", cls.date_added) == current_year)
                .scalar()
            )
            if not total_ms:
                return 0.0
            return round(total_ms / 3600000, 1)
        except Exception:
            return 0.0

    @classmethod
    def average_rating_this_year(cls) -> float:
        """
        Average rating (0-100 scale) for releases added this year.

        Returns:
            float: Average rating, rounded to 1 decimal place. Returns 0.0 on error
            or if no releases have been added this year.
        """
        try:
            current_year = datetime.now().year
            avg = (
                app_db.session.query(func.avg(cls.rating))
                .filter(extract("year", cls.date_added) == current_year)
                .scalar()
            )
            return round(avg or 0, 1)
        except Exception:
            return 0.0

    @classmethod
    def rating_distribution(cls, year: Optional[int] = None) -> dict:
        """
        Buckets release ratings (stored 0-100) into ten deciles for a
        histogram, and calculates the median.

        Args:
            year (int, optional): If given, only considers releases listened
                to in that calendar year. Defaults to all-time.

        Returns:
            dict: {
                "buckets": list[int] of length 10, index 0 = ratings 0-9, ... index 9 = ratings 90-100,
                "median": float, the median rating on the 0-10 display scale,
            }
        """
        query = app_db.session.query(cls.rating)
        if year is not None:
            query = query.filter(extract("year", cls.listen_date) == year)
        ratings = [row[0] for row in query.all()]
        buckets = [0] * 10
        if not ratings:
            return {"buckets": buckets, "median": 0.0}
        for rating in ratings:
            buckets[min(rating // 10, 9)] += 1
        sorted_ratings = sorted(ratings)
        count = len(sorted_ratings)
        mid = count // 2
        if count % 2 == 0:
            median = (sorted_ratings[mid - 1] + sorted_ratings[mid]) / 2
        else:
            median = sorted_ratings[mid]
        return {"buckets": buckets, "median": round(median / 10, 1)}

    @classmethod
    def listen_years(cls) -> list[int]:
        """Distinct calendar years with at least one logged listen, newest first."""
        rows = (
            app_db.session.query(extract("year", cls.listen_date).cast(Integer))
            .distinct()
            .all()
        )
        return sorted({int(row[0]) for row in rows if row[0] is not None}, reverse=True)

    @classmethod
    def stats_for_year(cls, year: Optional[int] = None) -> dict:
        """
        Aggregate release count, total runtime (hours), and mean rating
        (0-10 scale) for a calendar year, or across all time if `year` is None.
        """
        query = app_db.session.query(
            func.count(cls.id),
            func.sum(cls.runtime),
            func.avg(cls.rating),
        )
        if year is not None:
            query = query.filter(extract("year", cls.listen_date) == year)
        count, total_runtime, avg_rating = query.one()
        return {
            "count": count or 0,
            "runtime_hours": round((total_runtime or 0) / 3600000, 1),
            "mean_rating": round((avg_rating or 0) / 10, 1),
        }

    @classmethod
    def first_listen_date(cls) -> Optional[date]:
        """Date of the earliest logged listen, or None if nothing is logged."""
        earliest = app_db.session.query(func.min(cls.listen_date)).scalar()
        if not earliest:
            return None
        return earliest.date() if hasattr(earliest, "date") else earliest

    @classmethod
    def days_span(cls, year: Optional[int] = None) -> int:
        """
        Number of days elapsed in a calendar year (up to today, if it's the
        current year), or since the earliest logged listen if `year` is None.
        """
        today = date.today()
        if year is not None:
            start = date(year, 1, 1)
            end = today if year == today.year else date(year, 12, 31)
            return max((end - start).days + 1, 1)
        earliest = app_db.session.query(func.min(cls.listen_date)).scalar()
        if not earliest:
            return 1
        start = earliest.date() if hasattr(earliest, "date") else earliest
        return max((today - start).days + 1, 1)

    @classmethod
    def listen_dates(cls, year: Optional[int] = None) -> list[date]:
        """
        Listen dates (one entry per logged listen, duplicates included) for a
        calendar year, or across all time if `year` is None.
        """
        query = app_db.session.query(cls.listen_date)
        if year is not None:
            query = query.filter(extract("year", cls.listen_date) == year)
        return [
            row[0].date() if hasattr(row[0], "date") else row[0]
            for row in query.all()
            if row[0] is not None
        ]

    @classmethod
    def listens_by_month(cls, year: int) -> list[dict]:
        """
        Monthly listen counts for a calendar year, from January up to the
        current month if `year` is the current year, otherwise through December.
        """
        month_names = [
            "JAN", "FEB", "MAR", "APR", "MAY", "JUN",
            "JUL", "AUG", "SEP", "OCT", "NOV", "DEC",
        ]
        rows = (
            app_db.session.query(
                extract("month", cls.listen_date).cast(Integer).label("month"),
                func.count(cls.id),
            )
            .filter(extract("year", cls.listen_date) == year)
            .group_by("month")
            .all()
        )
        counts = {int(month): count for month, count in rows}
        today = date.today()
        last_month = today.month if year == today.year else 12
        return [
            {"label": month_names[m - 1], "value": counts.get(m, 0)}
            for m in range(1, last_month + 1)
        ]

    @classmethod
    def listens_by_year(cls) -> list[dict]:
        """Listen counts grouped by calendar year, ascending, across all time."""
        # Group/order by the expression itself rather than the "year" label: Release
        # already has a real `year` column, and Postgres (unlike SQLite) resolves a
        # bare "year" reference in GROUP BY/ORDER BY to that column, not this alias.
        year_expr = extract("year", cls.listen_date).cast(Integer)
        rows = (
            app_db.session.query(
                year_expr.label("year"),
                func.count(cls.id),
            )
            .group_by(year_expr)
            .order_by(year_expr)
            .all()
        )
        return [
            {"label": str(int(year)), "value": count}
            for year, count in rows
            if year is not None
        ]

    @classmethod
    def dynamic_search(cls, data: dict) -> list[Release]:
        """
        Dynamically search for Release objects based on the provided search criteria.

        Args:
            data (dict): A dictionary containing the search criteria.

        Returns:
            list[Release]: A list of Release objects representing the matching releases.
        """
        if not isinstance(data, dict):
            raise ValueError("Search criteria must be a dictionary")

        query = app_db.session.query(cls)
        search_keys = [
            "name",
            "artist",
            "country",
            "main_genre",
            "label",
            "rating",
            "year",
        ]
        for key, value in data.items():
            if value == "" or value == [""] or key not in search_keys:
                pass  # Empty value or key not meant for searching, do nothing
            elif key == "name":
                query = query.filter(cls.name.ilike(f"%{value}%"))
            elif key == "artist":
                artist_ids = Artist.id_by_matching_name(name=value)
                query = query.filter(cls.artist_id.in_(artist_ids))
            elif key == "label":
                label_ids = Label.id_by_matching_name(name=value)
                query = query.filter(cls.label_id.in_(label_ids))
            elif key == "rating":
                operator = data["rating_comparison"]  # <, ==, or >
                query = apply_comparison_filter(
                    query=query, model=cls, key=key, operator=operator, value=value
                )
            elif key == "year":
                operator = data["year_comparison"]  # <, ==, or >
                query = apply_comparison_filter(
                    query=query, model=cls, key=key, operator=operator, value=value
                )
            elif key == "main_genre":
                query = query.filter(cls.main_genre.has(name=value))
            else:
                # generic handler for any other search key not matching above (country, genre)
                query = query.filter(getattr(cls, key) == value)
        results = query.order_by(cls.id).all()
        return results

    @classmethod
    def browse_search(
        cls,
        q: str = "",
        country: str = "",
        genre: str = "",
        year_min: Optional[int] = None,
        rating_min: Optional[int] = None,
        sort: str = "listened",
        page: int = 1,
        per_page: int = 30,
    ) -> tuple[list[Release], int]:
        """
        Search, filter, sort, and paginate releases at the SQL level for the
        Browse page.

        Only the current page's rows are hydrated with relationships
        (artist, label, main_genre); filtering/sorting/counting all run
        against the full table without loading it into Python.

        Returns:
            tuple[list[Release], int]: (releases for the requested page,
            total count of releases matching the filters).
        """
        query = app_db.session.query(cls.id)
        if q:
            artist_ids = Artist.id_by_matching_name(q)
            query = query.filter(
                or_(cls.name.ilike(f"%{q}%"), cls.artist_id.in_(artist_ids))
            )
        if country:
            query = query.filter(cls.country == country)
        if genre:
            query = query.filter(cls.main_genre.has(name=genre))
        if year_min:
            query = query.filter(cls.year >= year_min)
        if rating_min:
            query = query.filter(cls.rating >= rating_min)

        total = query.count()

        sort_map = {
            "listened": cls.listen_date.desc(),
            "rating": cls.rating.desc(),
            "year": cls.year.desc(),
            "az": cls.name.asc(),
        }
        query = query.order_by(sort_map.get(sort, sort_map["listened"]))

        ids = [
            row.id
            for row in query.offset((page - 1) * per_page).limit(per_page).all()
        ]
        releases_by_id = {r.id: r for r in cls.by_ids(ids)}
        return [releases_by_id[i] for i in ids if i in releases_by_id], total

    @classmethod
    def get_reviews(
        cls,
        release_id: int,
    ) -> list[Row]:
        """
        Retrieves a list of reviews for the specified release ID.

        Args:
            release_id (int): The ID of the release to retrieve reviews for.

        Returns:
            list[Row]: List of review objects, where each contains timestamp & text of the review.

        Raises:
            ValueError: If `release_id` is a non-integer or an integer less than 0.
        """
        if not isinstance(release_id, int) or release_id < 0:
            raise ValueError("Release ID must be a positive integer.")
        reviews = (
            app_db.session.query(
                func.to_char(Review.timestamp, "YYYY-MM-DD HH24:MI").label("timestamp"),
                Review.text,
            ).where(Review.release_id == release_id)
        ).all()
        return reviews

    @staticmethod
    def create_new(data: dict) -> int:
        """
        Creates a new release record in the database and retrieves the assigned ID.

        Args:
            data (dict): A dictionary containing the data for the new release,
                         including the name, artist name, label name, and release group MBID.

        Returns:
            int: The ID of the newly created release.
        """
        if not isinstance(data, dict):
            raise ValueError("data argument must be a dictionary")
        from ...api import Util, image

        # If the user picked specific art during the search flow, the chosen
        # image arrives as a URL; keep it out of the DB row so a raw URL is
        # never persisted, and download it (and write the file path) below.
        image_url = data.pop("image", None)

        new_release = Release(**data)
        release_id = insert(new_release)

        # A failure to fetch the cover image shouldn't fail the whole
        # submission, since the release itself has already been saved.
        try:
            if image_url is not None:
                try:
                    new_image = Util.get_image_from_url(
                        entity_type="release", url=image_url
                    )
                except Exception:
                    # The user's chosen art couldn't be downloaded; fall back to
                    # the automatic CoverArtArchive/Discogs lookup rather than
                    # saving the release with no art at all.
                    print(
                        f"WARNING: Chosen image download failed for release "
                        f"{release_id}; falling back to auto-fetch"
                    )
                    new_image = image.fetch_image(
                        entity_type="release",
                        release_name=data["name"],
                        artist_name=data["artist_name"],
                        label_name=data["label_name"],
                        mbid=data["release_group_mbid"],
                    )
            else:
                new_image = image.fetch_image(
                    entity_type="release",
                    release_name=data["name"],
                    artist_name=data["artist_name"],
                    label_name=data["label_name"],
                    mbid=data["release_group_mbid"],
                )
            if new_image is not None:
                new_release.image = new_image
                update(new_release)
        except Exception as err:
            print(f"WARNING: Could not fetch image for release {release_id}: {err}")

        return release_id


class ArtistOrLabel(MusicBrainzEntity):
    """
    Abstract base class for Artist and Label models with shared fields.

    Attributes:
        id: Primary key identifier
        mbid: Optional MusicBrainz ID
        name: Name of the artist/label
        country: Optional country of origin
        type: Optional type classification
        begin: Optional start date
        end: Optional end date
        image: Optional image file path
    """

    __abstract__ = True

    type: Mapped[str | None] = mapped_column(String)
    begin: Mapped[date | None] = mapped_column(Date, nullable=True)
    end: Mapped[date | None] = mapped_column(Date, nullable=True)

    def __init__(self, **kwargs: Any) -> None:
        super().__init__()
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id={self.id}, name='{self.name}')"

    @classmethod
    def period_counts(cls, year: Optional[int] = None) -> dict:
        """
        Distinct entity (Artist or Label) count and average releases per
        entity, for a calendar year or across all time if `year` is None.

        Returns:
            dict: {"count": int, "avg_releases": float}
        """
        relation_id = (
            Release.artist_id if cls.__tablename__ == "artist" else Release.label_id
        )
        query = (
            app_db.session.query(relation_id, func.count(Release.id))
            .join(cls, relation_id == cls.id)
            .where(cls.name.notin_(["[NONE]", "Various Artists", "", "[no label]"]))
            .group_by(relation_id)
        )
        if year is not None:
            query = query.filter(extract("year", Release.listen_date) == year)
        rows = query.all()
        entity_count = len(rows)
        total_releases = sum(row[1] for row in rows)
        avg = round(total_releases / entity_count, 1) if entity_count else 0.0
        return {"count": entity_count, "avg_releases": avg}

    @classmethod
    def frequency_highest(cls, limit: int = 10) -> list[dict]:
        """
        Retrieve the top `limit` most frequently occurring Artists or Labels,
        along with the count of their associated Releases and their image file paths.

        This method is a class method, so it can be called on either the Artist or Label model classes.

        Args:
            limit (int): The maximum number of results to return, defaults to 10.

        Returns:
            list[dict]: A list of dictionaries, where each dictionary contains the following keys:
                - "name": The name of the Artist or Label.
                - "count": The number of Releases associated with the Artist or Label.
                - "image": The file path of the image associated with the Artist or Label.

        Raises:
            ValueError: If `limit` is not a positive integer.
        """
        if not isinstance(limit, int) or limit <= 0:
            raise ValueError("Limit must be a positive integer.")
        relation_id = (
            Release.artist_id if cls.__tablename__ == "artist" else Release.label_id
        )

        try:
            query = (
                app_db.session.query(
                    cls.name, func.count(relation_id).label("count"), cls.image
                )
                .join(Release, relation_id == cls.id)
                .where(cls.name.notin_(["[NONE]", "Various Artists", "", "[no label]"]))
                .group_by(cls.name, cls.image)
                .order_by(func.count(relation_id).desc())
                .limit(limit)
                .all()
            )
        except Exception:
            return []
        results = [
            {"name": result.name, "count": result.count, "image": result.image}
            for result in query
        ]
        return results

    @classmethod
    def on_repeat(cls, days: int = 90, limit: int = 3) -> list[dict]:
        """
        Retrieve the entities (Artists or Labels) listened to most often within
        the last `days` days, along with their release count and average rating
        in that window.

        Args:
            days (int): Size of the trailing window, in days. Defaults to 90.
            limit (int): Maximum number of entities to return. Defaults to 3.

        Returns:
            list[dict]: Each dict has "id", "name", "image", "count", and
            "average_rating" (0-10 scale, one decimal). Empty list on error.
        """
        from datetime import timedelta

        relation_id = (
            Release.artist_id if cls.__tablename__ == "artist" else Release.label_id
        )
        cutoff = datetime.now() - timedelta(days=days)
        try:
            query = (
                app_db.session.query(
                    cls.id,
                    cls.name,
                    cls.image,
                    func.count(Release.id).label("count"),
                    func.avg(Release.rating).label("average_rating"),
                )
                .join(Release, relation_id == cls.id)
                .where(cls.name.notin_(["[NONE]", "Various Artists", "", "[no label]"]))
                .where(Release.listen_date >= cutoff)
                .group_by(cls.id, cls.name, cls.image)
                .order_by(func.count(Release.id).desc())
                .limit(limit)
                .all()
            )
        except Exception:
            return []
        return [
            {
                "id": row.id,
                "name": row.name,
                "image": row.image,
                "count": row.count,
                "average_rating": round((row.average_rating or 0) / 10, 1),
            }
            for row in query
        ]

    @classmethod
    def average_ratings_and_total_counts(
        cls,
    ) -> list[Row]:
        """
        Calculates the average ratings and total release counts for entities (Artists or Labels) in the database.

        Returns:
            list[Row]: A list of database rows containing the following fields:
                - id: The unique identifier for the entity.
                - name: The name of the entity.
                - average_rating: The average rating for the entity's releases.
                - release_count: The total number of releases for the entity.
                - image: The file path of the image associated with the entity.

        Raises:
            TypeError: If the method is called on a class that is not either the Artist or Label class.
        """
        if cls.__tablename__ == "artist":
            relation_id = Release.artist_id
        elif cls.__tablename__ == "label":
            relation_id = Release.label_id
        else:
            raise TypeError("Method only supported by Artist and Label classes.")
        try:
            entities = (
                app_db.session.query(
                    cls.id,
                    cls.name,
                    func.avg(Release.rating).label("average_rating"),
                    func.count(Release.id).label("release_count"),
                    cls.image,
                )
                .join(Release, relation_id == cls.id)
                .where(cls.name.notin_(["[NONE]", "Various Artists"]))
                .having(func.count(Release.id) > 1)
                .group_by(cls.name, cls.id)
                .order_by(func.avg(Release.rating).desc())
                .all()
            )
        except Exception:
            return []
        return entities

    @classmethod
    def browse_search(
        cls,
        q: str = "",
        country: str = "",
        type_: str = "",
        releases_min: Optional[int] = None,
        rating_min: Optional[int] = None,
        sort: str = "releases",
        page: int = 1,
        per_page: int = 30,
    ) -> tuple[list[Row], int]:
        """
        Search, filter, sort, and paginate Artists or Labels at the SQL
        level for the Browse page, joined with each entity's release count
        and average rating.

        Returns:
            tuple[list[Row], int]: (rows for the requested page, total count
            of entities matching the filters). Each row has id, name, image,
            country, type, release_count, average_rating.
        """
        if cls.__tablename__ == "artist":
            relation_id = Release.artist_id
        elif cls.__tablename__ == "label":
            relation_id = Release.label_id
        else:
            raise TypeError("Method only supported by Artist and Label classes.")

        query = (
            app_db.session.query(
                cls.id,
                cls.name,
                cls.image,
                cls.country,
                cls.type,
                func.count(Release.id).label("release_count"),
                func.avg(Release.rating).label("average_rating"),
            )
            .join(Release, relation_id == cls.id)
            .where(cls.name.notin_(["[NONE]", "Various Artists", "", "[no label]"]))
            .group_by(cls.id, cls.name, cls.image, cls.country, cls.type)
        )
        if q:
            query = query.filter(cls.name.ilike(f"%{q}%"))
        if country:
            query = query.filter(cls.country == country)
        if type_:
            query = query.filter(cls.type == type_)
        if releases_min:
            query = query.having(func.count(Release.id) >= releases_min)
        if rating_min:
            query = query.having(func.avg(Release.rating) >= rating_min)

        total = query.count()

        sort_map = {
            "releases": func.count(Release.id).desc(),
            "rating": func.avg(Release.rating).desc(),
            "az": cls.name.asc(),
        }
        query = query.order_by(sort_map.get(sort, sort_map["releases"]))

        rows = query.offset((page - 1) * per_page).limit(per_page).all()
        return rows, total

    @classmethod
    def average_ratings_bayesian(
        cls,
        sort_order: str = "desc",
    ) -> list[dict]:
        """
        Calculates the Bayesian average rating for entities (Artists or Labels) in the database, taking into account both the average rating and the number of releases for each entity.

        The Bayesian average is calculated as a weighted average between the entity's average rating and the overall mean average rating, with the weight determined by the number of releases for that entity.

        Args:
            sort_order (str, optional): The order to sort the results, either 'desc' (descending) or 'asc' (ascending). Defaults to 'desc'.

        Returns:
            list[dict]: A list of dictionaries containing the following fields for each entity:
                - id: The unique identifier for the entity.
                - name: The name of the entity.
                - rating: The Bayesian average rating for the entity.
                - image: The file path of the image associated with the entity.
                - count: The total number of releases for the entity.

        Raises:
            ValueError: If the `sort_order` parameter is not 'desc' or 'asc'.
        """
        if not isinstance(sort_order, str) or sort_order not in ["desc", "asc"]:
            raise ValueError(
                f"Unrecognized sort order: {sort_order}. Valid orders are: 'desc', 'asc'"
            )

        entities = cls.average_ratings_and_total_counts()
        entity_count = len(entities)
        if entity_count == 0:
            return []

        mean_avg, mean_count = mean_avg_and_count(entities)
        items = []
        for entity in entities:
            entity_avg = int(entity.average_rating)
            entity_count = int(entity.release_count)

            weight = entity_count / (entity_count + mean_count)
            bayesian = bayesian_avg(
                item_weight=weight, item_avg=entity_avg, mean_avg=mean_avg
            )
            items.append(
                {
                    "id": entity.id,
                    "name": entity.name,
                    "rating": round(bayesian),
                    "image": entity.image,
                    "count": entity.release_count,
                }
            )

        # Sort results by Bayesian average
        # 'order' is used for sorted(reverse=..)
        # Hence, order = True means descending; False means ascending
        order = True
        if sort_order == "asc":
            order = False

        sorted_entities = sorted(items, key=lambda k: k["rating"], reverse=order)
        return sorted_entities

    @classmethod
    def statistic(cls, sort_order: str, metric: str, item_property: str) -> list[dict]:
        # Currently unused
        """
        Search for a typical statistic, i.e. average rating, total count
        :param sort_order: 'desc' or 'asc'; determines the order to sort the results before return
        :param metric: The type of statistic to retrieve; 'average' or 'total'
        :param item_property: The property (column) to calculate the statistic of
        :return: Sorted list of dictionaries containing data related to the Artist/Label and the queried statistic
        """
        if sort_order not in ["asc", "desc"]:
            raise ValueError(
                f"Unrecognized sort order: {sort_order}. Valid orders are: 'desc', 'asc'"
            )

        order = "desc"
        if sort_order == "lowest":
            order = "asc"

        result = cls.average_ratings_and_total_counts()
        if metric == "average":
            if item_property == "rating":
                return sorted(result, key=lambda k: k["rating"], reverse=order)
            if item_property == "runtime":
                return sorted(result, key=lambda k: k["runtime"], reverse=order)

        elif metric == "total":
            if item_property == "count":
                return sorted(result, key=lambda k: k["count"], reverse=order)
            if item_property == "runtime":
                return sorted(result, key=lambda k: k["runtime"], reverse=order)

    @classmethod
    def dynamic_search(cls, filters: dict) -> List[ArtistOrLabel]:
        """
        Perform a dynamic search on the database model represented by `cls`, using the provided `filters` dictionary.

        The `filters` dictionary can contain the following keys:
        - `name`: Perform a partial string match on the `name` column.
        - `begin_date`: Perform a comparison filter on the `begin_date` column, using the `begin_comparison` key to specify the comparison operator (`<`, `=`, or `>`).
        - `end_date`: Perform a comparison filter on the `end_date` column, using the `end_comparison` key to specify the comparison operator (`<`, `=`, or `>`).
        - Other keys: Filter the results where the column value matches the provided value.

        Returns:
            A list of model instances that match the provided filters.

        Raises:
            ValueError: If `filters` is not a dict
        """
        if not isinstance(filters, dict):
            raise ValueError("filters must be a dictionary")

        query = app_db.session.query(cls)
        search_keys = ["name", "begin_date", "end_date", "country", "type"]
        for key, value in filters.items():
            if value == "" or key not in search_keys:
                pass  # Empty value or key not meant from searching, pass
            elif key == "name":
                query = query.filter(cls.name.ilike(f"%{value}%"))
            elif key == "begin_date":
                operator = filters["begin_comparison"]
                if operator not in ["<", "=", ">"]:
                    raise ValueError(
                        f"Unexpected operator value for begin_comparison: {operator}"
                    )
                query = apply_comparison_filter(
                    query=query, model=cls, key=key, operator=operator, value=value
                )
            elif key == "end_date":
                operator = filters["end_comparison"]
                if operator not in ["<", "=", ">"]:
                    raise ValueError(
                        f"Unexpected operator value for end_comparison: {operator}"
                    )
                query = apply_comparison_filter(
                    query=query, model=cls, key=key, operator=operator, value=value
                )
            else:
                query = query.filter(getattr(cls, key) == value)
        # Filter out names that do not refer to a specific real-world entity
        results = (
            query.where(cls.name != "[NONE]")
            .where(cls.name != "[no label]")
            .where(cls.name != "Various Artists")
            .all()
        )
        return results

    @classmethod
    def create_if_not_exist(cls, name: str, mbid: str = None) -> int:
        """
        Create a new instance of the model if it does not already exist in the database.

        Args:
            name (str): The name of the item to create.
            mbid (str): [optional] The MusicBrainz ID of the item to create.

        Returns:
            int: The ID of the created or existing item.
        """
        from ...api import MusicBrainz, image

        item_exists = cls.exists_by_mbid(mbid)
        if item_exists:
            return item_exists.id
        item_exists = cls.exists_by_name(name)
        if item_exists:
            return item_exists.id
        else:
            # Grab image, start/end date, type, and insert
            if cls.__name__ == "Label":
                item_search = MusicBrainz.label_search(name=name, mbid=mbid)
                if item_search is None:
                    item_search = {"name": name}
                new_item = cls(**item_search)
            elif cls.__name__ == "Artist":
                item_search = MusicBrainz.artist_search(name=name, mbid=mbid)
                if item_search is None:
                    item_search = {"name": name}
                new_item = cls(**item_search)
            else:
                raise ValueError(
                    f"Unsupported class: {cls} - supported classes are Label and Artist"
                )

            # check if we got a mbid from the above search
            if item_search["mbid"]:
                item_exists = cls.exists_by_mbid(item_search["mbid"])
                if item_exists:
                    return item_exists.id

            item_id = insert(new_item)
            # TODO: see if image.fetch_image() can be refactored; instead of label_name and artist_name use item_name
            if cls.__name__ == "Label":
                new_image = image.fetch_image(
                    entity_type="label",
                    label_name=name,
                    mbid=None,
                    release_name=None,
                    artist_name=None,
                )
            elif cls.__name__ == "Artist":
                new_image = image.fetch_image(
                    entity_type="artist",
                    artist_name=name,
                    mbid=None,
                    release_name=None,
                    label_name=None,
                )
            else:
                new_image = None
            if new_image is not None:
                new_item.image = new_image
                update(new_item)
            # TODO: figure out a way to call image.fetch_image() upon any insertion so it doesn't need to be manually called
        return item_id


class Label(ArtistOrLabel):
    __tablename__ = "label"

    releases = relationship(
        "Release", back_populates="label", cascade="all, delete-orphan"
    )
    artists = relationship(
        "Artist", secondary=label_artist_association, back_populates="labels"
    )
    genres = relationship(
        "Genre", secondary=label_genre_association, back_populates="labels"
    )


class Artist(ArtistOrLabel):
    __tablename__ = "artist"

    releases = relationship(
        "Release", back_populates="artist", cascade="all, delete-orphan"
    )
    labels = relationship(
        "Label", secondary=label_artist_association, back_populates="artists"
    )
    genres = relationship(
        "Genre", secondary=artist_genre_association, back_populates="artists"
    )
    # Releases manually credited to this artist as a collaborator via
    # release_collab_association, on top of their own `releases`.
    collab_releases = relationship(
        "Release",
        secondary=release_collab_association,
        back_populates="collab_artists",
    )

    @property
    def all_releases(self) -> list[Release]:
        """
        This artist's full discography: releases they're the primary credit
        for, plus releases manually credited to them as a collaborator (see
        `release_collab_association`), newest listen first (ties broken by
        id, consistent with Release.home_data_light / build_day_groups).

        Deduped in case a release's own primary artist is also (redundantly)
        added as one of its collab artists.
        """
        combined = dict.fromkeys([*self.releases, *self.collab_releases])
        return sorted(combined, key=lambda r: (r.listen_date, r.id), reverse=True)
