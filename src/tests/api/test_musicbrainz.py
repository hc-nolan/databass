import pytest
from databass.api.musicbrainz import MusicBrainz, MbzParser
from databass.api.types import ReleaseInfo
import musicbrainzngs as mbz
import datetime


class TestInitialize:
    # Tests for MusicBrainz.release_search()
    def test_initialize_success(self, mocker):
        """
        Test the successful initialization of the MusicBrainz API client.

        Verifies that the `MusicBrainz.initialize()` method correctly sets the
        `MusicBrainz.init` flag to `True` and calls the `musicbrainzngs.set_useragent()`
        function to initialize the MusicBrainz API client.
        """
        mock_mbz = mocker.patch("musicbrainzngs.set_useragent")
        assert MusicBrainz.init is False
        MusicBrainz.initialize()
        mock_mbz.assert_called_once()
        assert MusicBrainz.init is True


class TestMusicBrainzReleaseSearch:
    @pytest.fixture
    def mock_mbz_response(self):
        return {
            "release-list": [
                {
                    "id": "123",
                    "title": "Test Album",
                    "artist-credit": [{"name": "Test Artist", "artist": {"id": "456"}}],
                    "label-info-list": [{"label": {"id": "789", "name": "Test Label"}}],
                    "date": "2023-01-01",
                    "medium-list": [{"format": "CD", "track-count": 10}],
                    "country": "US",
                    "release-group": {"id": "999"},
                }
            ]
        }

    @pytest.mark.parametrize(
        "search_params",
        [
            {"release": "Test Album"},
            {"artist": "Test Artist"},
            {"label": "Test Label"},
            {"release": "Test Album", "artist": "Test Artist"},
            {"release": "Test Album", "artist": "Test Artist", "label": "Test Label"},
        ],
    )
    def test_valid_search_parameters(self, mocker, mock_mbz_response, search_params):
        """
        Test release search with various valid parameter combinations
        """
        mocker.patch("musicbrainzngs.search_releases", return_value=mock_mbz_response)
        MusicBrainz.init = True

        result = MusicBrainz.release_search(**search_params)

        assert isinstance(result, list)
        assert len(result) == 1

        # Verify the structure of the returned data matches ReleaseInfo
        release_info = result[0]
        assert all(key in release_info for key in ReleaseInfo.__annotations__)
        assert release_info["release"]["mbid"] == "123"
        assert release_info["artist"]["mbid"] == "456"
        assert release_info["format"] == "CD"
        assert release_info["country"] == "US"
        assert release_info["date"] == 2023

    def test_empty_search_parameters(self):
        """
        Test that searching with no parameters raises ValueError
        """
        MusicBrainz.init = True
        with pytest.raises(ValueError, match="At least one query term is required"):
            MusicBrainz.release_search()

    def test_missing_label_info(self, mocker):
        """
        Test handling of releases without label information
        """
        response = {
            "release-list": [
                {
                    "id": "123",
                    "title": "Test Album",
                    "artist-credit": [{"name": "Test Artist", "artist": {"id": "456"}}],
                    "release-group": {"id": "999"},
                }
            ]
        }
        mocker.patch("musicbrainzngs.search_releases", return_value=response)
        MusicBrainz.init = True

        result = MusicBrainz.release_search(release="Test Album")

        assert result[0]["label"]["mbid"] is None
        assert result[0]["label"]["name"] is None

    def test_invalid_date_handling(self, mocker):
        """
        Test handling of releases with invalid date formats
        """
        response = {
            "release-list": [
                {
                    "id": "123",
                    "title": "Test Album",
                    "artist-credit": [{"name": "Test Artist", "artist": {"id": "456"}}],
                    "date": "invalid-date",
                    "release-group": {"id": "999"},
                }
            ]
        }
        mocker.patch("musicbrainzngs.search_releases", return_value=response)
        MusicBrainz.init = True

        result = MusicBrainz.release_search(release="Test Album")

        assert result[0]["date"] == ""

    def test_multiple_discs_track_count(self, mocker):
        """
        Test correct calculation of track count for multi-disc releases
        """
        response = {
            "release-list": [
                {
                    "id": "123",
                    "title": "Test Album",
                    "artist-credit": [{"name": "Test Artist", "artist": {"id": "456"}}],
                    "medium-list": [{"track-count": 10}, {"track-count": 12}],
                    "release-group": {"id": "999"},
                }
            ]
        }
        mocker.patch("musicbrainzngs.search_releases", return_value=response)
        MusicBrainz.init = True

        result = MusicBrainz.release_search(release="Test Album")

        assert result[0]["track_count"] == 22


