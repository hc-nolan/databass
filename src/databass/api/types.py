"""Defines various helper types"""

from datetime import date
from typing import TypedDict, Optional


class EntityInfo(TypedDict, total=False):
    """Holds generic entity data"""

    name: str
    mbid: str
    begin: Optional[date]
    end: Optional[date]
    country: Optional[str]
    type: Optional[str]


class ArtistInfo(EntityInfo):
    """Artist entity data"""

    pass


class LabelInfo(EntityInfo):
    """Label entity data"""

    pass


class ReleaseInfo(TypedDict, total=False):
    """Release entity data"""

    release: dict[str, str]
    artist: dict[str, str]
    label: dict[str, str]
    date: str
    format: str
    track_count: str
    country: str
    release_group_id: str


class SearchResult(TypedDict, total=False):
    """MusicBrainz search result data"""

    name: str
    id: str
    life_span: dict[str, str]
    country: str
    type: str
