"""
Many-to-many association tables shared across model classes. Kept separate
from the classes themselves since e.g. label_artist_association is needed by
both Label and Artist.
"""

from sqlalchemy import Table, Column, ForeignKey

from .base import Base

# Relationship tables
label_artist_association = Table(
    "label_artist_association",
    Base.metadata,
    Column("label_id", ForeignKey("label.id", ondelete="CASCADE"), primary_key=True),
    Column("artist_id", ForeignKey("artist.id", ondelete="CASCADE"), primary_key=True),
)

label_genre_association = Table(
    "label_genre_association",
    Base.metadata,
    Column("label_id", ForeignKey("label.id", ondelete="CASCADE"), primary_key=True),
    Column("genre_id", ForeignKey("genre.id", ondelete="CASCADE"), primary_key=True),
)

artist_genre_association = Table(
    "artist_genre_association",
    Base.metadata,
    Column("artist_id", ForeignKey("artist.id", ondelete="CASCADE"), primary_key=True),
    Column("genre_id", ForeignKey("genre.id", ondelete="CASCADE"), primary_key=True),
)

release_genre_association = Table(
    "release_genre_association",
    Base.metadata,
    Column("release_id", ForeignKey("release.id"), primary_key=True),
    Column("genre_id", ForeignKey("genre.id"), primary_key=True),
)

# Manually-declared collaboration credits: lets a release be included in an
# artist's discography in addition to (not instead of) its primary
# Release.artist_id credit. Needed because collaborative releases are
# inconsistently credited upstream (e.g. Sour Soul is credited solely to
# BADBADNOTGOOD, but should also show up under Ghostface Killah).
release_collab_association = Table(
    "release_collab_association",
    Base.metadata,
    Column("release_id", ForeignKey("release.id", ondelete="CASCADE"), primary_key=True),
    Column("artist_id", ForeignKey("artist.id", ondelete="CASCADE"), primary_key=True),
)
