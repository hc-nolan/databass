from db import get_db_session
from databass.classes import Release, Artist, Label, Review, Goal, Country, Genre  # noqa


def create_release(data: Release):
    def transaction(tx, data: Release):
        result = tx.run(
            """
            UNWIND $data as data
            CREATE (r:Release)
            SET r.name = data.name,
                r.mbid = data.mbid,
                r.image = data.image,
                r.date_added = data.date_added,
                r.rating = data.rating,
                r.year = data.year,
                r.runtime = data.runtime,
                r.track_count = data.track_count,
            """,
            data=data,
        )
        return list(result)

    with get_db_session() as session:
        session.execute_write(transaction, data)


def create_artist(data: Artist):
    def transaction(tx, data: Artist):
        result = tx.run(
            """
            UNWIND $data as data
            CREATE (a:Artist)
            SET a.name = data.name,
                a.mbid = data.mbid,
                a.image = data.image,
                a.date_added = data.date_added,
                a.kind = data.kind,
                a.begin_date = data.begin_date,
                a.end_date = data.end_date
            """,
            data=data,
        )
        return list(result)

    with get_db_session() as session:
        session.execute_write(transaction, data)


def create_label(data: Label):
    def transaction(tx, data: Label):
        result = tx.run(
            """
            UNWIND $data as data
            CREATE (l:Label)
            SET l.name = data.name,
                l.mbid = data.mbid,
                l.image = data.image,
                l.date_added = data.date_added,
                l.kind = data.kind,
                l.begin_date = data.begin_date,
                l.end_date = data.end_date
            """,
            data=data,
        )
        return list(result)

    with get_db_session() as session:
        session.execute_write(transaction, data)


def create_country(data: Country):
    def transaction(tx, data: Country):
        result = tx.run(
            """
            UNWIND $data as data
            CREATE (c:Country)
            SET c.name = data.name,
                c.mbid = data.mbid,
                c.date_added = data.date_added,
                c.code = data.code
            """,
            data=data,
        )
        return list(result)

    with get_db_session() as session:
        session.execute_write(transaction, data)


def create_genre(data: Genre):
    def transaction(tx, data: Genre):
        result = tx.run(
            """
            UNWIND $data as data
            CREATE (g:Genre)
            SET g.name = data.name,
                g.mbid = data.mbid,
                g.date_added = data.date_added,
            """,
            data=data,
        )
        return list(result)

    with get_db_session() as session:
        session.execute_write(transaction, data)


def create_goal(data: Goal):
    def transaction(tx, data: Goal):
        result = tx.run(
            """
            UNWIND $data as data
            CREATE (g:Goal)
            SET g.start = data.start,
                g.end = data.end,
                g.status = data.status,
                g.completed_on = data.completed_on,
                g.amount = data.amount,
                g.date_added = data.date_added,
            """,
            data=data,
        )
        return list(result)

    with get_db_session() as session:
        session.execute_write(transaction, data)


def create_review(data: Review):
    def transaction(tx, data: Review):
        result = tx.run(
            """
            UNWIND $data as data
            CREATE (r:Review)
            SET r.content = data.content,
                r.date_added = data.date_added,
            """,
            data=data,
        )
        return list(result)

    with get_db_session() as session:
        session.execute_write(transaction, data)


def create_release_artist_relation(release: Release, artist: Artist):
    def transaction(tx, release: Release, artist: Artist):
        result = tx.run(
            """
            UNWIND $release as release
            UNWIND $artist as artist
            MERGE (r:Release {id: release.id})
            MERGE (a:Artist {id: artist.id})
            MERGE (r)-[:MADE_BY]->(a)
            """,
            release=release,
            artist=artist,
        )
        return list(result)

    with get_db_session() as session:
        session.execute_write(transaction, release, artist)


def create_release_label_relation(release: Release, label: Label):
    def transaction(tx, release: Release, label: Label):
        result = tx.run(
            """
            UNWIND $release as release
            UNWIND $label as label
            MERGE (r:Release {id: release.id})
            MERGE (l:Label {id: label.id})
            MERGE (r)-[:RELEASED_BY]->(l)
            """,
            release=release,
            label=label,
        )
        return list(result)

    with get_db_session() as session:
        session.execute_write(transaction, release, label)


def create_release_country_relation(release: Release, country: Country):
    def transaction(tx, release: Release, country: Country):
        result = tx.run(
            """
            UNWIND $release as release
            UNWIND $country as country
            MERGE (r:Release {id: release.id})
            MERGE (c:Country {id: country.id})
            MERGE (r)-[:RELEASED_IN]->(c)
            """,
            release=release,
            country=country,
        )
        return list(result)

    with get_db_session() as session:
        session.execute_write(transaction, release, country)


def create_release_genre_relation(release: Release, genre: Genre):
    def transaction(tx, release: Release, genre: Genre):
        result = tx.run(
            """
            UNWIND $release as release
            UNWIND $genre as genre
            MERGE (r:Release {id: release.id})
            MERGE (g:Genre {id: genre.id})
            MERGE (r)-[:HAS_GENRE]->(g)
            """,
            release=release,
            genre=genre,
        )
        return list(result)

    with get_db_session() as session:
        session.execute_write(transaction, release, genre)
