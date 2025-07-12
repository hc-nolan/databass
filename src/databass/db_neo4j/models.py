from neomodel import (
    StructuredNode,
    StringProperty,
    IntegerProperty,
    UniqueIdProperty,
    RelationshipTo,
    DateTimeProperty,
    DateProperty,
)


class Base(StructuredNode):
    """Abstract base class for all entities"""

    __abstract_node__ = True
    uid = UniqueIdProperty()
    date_added = DateTimeProperty(required=True)


class MusicBrainzEntity(Base):
    """Abstract base class for entities from MusicBrainz"""

    __abstract_node__ = True
    name = StringProperty(required=True)
    mbid = StringProperty()
    image = StringProperty()


class Country(MusicBrainzEntity):
    """Database class for Country entities"""

    __label__ = "Country"
    code = StringProperty(required=True)


class Genre(MusicBrainzEntity):
    """Database class for Genre entities"""

    __label__ = "Genre"
    pass


class Artist(MusicBrainzEntity):
    """Database class for Artist entities"""

    __label__ = "Artist"
    artistID = IntegerProperty(required=True, unique_index=True)
    kind = StringProperty(required=True)
    # kind = StringProperty(choices={"group": "group", "person": "person"}, required=True)
    begin_date = DateProperty()
    end_date = DateProperty()
    country = RelationshipTo("Country", "IS_FROM")


class Label(MusicBrainzEntity):
    """Database class for Label entities"""

    __label__ = "Label"
    labelID = IntegerProperty(required=True, unique_index=True)
    # TODO: determine valid Label kinds
    kind = StringProperty(
        # choices={
        #     "imprint": "imprint",
        #     "production": "production",
        #     "original production": "original production",
        #     "distributor": "distributor",
        #     "publisher": "publisher",
        # },
        required=True,
    )
    begin_date = DateProperty()
    end_date = DateProperty()
    country = RelationshipTo("Country", "IS_FROM")


class Release(MusicBrainzEntity):
    """Database class for Release entities"""

    __label__ = "Release"
    releaseID = IntegerProperty(required=True, unique_index=True)
    listened = DateTimeProperty(required=True)
    rating = IntegerProperty(required=True)
    year = IntegerProperty(default=0)
    runtime = IntegerProperty(default=0)
    trackCount = IntegerProperty(default=0)
    artist = RelationshipTo("Artist", "MADE_BY")
    label = RelationshipTo("Label", "RELEASED_BY")
    country = RelationshipTo("Country", "RELEASED_IN")
    # TODO: decide if main genre should be separated
    genres = RelationshipTo("Genre", "HAS_GENRE")


class Review(Base):
    """Database class for Review entities"""

    content = StringProperty(required=True)
    release = RelationshipTo("Release", "IS_ABOUT")


class Goal(Base):
    """Database class for Goal entities"""

    start = DateTimeProperty(required=True)
    end = DateTimeProperty(required=True)
    completed_on = DateTimeProperty(required=True)
    status = StringProperty(
        required=True,
        # choices={"ongoing": "ongoing", "complete": "complete"}
    )
    amount = IntegerProperty(required=True)
    targets_release = RelationshipTo("Release", "TARGETS_RELEASE")
    targets_artist = RelationshipTo("Artist", "TARGETS_ARTIST")
    targets_label = RelationshipTo("Label", "TARGETS_LABEL")