class TestMusicBrainzLabelSearch:
    @pytest.fixture
    def mock_label_data(self):
        return {
            "label": {
                "name": "Test Label",
                "id": "test-id-123",
                "life-span": {"begin": "1990-01-01", "end": "2020-12-31"},
                "country": "US",
                "type": "Production",
            }
        }

    @pytest.mark.parametrize(
        "name,mbid",
        [
            ("Test Label", "test-id-123"),
            ("Another Label", "another-id-456"),
        ],
    )
    def test_label_search_with_mbid(self, name, mbid, mock_label_data, mocker):
        """
        Test label search when MBID is provided, verifying direct label lookup
        """
        mocker.patch.object(mbz, "get_label_by_id", return_value=mock_label_data)
        result = MusicBrainz.label_search(name=name, mbid=mbid)

        assert isinstance(result, dict)
        assert all(
            key in result for key in ["name", "mbid", "begin", "end", "country", "type"]
        )
        assert result["name"] == "Test Label"
        assert result["mbid"] == "test-id-123"
        assert result["country"] == "US"
        assert result["type"] == "Production"

    def test_label_search_without_mbid(self, mock_label_data, mocker):
        """
        Test label search using only name, verifying search and subsequent lookup
        """
        search_result = {"label-list": [{"id": "found-id-789", "name": "Found Label"}]}
        mocker.patch.object(mbz, "search_labels", return_value=search_result)
        mocker.patch.object(mbz, "get_label_by_id", return_value=mock_label_data)

        result = MusicBrainz.label_search(name="Found Label")
        assert isinstance(result, dict)
        assert all(
            key in result for key in ["name", "mbid", "begin", "end", "country", "type"]
        )
        assert result["name"] == "Test Label"

    def test_label_search_invalid_input(self):
        """
        Test label search with invalid input parameters
        """
        assert MusicBrainz.label_search(name="") is None
        assert MusicBrainz.label_search(name=None) is None
        assert MusicBrainz.label_search(name=123) is None

    def test_label_search_no_results(self, mocker):
        """
        Test label search when no results are found
        """
        mocker.patch.object(mbz, "search_labels", return_value={"label-list": []})
        assert MusicBrainz.label_search(name="Nonexistent Label") is None

    def test_label_search_api_error(self, mocker):
        """
        Test label search when API returns an error
        """
        mocker.patch.object(mbz, "get_label_by_id", side_effect=Exception("API Error"))
        with pytest.raises(Exception):
            MusicBrainz.label_search(name="Error Label", mbid="error-id")

    def test_label_search_partial_data(self, mocker):
        """
        Test label search with incomplete label data returned from API
        """
        partial_data = {
            "label": {
                "name": "Partial Label",
                "id": "partial-id",
            }
        }
        mocker.patch.object(mbz, "get_label_by_id", return_value=partial_data)

        result = MusicBrainz.label_search(name="Partial", mbid="partial-id")
        assert isinstance(result, dict)
        assert all(
            key in result for key in ["name", "mbid", "begin", "end", "country", "type"]
        )
        assert result["name"] == "Partial Label"
        assert result["mbid"] == "partial-id"
        assert result["begin"] == datetime.date(1, 1, 1)
        assert result["end"] == datetime.date(9999, 12, 31)
        assert result["country"] is None
        assert result["type"] is None


