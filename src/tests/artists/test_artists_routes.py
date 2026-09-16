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


@pytest.fixture()
def existing_artist(app):
    with app.app_context():
        artist = Artist(name="Test Artist")
        app_db.session.add(artist)
        app_db.session.commit()
        return artist.id


class TestEditArtist:
    # Tests for /artist/<id>/edit
    def test_edit_unsupported_image_url_flashes_error(self, client, mocker, existing_artist):
        """
        An image URL with an unsupported file type should redirect to the
        error page with a specific message instead of crashing.
        """
        mocker.patch(
            "databass.artists.routes.Util.get_image",
            side_effect=ValueError(
                "ERROR: No supported image type found in URL: https://example.com/page"
            ),
        )
        response = client.post(
            f"/artist/{existing_artist}/edit",
            data={"image": "https://example.com/page"},
        )
        assert response.status_code == 302
        assert response.location == "/error"

        error_response = client.get("/error")
        assert b"No supported image type found" in error_response.data


class TestApiEditArtist:
    # Tests for PUT /api/artist/<id>
    def test_api_edit_unsupported_image_url_returns_400(self, client, mocker, existing_artist):
        mocker.patch(
            "databass.artists.routes.Util.get_image",
            side_effect=ValueError(
                "ERROR: No supported image type found in URL: https://example.com/page"
            ),
        )
        response = client.put(
            f"/api/artist/{existing_artist}",
            json={"image": "https://example.com/page"},
        )
        assert response.status_code == 400
        assert "No supported image type found" in response.get_json()["error"]
