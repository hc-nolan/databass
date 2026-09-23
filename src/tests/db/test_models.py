import pytest
from databass import create_app
from databass.db.models import (
    Release,
    Artist,
    Label,
    ArtistOrLabel,
    Goal,
    Genre,
    mean_avg_and_count,
    bayesian_avg,
)
from datetime import datetime, timedelta


@pytest.fixture
def app():
    """Create and configure a test Flask application"""
    app = create_app()
    app.config.update({"TESTING": True})
    return app


class TestBaseGetAll:
    """
    Test suite for Base.get_all class method

    Uses Release as a concrete model class since Base is not actually used in the database.
    """

    def test_get_all_returns_list(self, mocker):
        """
        Test that get_all returns a list regardless of whether entries exist
        """
        mock_query = mocker.patch("databass.db.base.app_db.session.query")
        mock_query.return_value.all.return_value = []

        result = Release.get_all()
        assert isinstance(result, list)

    def test_get_all_returns_all_entries(self, mocker):
        """
        Test that get_all returns all entries from the database
        """
        mock_entries = [mocker.Mock(), mocker.Mock(), mocker.Mock()]
        mock_query = mocker.patch("databass.db.base.app_db.session.query")
        mock_query.return_value.all.return_value = mock_entries

        result = Release.get_all()
        assert len(result) == 3
        assert result == mock_entries

    def test_get_all_queries_correct_model(self, mocker):
        """
        Test that get_all queries the correct model class
        """
        mock_query = mocker.patch("databass.db.base.app_db.session.query")
        mock_query.return_value.all.return_value = []

        Release.get_all()
        mock_query.assert_called_once_with(Release)


class TestBaseTotalCount:
    """
    Test suite for Base.total_count class method

    Uses Release as a concrete model class since Base is not actually used in the database.
    """

    def test_total_count_returns_integer(self, mocker):
        """
        Test that total_count returns an integer value
        """
        mock_query = mocker.patch("databass.db.base.app_db.session.query")
        mock_query.return_value.count.return_value = 0

        # Mock the session to ensure it returns the count value
        mock_session = mocker.patch("databass.db.base.app_db.session")
        mock_session.query.return_value.count.return_value = 0

        result = Release.total_count()
        print(result)
        assert isinstance(result, int)

    def test_total_count_queries_correct_model(self, mocker):
        """
        Test that total_count queries the correct model class
        """
        mock_query = mocker.patch("databass.db.base.app_db.session.query")
        mock_query.return_value.count.return_value = 0

        Release.total_count()
        mock_query.assert_called_once_with(Release)

    @pytest.mark.parametrize("count_value", [0, 1, 100])
    def test_total_count_returns_correct_value(self, mocker, count_value):
        """
        Test that total_count returns the correct count from the database
        """
        # Mock both query and session to ensure proper return value
        mock_session = mocker.patch("databass.db.base.app_db.session")
        mock_session.query.return_value.count.return_value = count_value

        result = Release.total_count()
        assert result == count_value

    def test_total_count_with_database(self, mocker):
        """
        Test total_count with database operations through mocking
        """
        mock_query = mocker.patch("databass.db.base.app_db.session.query")
        mock_query.return_value.count.return_value = 0

        initial_count = Release.total_count()
        assert initial_count == 0

        # Simulate adding records by changing mock return value
        mock_query.return_value.count.return_value = 3

        final_count = Release.total_count()
        assert final_count == 3


class TestBaseExistsById:
    """Test suite for Base.exists_by_id class method"""

    def test_exists_by_id_returns_none_for_nonexistent_id(self, mocker):
        """Test that exists_by_id returns None when no matching ID is found"""
        mock_query = mocker.patch("databass.db.base.app_db.session.query")
        mock_query.return_value.filter.return_value.one_or_none.return_value = None

        result = Release.exists_by_id(999)
        assert result is None
        mock_query.assert_called_once_with(Release)

    def test_exists_by_id_returns_object_when_found(self, mocker):
        """Test that exists_by_id returns the object when a matching ID is found"""
        mock_release = mocker.Mock()
        mock_query = mocker.patch("databass.db.base.app_db.session.query")
        mock_query.return_value.filter.return_value.one_or_none.return_value = (
            mock_release
        )

        result = Release.exists_by_id(1)
        assert result == mock_release
        mock_query.assert_called_once_with(Release)

    @pytest.mark.parametrize("test_id", [None, "string_id", 3.14, [], {}])
    def test_exists_by_id_with_invalid_id_types(self, mocker, test_id):
        """Test that exists_by_id handles invalid ID types appropriately"""
        mock_query = mocker.patch("databass.db.base.app_db.session.query")

        result = Release.exists_by_id(test_id)
        # Should still attempt to query even with invalid types
        # as SQLAlchemy will handle type conversion/errors
        mock_query.assert_called_once_with(Release)

    def test_exists_by_id_query_construction(self, mocker):
        """Test that exists_by_id constructs the correct query"""
        mock_query = mocker.patch("databass.db.base.app_db.session.query")
        mock_filter = mocker.Mock()
        mock_query.return_value.filter = mock_filter
        mock_filter.return_value.one_or_none.return_value = None

        Release.exists_by_id(1)

        # Verify the query chain
        mock_query.assert_called_once_with(Release)
        mock_filter.assert_called_once()

    def test_exists_by_id_handles_database_error(self, mocker):
        """Test that exists_by_id handles database errors gracefully"""
        mock_query = mocker.patch("databass.db.base.app_db.session.query")
        mock_query.return_value.filter.return_value.one_or_none.side_effect = Exception(
            "Database error"
        )

        result = Release.exists_by_id(1)
        assert result is None
        mock_query.assert_called_once_with(Release)


class TestBaseGetDistinctColumnValues:
    """Test suite for Base.get_distinct_column_values class method"""

    def test_get_distinct_column_values_returns_list(self, mocker):
        """Test that get_distinct_column_values returns a list"""
        mock_query = mocker.patch("databass.db.base.app_db.session.query")
        mock_query.return_value = []

        result = Release.get_distinct_column_values("main_genre")
        assert isinstance(result, list)

    @pytest.mark.parametrize(
        "column,values",
        [
            ("main_genre", ["Rock", "Jazz", "Electronic"]),
            ("country", ["US", "UK", "DE"]),
            ("rating", [1, 2, 3, 4, 5]),
        ],
    )
    def test_get_distinct_column_values_returns_correct_values(
        self, mocker, column, values
    ):
        """Test that get_distinct_column_values returns the correct distinct values for a given column"""
        mock_query = mocker.patch("databass.db.base.app_db.session.query")
        mock_query.return_value = [(value,) for value in values]

        result = Release.get_distinct_column_values(column)
        assert result == values

    def test_get_distinct_column_values_invalid_column(self):
        """Test that get_distinct_column_values raises AttributeError for invalid column name"""
        with pytest.raises(AttributeError):
            Release.get_distinct_column_values("nonexistent_column")

    def test_get_distinct_column_values_handles_empty_results(self, mocker):
        """Test that get_distinct_column_values handles empty result sets correctly"""
        mock_query = mocker.patch("databass.db.base.app_db.session.query")
        mock_query.return_value = []

        result = Release.get_distinct_column_values("main_genre")
        assert result == []

    def test_get_distinct_column_values_queries_correct_attribute(self, mocker):
        """Test that get_distinct_column_values constructs the query with the correct column attribute"""
        mock_query = mocker.patch("databass.db.base.app_db.session.query")
        mock_query.return_value = []

        Release.get_distinct_column_values("main_genre")

        # Verify the distinct() call was made on the correct column
        mock_query.assert_called_once()
        args = mock_query.call_args[0]
        assert "genre" in str(args[0])


