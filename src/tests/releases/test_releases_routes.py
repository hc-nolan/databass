import pytest
from databass import create_app
from databass.db.base import app_db
from databass.db.models import Artist, Label, Genre, Release
from werkzeug.datastructures import MultiDict
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


class TestRelease:
    # Tests for /release
    def test_release_successful_page_load(self, app, client):
        with app.app_context():
            artist = Artist(mbid=None, name="ScHoolboy Q")
            label = Label(mbid=None, name="Top Dawg Entertainment")
            genre = Genre(name="hiphop")
            app_db.session.add_all([artist, label, genre])
            app_db.session.commit()

            release = Release(
                mbid=None,
                artist_id=artist.id,
                label_id=label.id,
                name="BLUE LIPS",
                country="[Worldwide]",
                year=2024,
                runtime=3361000,
                rating=70,
                listen_date=datetime.datetime(2024, 3, 3, 0, 0),
                track_count=18,
                main_genre_id=genre.id,
            )
            app_db.session.add(release)
            app_db.session.commit()
            release_id = release.id

        response = client.get(f"/release/{release_id}")
        assert response.status_code == 200
        assert b"BLUE LIPS" in response.data

    def test_release_not_found(self, client, mocker):
        mocker.patch("databass.db.models.Release.exists_by_id", return_value=False)
        response = client.get("/release/99999999999999999999")
        assert response.status_code == 302
        assert b"You should be redirected automatically" in response.data