class TestMusicBrainzArtistSearch:
    @pytest.fixture
    def mock_artist_data(self):
        return {
            "artist": {
                "name": "Test Artist",
                "id": "test-id-123",
                "life-span": {"begin": "1990-01-01", "end": "2020-12-31"},
                "country": "US",
                "type": "Person",
            }
        }

    @pytest.mark.parametrize(
        "name,mbid",
        [
            ("Test Artist", "test-id-123"),
            ("Another Artist", "another-id-456"),
        ],
    )
    def test_artist_search_with_mbid(self, name, mbid, mock_artist_data, mocker):
        """
        Test artist search when MBID is provided, verifying direct artist lookup
        and proper parsing of the returned data structure
        """
        mocker.patch.object(mbz, "get_artist_by_id", return_value=mock_artist_data)
        result = MusicBrainz.artist_search(name=name, mbid=mbid)

        assert isinstance(result, dict)
        assert all(
            key in result for key in ["name", "mbid", "begin", "end", "country", "type"]
        )
        assert result["name"] == "Test Artist"
        assert result["mbid"] == "test-id-123"
        assert result["country"] == "US"
        assert result["type"] == "Person"

    def test_artist_search_without_mbid(self, mock_artist_data, mocker):
        """
        Test artist search using only name, verifying search functionality
        and subsequent artist lookup
        """
        search_result = {
            "artist-list": [{"id": "found-id-789", "name": "Found Artist"}]
        }
        mocker.patch.object(mbz, "search_artists", return_value=search_result)
        mocker.patch.object(mbz, "get_artist_by_id", return_value=mock_artist_data)

        result = MusicBrainz.artist_search(name="Found Artist")
        assert isinstance(result, dict)
        assert all(
            key in result for key in ["name", "mbid", "begin", "end", "country", "type"]
        )
        assert result["name"] == "Test Artist"

    @pytest.mark.parametrize("invalid_input", ["", None, 123, [], {}])
    def test_artist_search_invalid_input(self, invalid_input):
        """
        Test artist search with various invalid input parameters,
        ensuring proper handling of edge cases
        """
        assert MusicBrainz.artist_search(name=invalid_input) is None

    def test_artist_search_no_results(self, mocker):
        """
        Test artist search when no results are found in the database
        """
        mocker.patch.object(mbz, "search_artists", return_value={"artist-list": []})
        result = MusicBrainz.artist_search(name="Nonexistent Artist")
        assert result is None

    def test_artist_search_api_error(self, mocker):
        """
        Test artist search when API returns an error,
        ensuring proper error handling
        """
        mocker.patch.object(mbz, "get_artist_by_id", side_effect=Exception("API Error"))
        result = MusicBrainz.artist_search(name="Error Artist", mbid="error-id")
        assert result is None

    def test_artist_search_partial_data(self, mocker):
        """
        Test artist search with incomplete artist data returned from API,
        ensuring proper handling of missing fields
        """
        partial_data = {
            "artist": {
                "name": "Partial Artist",
                "id": "partial-id",
            }
        }
        mocker.patch.object(mbz, "get_artist_by_id", return_value=partial_data)

        result = MusicBrainz.artist_search(name="Partial", mbid="partial-id")
        assert isinstance(result, dict)
        assert all(
            key in result for key in ["name", "mbid", "begin", "end", "country", "type"]
        )
        assert result["name"] == "Partial Artist"
        assert result["mbid"] == "partial-id"
        assert result["begin"] == datetime.date(1, 1, 1)
        assert result["end"] == datetime.date(9999, 12, 31)
        assert result["country"] is None
        assert result["type"] is None