class TestMusicBrainzEntityExistsByMbid:
    """Test suite for MusicBrainzEntity.exists_by_mbid class method"""

    def test_exists_by_mbid_returns_none_for_nonexistent_mbid(self, mocker):
        """Test that exists_by_mbid returns None when no matching MBID is found"""
        mock_query = mocker.patch("databass.db.base.app_db.session.query")
        mock_query.return_value.filter.return_value.first.return_value = None

        result = Release.exists_by_mbid("non-existent-mbid")
        assert result is None
        mock_query.assert_called_once_with(Release)

    def test_exists_by_mbid_returns_entity_when_found(self, mocker):
        """Test that exists_by_mbid returns the entity when a matching MBID is found"""
        mock_entity = mocker.Mock()
        mock_query = mocker.patch("databass.db.base.app_db.session.query")
        mock_query.return_value.filter.return_value.first.return_value = (
            mock_entity
        )

        result = Release.exists_by_mbid("valid-mbid")
        assert result == mock_entity
        mock_query.assert_called_once_with(Release)

    @pytest.mark.parametrize("invalid_mbid", [None, "", 123, [], {}, True])
    def test_exists_by_mbid_with_invalid_mbid_types(self, invalid_mbid, mocker):
        """Test that exists_by_mbid returns None for invalid MBID types"""
        mock_query = mocker.patch("databass.db.base.app_db.session.query")

        result = Release.exists_by_mbid(invalid_mbid)
        assert result is None
        # Verify query was never called with invalid input
        mock_query.assert_not_called()

    def test_exists_by_mbid_query_construction(self, mocker):
        """Test that exists_by_mbid constructs the correct query"""
        mock_query = mocker.patch("databass.db.base.app_db.session.query")
        mock_filter = mocker.Mock()
        mock_query.return_value.filter = mock_filter
        mock_filter.return_value.first.return_value = None

        Release.exists_by_mbid("test-mbid")

        # Verify the query chain
        mock_query.assert_called_once_with(Release)
        mock_filter.assert_called_once()

    def test_exists_by_mbid_with_whitespace_mbid(self, mocker):
        """Test that exists_by_mbid handles MBIDs with whitespace correctly"""
        mock_entity = mocker.Mock()
        mock_query = mocker.patch("databass.db.base.app_db.session.query")
        mock_query.return_value.filter.return_value.first.return_value = (
            mock_entity
        )

        result = Release.exists_by_mbid("  valid-mbid  ")
        assert result == mock_entity
        mock_query.assert_called_once_with(Release)


class TestMusicBrainzEntityExistsByName:
    """Test suite for MusicBrainzEntity.exists_by_name class method"""

    def test_exists_by_name_returns_none_for_nonexistent_name(self, mocker):
        """Test that exists_by_name returns None when no matching name is found"""
        mock_query = mocker.patch("databass.db.base.app_db.session.query")
        mock_query.return_value.filter.return_value.one_or_none.return_value = None

        result = Release.exists_by_name("non-existent-name")
        assert result is None
        mock_query.assert_called_once_with(Release)

    def test_exists_by_name_returns_entity_when_found(self, mocker):
        """Test that exists_by_name returns the entity when a matching name is found"""
        mock_entity = mocker.Mock()
        mock_query = mocker.patch("databass.db.base.app_db.session.query")
        mock_query.return_value.filter.return_value.one_or_none.return_value = (
            mock_entity
        )

        result = Release.exists_by_name("Test Release")
        assert result == mock_entity
        mock_query.assert_called_once_with(Release)

    @pytest.mark.parametrize("invalid_name", [None, "", 123, [], {}, True])
    def test_exists_by_name_with_invalid_name_types(self, invalid_name, mocker):
        """Test that exists_by_name returns None for invalid name types"""
        mock_query = mocker.patch("databass.db.base.app_db.session.query")

        result = Release.exists_by_name(invalid_name)
        assert result is None
        # Verify query was never called with invalid input
        mock_query.assert_not_called()

    def test_exists_by_name_query_construction(self, mocker):
        """Test that exists_by_name constructs the correct query with case-insensitive search"""
        mock_query = mocker.patch("databass.db.base.app_db.session.query")
        mock_filter = mocker.Mock()
        mock_query.return_value.filter = mock_filter
        mock_filter.return_value.one_or_none.return_value = None

        test_name = "Test Name"
        Release.exists_by_name(test_name)

        # Verify the query chain
        mock_query.assert_called_once_with(Release)
        # Verify case-insensitive LIKE is used in the query
        mock_filter.assert_called_once()
        filter_arg = mock_filter.call_args[0][0]
        assert "lower(release.name) like lower" in str(filter_arg).lower()

    def test_exists_by_name_with_whitespace_name(self, mocker):
        """Test that exists_by_name handles names with whitespace correctly"""
        mock_entity = mocker.Mock()
        mock_query = mocker.patch("databass.db.base.app_db.session.query")
        mock_query.return_value.filter.return_value.one_or_none.return_value = (
            mock_entity
        )

        result = Release.exists_by_name("  Test Name  ")
        assert result == mock_entity
        mock_query.assert_called_once_with(Release)


class TestReleaseAverageRuntime:
    """Test suite for Release.average_runtime class method"""

    def test_average_runtime_returns_float(self, mocker):
        """Test that average_runtime returns a float value"""
        mock_query = mocker.patch("databass.db.base.app_db.session.query")
        mock_query.return_value.scalar.return_value = (
            180000  # 3 minutes in milliseconds
        )

        result = Release.average_runtime()
        assert isinstance(result, float)

    @pytest.mark.parametrize(
        "runtime_ms,expected_minutes",
        [
            (180000, 3.00),  # 3 minutes
            (300000, 5.00),  # 5 minutes
            (150000, 2.50),  # 2.5 minutes
            (90000, 1.50),  # 1.5 minutes
            (0, 0.00),  # 0 minutes
        ],
    )
    def test_average_runtime_correct_conversion(
        self, mocker, runtime_ms, expected_minutes
    ):
        """Test that average_runtime correctly converts milliseconds to minutes"""
        mock_query = mocker.patch("databass.db.base.app_db.session.query")
        mock_query.return_value.scalar.return_value = runtime_ms

        result = Release.average_runtime()
        assert result == expected_minutes

    def test_average_runtime_empty_database(self, mocker):
        """Test that average_runtime returns 0 when database is empty"""
        mock_query = mocker.patch("databass.db.base.app_db.session.query")
        mock_query.return_value.scalar.return_value = None

        result = Release.average_runtime()
        assert result == 0

    def test_average_runtime_rounds_to_two_decimals(self, mocker):
        """Test that average_runtime rounds to 2 decimal places"""
        mock_query = mocker.patch("databass.db.base.app_db.session.query")
        mock_query.return_value.scalar.return_value = 123456  # 2.0576 minutes

        result = Release.average_runtime()
        assert str(result).split(".")[-1] <= "99"
        assert len(str(result).split(".")[-1]) <= 2

    def test_average_runtime_database_error(self, mocker):
        """Test that average_runtime raises exceptions for database errors"""
        mock_query = mocker.patch("databass.db.base.app_db.session.query")
        mock_query.return_value.scalar.side_effect = Exception("Database error")

        result = Release.average_runtime()
        assert result == 0


class TestReleaseTotalRuntime:
    """Test suite for Release.total_runtime class method"""

    def test_total_runtime_returns_float(self, mocker):
        """Test that total_runtime returns a float value"""
        mock_query = mocker.patch("databass.db.base.app_db.session.query")
        mock_query.return_value.scalar.return_value = 3600000  # 1 hour in milliseconds

        result = Release.total_runtime()
        assert isinstance(result, float)

    @pytest.mark.parametrize(
        "runtime_ms,expected_hours",
        [
            (3600000, 1.00),  # 1 hour
            (7200000, 2.00),  # 2 hours
            (5400000, 1.50),  # 1.5 hours
            (1800000, 0.50),  # 0.5 hours
            (0, 0.00),  # 0 hours
        ],
    )
    def test_total_runtime_correct_conversion(self, mocker, runtime_ms, expected_hours):
        """Test that total_runtime correctly converts milliseconds to hours"""
        mock_query = mocker.patch("databass.db.base.app_db.session.query")
        mock_query.return_value.scalar.return_value = runtime_ms

        result = Release.total_runtime()
        assert result == expected_hours

    def test_total_runtime_empty_database(self, mocker):
        """Test that total_runtime returns 0 when database is empty"""
        mock_query = mocker.patch("databass.db.base.app_db.session.query")
        mock_query.return_value.scalar.return_value = None

        result = Release.total_runtime()
        assert result == 0

    def test_total_runtime_rounds_to_two_decimals(self, mocker):
        """Test that total_runtime rounds to 2 decimal places"""
        mock_query = mocker.patch("databass.db.base.app_db.session.query")
        mock_query.return_value.scalar.return_value = 4444444  # 1.2345... hours

        result = Release.total_runtime()
        assert str(result).split(".")[-1] <= "99"
        assert len(str(result).split(".")[-1]) <= 2

    def test_total_runtime_handles_type_error(self, mocker):
        """Test that total_runtime handles TypeError gracefully by returning 0"""
        mock_query = mocker.patch("databass.db.base.app_db.session.query")
        mock_query.return_value.scalar.side_effect = TypeError("Invalid type")

        result = Release.total_runtime()
        assert result == 0


