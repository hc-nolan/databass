import pytest
from databass import create_app
import datetime


# TODO: this fixture is a duplicate of the same fixture in other tests; figure out how to generalize/reuse a single fixture instead of duplicating the code
@pytest.fixture()
def app():
    app = create_app()
    app.config.update({"TESTING": True})
    return app


@pytest.fixture()
def client(app):
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
    def test_releases_redirects_to_browse(self, client):
        response = client.get("/releases")
        assert response.status_code == 301
        assert response.headers["Location"] == "/browse/releases"


class TestApiEditRelease:
    # Tests for GET /api/release/<id>/edit, PUT /api/release/<id>
    def test_edit_get_success(
        self, mocker, client, mock_release_data, mock_artist_data, mock_label_data
    ):
        """
        Test for successful handling of a GET request, which returns the editable fields
        """
        mock_release_data.main_genre = None
        mock_release_data.genres = []
        mock_release_data.collab_artists = []
        mocker.patch(
            "databass.db.models.Release.exists_by_id", return_value=mock_release_data
        )
        mocker.patch(
            "databass.db.models.Release.get_distinct_column_values",
            return_value=["a", "b"],
        )
        mocker.patch(
            "databass.db.models.Label.exists_by_id", return_value=mock_label_data
        )
        mocker.patch(
            "databass.db.models.Artist.exists_by_id", return_value=mock_artist_data
        )
        response = client.get("/api/release/1/edit")
        assert response.status_code == 200
        assert response.get_json()["name"] == "BLUE LIPS"

    def test_edit_get_non_existing_release(self, client, mocker):
        """
        Test for successful handling of a GET request for a release that does not exist
        """
        mocker.patch("databass.db.models.Release.exists_by_id", return_value=False)
        response = client.get("/api/release/9999999999/edit")
        assert response.status_code == 404

    def test_edit_post_success(self, client, mock_release_data, mocker):
        """
        Test for successful handling of a PUT request, which submits edited data
        """
        mocker.patch("databass.db.construct_item", return_value=mock_release_data)
        mocker.patch(
            "databass.db.models.Release.exists_by_id", return_value=mock_release_data
        )
        mocker.patch("databass.db.update")
        mocker.patch(
            "databass.releases.routes.build_release_detail", return_value={"id": 1}
        )
        response = client.put(
            "/api/release/1",
            json={
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
        assert response.status_code == 200

    def test_edit_post_sets_collab_artists(self, client, mock_release_data, mocker):
        """
        Test that submitting collab_artists resolves each name to an Artist
        via create_if_not_exist and includes them in the submitted data
        """
        mock_construct = mocker.patch(
            "databass.db.construct_item", return_value=mock_release_data
        )
        mocker.patch(
            "databass.db.models.Release.exists_by_id", return_value=mock_release_data
        )
        mocker.patch("databass.db.update")
        mocker.patch(
            "databass.releases.routes.build_release_detail", return_value={"id": 1}
        )
        mock_create = mocker.patch(
            "databass.db.models.Artist.create_if_not_exist", return_value=2
        )
        mock_artist = mocker.MagicMock()
        mocker.patch("databass.db.models.Artist.exists_by_id", return_value=mock_artist)

        response = client.put(
            "/api/release/1", json={"collab_artists": "Ghostface Killah"}
        )

        assert response.status_code == 200
        mock_create.assert_called_once_with("Ghostface Killah")
        submit_data = mock_construct.call_args[0][1]
        assert submit_data["collab_artists"] == [mock_artist]

    def test_edit_post_clears_collab_artists_when_field_empty(
        self, client, mock_release_data, mocker
    ):
        """
        Test that submitting an empty collab_artists field clears any
        previously-set collab credits, rather than leaving them untouched
        """
        mock_construct = mocker.patch(
            "databass.db.construct_item", return_value=mock_release_data
        )
        mocker.patch(
            "databass.db.models.Release.exists_by_id", return_value=mock_release_data
        )
        mocker.patch("databass.db.update")
        mocker.patch(
            "databass.releases.routes.build_release_detail", return_value={"id": 1}
        )

        response = client.put("/api/release/1", json={"collab_artists": ""})

        assert response.status_code == 200
        submit_data = mock_construct.call_args[0][1]
        assert submit_data["collab_artists"] == []

    def test_edit_post_collab_artist_name_with_comma_not_split(
        self, client, mock_release_data, mocker
    ):
        """
        Test that submitting multiple collab artists as a list resolves each
        full name, even when a name itself contains a comma (e.g. "Earth,
        Wind & Fire"), rather than splitting it into fragments
        """
        mock_construct = mocker.patch(
            "databass.db.construct_item", return_value=mock_release_data
        )
        mocker.patch(
            "databass.db.models.Release.exists_by_id", return_value=mock_release_data
        )
        mocker.patch("databass.db.update")
        mocker.patch(
            "databass.releases.routes.build_release_detail", return_value={"id": 1}
        )
        mock_create = mocker.patch(
            "databass.db.models.Artist.create_if_not_exist", return_value=2
        )
        mock_artist = mocker.MagicMock()
        mocker.patch(
            "databass.db.models.Artist.exists_by_id", return_value=mock_artist
        )

        response = client.put(
            "/api/release/1",
            json={"collab_artists": ["Earth, Wind & Fire", "Nile Rodgers"]},
        )

        assert response.status_code == 200
        mock_create.assert_any_call("Earth, Wind & Fire")
        mock_create.assert_any_call("Nile Rodgers")
        assert mock_create.call_count == 2
        submit_data = mock_construct.call_args[0][1]
        assert submit_data["collab_artists"] == [mock_artist, mock_artist]

    def test_edit_post_genre_name_with_comma_not_split(
        self, client, mock_release_data, mocker
    ):
        """
        Test that submitting multiple genres as a list resolves each full
        name, even when a name itself contains a comma, rather than
        splitting it into fragments
        """
        mock_construct = mocker.patch(
            "databass.db.construct_item", return_value=mock_release_data
        )
        mocker.patch(
            "databass.db.models.Release.exists_by_id", return_value=mock_release_data
        )
        mocker.patch("databass.db.update")
        mocker.patch(
            "databass.releases.routes.build_release_detail", return_value={"id": 1}
        )
        mock_genre = mocker.MagicMock()
        mock_create_genre = mocker.patch(
            "databass.db.models.Genre.create_if_not_exists", return_value=mock_genre
        )

        response = client.put(
            "/api/release/1",
            json={"genres": ["Chill, Wave", "synthpop"]},
        )

        assert response.status_code == 200
        mock_create_genre.assert_any_call("Chill, Wave")
        mock_create_genre.assert_any_call("synthpop")
        assert mock_create_genre.call_count == 2
        submit_data = mock_construct.call_args[0][1]
        assert submit_data["genres"] == [mock_genre, mock_genre]

    def test_edit_post_failure_non_existing_release(self, client, mocker):
        """
        Test for successful handling of a PUT request to a release that does not exist
        """
        mock_release = mocker.patch(
            "databass.db.models.Release.exists_by_id", return_value=False
        )
        response = client.put("/api/release/9999999999", json={})
        mock_release.assert_called_once()
        assert response.status_code == 404

    def test_api_edit_unsupported_image_url_returns_400(
        self, client, mock_release_data, mocker
    ):
        mocker.patch(
            "databass.db.models.Release.exists_by_id", return_value=mock_release_data
        )
        mocker.patch(
            "databass.releases.routes.Util.get_image_from_url",
            side_effect=ValueError(
                "ERROR: No supported image type found in URL: https://example.com/page"
            ),
        )
        response = client.put(
            "/api/release/1",
            json={"image": "https://example.com/page"},
        )
        assert response.status_code == 400
        assert "No supported image type found" in response.get_json()["error"]

    def test_edit_post_integrity_error_names_field(self, client, mock_release_data, mocker):
        """A unique-constraint violation on save should name the offending field."""
        from sqlalchemy.exc import IntegrityError

        mocker.patch("databass.db.construct_item", return_value=mock_release_data)
        mocker.patch(
            "databass.db.models.Release.exists_by_id", return_value=mock_release_data
        )
        mocker.patch(
            "databass.releases.routes.db.update",
            side_effect=IntegrityError(
                "statement", {}, Exception("UNIQUE constraint failed: release.mbid")
            ),
        )
        response = client.put(
            "/api/release/1",
            json={"name": "BLUE LIPS", "id": "1"},
        )
        assert response.status_code == 400
        assert "mbid" in response.get_json()["error"]
        assert "already exists" in response.get_json()["error"]

class TestAddReview:
    # Tests for POST /api/release/<id>/reviews
    def test_add_review_success(self, client, mock_release_data, mocker):
        """
        Test for successful review addition
        """
        mock_release = mocker.patch(
            "databass.db.models.Release.exists_by_id", return_value=mock_release_data
        )
        mock_construct = mocker.patch("databass.db.construct_item")
        mock_insert = mocker.patch("databass.db.insert")
        mocker.patch(
            "databass.releases.routes.build_release_detail", return_value={"id": 1}
        )

        response = client.post(
            "/api/release/1/reviews",
            json={"text": "release review"},
        )

        assert response.status_code == 201
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
            "/api/release/1/reviews",
            json={"text": "release review"},
        )
        assert response.status_code == 404
        mock_release.assert_called_once()

    def test_add_review_fail_malformed_request(self, client, mock_release_data, mocker):
        """
        Test for successful handling of a request with missing data
        """
        mock_release = mocker.patch(
            "databass.db.models.Release.exists_by_id", return_value=mock_release_data
        )
        response = client.post("/api/release/1/reviews", json={})
        assert response.status_code == 400
        mock_release.assert_called_once()


class TestEditReview:
    # Tests for PUT /api/release/<id>/reviews/<review_id>
    def test_edit_review_success(self, client, mock_release_data, mocker):
        """
        Test for successful editing of an existing review's text
        """
        mocker.patch(
            "databass.db.models.Release.exists_by_id", return_value=mock_release_data
        )
        mock_review = mocker.MagicMock()
        mock_review.id = 1
        mock_review.release_id = 1
        mocker.patch("databass.db.models.Review.exists_by_id", return_value=mock_review)
        mock_update = mocker.patch("databass.db.update")
        mocker.patch(
            "databass.releases.routes.build_release_detail", return_value={"id": 1}
        )

        response = client.put(
            "/api/release/1/reviews/1",
            json={"text": "updated review text"},
        )

        assert response.status_code == 200
        assert mock_review.text == "updated review text"
        mock_update.assert_called_once_with(mock_review)

    def test_edit_review_fail_non_existing_release(self, client, mocker):
        """
        Test for proper handling of a request to edit a review on a release that does not exist
        """
        mocker.patch("databass.db.models.Release.exists_by_id", return_value=False)
        response = client.put(
            "/api/release/1/reviews/1",
            json={"text": "updated review text"},
        )
        assert response.status_code == 404

    def test_edit_review_fail_malformed_request(self, client, mock_release_data, mocker):
        """
        Test for proper handling of a request missing the review text
        """
        mocker.patch(
            "databass.db.models.Release.exists_by_id", return_value=mock_release_data
        )
        response = client.put("/api/release/1/reviews/1", json={})
        assert response.status_code == 400

    def test_edit_review_fail_non_existing_review(self, client, mock_release_data, mocker):
        """
        Test for proper handling of a request to edit a review that does not exist
        """
        mocker.patch(
            "databass.db.models.Release.exists_by_id", return_value=mock_release_data
        )
        mocker.patch("databass.db.models.Review.exists_by_id", return_value=None)
        response = client.put(
            "/api/release/1/reviews/99",
            json={"text": "updated review text"},
        )
        assert response.status_code == 404

    def test_edit_review_fail_review_belongs_to_different_release(
        self, client, mock_release_data, mocker
    ):
        """
        Test that a review can't be edited via a mismatched release_id in the URL
        """
        mocker.patch(
            "databass.db.models.Release.exists_by_id", return_value=mock_release_data
        )
        mock_review = mocker.MagicMock()
        mock_review.id = 1
        mock_review.release_id = 2
        mocker.patch("databass.db.models.Review.exists_by_id", return_value=mock_review)
        response = client.put(
            "/api/release/1/reviews/1",
            json={"text": "updated review text"},
        )
        assert response.status_code == 404