class TestParseSearchResult:
    @pytest.fixture
    def valid_search_result(self):
        return {
            "name": "Test Entity",
            "id": "test-id-123",
            "life_span": {"begin": "1990-01-01", "end": "2020-12-31"},
            "country": "US",
            "type": "Group",
        }

    def test_valid_complete_result(self, valid_search_result):
        """
        Test parsing a complete search result with all fields present,
        verifying that all fields are correctly extracted and converted
        """
        result = MbzParser.parse_search_result(valid_search_result)

        assert isinstance(result, dict)
        assert result["name"] == "Test Entity"
        assert result["mbid"] == "test-id-123"
        assert result["begin"] == datetime.date(1990, 1, 1)
        assert result["end"] == datetime.date(2020, 12, 31)
        assert result["country"] == "US"
        assert result["type"] == "Group"

    @pytest.mark.parametrize("missing_field", ["life_span", "country", "type"])
    def test_missing_optional_fields(self, valid_search_result, missing_field):
        """
        Test parsing results with various optional fields missing,
        ensuring the parser handles missing fields gracefully
        """
        valid_search_result.pop(missing_field, None)
        result = MbzParser.parse_search_result(valid_search_result)

        assert result["name"] == "Test Entity"
        assert result["mbid"] == "test-id-123"
        if missing_field == "life_span":
            assert result["begin"] == datetime.date(1, 1, 1)
            assert result["end"] == datetime.date(9999, 12, 31)
        elif missing_field == "country":
            assert result["country"] is None
        elif missing_field == "type":
            assert result["type"] is None

    @pytest.mark.parametrize("invalid_input", [None, {}, [], "invalid", 123])
    def test_invalid_input(self, invalid_input):
        """
        Test parsing with invalid input types,
        ensuring appropriate error handling
        """
        with pytest.raises(
            ValueError, match="Invalid or empty search result passed to the function"
        ):
            MbzParser.parse_search_result(invalid_input)

    def test_partial_life_span(self, valid_search_result):
        """
        Test parsing a result with partial life_span data,
        verifying correct handling of missing begin/end dates
        """
        valid_search_result["life_span"] = {"begin": "1990-01-01"}
        result = MbzParser.parse_search_result(valid_search_result)

        assert result["begin"] == datetime.date(1990, 1, 1)
        assert result["end"] == datetime.date(9999, 12, 31)

    @pytest.mark.parametrize("date_format", ["1990", "1990-01", "1990-01-01"])
    def test_various_date_formats(self, valid_search_result, date_format):
        """
        Test parsing different date formats in the life_span field,
        ensuring proper date parsing for various formats
        """
        valid_search_result["life_span"]["begin"] = date_format
        result = MbzParser.parse_search_result(valid_search_result)

        assert isinstance(result["begin"], datetime.date)
        assert result["begin"].year == 1990


class TestGetReleaseLength:
    @pytest.mark.parametrize(
        "mbid",
        [
            "2ab9206e-4408-47e3-92cc-283d2b96c896",
            "123e4567-e89b-12d3-a456-426614174000",
        ],
    )
    def test_valid_release_length(self, mocker, mbid):
        """
        Test calculating total release length with valid release data containing
        multiple discs and tracks with proper length information.
        """
        mock_release_data = {
            "release": {
                "medium-list": [
                    {"track-list": [{"length": "180000"}, {"length": "200000"}]},
                    {"track-list": [{"length": "160000"}, {"length": "190000"}]},
                ]
            }
        }
        mocker.patch("musicbrainzngs.get_release_by_id", return_value=mock_release_data)

        result = MusicBrainz.get_release_length(mbid)
        assert result == 730000  # Returns after first track due to finally block

    @pytest.mark.parametrize("invalid_mbid", [None, "", 123, [], {}])
    def test_invalid_mbid(self, invalid_mbid):
        """
        Test handling of invalid MBID inputs, ensuring zero is returned.
        """
        result = MusicBrainz.get_release_length(invalid_mbid)
        assert result == 0

    def test_missing_length_data(self, mocker):
        """
        Test handling of release data where track length information is missing.
        """
        mock_release_data = {
            "release": {
                "medium-list": [
                    {"track-list": [{"title": "Track 1"}, {"title": "Track 2"}]}
                ]
            }
        }
        mocker.patch("musicbrainzngs.get_release_by_id", return_value=mock_release_data)

        result = MusicBrainz.get_release_length("valid-mbid")
        assert result == 0

    def test_api_error(self, mocker):
        """
        Test handling of API errors when fetching release data.
        """
        mocker.patch(
            "musicbrainzngs.get_release_by_id", side_effect=Exception("API Error")
        )

        result = MusicBrainz.get_release_length("valid-mbid")
        assert result == 0

    def test_uninitialized_state(self, mocker):
        """
        Test behavior when MusicBrainz is not initialized, verifying automatic initialization.
        """
        MusicBrainz.init = False

        # Mock initialize to set init flag to True
        def mock_initialize():
            MusicBrainz.init = True

        mock_init = mocker.patch.object(
            MusicBrainz, "initialize", side_effect=mock_initialize
        )
        mocker.patch(
            "musicbrainzngs.get_release_by_id",
            return_value={
                "release": {"medium-list": [{"track-list": [{"length": "180000"}]}]}
            },
        )

        result = MusicBrainz.get_release_length("valid-mbid")
        mock_init.assert_called_once()
        assert result == 180000