class TestEdit:
    # Tests for /release/<id>/edit
    def test_edit_get_success(
        self, mocker, client, mock_release_data, mock_artist_data, mock_label_data
    ):
        """
        Test for successful handling of a GET request, which displays the editable fields
        """
        mocker.patch(
            "databass.db.models.Release.exists_by_id", return_value=mock_release_data
        )
        mocker.patch(
            "databass.db.models.Release.get_distinct_column_values",
            return_value=["a", "b"],
        )
        mocker.patch("databass.db.models.Label.exists_by_id", return_value=True)
        mocker.patch("databass.db.models.Artist.exists_by_id", return_value=True)
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
        mocker.patch("databass.db.construct_item", return_value=mock_release_data)
        mocker.patch(
            "databass.db.models.Release.exists_by_id", return_value=mock_release_data
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
        mock_create = mocker.patch(
            "databass.db.models.Artist.create_if_not_exist", return_value=2
        )
        mock_artist = mocker.MagicMock()
        mocker.patch("databass.db.models.Artist.exists_by_id", return_value=mock_artist)

        response = client.post(
            "/release/1/edit", data={"collab_artists": "Ghostface Killah"}
        )

        assert response.status_code == 302
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

        response = client.post("/release/1/edit", data={"collab_artists": ""})

        assert response.status_code == 302
        submit_data = mock_construct.call_args[0][1]
        assert submit_data["collab_artists"] == []

    def test_edit_post_collab_artist_name_with_comma_not_split(
        self, client, mock_release_data, mocker
    ):
        """
        Test that submitting multiple collab artists as repeated form fields
        resolves each full name, even when a name itself contains a comma
        (e.g. "Earth, Wind & Fire"), rather than splitting it into fragments
        """
        mock_construct = mocker.patch(
            "databass.db.construct_item", return_value=mock_release_data
        )
        mocker.patch(
            "databass.db.models.Release.exists_by_id", return_value=mock_release_data
        )
        mocker.patch("databass.db.update")
        mock_create = mocker.patch(
            "databass.db.models.Artist.create_if_not_exist", return_value=2
        )
        mock_artist = mocker.MagicMock()
        mocker.patch(
            "databass.db.models.Artist.exists_by_id", return_value=mock_artist
        )

        response = client.post(
            "/release/1/edit",
            data=MultiDict(
                [
                    ("collab_artists", "Earth, Wind & Fire"),
                    ("collab_artists", "Nile Rodgers"),
                ]
            ),
        )

        assert response.status_code == 302
        mock_create.assert_any_call("Earth, Wind & Fire")
        mock_create.assert_any_call("Nile Rodgers")
        assert mock_create.call_count == 2
        submit_data = mock_construct.call_args[0][1]
        assert submit_data["collab_artists"] == [mock_artist, mock_artist]

    def test_edit_post_genre_name_with_comma_not_split(
        self, client, mock_release_data, mocker
    ):
        """
        Test that submitting multiple genres as repeated form fields resolves
        each full name, even when a name itself contains a comma, rather than
        splitting it into fragments
        """
        mock_construct = mocker.patch(
            "databass.db.construct_item", return_value=mock_release_data
        )
        mocker.patch(
            "databass.db.models.Release.exists_by_id", return_value=mock_release_data
        )
        mocker.patch("databass.db.update")
        mock_genre = mocker.MagicMock()
        mock_create_genre = mocker.patch(
            "databass.db.models.Genre.create_if_not_exists", return_value=mock_genre
        )

        response = client.post(
            "/release/1/edit",
            data=MultiDict(
                [
                    ("genres", "Chill, Wave"),
                    ("genres", "synthpop"),
                ]
            ),
        )

        assert response.status_code == 302
        mock_create_genre.assert_any_call("Chill, Wave")
        mock_create_genre.assert_any_call("synthpop")
        assert mock_create_genre.call_count == 2
        submit_data = mock_construct.call_args[0][1]
        assert submit_data["genres"] == [mock_genre, mock_genre]

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
        mocker.patch("databass.db.models.Release.exists_by_id", return_value="a")
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

    def test_delete_review_success_redirects_to_referrer(self, client, mocker):
        """
        Test that deleting a review redirects back to the referring page instead of home
        """
        mocker.patch("databass.db.delete")
        mocker.patch("databass.db.models.Review.exists_by_id", return_value=mocker.MagicMock())
        delete_data = {"id": 1, "type": "review"}
        response = client.post(
            "/delete", json=delete_data, headers={"Referer": "/release/1"}
        )
        assert response.status_code == 302
        assert response.location == "/release/1"

    def test_delete_fail_non_existing_review(self, client, mocker):
        """
        Test for proper handling of a deletion request for a review that does not exist,
        checked against the correct model rather than always Release
        """
        mocker.patch("databass.db.models.Release.exists_by_id", return_value="a")
        mocker.patch("databass.db.models.Review.exists_by_id", return_value=False)
        delete_data = {"id": 1, "type": "review"}
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


class TestEditReview:
    # Tests for /release/<id>/edit_review
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

        response = client.post(
            "/release/1/edit_review",
            data={"id": 1, "text": "updated review text"},
            headers={"Referer": "/release/1"},
        )

        assert response.status_code == 302
        assert response.location == "/release/1"
        assert mock_review.text == "updated review text"
        mock_update.assert_called_once_with(mock_review)

    def test_edit_review_fail_non_existing_release(self, client, mocker):
        """
        Test for proper handling of a request to edit a review on a release that does not exist
        """
        mocker.patch("databass.db.models.Release.exists_by_id", return_value=False)
        response = client.post(
            "/release/1/edit_review",
            data={"id": 1, "text": "updated review text"},
            headers={"Referer": "/release/1"},
        )
        assert response.status_code == 302
        assert response.location == "/error"

    def test_edit_review_fail_malformed_request(self, client, mock_release_data, mocker):
        """
        Test for proper handling of a request missing the review id or text
        """
        mocker.patch(
            "databass.db.models.Release.exists_by_id", return_value=mock_release_data
        )
        response = client.post(
            "/release/1/edit_review",
            data={"id": 1},
            headers={"Referer": "/release/1"},
        )
        assert response.status_code == 302
        assert response.location == "/error"

    def test_edit_review_fail_non_existing_review(self, client, mock_release_data, mocker):
        """
        Test for proper handling of a request to edit a review that does not exist
        """
        mocker.patch(
            "databass.db.models.Release.exists_by_id", return_value=mock_release_data
        )
        mocker.patch("databass.db.models.Review.exists_by_id", return_value=None)
        response = client.post(
            "/release/1/edit_review",
            data={"id": 99, "text": "updated review text"},
            headers={"Referer": "/release/1"},
        )
        assert response.status_code == 302
        assert response.location == "/error"

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
        response = client.post(
            "/release/1/edit_review",
            data={"id": 1, "text": "updated review text"},
            headers={"Referer": "/release/1"},
        )
        assert response.status_code == 302
        assert response.location == "/error"
