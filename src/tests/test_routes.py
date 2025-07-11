import pytest
from databass import create_app
from datetime import datetime


@pytest.fixture()
def client():
    app = create_app()
    app.config.update({"TESTING": True})
    with app.test_client() as client:
        yield client


class TestHome:
    # Tests for /, /home
    def test_home_page_load_success(self, client):
        response = client.get("/")
        assert response.status_code == 200
        assert b"home_release_table" in response.data


class TestNew:
    # Tests for /new
    def test_new_page_load_success(self, client):
        response = client.get("/new")
        assert response.status_code == 200
        assert b"new-release" in response.data


class TestSearch:
    # Tests for /search
    def test_search_page_load_success(self, client, mocker):
        """
        Test for successful page load
        """
        mocker.patch(
            "databass.api.MusicBrainz.release_search",
            return_value=[
                {
                    "release": {"name": "name"},
                    "artist": {"name": "name"},
                    "label": {"name": "name"},
                }
            ],
        )
        response = client.post(
            "/search",
            json={
                "referrer": "search",
                "release": "search",
                "artist": "",
                "label": "",
            },
        )
        assert response.status_code == 200
        assert b"data_form" in response.data

    def test_search_page_load_success_no_results(self, client, mocker):
        """
        Test for successful page load when no search results are found
        """
        mocker.patch("databass.api.MusicBrainz.release_search", return_value=[])
        response = client.post(
            "/search",
            json={
                "referrer": "search",
                "release": "search",
                "artist": "",
                "label": "",
            },
        )
        assert response.status_code == 200
        assert b"No search results" in response.data

    def test_search_malformed_request_no_search_terms(self, client):
        """
        Test for successful page load
        """
        response = client.post(
            "/search",
            json={"referrer": "search", "release": None, "artist": None, "label": None},
        )
        assert response.status_code == 302
        assert response.location == "/error"

    def test_search_non_json(self, client):
        """
        Test for successful handling of a request missing JSON data
        """
        response = client.post("/search")
        assert response.status_code == 415


class TestSubmit:
    # Tests for /submit
    # TODO: make compatible with manual submission after routes.submit_manual() is merged into routes.submit()
    def test_submit_malformed_request(self, client):
        """
        Test for successful handling of a request missing required data
        """
        response = client.post("/submit")
        assert response.status_code == 302
        assert response.location == "/error"

    @pytest.mark.parametrize(
        "data_dict",
        [
            {
                "manual_submit": "false",
                "artist": "Silly Goose",
                "artist_mbid": "da677401-713b-4b4a-969f-a0a6655fe2d3",
                "country": "",
                "main_genre": "a",
                "label": "Rap Rock Records",
                "label_mbid": "16a5347b-2d21-4ea6-b2b1-340374587cc8",
                "rating": "5",
                "release_group_id": "15332fc6-a448-49c0-b057-2596bf0d96a8",
                "release_mbid": "52feb9b9-98f5-46af-a108-b5f01540419c",
                "release_name": "King Of The Hill",
                "year": "3452",
                "genres": "",
                "track_count": "1",
            },
            {
                "art": "",
                "artist": "asfd",
                "main_genre": "asdf",
                "label": "asdf",
                "manual_submit": "true",
                "name": "asdf",
                "rating": "50",
                "year": "2100",
                "genres": "asdf",
            },
        ],
    )
    def test_submit_successful_page_load(self, client, mocker, data_dict):
        """Test for successful submission and redirection"""

        # Mock the handle_submit_data function
        mock_handler = mocker.patch("databass.routes.handle_submit_data")

        # Ensure that the mock handler is correctly called in the test
        response = client.post("/submit", data=data_dict)

        # Assert the response contains "redirected" in the data and that it's a 302 redirect
        assert b"redirected" in response.data
        assert response.status_code == 302

        # Check if handle_submit_data was called
        mock_handler.assert_called_once()


class TestStats:
    # Tests for /stats
    def test_home_page_load_success(self, client, mocker):
        mock_get_stats = mocker.patch("databass.routes.get_all_stats", return_value={})
        response = client.get("/stats")
        assert response.status_code == 200
        assert b"stats" in response.data
        mock_get_stats.assert_called_once()