class TestReleaseRatingsLowest:
    """Test suite for Release.ratings_lowest class method"""

    def test_ratings_lowest_returns_list(self, mocker):
        """Test that ratings_lowest returns a list regardless of whether entries exist"""
        mock_query = mocker.patch("databass.db.base.app_db.session.query")
        mock_query.return_value.limit.return_value.order_by.return_value.all.return_value = []

        result = Release.ratings_lowest()
        assert isinstance(result, list)

    @pytest.mark.parametrize(
        "limit,expected_count", [(1, 1), (5, 5), (10, 10), (100, 100)]
    )
    def test_ratings_lowest_respects_limit(self, mocker, limit, expected_count):
        """Test that ratings_lowest returns the correct number of entries based on limit parameter"""
        mock_entries = [mocker.Mock() for _ in range(expected_count)]
        mock_query = mocker.patch("databass.db.base.app_db.session.query")
        mock_query.return_value.limit.return_value.order_by.return_value.all.return_value = mock_entries

        result = Release.ratings_lowest(limit=limit)
        assert len(result) == expected_count
        mock_query.return_value.limit.assert_called_once_with(limit)

    def test_ratings_lowest_orders_ascending(self, mocker):
        """Test that ratings_lowest orders results by rating in ascending order"""
        mock_query = mocker.patch("databass.db.base.app_db.session.query")
        mock_order = mocker.Mock()
        mock_query.return_value.limit.return_value.order_by = mock_order

        Release.ratings_lowest()
        mock_order.assert_called_once()
        order_arg = mock_order.call_args[0][0]
        assert "rating" in str(order_arg)
        assert "ASC" in str(order_arg)

    @pytest.mark.parametrize("invalid_limit", [0, -1, -100, "string", [], {}, None])
    def test_ratings_lowest_invalid_limit(self, invalid_limit):
        """Test that ratings_lowest raises ValueError for invalid limit values"""
        with pytest.raises(ValueError, match="Limit must be a positive integer"):
            Release.ratings_lowest(limit=invalid_limit)

    def test_ratings_lowest_queries_correct_columns(self, mocker):
        """Test that ratings_lowest queries the expected columns"""
        mock_query = mocker.patch("databass.db.base.app_db.session.query")
        mock_query.return_value.limit.return_value.order_by.return_value.all.return_value = []

        Release.ratings_lowest()

        # Verify the correct columns are being queried
        query_args = mock_query.call_args[0]
        expected_columns = ["id", "name", "rating", "artist_id", "label_id"]
        for column in expected_columns:
            assert any(column in str(arg) for arg in query_args)


class TestReleaseRatingsHighest:
    """Test suite for Release.ratings_highest class method"""

    def test_ratings_highest_returns_list(self, mocker):
        """Test that ratings_highest returns a list regardless of whether entries exist"""
        mock_query = mocker.patch("databass.db.base.app_db.session.query")
        mock_query.return_value.limit.return_value.order_by.return_value.all.return_value = []

        result = Release.ratings_highest()
        assert isinstance(result, list)

    @pytest.mark.parametrize(
        "limit,expected_count", [(1, 1), (5, 5), (10, 10), (100, 100)]
    )
    def test_ratings_highest_respects_limit(self, mocker, limit, expected_count):
        """Test that ratings_highest returns the correct number of entries based on limit parameter"""
        mock_entries = [mocker.Mock() for _ in range(expected_count)]
        mock_query = mocker.patch("databass.db.base.app_db.session.query")
        mock_query.return_value.limit.return_value.order_by.return_value.all.return_value = mock_entries

        result = Release.ratings_highest(limit=limit)
        assert len(result) == expected_count
        mock_query.return_value.limit.assert_called_once_with(limit)

    def test_ratings_highest_orders_descending(self, mocker):
        """Test that ratings_highest orders results by rating in descending order"""
        mock_query = mocker.patch("databass.db.base.app_db.session.query")
        mock_order = mocker.Mock()
        mock_query.return_value.limit.return_value.order_by = mock_order

        Release.ratings_highest()
        mock_order.assert_called_once()
        order_arg = mock_order.call_args[0][0]
        assert "rating" in str(order_arg)
        assert "DESC" in str(order_arg)

    @pytest.mark.parametrize("invalid_limit", [0, -1, -100, "string", [], {}, None])
    def test_ratings_highest_invalid_limit(self, invalid_limit):
        """Test that ratings_highest raises ValueError for invalid limit values"""
        with pytest.raises(ValueError, match="Limit must be a positive integer"):
            Release.ratings_highest(limit=invalid_limit)

    def test_ratings_highest_queries_correct_columns(self, mocker):
        """Test that ratings_highest queries the expected columns"""
        mock_query = mocker.patch("databass.db.base.app_db.session.query")
        mock_query.return_value.limit.return_value.order_by.return_value.all.return_value = []

        Release.ratings_highest()

        # Verify the correct columns are being queried
        query_args = mock_query.call_args[0]
        expected_columns = ["id", "name", "rating", "artist_id", "label_id"]
        for column in expected_columns:
            assert any(column in str(arg) for arg in query_args)


class TestReleaseRatingsAverage:
    """Test suite for Release.ratings_average class method"""

    def test_ratings_average_returns_float(self, mocker):
        """Test that ratings_average returns a float value"""
        mock_query = mocker.patch("databass.db.base.app_db.session.query")
        mock_query.return_value.scalar.return_value = 4.5

        result = Release.ratings_average()
        assert isinstance(result, float)

    @pytest.mark.parametrize(
        "ratings,expected",
        [
            (4.567, 4.57),  # Test rounding up
            (3.234, 3.23),  # Test rounding down
            (5.0, 5.00),  # Test whole number
            (0.0, 0.00),  # Test zero
            (None, 0.00),  # Test None value
        ],
    )
    def test_ratings_average_correct_rounding(self, mocker, ratings, expected):
        """Test that ratings_average correctly rounds to 2 decimal places"""
        mock_query = mocker.patch("databass.db.base.app_db.session.query")
        mock_query.return_value.scalar.return_value = ratings

        result = Release.ratings_average()
        assert result == expected

    def test_ratings_average_empty_database(self, mocker):
        """Test that ratings_average returns 0.0 when database is empty"""
        mock_query = mocker.patch("databass.db.base.app_db.session.query")
        mock_query.return_value.scalar.return_value = None

        result = Release.ratings_average()
        assert result == 0.0

    def test_ratings_average_handles_database_error(self, mocker):
        """Test that ratings_average returns 0.0 when database error occurs"""
        mock_query = mocker.patch("databass.db.base.app_db.session.query")
        mock_query.return_value.scalar.side_effect = Exception("Database error")

        result = Release.ratings_average()
        assert result == 0.0

    def test_ratings_average_queries_correct_function(self, mocker):
        """Test that ratings_average uses the correct SQL AVG function"""
        mock_query = mocker.patch("databass.db.base.app_db.session.query")
        mock_query.return_value.scalar.return_value = 4.0

        Release.ratings_average()

        # Verify AVG function is called on the rating column
        query_args = mock_query.call_args[0]
        assert "avg" in str(query_args[0]).lower()
        assert "rating" in str(query_args[0]).lower()


