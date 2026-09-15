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


class TestMeanAvgAndCount:
    # Tests for mean_avg_and_count()
    @pytest.mark.parametrize(
        "input_list,expected_avg,expected_count",
        [
            ([{"avg": 98, "count": 5},{"avg": 80, "count": 10}], 89.0, 7.5),
            ([{"avg": 47, "count": 1},{"avg": 53, "count": 4},{"avg": 62, "count": 2}], 54.0, 2.3333333333333335)
        ]
    )
    def test_mean_avg_and_count_success(self, input_list, expected_avg, expected_count, mocker):
        """
        Test for proper handling of successful calculation of average and total count
        """
        # Construct list of mock objects to be passed to the function
        mock_list = []
        for item in input_list:
            mock_item = mocker.MagicMock()
            mock_item.average_rating = item["avg"]
            mock_item.release_count = item["count"]
            mock_list.append(mock_item)

        result_avg, result_count = mean_avg_and_count(mock_list)
        assert result_avg == expected_avg
        assert result_count == expected_count


    def test_mean_avg_and_count_fail(self, mocker):
        """
        Test for proper handling of invalid input data; invalid element should be discounted from the end calculation
        """
        mock_row = mocker.MagicMock()
        mock_row.average_rating = 60
        mock_row.release_count = 2
        entity_list = [{"test": 1}, mock_row]
        result_avg, result_count = mean_avg_and_count(entity_list)
        assert result_avg == 60
        assert result_count == 2


class TestBayesianAvg:
    # Tests for bayesian_avg()
    @pytest.mark.parametrize(
        "weight,item_avg,mean_avg",
        [
            (2.0, 1.0, None),
            (2.0, None, 3.0),
            (None, 1.0, 3.0)
        ]
    )
    def test_bayesian_avg_missing_value(self, weight, item_avg, mean_avg):
        """
        Test for correct handling of input with missing values
        """
        with pytest.raises(ValueError, match="Input missing one of the required values"):
            bayesian_avg(
                    item_weight=weight,
                    item_avg=item_avg,
                    mean_avg=mean_avg
            )

    @pytest.mark.parametrize(
        "weight,item_avg,mean_avg,expected",
        [
            (1.0, 2.0, 3.0, 2.0),
            (2.0, 3.0, 1.0, 5.0),
            (3.0, 1.0, 2.0, -1.0)
        ]
    )
    def test_bayesian_avg_correct_return(self, weight, item_avg, mean_avg, expected):
        """
        Test for correct handling of valid input
        """
        result = bayesian_avg(
                item_weight=weight,
                item_avg=item_avg,
                mean_avg=mean_avg
        )
        assert result == expected
        
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