class TestGetImage:
    @pytest.mark.parametrize(
        "mbid,size",
        [
            ("2ab9206e-4408-47e3-92cc-283d2b96c896", "250"),
            ("123e4567-e89b-12d3-a456-426614174000", "500"),
            ("550e8400-e29b-41d4-a716-446655440000", "1200"),
        ],
    )
    def test_valid_image_fetch(self, mocker, mbid, size):
        """
        Test successful image retrieval with valid MBID and size parameters,
        verifying that the function returns bytes data.
        """
        mock_image = b"mock_image_data"
        mocker.patch(
            "musicbrainzngs.get_release_group_image_front", return_value=mock_image
        )

        result = MusicBrainz.get_image(mbid, size)
        assert result == mock_image

    def test_fallback_image_fetch(self, mocker):
        """
        Test successful image retrieval through fallback mechanism when primary
        method fails, verifying correct handling of image list and subsequent fetch.
        """
        mock_image = b"fallback_image_data"
        mbid = "test-mbid"

        # Mock primary method to fail
        mocker.patch(
            "musicbrainzngs.get_release_group_image_front",
            side_effect=mbz.musicbrainz.ResponseError(None, None),
        )

        # Mock fallback methods
        mocker.patch(
            "musicbrainzngs.get_image_list",
            return_value={"images": [{"id": "cover-id"}]},
        )
        mocker.patch("musicbrainzngs.get_image", return_value=mock_image)

        result = MusicBrainz.get_image(mbid)
        assert result == mock_image

    @pytest.mark.parametrize("invalid_size", ["abc", "-250", "0x123", "", "!@#"])
    def test_invalid_size_parameter(self, invalid_size):
        """
        Test handling of invalid size parameters, ensuring None is returned
        for non-numeric size values.
        """
        result = MusicBrainz.get_image("valid-mbid", size=invalid_size)
        assert result is None

    @pytest.mark.parametrize("invalid_mbid", [None, "", 123, [], {}])
    def test_invalid_mbid_parameter(self, invalid_mbid):
        """
        Test handling of invalid MBID parameters, ensuring None is returned
        for non-string MBID values.
        """
        result = MusicBrainz.get_image(invalid_mbid)
        assert result is None

    def test_no_images_found(self, mocker):
        """
        Test handling of cases where no images are found for a valid MBID,
        verifying None is returned.
        """
        mocker.patch(
            "musicbrainzngs.get_release_group_image_front",
            side_effect=mbz.musicbrainz.ResponseError(None, None),
        )
        mocker.patch("musicbrainzngs.get_image_list", return_value={"images": []})

        result = MusicBrainz.get_image("valid-mbid")
        assert result is None

    def test_api_error_handling(self, mocker):
        """
        Test handling of API errors during image fetch, ensuring None is returned
        when unexpected errors occur.
        """
        mocker.patch(
            "musicbrainzngs.get_release_group_image_front",
            side_effect=Exception("Unexpected API error"),
        )

        result = MusicBrainz.get_image("valid-mbid")
        assert result is None

    def test_missing_image_id(self, mocker):
        """
        Test handling of missing image ID in fallback response,
        verifying None is returned when image ID cannot be found.
        """
        mocker.patch(
            "musicbrainzngs.get_release_group_image_front",
            side_effect=mbz.musicbrainz.ResponseError(None, None),
        )
        mocker.patch("musicbrainzngs.get_image_list", return_value={"images": [{}]})

        result = MusicBrainz.get_image("valid-mbid")
        assert result is None