class TestReleaseHomeData:
    """Test suite for Release.home_data class method"""

    def test_home_data_returns_list(self, mocker):
        """Test that home_data returns a list regardless of whether entries exist"""
        mock_query = mocker.patch("databass.db.base.app_db.session.query")
        mock_order_by = mock_query.return_value.order_by
        mock_order_by.return_value.all.return_value = []

        result = Release.home_data()
        assert isinstance(result, list)

    def test_home_data_orders_by_id_desc(self, mocker):
        """Test that home_data orders results by release ID in descending order"""
        mock_query = mocker.patch("databass.db.base.app_db.session.query")
        mock_order_by = mock_query.return_value.order_by
        mock_order_by.return_value.all.return_value = []

        Release.home_data()

        mock_query.assert_called_once_with(Release)
        mock_order_by.assert_called_once()


class TestReleaseHomeDataLight:
    """Test suite for Release.home_data_light class method"""

    def test_home_data_light_returns_list(self, mocker):
        """Test that home_data_light returns a list regardless of whether entries exist"""
        mock_query = mocker.patch("databass.db.base.app_db.session.query")
        mock_order_by = mock_query.return_value.order_by
        mock_order_by.return_value.all.return_value = []

        result = Release.home_data_light()
        assert isinstance(result, list)

    def test_home_data_light_orders_by_listen_date_desc(self, mocker):
        """Test that home_data_light orders results by listen date descending"""
        mock_query = mocker.patch("databass.db.base.app_db.session.query")
        mock_order_by = mock_query.return_value.order_by
        mock_order_by.return_value.all.return_value = []

        Release.home_data_light()

        mock_order_by.assert_called_once()

    def test_home_data_light_only_queries_lightweight_columns(self, mocker):
        """Test that home_data_light doesn't select whole Release objects"""
        mock_query = mocker.patch("databass.db.base.app_db.session.query")
        mock_query.return_value.order_by.return_value.all.return_value = []

        Release.home_data_light()

        query_args = mock_query.call_args[0]
        assert len(query_args) == 3
        assert all(arg is not Release for arg in query_args)

    def test_home_data_light_returns_empty_on_exception(self, mocker):
        """Test that home_data_light returns an empty list on error"""
        mock_query = mocker.patch("databass.db.base.app_db.session.query")
        mock_query.side_effect = Exception("Database error")

        result = Release.home_data_light()
        assert result == []


class TestReleaseByIds:
    """Test suite for Release.by_ids class method"""

    def test_by_ids_empty_list_returns_empty(self, mocker):
        """Test that by_ids returns an empty list without querying when given no IDs"""
        mock_query = mocker.patch("databass.db.base.app_db.session.query")

        result = Release.by_ids([])
        assert result == []
        mock_query.assert_not_called()

    def test_by_ids_filters_by_id(self, mocker):
        """Test that by_ids filters the query by the given IDs"""
        mock_query = mocker.patch("databass.db.base.app_db.session.query")
        chain = mock_query.return_value
        chain.filter.return_value = chain
        chain.options.return_value = chain
        chain.all.return_value = []

        Release.by_ids([1, 2, 3])

        mock_query.assert_called_once_with(Release)
        chain.filter.assert_called_once()


class TestReleaseListensThisYear:
    """Test suite for Release.listens_this_year class method"""

    def test_listens_this_year_returns_integer(self, mocker):
        """Test that listens_this_year returns an integer value"""
        mock_query = mocker.patch("databass.db.base.app_db.session.query")
        mock_query.return_value.filter.return_value.scalar.return_value = 5

        result = Release.listens_this_year()
        assert isinstance(result, int)

    @pytest.mark.parametrize(
        "count_value",
        [
            0,  # No listens
            1,  # Single listen
            50,  # Multiple listens
            100,  # Large number of listens
        ],
    )
    def test_listens_this_year_returns_correct_count(self, mocker, count_value):
        """Test that listens_this_year returns the correct count from the database"""
        mock_query = mocker.patch("databass.db.base.app_db.session.query")
        mock_query.return_value.filter.return_value.scalar.return_value = count_value

        result = Release.listens_this_year()
        assert result == count_value

    def test_listens_this_year_handles_database_error(self, mocker):
        """Test that listens_this_year returns 0 when a database error occurs"""
        mock_query = mocker.patch("databass.db.base.app_db.session.query")
        mock_query.return_value.filter.return_value.scalar.side_effect = Exception(
            "Database error"
        )

        result = Release.listens_this_year()
        assert result == 0

    def test_listens_this_year_uses_correct_columns(self, mocker):
        """Test that listens_this_year queries the correct database columns"""
        mock_query = mocker.patch("databass.db.base.app_db.session.query")
        mock_query.return_value.filter.return_value.scalar.return_value = 0

        Release.listens_this_year()

        # Verify count and listen_date columns are used
        query_args = mock_query.call_args[0]
        assert "count" in str(query_args[0]).lower()
        assert "release.id" in str(query_args[0]).lower()


class TestReleaseAddedPerDayThisYear:
    """Test suite for Release.listens_per_day class method"""

    # TODO: move this to tests for Base class

    def test_added_per_day_this_year_returns_float(self, mocker):
        """Test that added_per_day_this_year returns a float value"""
        mock_listens = mocker.patch("databass.db.models.Release.listens_this_year")
        mock_listens.return_value = 10

        result = Release.added_per_day_this_year()
        assert isinstance(result, float)

    @pytest.mark.parametrize(
        "listens,days,expected",
        [
            (365, 365, 1.00),  # One listen per day
            (0, 100, 0.00),  # No listens
            (50, 25, 2.00),  # Multiple listens per day
            (10, 100, 0.10),  # Less than one listen per day
            (1, 1, 1.00),  # Single day, single listen
        ],
    )
    def test_added_per_day_this_year_calculation(self, mocker, listens, days, expected):
        """Test that added_per_day_this_year correctly calculates average listens"""
        mock_listens = mocker.patch("databass.db.models.Release.added_this_year")
        mock_listens.return_value = listens

        mock_date = mocker.patch("databass.db.models.base.date")
        mock_date.today.return_value.timetuple.return_value.tm_yday = days

        result = Release.added_per_day_this_year()
        assert result == expected

    def test_added_per_day_this_year_handles_zero_days(self, mocker):
        """Test that added_per_day_this_year returns 0.0 when days_this_year is 0"""
        mock_listens = mocker.patch("databass.db.models.Release.added_this_year")
        mock_date = mocker.patch("databass.db.models.base.date")
        mock_date.today.return_value.timetuple.return_value.tm_yday = 0

        result = Release.added_per_day_this_year()
        assert result == 0.0
        # Verify added_this_year was never called
        mock_listens.assert_not_called()

    def test_added_per_day_this_year_rounds_to_two_decimals(self, mocker):
        """Test that added_per_day_this_year rounds to 2 decimal places"""
        mock_listens = mocker.patch("databass.db.models.Release.added_this_year")
        mock_listens.return_value = 100

        mock_date = mocker.patch("databass.db.models.base.date")
        mock_date.today.return_value.timetuple.return_value.tm_yday = 33
        # Should result in 3.0303... before rounding

        result = Release.added_per_day_this_year()
        assert str(result).split(".")[-1] <= "99"
        assert len(str(result).split(".")[-1]) <= 2

    def test_added_per_day_this_year_uses_correct_year_day(self, mocker):
        """Test that added_per_day_this_year uses the correct day of year"""
        mock_listens = mocker.patch("databass.db.models.Release.added_this_year")
        mock_date = mocker.patch("databass.db.models.base.date")
        mock_timetuple = mocker.Mock()
        mock_timetuple.tm_yday = 100

        mock_date.today.return_value.timetuple.return_value = mock_timetuple
        mock_listens.return_value = 200

        Release.added_per_day_this_year()
        mock_date.today.assert_called_once()
        mock_date.today.return_value.timetuple.assert_called_once()


