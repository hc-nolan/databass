import psycopg2
from databass import create_app
from databass.db import models
from databass.db.operations import insert

conn = psycopg2.connect(dbname="db2migrate")
cur = conn.cursor()

def main():
    app = create_app()
    with app.app_context():
        # phony genre - required for releases that have no genre
        g = models.Genre()
        g.name = "null"
        g.id = 0
        insert(g)

        for i in range(1, 1100):
            print(i)
            release_old = select("release", i)
            if release_old is not None:
                artist_old = select("artist", release_old[2])
                label_old = select("label", release_old[3])
                tags_old = gettags(i)

                artist = new_artist(artist_old)
                label = new_label(label_old)
                main_genre = new_genre(release_old[11])
                genres = []
                for t in tags_old:
                    if t[2] != '':
                        genres.append(new_genre_from_tag(t))

                release = new_release(old=release_old, artist=artist, label=label, main_genre=main_genre, genres=genres)
                try:
                    for r in release_old[14]:
                        new_review(r, release)
                except TypeError:
                    pass



def select(table, entry_id):
    cur.execute(f"SELECT * FROM {table} WHERE id = {entry_id}")
    return cur.fetchone()

def gettags(release_id):
    cur.execute(f"SELECT * FROM tag WHERE release_id = {release_id}")
    return cur.fetchall()

def new_artist(old):
    exists = models.Artist.exists_by_id(old[0])
    if exists:
        return exists
    new = models.Artist()
    return new_label_or_artist(old, new)

def new_label(old):
    exists = models.Label.exists_by_id(old[0])
    if exists:
        return exists
    new = models.Label()
    return new_label_or_artist(old, new)

def new_label_or_artist(old, new):
    new.id = old[0]
    new.mbid = old[1]
    new.name = old[2]
    new.country = old[3]
    new.type = old[4]
    new.begin = old[5]
    new.end = old[6]
    new.image = old[7]
    new.date_added = old[8]
    insert(new)
    return new

def new_genre(old):
    if old == '':
        return None
    print(old)
    exists = models.Genre.exists_by_name(old)
    if exists:
        return exists
    new = models.Genre()
    new.name = old
    insert(new)
    return new

def new_genre_from_tag(old):
    exists = models.Genre.exists_by_name(old[2])
    if exists:
        return exists
    new = models.Genre()
    new.name = old[2]
    insert(new)
    return new

def new_release(old, artist, label, main_genre, genres):
    new = models.Release()
    new.id = old[0]
    new.mbid = old[1]
    # new.artist_id = old[2]
    # new.label_id = old[3]
    new.artist = artist
    new.label = label
    new.name = old[4]
    new.year = old[5]
    new.runtime = old[6]
    new.rating = old[7]
    new.listen_date = old[8]
    new.track_count = old[9]
    new.country = old[10]
    if main_genre:
        new.main_genre_id = main_genre.id
    else:
        new.main_genre_id = 0
    new.genres = genres
    return insert(new)

def new_review(old, release):
    new = models.Review()
    new.id = old[0]
    new.release_id = release.id
    new.timestamp = old[2]
    new.text = old[3]
    new.date_added = old[4]


main()
