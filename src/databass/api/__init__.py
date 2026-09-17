"""
Implements classes for calling MusicBrainz and Discogs APIs and Util class for various misc tasks
"""

from .musicbrainz import MusicBrainz
from .discogs import Discogs
from .util import Util
from . import image
__all__ = ["MusicBrainz", "Discogs", "Util", "image"]
