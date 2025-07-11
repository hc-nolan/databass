import pytest
from databass import create_app


# TODO: this fixture is a duplicate of the same fixture in test_routes.py; figure out how to generalize/reuse a single fixture instead of duplicating the code
@pytest.fixture()
def client():
    app = create_app()
    app.config.update({"TESTING": True})
    with app.test_client() as client:
        yield client


class TestArtists:
    # Tests for /artists
    def test_artists_successful_page_load(self, client, mocker):
        mock_db = mocker.patch(
            "databass.db.models.Artist.get_distinct_column_values",
            return_value=["US", "UK"],
        )
        response = client.get("/artists")
        assert response.status_code == 200
        assert b"UK" in response.data
        assert b"artist_search" in response.data


class TestArtist:
    # Tests for /artist
    def test_artist_successful_page_load(self, client, mocker):
        import datetime

        mock_artist_data = mocker.MagicMock()
        mock_artist_data.begin = datetime.date(1986, 10, 26)
        mock_artist_data.country = None
        mock_artist_data.end = datetime.date(9999, 12, 31)
        mock_artist_data.id = 1
        mock_artist_data.image = "./static/img/artist/1.jpg"
        mock_artist_data.mbid = "bce6d667-cde8-485e-b078-c0a05adea36d"
        mock_artist_data.name = "ScHoolboy Q"
        mock_artist_data.type = "Person"

        mocker.patch("databass.db.models.Artist.releases", return_value=[])
        mocker.patch(
            "databass.db.models.Artist.exists_by_id", return_value=mock_artist_data
        )

        response = client.get("/artist/1")
        assert response.status_code == 200
        assert b"artist_container" in response.data

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
