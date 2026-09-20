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


@pytest.fixture()
def existing_artist(app):
    with app.app_context():
        artist = Artist(name="Test Artist")
        app_db.session.add(artist)
        app_db.session.commit()
        return artist.id


class TestArtistMissing:
    # Tests for /api/artist/<id>/missing
    def test_no_mbid_returns_empty(self, client, existing_artist):
        response = client.get(f"/api/artist/{existing_artist}/missing")
        assert response.status_code == 200
        assert response.get_json() == {"missing": []}

    def test_returns_unlogged_albums(self, app, client, mocker):
        with app.app_context():
            artist = Artist(
                mbid="bce6d667-cde8-485e-b078-c0a05adea36d",
                name="ScHoolboy Q",
            )
            app_db.session.add(artist)
            app_db.session.commit()
            artist_id = artist.id

        mocker.patch(
            "databass.detail.MusicBrainz.artist_release_groups",
            return_value=[
                {"mbid": "a", "name": "Setbacks", "year": "2011"},
                {"mbid": "b", "name": "Oxymoron", "year": "2014"},
            ],
        )

        response = client.get(f"/api/artist/{artist_id}/missing")
        assert response.status_code == 200
        names = [m["name"] for m in response.get_json()["missing"]]
        assert names == ["Setbacks", "Oxymoron"]

    def test_artist_not_found(self, client):
        response = client.get("/api/artist/999999/missing")
        assert response.status_code == 404


class TestApiEditArtist:
    # Tests for PUT /api/artist/<id>
    def test_api_edit_unsupported_image_url_returns_400(self, client, mocker, existing_artist):
        mocker.patch(
            "databass.artists.routes.Util.get_image_from_url",
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
