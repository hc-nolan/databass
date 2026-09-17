import pytest
from databass.db.util import *


class MockModel:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

mock_models = {
    'Release': MockModel,
    'Artist': MockModel,
    'Label': MockModel,
    'Goal': MockModel,
    'Review': MockModel,
    'Tag': MockModel,
}

@pytest.fixture
def mock_model_fixture():
    return lambda model_name: mock_models.get(model_name.capitalize(), None)




# class TestNextItem:
    # Tests for next_item()
    # Skipping tests for this function for now, because the only place it is used is in /fix_images

# class TestApplyComparisonFilter:
    # Tests for apply_comparison_filter()
    # Skipping tests for this function for now; all it does is add terms to the SQLAlchemy query
    # Could still add a few basic tests for correct error handling though


class TestGetAllStats:
    # Tests for get_all_stats()
    def test_get_all_stats_success(self):
        """
        Test for correct handling of successfully returned stats data
        """

    def test_get_all_stats_fail(self):
        """
        Test for successful handling of errored stats function result
        """



class TestHandleSubmitData:
    # Tests for handle_submit_data()
    def test_handle_submit_test_success(self):
        pass

    def _base_submit_data(self, **overrides):
        data = {
            "mbid": None,
            "label_mbid": None,
            "label_name": None,
            "artist_mbid": None,
            "artist_name": None,
            "main_genre": None,
            "genres": None,
            "note": None,
        }
        data.update(overrides)
        return data

    def _patch_common(self, mocker):
        mocker.patch("databass.db.util.Label.create_if_not_exist", return_value=0)
        mocker.patch("databass.db.util.Artist.create_if_not_exist", return_value=0)
        mocker.patch("databass.db.util.Release.create_new", return_value=1)
        mocker.patch("databass.db.util.Goal.check_goals", return_value=[])
        return mocker.patch(
            "databass.db.util.Genre.create_if_not_exists", side_effect=lambda name: name
        )

    def test_handle_submit_data_accepts_genres_as_list(self, mocker):
        """genres is sent as a list by the JSON API; it should not raise"""
        genre_mock = self._patch_common(mocker)
        submit_data = self._base_submit_data(genres=["rock", "jazz"])

        result = handle_submit_data(submit_data)

        genre_mock.assert_any_call("rock")
        genre_mock.assert_any_call("jazz")
        assert result == []

    def test_handle_submit_data_accepts_genres_as_comma_string(self, mocker):
        """genres is sent as a comma-separated string by the legacy form POST"""
        genre_mock = self._patch_common(mocker)
        submit_data = self._base_submit_data(genres="rock,jazz")

        handle_submit_data(submit_data)

        genre_mock.assert_any_call("rock")
        genre_mock.assert_any_call("jazz")