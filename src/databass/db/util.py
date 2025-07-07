from typing import Type
from sqlalchemy.orm import query as sql_query
from .operations import insert

# from .models import *
# above imports all of the below
from sqlalchemy import extract, Integer
from sqlalchemy.exc import IntegrityError
from sqlalchemy.engine.row import Row
from .models import Artist, Release, Label, MusicBrainzEntity, Base, Goal, Genre


def get_valid_models():
    return [cls.__name__.lower() for cls in Base.__subclasses__()]


def apply_comparison_filter(
    query, model: Type[MusicBrainzEntity], key: str, operator: str, value: str
) -> sql_query:
    """
    Used by dynamic_search to perform comparisons on begin, end, year, or rating
    :param query: An SQLAlchemy query class
    :param model: The database model class to filter on
    :param key: The column to filter on - begin_date or end_date
    :param operator: Denotes the comparison to perform
    :param value: The value to compare against
    :return: Newly constructed query
    """
    attribute = getattr(model, key)
    if not attribute:
        raise NameError(f"No attribute '{key}' found in model {model}")
    try:
        val = int(value)
    except TypeError:
        raise TypeError(f"Value must be an integer, got {type(value)}: {value}")

    if operator not in ["<", "=", ">"]:
        raise ValueError(f"Unrecognized operator value for year_comparison: {operator}")

    if key in ("begin", "end"):
        query = query.filter(extract("year", attribute).cast(Integer).op(operator)(val))
    elif key == "rating":
        query = query.filter(Release.rating.op(operator)(value))
    elif key == "year":
        query = query.filter(Release.year.op(operator)(value))
    return query


# Utility function to calculate the mean average rating and total release count
# for releases associated with a specific Label/Artist
def mean_avg_and_count(entities: list[Row]) -> (int, int):
    """
    :param entities: List of SQLAlchemy Rows; returned from average_ratings_and_total_counts()
    :return: A tuple representing the mean average release rating and mean release count
    """
    avg = count = 0
    total = len(entities)
    for item in entities:
        try:
            avg += int(item.average_rating)
            count += int(item.release_count)
        except AttributeError:
            # TODO: consider logging info about the erroring release
            # Have not encountered this in practice, but if it is encountered
            # it means there is a corrupt entry
            total -= 1

    mean_avg = avg / total
    mean_count = count / total
    return mean_avg, mean_count


# Utility function used to calculate Bayesian average
def bayesian_avg(item_weight: float, item_avg: float, mean_avg: float) -> float:
    """
    Calculates the Bayesian average rating for a given item weight and average
    :param item_weight: Float representing the item's weight for the formula;
                        calculated as: count / (count + mean count)
    :param item_avg: Item's average rating
    :param mean_avg: Mean average release rating for all database entries
    :return: Float representing the Bayesian average rating for releases associated with this item
    """
    if not item_weight or not item_avg or not mean_avg:
        raise ValueError("Input missing one of the required values")
    return item_weight * item_avg + (1 - item_weight) * mean_avg


def get_all_stats():
    stats = {
        "total_listens": Release.total_count(),
        "total_artists": Artist.total_count(),
        "total_labels": Label.total_count(),
        "average_rating": Release.ratings_average(),
        "average_runtime": Release.average_runtime(),
        "total_runtime": Release.total_runtime(),
        "releases_this_year": Release.added_this_year(),
        "artists_this_year": Artist.added_this_year(),
        "labels_this_year": Label.added_this_year(),
        "releases_per_day": Release.added_per_day_this_year(),
        "artists_per_day": Artist.added_per_day_this_year(),
        "labels_per_day": Label.added_per_day_this_year(),
        "top_rated_labels": Label.average_ratings_bayesian()[0:10],
        "top_rated_artists": Artist.average_ratings_bayesian()[0:10],
        "top_frequent_labels": Label.frequency_highest()[0:10],
        "top_frequent_artists": Artist.frequency_highest()[0:10],
        "top_average_artists": Artist.average_ratings_and_total_counts()[0:10],
        "top_average_labels": Label.average_ratings_and_total_counts()[0:10],
    }
    return stats


def ensure_db_placeholders():
    """
    When no known artist/label is found, handle_submit_data() defaults to setting
    the ID for the artist/label to 0, which is a placeholder entry for all
    unknown values.

    This function ensures these entries exist.
    """
    label = Label()
    label.id = 0
    label.name = "Unknown"
    try:
        insert(label)
    except IntegrityError:
        pass
    artist = Artist()
    artist.id = 0
    artist.name = "Unknown"
    try:
        insert(artist)
    except IntegrityError:
        pass


def handle_submit_data(submit_data: dict) -> None:
    """
    Process dictionary data from routes.submit()
    - Fetches release runtime from MusicBrainz, if a MBID is provided
    - Checks if matching label/artist exists in the db, creates one if it doesn't
    - Inserts the new release and subgenres
    :param submit_data:
    :return:
    """
    from ..api import MusicBrainz

    if submit_data["mbid"]:
        runtime = MusicBrainz.get_release_length(submit_data["mbid"])
        submit_data["runtime"] = runtime
        # If we aren't handling a MusicBrainz release,
        # the user can optionally pass in the runtime and it's already in submit_data

    if submit_data["label_mbid"]:
        label_id = Label.create_if_not_exist(
            mbid=submit_data["label_mbid"],
            name=submit_data["label_name"],
        )
    elif submit_data["label_name"]:
        label_id = Label.create_if_not_exist(name=submit_data["label_name"])
    else:
        label_id = 0

    submit_data["label_id"] = label_id

    if submit_data["artist_mbid"]:
        artist_id = Artist.create_if_not_exist(
            mbid=submit_data["artist_mbid"],
            name=submit_data["artist_name"],
        )
    elif submit_data["artist_name"]:
        artist_id = Artist.create_if_not_exist(name=submit_data["artist_name"])
    else:
        artist_id = 0

    submit_data["artist_id"] = artist_id

    if submit_data["main_genre"] is not None:
        main_genre = Genre.create_if_not_exists(submit_data["main_genre"])
        submit_data["main_genre"] = main_genre
        submit_data["main_genre_id"] = main_genre.id

    genres = []
    if submit_data["genres"]:
        for g in submit_data["genres"].split(","):
            genres.append(Genre.create_if_not_exists(g))
    submit_data["genres"] = genres
    Release.create_new(submit_data)
    Goal.check_goals()
