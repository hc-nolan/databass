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


@pytest.fixture()
def existing_label(app):
    with app.app_context():
        label = Label(name="Test Label")
        app_db.session.add(label)
        app_db.session.commit()
        return label.id


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
