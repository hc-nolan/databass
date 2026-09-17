from __future__ import annotations
from datetime import datetime

from sqlalchemy import String, Integer, DateTime, func, distinct, or_
from sqlalchemy.orm import Mapped, mapped_column

from ..base import app_db
from ..operations import update
from .base import Base
from .catalog import Release


class Goal(Base):
    __tablename__ = "goal"
    start: Mapped[datetime] = mapped_column(DateTime)
    end: Mapped[datetime] = mapped_column(DateTime)
    completed: Mapped[datetime | None] = mapped_column(DateTime)
    type: Mapped[str] = mapped_column(String)  # i.e. release, album, label
    amount: Mapped[int] = mapped_column(Integer)

    @property
    def new_releases_since_start_date(self):
        """
        Returns the count of releases with a listen_date within the Goal's
        [start, end] window. This property is used to determine if the Goal
        has been met, based on the number of new releases logged during it.
        """
        return (
            app_db.session.query(func.count(Release.id))
            .filter(Release.listen_date >= self.start, Release.listen_date <= self.end)
            .scalar()
        )

    @property
    def new_artists_since_start_date(self):
        """
        Returns the count of distinct artists with a release logged (listen_date
        within the Goal's [start, end] window).
        """
        return (
            app_db.session.query(func.count(distinct(Release.artist_id)))
            .filter(Release.listen_date >= self.start, Release.listen_date <= self.end)
            .scalar()
        )

    @property
    def new_labels_since_start_date(self):
        """
        Returns the count of distinct labels with a release logged (listen_date
        within the Goal's [start, end] window).
        """
        return (
            app_db.session.query(func.count(distinct(Release.label_id)))
            .filter(Release.listen_date >= self.start, Release.listen_date <= self.end)
            .scalar()
        )

    @property
    def current_amount(self):
        """
        Returns the current progress towards the Goal, using the property matching its `type`.
        """
        match self.type:
            case "artist":
                return self.new_artists_since_start_date
            case "label":
                return self.new_labels_since_start_date
            case _:
                return self.new_releases_since_start_date

    def update_goal(self):
        """
        Updates the `end_actual` attribute of the `Goal` instance if the current amount
        since the goal's `start_date` is greater than or equal to the `amount` attribute.

        This method is used to check if a goal has been met, based on the current amount since
        the goal's start date. If the goal has been met, the `end_actual` attribute is updated
        to the current time.
        """
        print(f"Target amount: {self.amount} - Actual amount: {self.current_amount}")
        if self.type in ("release", "artist", "label"):
            if self.current_amount >= self.amount:
                print("Updating end_actual to current time")
                self.completed = datetime.now()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        for key, value in kwargs.items():
            setattr(self, key, value)

    @classmethod
    def get_incomplete(cls) -> list[Goal] | None:
        """
        Query database for goals without an end_actual date, meaning they have not been completed
        Returns a list of the goals if found; none otherwise
        """
        try:
            query = app_db.session.query(cls).where(cls.completed.is_(None))
            results = query.all()
        except Exception:
            return []
        if results:
            return results
        return []

    @classmethod
    def get_past(cls) -> list[Goal]:
        """
        Query database for goals that are either completed, or incomplete with an
        end date in the past (i.e. missed). Returns the goals newest-ended first.
        """
        try:
            query = (
                app_db.session.query(cls)
                .where(or_(cls.completed.isnot(None), cls.end < datetime.now()))
                .order_by(cls.end.desc())
            )
            return query.all()
        except Exception:
            return []

    @classmethod
    def check_goals(cls) -> list[Goal]:
        """
        Checks all incomplete goals and updates them if the goal has been met.

        This method retrieves all incomplete goals from the database, then for each goal it calls the `update_goal()` method to check if the goal has been met based on the number of new releases since the goal's start date. If the goal has been met, the `end_actual` attribute is updated to the current time, and the updated goal is saved to the database.

        Returns the list of goals that were newly completed by this check.
        """
        newly_completed = []
        active_goals = cls.get_incomplete()
        if active_goals is not None:
            for goal in active_goals:
                goal.update_goal()
                if goal.completed:
                    # Goal is complete; updating db entry
                    update(goal)
                    newly_completed.append(goal)
        return newly_completed