class TestReleaseDynamicSearch:
    """Test suite for Release.dynamic_search class method"""

    def test_dynamic_search_returns_list(self, mocker):
        """Test that dynamic_search returns a list regardless of search criteria"""
        mock_query = mocker.patch("databass.db.base.app_db.session.query")
        mock_query.return_value.order_by.return_value.all.return_value = []

        result = Release.dynamic_search({})
        assert isinstance(result, list)

    def test_dynamic_search_invalid_input(self):
        """Test that dynamic_search raises ValueError for non-dict input"""
        with pytest.raises(ValueError, match="Search criteria must be a dictionary"):
            Release.dynamic_search("invalid input")

    def test_dynamic_search_empty_values(self, mocker):
        """Test that dynamic_search properly handles empty values in search criteria"""
        mock_query = mocker.MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = []

        mocker.patch("databass.db.base.app_db.session.query", return_value=mock_query)

        result = Release.dynamic_search({"name": "", "genre": "NO VALUE"})
        assert isinstance(result, list)
        assert len(result) == 0

    def test_dynamic_search_label_filter(self, mocker):
        """Test that dynamic_search correctly handles label filtering"""
        mock_query = mocker.patch("databass.db.base.app_db.session.query")
        mock_label = mocker.Mock()
        mock_label.id = 1
        mock_exists = mocker.patch("databass.db.models.Label.id_by_matching_name")
        mock_exists.return_value = [mock_label]

        Release.dynamic_search({"label": "Test Label"})

        mock_exists.assert_called_once_with(name="Test Label")
        mock_query.return_value.filter.assert_called()

    def test_dynamic_search_artist_filter(self, mocker):
        """Test that dynamic_search correctly handles artist filtering"""
        mock_query = mocker.patch("databass.db.base.app_db.session.query")
        mock_artist = mocker.Mock()
        mock_artist.id = 1
        mock_exists = mocker.patch("databass.db.models.Artist.id_by_matching_name")
        mock_exists.return_value = [mock_artist]

        Release.dynamic_search({"artist": "Test Artist"})

        mock_exists.assert_called_once_with(name="Test Artist")
        mock_query.return_value.filter.assert_called()

    def test_dynamic_search_comparison_filters(self, mocker):
        """Test that dynamic_search correctly handles comparison filters"""
        mocker.patch("databass.db.base.app_db.session.query")
        mock_apply = mocker.patch("databass.db.models.catalog.apply_comparison_filter")

        Release.dynamic_search(
            {
                "rating": "5",
                "rating_comparison": ">",
                "year": "2023",
                "year_comparison": "=",
            }
        )

        assert mock_apply.call_count == 2

    def test_dynamic_search_genres_filter(self, mocker):
        """Test that dynamic_search correctly handles genre filtering"""
        mock_query = mocker.patch("databass.db.base.app_db.session.query")
        mock_query_instance = mock_query.return_value
        mock_filter = mock_query_instance.filter
        mock_filter.return_value = mock_query_instance

        mock_genre_lookup = mocker.patch("databass.db.models.Genre.exists_by_name")
        mock_genre_lookup.return_value = "rock"

        Release.dynamic_search({"main_genre": "rock"})

        mock_filter.assert_called_once()

        mock_query_instance.order_by.return_value.all.assert_called_once()


class TestReleaseGetReviews:
    """Test suite for Release.get_reviews class method"""

    def test_get_reviews_returns_list(self, mocker):
        """Test that get_reviews returns a list regardless of whether reviews exist"""
        mock_query = mocker.patch("databass.db.base.app_db.session.query")
        mock_query.return_value.where.return_value.all.return_value = []

        result = Release.get_reviews(1)
        assert isinstance(result, list)

    def test_get_reviews_queries_correct_columns(self, mocker):
        """Test that get_reviews queries the expected columns"""
        mock_query = mocker.patch("databass.db.base.app_db.session.query")
        mock_query.return_value.where.return_value.all.return_value = []

        Release.get_reviews(1)

        # Verify the correct columns are being queried
        query_args = mock_query.call_args[0]
        assert "timestamp" in str(query_args[0])
        assert "text" in str(query_args[1])

    @pytest.mark.parametrize(
        "invalid_id",
        [
            None,
            "string_id",
            -1,
            3.14,
            [],
            {},
        ],
    )
    def test_get_reviews_invalid_release_id(self, invalid_id):
        """Test that get_reviews raises ValueError for invalid release ID types"""
        with pytest.raises(ValueError, match="Release ID must be a positive integer"):
            Release.get_reviews(invalid_id)

    def test_get_reviews_returns_correct_data(self, mocker):
        """Test that get_reviews returns the correct review data structure"""
        mock_review = mocker.Mock()
        mock_review.timestamp = "2024-01-01 12:00"
        mock_review.text = "Test review text"

        mock_query = mocker.patch("databass.db.base.app_db.session.query")
        mock_query.return_value.where.return_value.all.return_value = [mock_review]

        result = Release.get_reviews(1)
        assert len(result) == 1
        assert result[0].timestamp == mock_review.timestamp
        assert result[0].text == mock_review.text

    def test_get_reviews_filters_by_release_id(self, mocker):
        """Test that get_reviews filters reviews by the correct release ID"""
        mock_query = mocker.patch("databass.db.base.app_db.session.query")
        mock_where = mocker.Mock()
        mock_query.return_value.where = mock_where
        mock_where.return_value.all.return_value = []

        test_id = 42
        Release.get_reviews(test_id)

        mock_where.assert_called_once()
        where_arg = mock_where.call_args[0][0]
        assert "review.release_id" in str(where_arg)

    def test_get_reviews_empty_results(self, mocker):
        """Test that get_reviews handles releases with no reviews"""
        mock_query = mocker.patch("databass.db.base.app_db.session.query")
        mock_query.return_value.where.return_value.all.return_value = []

        result = Release.get_reviews(1)
        assert result == []


class TestReleaseCreateNew:
    """Test suite for Release.create_new static method"""

    def test_create_new_returns_integer(self, mocker):
        """Test that create_new returns an integer ID"""
        mock_insert = mocker.patch("databass.db.models.catalog.insert")
        mock_get_image = mocker.patch("databass.api.image.fetch_image")

        mock_insert.return_value = 42
        mock_get_image.return_value = "path/to/image.jpg"

        test_data = {
            "name": "Test Release",
            "artist_name": "Test Artist",
            "label_name": "Test Label",
            "release_group_mbid": "test-mbid",
            "image": None,
        }

        result = Release.create_new(test_data)
        assert isinstance(result, int)
        assert result == 42

    @pytest.mark.parametrize("invalid_data", [None, "string", 123, [], set(), True])
    def test_create_new_invalid_data_type(self, invalid_data):
        """Test that create_new raises ValueError for non-dict input"""
        with pytest.raises(ValueError, match="data argument must be a dictionary"):
            Release.create_new(invalid_data)

    def test_create_new_constructs_release_correctly(self, mocker):
        """Test that create_new constructs a Release with the given data before inserting"""
        mock_insert = mocker.patch("databass.db.models.catalog.insert")
        mocker.patch("databass.api.image.fetch_image", return_value=None)

        test_data = {
            "name": "Test Release",
            "artist_name": "Test Artist",
            "label_name": "Test Label",
            "release_group_mbid": "test-mbid",
            "image": None,
        }

        Release.create_new(test_data)

        inserted_release = mock_insert.call_args[0][0]
        assert isinstance(inserted_release, Release)
        for key, value in test_data.items():
            assert getattr(inserted_release, key) == value

    def test_create_new_missing_optional_fields(self, mocker):
        """Test that create_new doesn't raise when optional fields are absent"""
        mock_insert = mocker.patch("databass.db.models.catalog.insert")
        mock_get_image = mocker.patch("databass.api.image.fetch_image")
        mock_insert.return_value = 1

        test_data = {"name": "Test Release"}

        result = Release.create_new(test_data)
        assert result == 1
        mock_get_image.assert_not_called()

    def test_create_new_with_chosen_image_url(self, mocker):
        """Chosen art arrives as a URL: download it and never persist the raw URL."""
        mock_insert = mocker.patch("databass.db.models.catalog.insert", return_value=7)
        mock_update = mocker.patch("databass.db.models.catalog.update")
        mock_get_image_url = mocker.patch(
            "databass.api.Util.get_image_from_url",
            return_value="./static/img/release/art.png",
        )
        mock_fetch_image = mocker.patch("databass.api.image.fetch_image")

        test_data = {
            "name": "Test Release",
            "artist_name": "Test Artist",
            "label_name": "Test Label",
            "release_group_mbid": "rg-1",
            "image": "https://coverartarchive.org/release/rel-1/front",
        }

        result = Release.create_new(test_data)

        assert result == 7
        mock_get_image_url.assert_called_once_with(
            entity_type="release",
            url="https://coverartarchive.org/release/rel-1/front",
        )
        mock_fetch_image.assert_not_called()
        inserted_release = mock_insert.call_args[0][0]
        # the persisted value is the downloaded file path, never the raw URL
        assert inserted_release.image == "./static/img/release/art.png"
        mock_update.assert_called_once()
        assert mock_update.call_args[0][0].image == "./static/img/release/art.png"

    def test_create_new_chosen_image_failure_falls_back_to_auto_fetch(self, mocker):
        """If the chosen image can't be downloaded, fall back to the auto lookup."""
        mocker.patch("databass.db.models.catalog.insert", return_value=7)
        mocker.patch(
            "databass.api.Util.get_image_from_url", side_effect=Exception("boom")
        )
        mock_fetch_image = mocker.patch(
            "databass.api.image.fetch_image",
            return_value="./static/img/release/auto.jpg",
        )
        mock_update = mocker.patch("databass.db.models.catalog.update")

        test_data = {
            "name": "Test Release",
            "artist_name": "Test Artist",
            "label_name": "Test Label",
            "release_group_mbid": "rg-1",
            "image": "https://coverartarchive.org/release/rel-1/front",
        }

        result = Release.create_new(test_data)

        assert result == 7
        mock_fetch_image.assert_called_once()
        assert mock_update.call_args[0][0].image == "./static/img/release/auto.jpg"


