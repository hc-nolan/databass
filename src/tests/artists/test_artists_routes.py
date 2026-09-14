import pytest
from databass import create_app
from databass.db.base import app_db
from databass.db.models import Artist


# TODO: this fixture is a duplicate of the same fixture in test_routes.py; figure out how to generalize/reuse a single fixture instead of duplicating the code
@pytest.fixture()
def app():
    app = create_app()
    app.config.update({"TESTING": True})
    return app


@pytest.fixture()
def client(app):
    with app.test_client() as client:
        yield client


class TestArtists:
    # Tests for /artists
    def test_artists_redirects_to_browse(self, client):
        response = client.get("/artists")
        assert response.status_code == 301
        assert response.headers["Location"] == "/browse/artists"


class TestArtist:
    # Tests for /artist
    def test_artist_successful_page_load(self, app, client):
        import datetime

        with app.app_context():
            artist = Artist(
                mbid="bce6d667-cde8-485e-b078-c0a05adea36d",
                name="ScHoolboy Q",
                begin=datetime.date(1986, 10, 26),
                end=datetime.date(9999, 12, 31),
                type="person",
            )
            app_db.session.add(artist)
            app_db.session.commit()
            artist_id = artist.id

        response = client.get(f"/artist/{artist_id}")
        assert response.status_code == 200
        assert b"ScHoolboy Q" in response.data

    def test_artist_not_found(self, client, mocker):
        mocker.patch("databass.db.models.Artist.exists_by_id", return_value=False)
        response = client.get("/artist/999")
        assert response.status_code == 302
        assert b"You should be redirected automatically" in response.data


# class TestEdit:
#     # Tests for /artist/<id>/edit
#     def test_edit_successful_get(self, client):
#         """
#         Test for successful handling of a GET request, which displays the editable fields
#         """
#
#     def test_edit_non_existing_release(self, client):
#         """
#         Test for successful handling of a GET request for a release that does not exist
#         """
#
#     def test_edit_successful_post(self, client):
#         """
#         Test for successful handling of a POST request, which submits edited data
#         """
#
#     def test_edit_failed_post(self, client):
#         """
#         Test for successful handling of a malformed POST request
#         """
