from abc import ABC
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Optional


@dataclass
class MusicBrainzEntity(ABC):
    """Base class for all MusicBrainz entities"""

    name: str
    # MBID must be optional, since we still want to support entities that do
    # not exist on MusicBrainz
    mbid: Optional[str] = None
    image: Optional[str] = None


@dataclass
class Release(MusicBrainzEntity):
    rating: int = 0
    year: int = 0
    runtime: int = 0
    track_count: int = 0
    country: str = ""


# TODO: double check the valid kinds
ArtistKind = Literal["band", "artist"]


@dataclass
class Artist(MusicBrainzEntity):
    kind: ArtistKind = "artist"
    begin_date: datetime = datetime(year=1, month=1, day=1)
    end_date: datetime = datetime(year=1, month=1, day=1)
    country: str = ""


# TODO: double check the valid kinds
LabelKind = Literal["imprint"]


@dataclass
class Label(MusicBrainzEntity):
    # TODO: add appropriate default label kind value
    kind: LabelKind = ""
    begin_date: datetime = datetime(year=1, month=1, day=1)
    end_date: datetime = datetime(year=1, month=1, day=1)
    country: str = ""


@dataclass
class Country(MusicBrainzEntity):
    code: str = ""  # coutry code


@dataclass
class Genre(MusicBrainzEntity):
    pass


GoalStatus = Literal["ongoing", "complete"]


@dataclass
class Goal:
    data_added: datetime
    start: datetime
    end: datetime
    status: GoalStatus
    completed_on: datetime
    amount: int


@dataclass
class Review:
    data_added: datetime
    content: str


@dataclass
class ReleaseInfo:
    release: Release
    artist: Artist
    label: Label
    year: int
    physical_format: str
    track_count: int
    release_group_mbid: str