class TestGoals:
    # Tests for /goals route
    def test_goals_no_goals_found(self, client, mocker):
        """
        Test for correct handling when no goals are found in database
        """
        mocker.patch("databass.db.models.Goal.get_incomplete", return_value=[])
        response = client.get("/goals")
        assert response.status_code == 200
        assert b"No existing goals" in response.data

    def test_goals_all_goals_displayed(self, client, mocker):
        """
        Test that all goals available in database are displayed
        """
        mock_goals = [
            {
                "id": 1,
                "start": datetime(2024, 1, 1),
                "end": datetime(2025, 1, 1),
                "completed": None,
                "type": "release",
                "amount": 50,
            },
            {
                "id": 2,
                "start": datetime(2024, 1, 1),
                "end": datetime(2026, 1, 1),
                "completed": None,
                "type": "album",
                "amount": 10,
            },
            {
                "id": 3,
                "start": datetime(2024, 1, 1),
                "end": datetime(2027, 1, 1),
                "completed": None,
                "type": "label",
                "amount": 250,
            },
        ]
        mocker.patch("databass.db.models.Goal.get_incomplete", return_value=mock_goals)
        response = client.get("/goals")
        assert response.status_code == 200
        assert b"2027-01-01" in response.data
        assert b"10" in response.data
        assert b"release" in response.data


class TestAddGoal:
    # Tests for /add_goal
    def test_add_goals_no_payload(self, client):
        """
        Test for successful handling of empty payload
        """
        response = client.post("/add_goal")
        assert response.status_code == 302
        assert response.location == "/error"

    def test_add_goals_goal_construction_error(self, client, mocker):
        """
        Test for successful handling of Goal object construction errors
        """
        data = {
            "amount": "4",
            "end_goal": "2024-10-24",
            "start_date": "2024-10-11",
            "type": "release",
        }
        mocker.patch("databass.db.construct_item", return_value=None)
        response = client.post("/add_goal", data=data)
        assert response.status_code == 302
        assert response.location == "/error"

    @pytest.mark.parametrize(
        "amount,end_goal,start_date,goal_type",
        [
            ("4", "2024-10-24", "2024-10-11", "release"),
            ("100000", "2025-01-01", "2030-12-12", "album"),
            ("4234", "2111-11-11", "3000-01-01", "label"),
        ],
    )
    def test_add_goals_goal_construction_success(
        self, client, mocker, amount, end_goal, start_date, goal_type
    ):
        """
        Test for successful Goal object construction and insertion
        """
        mock_insert = mocker.patch("databass.db.insert", return_value=2)
        mock_goal = mocker.patch("databass.db.construct_item", autospec=True)
        mock_instance = mock_goal.return_value
        mock_instance.id = 2

        data = {
            "amount": amount,
            "end_goal": end_goal,
            "start_date": start_date,
            "type": goal_type,
        }
        response = client.post("/add_goal", data=data)

        mock_goal.assert_called_once_with(
            model_name="goal",
            data_dict={
                "amount": amount,
                "end_goal": end_goal,
                "start_date": start_date,
                "type": goal_type,
            },
        )
        assert response.status_code == 302
        assert response.location == "/goals"
        mock_insert.assert_called_once_with(mock_goal.return_value)


class TestCountryCode:
    def test_country_code_with_valid_country(self, client):
        country_code = client.application.jinja_env.filters["country_code"]

        def test_filter(country: str):
            return country_code(country)

        assert test_filter("United States") == "US"

    def test_country_code_with_code(self, client):
        country_code = client.application.jinja_env.filters["country_code"]

        def test_filter(country: str):
            return country_code(country)

        assert test_filter("US") == "US"

    def test_country_code_with_invalid_country(self, client):
        country_code = client.application.jinja_env.filters["country_code"]

        def test_filter(country: str):
            return country_code(country)

        assert test_filter("Invalid Country") == "Invalid Country"

    def test_country_code_with_none(self, client):
        country_code = client.application.jinja_env.filters["country_code"]

        def test_filter(country: str):
            return country_code(country)

        assert test_filter(None) is None

    def test_country_code_with_partial_match(self, client, mocker):
        mock_lookup = mocker.patch("pycountry.countries.lookup")
        mock_lookup.side_effect = KeyError

        country_code = client.application.jinja_env.filters["country_code"]

        def test_filter(country: str):
            return country_code(country)

        assert test_filter("United") == "United"
        mock_lookup.assert_called_once_with("United")