class TestArtistOrLabelFrequencyHighest:
    """Test suite for ArtistOrLabel.frequency_highest class method"""

    def test_frequency_highest_returns_list(self, mocker):
        """Test that frequency_highest returns a list regardless of whether entries exist"""
        mock_query = mocker.patch("databass.db.base.app_db.session.query")
        mock_query.return_value.join.return_value.where.return_value.group_by.return_value.order_by.return_value.limit.return_value.all.return_value = []

        result = Artist.frequency_highest()
        assert isinstance(result, list)

    @pytest.mark.parametrize(
        "limit,expected_count", [(1, 1), (5, 5), (10, 10), (100, 100)]
    )
    def test_frequency_highest_respects_limit(self, mocker, limit, expected_count):
        """Test that frequency_highest returns the correct number of entries based on limit parameter"""
        mock_entries = [mocker.Mock() for _ in range(expected_count)]
        mock_query = mocker.patch("databass.db.base.app_db.session.query")
        mock_query.return_value.join.return_value.where.return_value.group_by.return_value.order_by.return_value.limit.return_value.all.return_value = mock_entries

        result = Artist.frequency_highest(limit=limit)
        assert len(result) == expected_count

    def test_frequency_highest_orders_by_count_desc(self, mocker):
        """Test that frequency_highest orders results by count in descending order"""
        mock_query = mocker.patch("databass.db.base.app_db.session.query")
        mock_order = mocker.Mock()
        mock_query.return_value.join.return_value.where.return_value.group_by.return_value.order_by = mock_order
        mock_order.return_value.limit.return_value.all.return_value = []

        Artist.frequency_highest()

        order_arg = mock_order.call_args[0][0]
        assert "DESC" in str(order_arg)

    def test_frequency_highest_returns_correct_structure(self, mocker):
        """Test that frequency_highest returns dictionaries with the expected keys"""
        mock_result = mocker.Mock()
        mock_result.name = "Test Artist"
        mock_result.count = 5
        mock_result.image = "test.jpg"

        mock_query = mocker.patch("databass.db.base.app_db.session.query")
        mock_query.return_value.join.return_value.where.return_value.group_by.return_value.order_by.return_value.limit.return_value.all.return_value = [
            mock_result
        ]

        result = Artist.frequency_highest()
        assert len(result) == 1
        assert all(key in result[0] for key in ["name", "count", "image"])
        assert result[0]["name"] == "Test Artist"
        assert result[0]["count"] == 5
        assert result[0]["image"] == "test.jpg"

    @pytest.mark.parametrize("invalid_limit", [0, -1, -100, "string", [], {}, None])
    def test_frequency_highest_invalid_limit(self, invalid_limit):
        """Test that frequency_highest raises ValueError for invalid limit values"""
        with pytest.raises(ValueError, match="Limit must be a positive integer"):
            Artist.frequency_highest(limit=invalid_limit)

    def test_frequency_highest_joins_correct_tables(self, mocker):
        """Test that frequency_highest performs the correct table joins"""
        mock_query = mocker.patch("databass.db.base.app_db.session.query")
        mock_join = mocker.Mock()
        mock_query.return_value.join = mock_join
        mock_join.return_value.where.return_value.group_by.return_value.order_by.return_value.limit.return_value.all.return_value = []

        Artist.frequency_highest()

        join_args = mock_join.call_args[0]
        assert "Release" in str(join_args)


class TestArtistOrLabelAverageRatingsAndTotalCounts:
    """Test suite for ArtistOrLabel.average_ratings_and_total_counts class method"""

    def test_average_ratings_and_total_counts_returns_list(self, mocker):
        """Test that average_ratings_and_total_counts returns a list regardless of whether entries exist"""
        mock_query = mocker.MagicMock()
        mock_query.join.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.having.return_value = mock_query
        mock_query.group_by.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = []

        mocker.patch("databass.db.base.app_db.session.query", return_value=mock_query)

        result = Artist.average_ratings_and_total_counts()
        assert isinstance(result, list)

    def test_average_ratings_and_total_counts_queries_correct_columns(self, mocker):
        """Test that average_ratings_and_total_counts queries the expected columns"""
        mock_query = mocker.patch("databass.db.base.app_db.session.query")
        mock_query.return_value.join.return_value.where.return_value.having.return_value.group_by.return_value.all.return_value = []

        Artist.average_ratings_and_total_counts()

        # Verify the correct columns are being queried
        query_args = mock_query.call_args[0]
        expected_columns = ["id", "name", "avg", "count", "image"]
        for column in expected_columns:
            assert any(column in str(arg).lower() for arg in query_args)

    def test_average_ratings_and_total_counts_joins_release_table(self, mocker):
        """Test that average_ratings_and_total_counts performs the correct table join with Release"""
        mock_query = mocker.patch("databass.db.base.app_db.session.query")
        mock_join = mocker.Mock()
        mock_query.return_value.join = mock_join
        mock_join.return_value.where.return_value.having.return_value.group_by.return_value.all.return_value = []

        Artist.average_ratings_and_total_counts()

        # Verify join with Release table
        mock_join.assert_called_once()
        join_args = mock_join.call_args[0]
        assert "Release" in str(join_args)

    @pytest.mark.parametrize("model_class", [Artist, Label])
    def test_average_ratings_and_total_counts_works_for_both_models(
        self, mocker, model_class
    ):
        """Test that average_ratings_and_total_counts works for both Artist and Label classes"""
        mock_query = mocker.MagicMock()
        mock_query.join.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.having.return_value = mock_query
        mock_query.group_by.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = []
        mocker.patch("databass.db.base.app_db.session.query", return_value=mock_query)

        result = model_class.average_ratings_and_total_counts()
        assert isinstance(result, list)

    def test_average_ratings_and_total_counts_invalid_class(self):
        """Test that average_ratings_and_total_counts raises TypeError when called on invalid class"""

        class InvalidClass(ArtistOrLabel):
            __tablename__ = "invalid"

        with pytest.raises(
            TypeError, match="Method only supported by Artist and Label classes"
        ):
            InvalidClass.average_ratings_and_total_counts()

    def test_average_ratings_and_total_counts_filters_by_minimum_releases(self, mocker):
        """Test that average_ratings_and_total_counts filters entities with more than one release"""
        mock_query = mocker.patch("databass.db.base.app_db.session.query")
        mock_having = mocker.Mock()
        mock_query.return_value.join.return_value.where.return_value.having = (
            mock_having
        )
        mock_having.return_value.group_by.return_value.all.return_value = []

        Artist.average_ratings_and_total_counts()

        # Verify HAVING clause requires more than one release
        having_arg = mock_having.call_args[0][0]
        assert "count" in str(having_arg).lower()
        assert "count(release.id)" in str(having_arg)


