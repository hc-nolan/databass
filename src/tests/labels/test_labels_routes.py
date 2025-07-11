import pytest
from databass import create_app


# TODO: this fixture is a duplicate of the same fixture in test_routes.py; figure out how to generalize/reuse a single fixture instead of duplicating the code
@pytest.fixture()
def client():
    app = create_app()
    app.config.update({"TESTING": True})
    with app.test_client() as client:
        yield client


class TestLabels:
    # Tests for /labels
    def test_labels_successful_page_load(self, client, mocker):
        """
        Test for successful page load
        """

        def mock_get_distinct_column_values(column_name):
            if column_name == "country":
                return ["US", "UK"]
            elif column_name == "type":
                return ["Original Production", "Imprint"]

        mock_db = mocker.patch(
            "databass.db.models.Label.get_distinct_column_values",
            side_effect=mock_get_distinct_column_values,
        )
        response = client.get("/labels")
        assert response.status_code == 200
        assert b"label_search" in response.data
        assert b"US" in response.data
        assert b"Imprint" in response.data
        assert mock_db.call_count == 2


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


# class TestEdit:
#     # Tests for /label/<id>/edit
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
