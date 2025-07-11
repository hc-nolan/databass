import pytest
from databass import create_app
import datetime


# TODO: this fixture is a duplicate of the same fixture in other tests; figure out how to generalize/reuse a single fixture instead of duplicating the code
@pytest.fixture()
def client():
    app = create_app()
    app.config.update({"TESTING": True})
    with app.test_client() as client:
        yield client


@pytest.fixture()
def mock_release_data(mocker):
    mock_release = mocker.MagicMock()
    mock_release.id = 1
    mock_release.artist_id = 1
    mock_release.label_id = 1
    mock_release.name = "BLUE LIPS"
    mock_release.country = "[Worldwide]"
    mock_release.genre = "hiphop"
    mock_release.image = "./static/img/release/1.jpg"
    mock_release.listen_date = datetime.datetime(2024, 3, 3, 0, 0)
    mock_release.mbid = "46004fde-3059-42a8-b399-daa0a18816e0"
    mock_release.rating = 70
    mock_release.year = 2024
    mock_release.review = None
    mock_release.runtime = 3361000
    mock_release.tags = None
    mock_release.track_count = 18
    return mock_release


@pytest.fixture()
def mock_artist_data(mocker):
    mock_artist = mocker.MagicMock()
    mock_artist.begin_date = datetime.date(1986, 10, 26)
    mock_artist.country = (None,)
    mock_artist.end_date = datetime.date(9999, 12, 31)
    mock_artist.id = 1
    mock_artist.image = "./static/img/artist/1.jpg"
    mock_artist.mbid = ("bce6d667-cde8-485e-b078-c0a05adea36d",)
    mock_artist.name = ("ScHoolboy Q",)
    mock_artist.type = "person"
    return mock_artist


@pytest.fixture()
def mock_label_data(mocker):
    mock_label = mocker.MagicMock()
    mock_label.begin_date = datetime.date(2004, 1, 1)
    mock_label.country = "US"
    mock_label.end_date = datetime.date(9999, 12, 31)
    mock_label.id = 1
    mock_label.image = None
    mock_label.mbid = "56d2501f-12b7-4cfd-b8f8-e95189ea27f5"
    mock_label.name = "Top Dawg Entertainment"
    mock_label.type = "Original Production"
    return mock_label


class TestReleases:
    # Tests for /releases
    def test_releases_successful_page_load(self, client):
        response = client.get("/releases")
        assert response.status_code == 200
        assert b"release_search" in response.data


class TestRelease:
    # Tests for /release
    def test_release_successful_page_load(
        self, client, mock_release_data, mock_artist_data, mock_label_data, mocker
    ):
        mocker.patch("databass.db.models.Release.get_reviews", return_value=[])
        response = client.get("/release/1")
        assert response.status_code == 200
        assert b"release_container" in response.data

    def test_release_not_found(self, client, mocker):
        mocker.patch("databass.db.models.Release.exists_by_id", return_value=False)
        response = client.get("/release/99999999999999999999")
        assert response.status_code == 302
        assert b"You should be redirected automatically" in response.data


class TestEdit:
    # Tests for /release/<id>/edit
    def test_edit_get_success(
        self, client, mock_release_data, mock_artist_data, mock_label_data
    ):
        """
        Test for successful handling of a GET request, which displays the editable fields
        """
        response = client.get("/release/1/edit")
        assert response.status_code == 200
        assert b"edit_form" in response.data

    def test_edit_get_non_existing_release(self, client, mocker):
        """
        Test for successful handling of a GET request for a release that does not exist
        """
        mocker.patch("databass.db.models.Release.exists_by_id", return_value=False)
        response = client.get("/release/9999999999/edit")
        assert response.status_code == 302
        assert response.location == "/error"
        assert b"You should be redirected automatically" in response.data

    def test_edit_post_success(self, client, mock_release_data, mocker):
        """
        Test for successful handling of a POST request, which submits edited data
        """
        mock_construct = mocker.patch(
            "databass.db.construct_item", return_value=mock_release_data
        )
        mocker.patch("databass.db.update")
        response = client.post(
            "/release/1/edit",
            data={
                "artist_id": "1",
                "country": "[Worldwide]",
                "genre": "hiphop",
                "id": "1",
                "image": "./static/img/release/1.jpg",
                "label_id": "1",
                "listen_date": "2024-03-04",
                "name": "BLUE LIPS",
                "rating": "1",
                "year": "2024",
                "tags": "None",
            },
        )
        assert response.status_code == 302
        assert response.location == "/"
        assert b"You should be redirected automatically" in response.data

    def test_edit_post_failure_non_existing_release(self, client, mocker):
        """
        Test for successful handling of a POST request to a release that does not exist
        """
        mock_release = mocker.patch(
            "databass.db.models.Release.exists_by_id", return_value=False
        )
        response = client.post("/release/9999999999/edit")
        mock_release.assert_called_once()
        assert response.status_code == 302
        assert response.location == "/error"
        assert b"You should be redirected automatically" in response.data


class TestDelete:
    # Tests for /delete
    def test_delete_success(self, client, mock_release_data, mocker):
        """
        Test for proper handling of a successful deletion
        """
        mocker.patch("databass.db.delete")
        delete_data = {"id": 1, "type": "release"}
        response = client.post("/delete", json=delete_data)
        assert response.status_code == 302
        assert response.location == "/"

    def test_delete_fail_malformed_request(self, client):
        """
        Test for proper handling of a deletion request that is missing required data
        """
        delete_data = {"id": 1}
        response = client.post("/delete", json=delete_data)
        assert response.status_code == 302
        assert response.location == "/error"

    def test_delete_fail_non_existing_release(self, client, mocker):
        """
        Test for proper handling of a deletion request for a release that does not exist
        """
        mocker.patch("databass.db.models.Release.exists_by_id", return_value=False)
        delete_data = {"id": 1, "type": "release"}
        response = client.post("/delete", json=delete_data)
        assert response.status_code == 302
        assert response.location == "/error"


class TestAddReview:
    # Tests for /release/<id>/add_review
    def test_add_review_success(self, client, mock_release_data, mocker):
        """
        Test for successful release addition
        """
        mock_release = mocker.patch(
            "databass.db.models.Release.exists_by_id", return_value=mock_release_data
        )
        mock_construct = mocker.patch("databass.db.construct_item")
        mock_insert = mocker.patch("databass.db.insert")

        response = client.post(
            "/release/1/add_review",
            data={"id": 1, "text": "release review"},
            headers={"Referer": "/release/1"},
        )

        assert response.status_code == 302
        assert response.location == "/release/1"
        mock_release.assert_called_once()
        mock_construct.assert_called_once()
        mock_insert.assert_called_once()

    def test_add_review_fail_non_existing_release(self, client, mocker):
        """
        Test for successful handling of a request to add a review to a release that does not exist
        """
        mock_release = mocker.patch(
            "databass.db.models.Release.exists_by_id", return_value=False
        )
        response = client.post(
            "/release/1/add_review",
            data={"id": 1, "text": "release review"},
            headers={"Referer": "/release/1"},
        )
        assert response.status_code == 302
        assert response.location == "/error"
        mock_release.assert_called_once()

    def test_add_review_fail_malformed_request(self, client, mock_release_data, mocker):
        """
        Test for successful handling of a request with missing data
        """
        mock_release = mocker.patch(
            "databass.db.models.Release.exists_by_id", return_value=mock_release_data
        )
        response = client.post(
            "/release/1/add_review", data={"id": 1}, headers={"Referer": "/release/1"}
        )
        assert response.status_code == 302
        assert response.location == "/error"
        mock_release.assert_called_once()
