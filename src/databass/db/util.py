from sqlalchemy.exc import IntegrityError
from .operations import insert
from .registry import construct_item
from .models import Artist, Release, Label, Base, Goal, Genre


def get_valid_models():
    return [cls.__name__.lower() for cls in Base.__subclasses__()]


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
    for model in (Label, Artist):
        if model.exists_by_id(0):
            continue
        placeholder = model()
        placeholder.id = 0
        placeholder.name = "Unknown"
        try:
            insert(placeholder)
        except IntegrityError:
            pass


def handle_submit_data(submit_data: dict) -> list[Goal]:
    """
    Process dictionary data from routes.submit()
    - Fetches release runtime from MusicBrainz, if a MBID is provided
    - Checks if matching label/artist exists in the db, creates one if it doesn't
    - Inserts the new release and subgenres
    :param submit_data:
    :return: list of goals that were newly completed as a result of this submission
    """
    from ..api import MusicBrainz

    if submit_data.get("mbid"):
        runtime = MusicBrainz.get_release_length(submit_data["mbid"])
        submit_data["runtime"] = runtime
        # If we aren't handling a MusicBrainz release,
        # the user can optionally pass in the runtime and it's already in submit_data

    if submit_data.get("label_mbid"):
        label_id = Label.create_if_not_exist(
            mbid=submit_data["label_mbid"],
            name=submit_data["label_name"],
        )
    elif submit_data.get("label_name"):
        label_id = Label.create_if_not_exist(name=submit_data["label_name"])
    else:
        label_id = 0

    submit_data["label_id"] = label_id

    if submit_data.get("artist_mbid"):
        artist_id = Artist.create_if_not_exist(
            mbid=submit_data["artist_mbid"],
            name=submit_data["artist_name"],
        )
    elif submit_data.get("artist_name"):
        artist_id = Artist.create_if_not_exist(name=submit_data["artist_name"])
    else:
        artist_id = 0

    submit_data["artist_id"] = artist_id

    if submit_data.get("main_genre") is not None:
        main_genre = Genre.create_if_not_exists(submit_data["main_genre"])
        submit_data["main_genre"] = main_genre
        submit_data["main_genre_id"] = main_genre.id

    genres = []
    raw_genres = submit_data.get("genres")
    if raw_genres:
        genre_names = raw_genres if isinstance(raw_genres, list) else raw_genres.split(",")
        for g in genre_names:
            g = g.strip()
            if g:
                genres.append(Genre.create_if_not_exists(g))
    submit_data["genres"] = genres
    note = submit_data.pop("note", None)
    release_id = Release.create_new(submit_data)

    if note:
        review = construct_item(
            "review", {"text": note, "release_id": release_id}
        )
        insert(review)

    return Goal.check_goals()
