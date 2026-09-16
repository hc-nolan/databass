import pytest
from databass import create_app
from databass.db.base import app_db
from databass.db.models import Label


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


class TestLabels:
    # Tests for /labels
    def test_labels_redirects_to_browse(self, client):
        response = client.get("/labels")
        assert response.status_code == 301
        assert response.headers["Location"] == "/browse/labels"


class TestLabel:
    # Tests for /label
    def test_label_successful_page_load(self, client, mocker):
        """
        Test for successful page load
        """
        mock_label = mocker.MagicMock()
        mock_label.id = 1
        mock_label.name = "Test Label"
        mock_label.country = "US"
        mock_db_label = mocker.patch(
            "databass.db.models.Label.exists_by_id", return_value=mock_label
        )
        mock_release = mocker.MagicMock()
        mock_release.Release = mocker.MagicMock()
        mock_release.Release.id = 1

        mock_country = mocker.MagicMock()
        mock_country.name = "United States"
        mock_get_country = mocker.patch(
            "pycountry.countries.get", return_value=mock_country
        )

        response = client.get("/label/1")
        assert response.status_code == 200
        assert b"Test Label" in response.data

    def test_label_not_found(self, client, mocker):
        mock_label_data = mocker.patch(
            "databass.db.models.Label.exists_by_id", return_value=False
        )
        response = client.get("/label/1")
        assert response.status_code == 302
        assert response.location == "/error"
        assert b"You should be redirected automatically" in response.data


@pytest.fixture()
def existing_label(app):
    with app.app_context():
        label = Label(name="Test Label")
        app_db.session.add(label)
        app_db.session.commit()
        return label.id


class TestEditLabel:
    # Tests for /label/<id>/edit
    def test_edit_unsupported_image_url_flashes_error(self, client, mocker, existing_label):
        mocker.patch(
            "databass.labels.routes.Util.get_image_from_url",
            side_effect=ValueError(
                "ERROR: No supported image type found in URL: https://example.com/page"
            ),
        )
        response = client.post(
            f"/label/{existing_label}/edit",
            data={"image": "https://example.com/page"},
        )
        assert response.status_code == 302
        assert response.location == "/error"

        error_response = client.get("/error")
        assert b"No supported image type found" in error_response.data


class TestApiEditLabel:
    # Tests for PUT /api/label/<id>
    def test_api_edit_unsupported_image_url_returns_400(self, client, mocker, existing_label):
        mocker.patch(
            "databass.labels.routes.Util.get_image_from_url",
            side_effect=ValueError(
                "ERROR: No supported image type found in URL: https://example.com/page"
            ),
        )
        response = client.put(
            f"/api/label/{existing_label}",
            json={"image": "https://example.com/page"},
        )
        assert response.status_code == 400
        assert "No supported image type found" in response.get_json()["error"]