class TestArtistOrLabelAverageRatingsBayesian:
    """Test suite for ArtistOrLabel.average_ratings_bayesian class method"""

    def test_average_ratings_bayesian_returns_list(self, mocker):
        """Test that average_ratings_bayesian returns a list regardless of whether entries exist"""
        mock_ratings = mocker.patch(
            "databass.db.models.ArtistOrLabel.average_ratings_and_total_counts"
        )
        mock_ratings.return_value = []

        result = Artist.average_ratings_bayesian()
        assert isinstance(result, list)

    @pytest.mark.parametrize(
        "sort_order,expected_order", [("desc", True), ("asc", False)]
    )
    def test_average_ratings_bayesian_sort_order(
        self, mocker, sort_order, expected_order
    ):
        """Test that average_ratings_bayesian sorts results correctly based on sort_order parameter"""
        mock_entity = mocker.Mock()
        mock_entity.id = 1
        mock_entity.name = "Test Entity"
        mock_entity.average_rating = 4
        mock_entity.release_count = 10
        mock_entity.image = "test.jpg"

        mock_ratings = mocker.patch(
            "databass.db.models.ArtistOrLabel.average_ratings_and_total_counts"
        )
        mock_ratings.return_value = [mock_entity]

        result = Artist.average_ratings_bayesian(sort_order=sort_order)
        assert len(result) > 0
        assert isinstance(result[0], dict)

        # Verify sort order was applied correctly
        if len(result) > 1:
            is_descending = result[0]["rating"] >= result[1]["rating"]
            assert is_descending == expected_order

    def test_average_ratings_bayesian_empty_database(self, mocker):
        """Test that average_ratings_bayesian handles empty database correctly"""
        mock_ratings = mocker.patch(
            "databass.db.models.ArtistOrLabel.average_ratings_and_total_counts"
        )
        mock_ratings.return_value = []

        result = Artist.average_ratings_bayesian()
        assert result == []

    @pytest.mark.parametrize(
        "invalid_sort_order", [None, 123, "invalid", "", "DESCENDING", "ASCENDING"]
    )
    def test_average_ratings_bayesian_invalid_sort_order(self, invalid_sort_order):
        """Test that average_ratings_bayesian raises ValueError for invalid sort orders"""
        with pytest.raises(ValueError, match="Unrecognized sort order"):
            Artist.average_ratings_bayesian(sort_order=invalid_sort_order)

    def test_average_ratings_bayesian_calculation(self, mocker):
        """Test that average_ratings_bayesian calculates Bayesian averages correctly"""
        mock_entity1 = mocker.Mock()
        mock_entity1.id = 1
        mock_entity1.name = "Entity 1"
        mock_entity1.average_rating = 4
        mock_entity1.release_count = 10
        mock_entity1.image = "test1.jpg"

        mock_entity2 = mocker.Mock()
        mock_entity2.id = 2
        mock_entity2.name = "Entity 2"
        mock_entity2.average_rating = 5
        mock_entity2.release_count = 5
        mock_entity2.image = "test2.jpg"

        mock_ratings = mocker.patch(
            "databass.db.models.ArtistOrLabel.average_ratings_and_total_counts"
        )
        mock_ratings.return_value = [mock_entity1, mock_entity2]

        result = Artist.average_ratings_bayesian()
        assert len(result) == 2
        assert all(
            key in result[0] for key in ["id", "name", "rating", "image", "count"]
        )

    def test_average_ratings_bayesian_rounding(self, mocker):
        """Test that average_ratings_bayesian rounds ratings correctly"""
        mock_entity = mocker.Mock()
        mock_entity.id = 1
        mock_entity.name = "Test Entity"
        mock_entity.average_rating = 4.6789
        mock_entity.release_count = 10
        mock_entity.image = "test.jpg"

        mock_ratings = mocker.patch(
            "databass.db.models.ArtistOrLabel.average_ratings_and_total_counts"
        )
        mock_ratings.return_value = [mock_entity]

        result = Artist.average_ratings_bayesian()
        assert isinstance(result[0]["rating"], int)


class TestArtistOrLabelDynamicSearch:
    """Test suite for ArtistOrLabel.dynamic_search class method"""

    def test_dynamic_search_returns_list(self, mocker):
        """Test that dynamic_search returns a list regardless of whether entries exist"""
        mock_query = mocker.patch("databass.db.base.app_db.session.query")
        mock_query.return_value.where.return_value.where.return_value.where.return_value.all.return_value = []

        result = Artist.dynamic_search({})
        assert isinstance(result, list)

    def test_dynamic_search_invalid_input(self):
        """Test that dynamic_search raises ValueError for non-dict input"""
        with pytest.raises(ValueError, match="filters must be a dictionary"):
            Artist.dynamic_search("invalid input")

    @pytest.mark.parametrize(
        "search_data,expected_calls",
        [
            ({"name": "Test Artist"}, ["filter"]),
            ({"country": "US"}, ["filter"]),
            ({"type": "Group"}, ["filter"]),
        ],
    )
    def test_dynamic_search_query_construction(
        self, mocker, search_data, expected_calls
    ):
        """Test that dynamic_search constructs appropriate queries based on search criteria"""
        mock_query = mocker.MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.all.return_value = []

        mocker.patch("databass.db.base.app_db.session.query", return_value=mock_query)
        Artist.dynamic_search(search_data)
        assert mock_query.filter.call_count >= len(expected_calls)

    def test_dynamic_search_empty_values(self, mocker):
        """Test that dynamic_search properly handles empty values in search criteria"""
        mock_query = mocker.MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.all.return_value = []

        mocker.patch("databass.db.base.app_db.session.query", return_value=mock_query)

        result = Artist.dynamic_search({"name": "", "country": "NO VALUE"})
        assert isinstance(result, list)
        assert len(result) == 0

    def test_dynamic_search_name_filter(self, mocker):
        """Test that dynamic_search correctly handles name filtering with case-insensitive partial match"""
        mock_query = mocker.patch("databass.db.base.app_db.session.query")
        mock_filter = mocker.Mock()
        mock_query.return_value.filter = mock_filter
        mock_filter.return_value.where.return_value.where.return_value.where.return_value.all.return_value = []

        Artist.dynamic_search({"name": "Test Artist"})
        mock_filter.assert_called_once()
        filter_arg = mock_filter.call_args[0][0]
        assert "lower(artist.name) like lower" in str(filter_arg).lower()

    def test_dynamic_search_invalid_comparison_operator(self, mocker):
        """Test that dynamic_search raises ValueError for invalid comparison operators"""
        # Mock the database session and query
        mock_session = mocker.patch("databass.db.base.app_db.session")
        mock_query = mocker.Mock()
        mock_session.query.return_value = mock_query

        # Mock the necessary query chain
        mock_query.filter.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.all.return_value = []

        with pytest.raises(ValueError, match="Unexpected operator value"):
            Artist.dynamic_search(
                {"begin_date": "2023-01-01", "begin_comparison": "invalid"}
            )


class TestArtistOrLabelCreateIfNotExist:
    """Test suite for ArtistOrLabel.create_if_not_exist class method"""

    def test_create_if_not_exist_returns_existing_id(self, mocker):
        """Test that create_if_not_exist returns existing ID when item exists"""
        mock_item = mocker.Mock()
        mock_item.id = 42
        mock_exists = mocker.patch("databass.db.models.ArtistOrLabel.exists_by_mbid")
        mock_exists.return_value = mock_item

        result = Artist.create_if_not_exist(name="Test Artist")
        assert result == 42


