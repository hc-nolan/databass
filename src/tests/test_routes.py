import pytest
from databass import create_app
from databass.db.models import Goal
from databass.routes import country_code
from datetime import datetime, timedelta


@pytest.fixture()
def client():
    app = create_app()
    app.config.update({"TESTING": True})
    with app.test_client() as client:
        yield client


class TestHome:
    # Tests for /api/home
    def test_home_page_load_success(self, client):
        response = client.get("/api/home")
        assert response.status_code == 200
        assert "total_logged" in response.json

    def test_home_does_not_show_expired_goal(self, client, mocker):
        now = datetime.now()
        expired = Goal(
            id=1,
            start=now - timedelta(days=365),
            end=now - timedelta(days=1),
            completed=None,
            type="release",
            amount=1500,
        )
        mocker.patch("databass.db.models.Goal.get_incomplete", return_value=[expired])

        response = client.get("/api/home")

        assert response.status_code == 200
        assert response.json["goal"] is None


class TestNew:
    # Tests for /api/new
    def test_new_page_load_success(self, client):
        response = client.get("/api/new")
        assert response.status_code == 200
        assert "today" in response.json


class TestSearch:
    # Tests for /api/search
    def test_search_page_load_success(self, client, mocker):
        """
        Test for successful search
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
            "/api/search",
            json={
                "referrer": "search",
                "release": "search",
                "artist": "",
                "label": "",
            },
        )
        assert response.status_code == 200
        assert len(response.json["results"]) == 1

    def test_search_page_load_success_no_results(self, client, mocker):
        """
        Test for successful handling when no search results are found
        """
        mocker.patch("databass.api.MusicBrainz.release_search", return_value=[])
        response = client.post(
            "/api/search",
            json={
                "referrer": "search",
                "release": "search",
                "artist": "",
                "label": "",
            },
        )
        assert response.status_code == 200
        assert response.json["results"] == []

    def test_search_malformed_request_no_search_terms(self, client):
        response = client.post(
            "/api/search",
            json={"referrer": "search", "release": None, "artist": None, "label": None},
        )
        assert response.status_code == 400
        assert "error" in response.json

    def test_search_non_json(self, client):
        """
        Test for successful handling of a request missing JSON data
        """
        response = client.post("/api/search")
        assert response.status_code == 415


class TestArt:
    # Tests for /api/art
    def test_art_search_success(self, client, mocker):
        mock_candidates = [
            {
                "source": "caa",
                "url": "http://coverartarchive.org/release/a/front",
                "thumb": "http://coverartarchive.org/release/a/front-250",
                "label": "Front",
            }
        ]
        mock_call = mocker.patch(
            "databass.routes.image.get_art_candidates", return_value=mock_candidates
        )

        response = client.post(
            "/api/art",
            json={
                "release_group_mbid": "rg-1",
                "release_mbid": "rel-1",
                "name": "Test Album",
                "artist": "Test Artist",
            },
        )

        assert response.status_code == 200
        assert response.json["candidates"] == mock_candidates
        mock_call.assert_called_once_with(
            release_group_mbid="rg-1",
            release_mbid="rel-1",
            release_name="Test Album",
            artist_name="Test Artist",
        )

    def test_art_search_no_candidates(self, client, mocker):
        mocker.patch("databass.routes.image.get_art_candidates", return_value=[])

        response = client.post(
            "/api/art",
            json={"name": "Test Album", "artist": "Test Artist"},
        )

        assert response.status_code == 200
        assert response.json["candidates"] == []

    def test_art_search_missing_data_returns_400(self, client):
        response = client.post("/api/art", json={})

        assert response.status_code == 400
        assert "error" in response.json

    def test_art_search_artist_only_returns_400(self, client):
        """Artist alone can't produce candidates, so it shouldn't pass validation."""
        response = client.post("/api/art", json={"artist": "Radiohead"})

        assert response.status_code == 400
        assert "error" in response.json

    def test_art_search_non_json(self, client):
        response = client.post("/api/art")

        assert response.status_code == 415


class TestGetReleaseData:
    # Tests for routes.get_release_data image passthrough
    def test_keeps_chosen_image_url(self):
        from databass.routes import get_release_data

        data = get_release_data(
            {
                "release_name": "Test Album",
                "year": "2020",
                "rating": "50",
                "image": "http://example.com/art.png",
                "listen_date": "2020-01-01",
            }
        )

        assert data["image"] == "http://example.com/art.png"

    def test_no_image_means_none(self):
        from databass.routes import get_release_data

        data = get_release_data(
            {
                "release_name": "Test Album",
                "year": "2020",
                "rating": "50",
                "listen_date": "2020-01-01",
            }
        )

        assert data["image"] is None


class TestSubmit:
    # Tests for /api/submit
    def test_submit_malformed_request(self, client):
        response = client.post("/api/submit", json={})
        assert response.status_code == 500
        assert "error" in response.json

    @pytest.mark.parametrize(
        "data_dict",
        [
            {
                "manual_submit": False,
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
                "manual_submit": True,
                "name": "asdf",
                "rating": "50",
                "year": "2100",
                "genres": "asdf",
            },
        ],
    )
    def test_submit_successful_page_load(self, client, mocker, data_dict):
        """Test for successful submission"""
        mock_handler = mocker.patch(
            "databass.routes.handle_submit_data", return_value=[]
        )

        response = client.post("/api/submit", json=data_dict)

        assert response.status_code == 201
        assert response.json["ok"] is True
        mock_handler.assert_called_once()

    def test_submit_integrity_error_shows_field_specific_message(self, client, mocker):
        """A unique-constraint violation should surface which field caused it."""
        from sqlalchemy.exc import IntegrityError

        mocker.patch(
            "databass.routes.handle_submit_data",
            side_effect=IntegrityError(
                "statement", {}, Exception("UNIQUE constraint failed: release.mbid")
            ),
        )
        data = {
            "manual_submit": True,
            "artist": "asdf",
            "main_genre": "asdf",
            "label": "asdf",
            "name": "asdf",
            "rating": "50",
            "year": "2100",
            "genres": "asdf",
        }
        response = client.post("/api/submit", json=data)
        assert response.status_code == 400
        assert "mbid" in response.json["error"]
        assert "already exists" in response.json["error"]

    def test_submit_unexpected_error_is_flashed_not_500(self, client, mocker):
        """Any other unexpected exception should also be surfaced, not crash."""
        mocker.patch(
            "databass.routes.handle_submit_data",
            side_effect=ValueError("ERROR: No supported image type found in URL: x"),
        )
        data = {
            "manual_submit": True,
            "artist": "asdf",
            "main_genre": "asdf",
            "label": "asdf",
            "name": "asdf",
            "rating": "50",
            "year": "2100",
            "genres": "asdf",
        }
        response = client.post("/api/submit", json=data)
        assert response.status_code == 400
        assert "No supported image type found" in response.json["error"]


class TestStats:
    # Tests for /api/stats
    def test_stats_page_load_success(self, client):
        response = client.get("/api/stats")
        assert response.status_code == 200
        assert "stats" in response.json

    def test_stats_period_ajax(self, client):
        response = client.get("/api/stats/period/all")
        assert response.status_code == 200
        assert "stats" in response.json

    def test_stats_get_artists(self, client):
        response = client.get("/api/stats/leaderboards/artists")
        assert response.status_code == 200
        assert "boards" in response.json

    def test_stats_get_labels(self, client):
        response = client.get("/api/stats/leaderboards/labels")
        assert response.status_code == 200
        assert "boards" in response.json


class TestGoals:
    # Tests for /api/goals (GET)
    def test_goals_no_active_goal(self, client, mocker):
        """
        Test for correct handling when there is no active (incomplete) goal
        """
        mocker.patch("databass.db.models.Goal.get_incomplete", return_value=[])
        mocker.patch("databass.db.models.Goal.get_past", return_value=[])
        response = client.get("/api/goals")
        assert response.status_code == 200
        assert response.json["active_goal"] is None
        assert response.json["past_goals"] == []

    def test_goals_active_goal_displayed(self, client, mocker):
        """
        Test that the most recent incomplete goal is returned as the active goal
        """
        active = Goal(
            id=1,
            start=datetime(2024, 1, 1),
            end=datetime(2027, 1, 1),
            completed=None,
            type="release",
            amount=250,
        )
        mocker.patch("databass.db.models.Goal.get_incomplete", return_value=[active])
        mocker.patch("databass.db.models.Goal.get_past", return_value=[])
        response = client.get("/api/goals")
        assert response.status_code == 200
        assert response.json["active_goal"]["target"] == 250
        assert response.json["active_goal"]["type_label"] == "releases"

    def test_goals_selects_newest_goal_containing_today(self, client, mocker):
        """Stale/future goals must not displace the newest genuinely active goal."""
        now = datetime.now()
        stale = Goal(
            id=1,
            start=now - timedelta(days=500),
            end=now - timedelta(days=1),
            completed=None,
            type="release",
            amount=1500,
        )
        future = Goal(
            id=2,
            start=now + timedelta(days=1),
            end=now + timedelta(days=365),
            completed=None,
            type="artist",
            amount=50,
        )
        older_active = Goal(
            id=3,
            start=now - timedelta(days=100),
            end=now + timedelta(days=100),
            completed=None,
            type="release",
            amount=250,
        )
        newer_active = Goal(
            id=4,
            start=now - timedelta(days=10),
            end=now + timedelta(days=100),
            completed=None,
            type="label",
            amount=25,
        )
        mocker.patch(
            "databass.db.models.Goal.get_incomplete",
            return_value=[stale, future, older_active, newer_active],
        )
        mocker.patch("databass.db.models.Goal.get_past", return_value=[])

        response = client.get("/api/goals")

        assert response.status_code == 200
        assert response.json["active_goal"]["target"] == 25
        assert response.json["active_goal"]["type_label"] == "labels"

    def test_goals_have_no_active_goal_when_only_stale_or_future(self, client, mocker):
        now = datetime.now()
        stale = Goal(
            id=1,
            start=now - timedelta(days=10),
            end=now - timedelta(days=1),
            completed=None,
            type="release",
            amount=100,
        )
        future = Goal(
            id=2,
            start=now + timedelta(days=1),
            end=now + timedelta(days=10),
            completed=None,
            type="release",
            amount=100,
        )
        mocker.patch(
            "databass.db.models.Goal.get_incomplete", return_value=[stale, future]
        )
        mocker.patch("databass.db.models.Goal.get_past", return_value=[])

        response = client.get("/api/goals")

        assert response.status_code == 200
        assert response.json["active_goal"] is None

    def test_goals_past_goals_displayed(self, client, mocker):
        """
        Test that completed and missed goals are returned under "past"
        """
        completed = Goal(
            id=2,
            start=datetime(2023, 1, 1),
            end=datetime(2024, 1, 1),
            completed=datetime(2023, 11, 2),
            type="release",
            amount=100,
        )
        missed = Goal(
            id=3,
            start=datetime(2022, 1, 1),
            end=datetime(2023, 1, 1),
            completed=None,
            type="artist",
            amount=50,
        )
        mocker.patch("databass.db.models.Goal.get_incomplete", return_value=[])
        mocker.patch(
            "databass.db.models.Goal.get_past", return_value=[completed, missed]
        )
        response = client.get("/api/goals")
        assert response.status_code == 200
        past_goals = response.json["past_goals"]
        badges = {g["badge"] for g in past_goals}
        titles = {g["title"] for g in past_goals}
        assert "COMPLETE" in badges
        assert "MISSED" in badges
        assert "100 releases" in titles
        assert "50 artists" in titles


class TestAddGoal:
    # Tests for /api/goals (POST)
    def test_add_goals_no_payload(self, client):
        response = client.post("/api/goals", json={})
        assert response.status_code == 400
        assert "error" in response.json

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
        response = client.post("/api/goals", json=data)
        assert response.status_code == 400
        assert "error" in response.json

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
        response = client.post("/api/goals", json=data)

        mock_goal.assert_called_once_with(model_name="goal", data_dict=data)
        assert response.status_code == 201
        assert response.json["ok"] is True
        mock_insert.assert_called_once_with(mock_goal.return_value)


class TestCountryCode:
    def test_country_code_with_valid_country(self):
        assert country_code("United States") == "US"

    def test_country_code_with_code(self):
        assert country_code("US") == "US"

    def test_country_code_with_invalid_country(self):
        assert country_code("Invalid Country") == "Invalid Country"

    def test_country_code_with_none(self):
        assert country_code(None) is None

    def test_country_code_with_partial_match(self, mocker):
        mock_lookup = mocker.patch("pycountry.countries.lookup")
        mock_lookup.side_effect = KeyError

        assert country_code("United") == "United"
        mock_lookup.assert_called_once_with("United")


class TestApiDelete:
    # Tests for DELETE /api/<item_type>/<item_id>
    def test_delete_success(self, client, mocker):
        mocker.patch("databass.db.models.Release.exists_by_id", return_value=True)
        mock_delete = mocker.patch("databass.db.delete")
        response = client.delete("/api/release/1")
        assert response.status_code == 200
        assert response.json["ok"] is True
        mock_delete.assert_called_once_with(item_type="release", item_id=1)

    def test_delete_fail_unsupported_item_type(self, client):
        response = client.delete("/api/unsupported/1")
        assert response.status_code == 404

    def test_delete_fail_non_existing_item(self, client, mocker):
        mocker.patch("databass.db.models.Review.exists_by_id", return_value=False)
        response = client.delete("/api/review/1")
        assert response.status_code == 404
        assert "error" in response.json