class TestGoalNewReleasesSinceStartDate:
    """Test suite for Goal.new_releases_since_start_date property"""

    def test_new_releases_since_start_date_returns_integer(self, mocker):
        """Test that new_releases_since_start_date returns an integer value"""
        mock_query = mocker.patch("databass.db.base.app_db.session.query")
        mock_query.return_value.filter.return_value.scalar.return_value = 5

        goal = Goal(start=datetime.now(), end=datetime.now())
        result = goal.new_releases_since_start_date
        assert isinstance(result, int)

    def test_new_releases_since_start_date_queries_correct_model(self, mocker):
        """Test that new_releases_since_start_date queries the Release model"""
        mock_query = mocker.patch("databass.db.base.app_db.session.query")
        mock_query.return_value.filter.return_value.scalar.return_value = 0

        goal = Goal(start=datetime.now(), end=datetime.now())
        goal.new_releases_since_start_date

        # Verify Release.id is being counted
        query_args = mock_query.call_args[0]
        assert "release.id" in str(query_args[0]).lower()

    def test_new_releases_since_start_date_uses_correct_filter(self, mocker):
        """Test that new_releases_since_start_date filters by the correct start date"""
        mock_query = mocker.patch("databass.db.base.app_db.session.query")
        mock_filter = mocker.Mock()
        mock_query.return_value.filter = mock_filter
        mock_filter.return_value.scalar.return_value = 0

        test_date = datetime(2024, 1, 1)
        goal = Goal(start=test_date, end=datetime(2024, 12, 31))
        goal.new_releases_since_start_date

        # Verify filter uses correct start date
        filter_arg = mock_filter.call_args[0][0]
        assert "listen_date" in str(filter_arg)
        assert ">=" in str(filter_arg)

    @pytest.mark.parametrize(
        "count_value",
        [
            0,  # No releases
            1,  # Single release
            50,  # Multiple releases
            100,  # Large number of releases
        ],
    )
    def test_new_releases_since_start_date_returns_correct_count(
        self, mocker, count_value
    ):
        """Test that new_releases_since_start_date returns the correct count from the database"""
        mock_query = mocker.patch("databass.db.base.app_db.session.query")
        mock_query.return_value.filter.return_value.scalar.return_value = count_value

        goal = Goal(start=datetime.now(), end=datetime.now())
        result = goal.new_releases_since_start_date
        assert result == count_value


class TestGoalProgressEnd:
    """Progress windows cap only currently active, incomplete goals."""

    def test_completed_goal_keeps_configured_future_end(self):
        configured_end = datetime.now().replace(microsecond=0) + timedelta(days=30)
        goal = Goal(
            start=datetime.now() - timedelta(days=10),
            end=configured_end,
            completed=datetime.now(),
        )

        assert goal._progress_end == configured_end

    def test_active_incomplete_goal_caps_at_now(self):
        goal = Goal(
            start=datetime.now() - timedelta(days=10),
            end=datetime.now() + timedelta(days=30),
            completed=None,
        )

        assert goal._progress_end < goal.end
        assert goal._progress_end <= datetime.now()


class TestGoalCurrentAmount:
    """Test suite for Goal.current_amount property dispatch"""

    @pytest.mark.parametrize(
        "goal_type,property_name",
        [
            ("release", "new_releases_since_start_date"),
            ("artist", "new_artists_since_start_date"),
            ("label", "new_labels_since_start_date"),
        ],
    )
    def test_current_amount_dispatches_by_type(
        self, mocker, goal_type, property_name
    ):
        """Test that current_amount reads the property matching the goal's type"""
        goal = Goal(start=datetime.now(), type=goal_type)
        mocker.patch.object(
            type(goal),
            property_name,
            new_callable=mocker.PropertyMock,
            return_value=7,
        )
        assert goal.current_amount == 7


class TestGoalGetPast:
    """Test suite for Goal.get_past classmethod"""

    def test_get_past_returns_empty_list_on_error(self, mocker):
        """Test that get_past returns an empty list if the query raises"""
        mocker.patch(
            "databass.db.base.app_db.session.query", side_effect=Exception("boom")
        )
        assert Goal.get_past() == []


class TestGoalCheckGoals:
    """Test suite for Goal.check_goals classmethod"""

    def test_check_goals_returns_newly_completed_goals(self, mocker):
        """Test that check_goals returns only the goals that just became completed"""
        completed_goal = Goal(type="release", amount=1)
        mocker.patch.object(
            Goal, "current_amount", new_callable=mocker.PropertyMock, return_value=1
        )
        untouched_goal = Goal(type="release", amount=10)

        mocker.patch.object(Goal, "get_incomplete", return_value=[completed_goal, untouched_goal])
        mocker.patch("databass.db.models.goal.update")

        result = Goal.check_goals()

        assert result == [completed_goal]
        assert completed_goal.completed is not None
        assert untouched_goal.completed is None

    def test_check_goals_returns_empty_list_when_none_completed(self, mocker):
        """Test that check_goals returns an empty list if no goals were completed"""
        untouched_goal = Goal(type="release", amount=10)
        mocker.patch.object(
            Goal, "current_amount", new_callable=mocker.PropertyMock, return_value=0
        )

        mocker.patch.object(Goal, "get_incomplete", return_value=[untouched_goal])
        mocker.patch("databass.db.models.goal.update")

        assert Goal.check_goals() == []


class TestArtistAllReleases:
    """Test suite for Artist.all_releases property"""

    def test_combines_own_and_collab_releases_newest_first(self):
        """all_releases merges releases and collab_releases, sorted by listen_date desc"""
        artist = Artist(name="Ghostface Killah")
        own = Release(name="Supreme Clientele", listen_date=datetime(2024, 1, 1))
        collab = Release(name="Sour Soul", listen_date=datetime(2024, 6, 1))
        artist.releases = [own]
        artist.collab_releases = [collab]

        assert artist.all_releases == [collab, own]

    def test_returns_empty_list_when_no_releases(self):
        """all_releases is an empty list when the artist has no own or collab releases"""
        artist = Artist(name="No Releases")
        artist.releases = []
        artist.collab_releases = []

        assert artist.all_releases == []

    def test_dedupes_release_credited_both_ways(self):
        """A release doesn't appear twice if it's redundantly in both releases and collab_releases"""
        artist = Artist(name="Ghostface Killah")
        release = Release(name="Sour Soul", listen_date=datetime(2024, 6, 1))
        artist.releases = [release]
        artist.collab_releases = [release]

        assert artist.all_releases == [release]

    def test_breaks_same_day_ties_by_id_descending(self):
        """Releases listened to on the same day are ordered by id descending"""
        artist = Artist(name="Artist")
        same_day = datetime(2024, 6, 1)
        older = Release(id=1, name="First Logged", listen_date=same_day)
        newer = Release(id=2, name="Second Logged", listen_date=same_day)
        artist.releases = [older, newer]
        artist.collab_releases = []

        assert artist.all_releases == [newer, older]


class TestMeanAvgAndCount:
    # Tests for mean_avg_and_count()
    @pytest.mark.parametrize(
        "input_list,expected_avg,expected_count",
        [
            ([{"avg": 98, "count": 5}, {"avg": 80, "count": 10}], 89.0, 7.5),
            (
                [
                    {"avg": 47, "count": 1},
                    {"avg": 53, "count": 4},
                    {"avg": 62, "count": 2},
                ],
                54.0,
                2.3333333333333335,
            ),
        ],
    )
    def test_mean_avg_and_count_success(
        self, input_list, expected_avg, expected_count, mocker
    ):
        """
        Test for proper handling of successful calculation of average and total count
        """
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
        [(2.0, 1.0, None), (2.0, None, 3.0), (None, 1.0, 3.0)],
    )
    def test_bayesian_avg_missing_value(self, weight, item_avg, mean_avg):
        """
        Test for correct handling of input with missing values
        """
        with pytest.raises(ValueError, match="Input missing one of the required values"):
            bayesian_avg(item_weight=weight, item_avg=item_avg, mean_avg=mean_avg)

    @pytest.mark.parametrize(
        "weight,item_avg,mean_avg,expected",
        [(1.0, 2.0, 3.0, 2.0), (2.0, 3.0, 1.0, 5.0), (3.0, 1.0, 2.0, -1.0)],
    )
    def test_bayesian_avg_correct_return(self, weight, item_avg, mean_avg, expected):
        """
        Test for correct handling of valid input
        """
        result = bayesian_avg(item_weight=weight, item_avg=item_avg, mean_avg=mean_avg)
        assert result == expected
