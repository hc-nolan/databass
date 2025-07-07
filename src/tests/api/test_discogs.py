import pytest
import requests.exceptions
from requests import Response
import time
import requests
from databass.api.discogs import Discogs, RATE_LIMIT_THRESHOLD


class TestUpdateRateLimit:
    """Tests for Discogs.update_rate_limit method"""

    def test_update_rate_limit_from_headers(self, mocker):
        """Test rate limit updates correctly from response headers"""
        mock_response = mocker.Mock(spec=requests.Response)
        mock_response.headers = {"x-discogs-ratelimit-remaining": "42"}

        Discogs.update_rate_limit(mock_response)
        assert Discogs.remaining_requests == 42


class TestIsThrottled:
    """Tests for Discogs.is_throttled method"""

    @pytest.mark.parametrize(
        "remaining,expected",
        [
            (None, False),  # Initial state
            (1.0, True),  # Below threshold
            (1.1, True),  # At threshold
            (2.0, False),  # Above threshold
            (0, True),  # Zero remaining
        ],
    )
    def test_throttle_detection(self, remaining, expected):
        """Test throttling detection for different remaining request counts"""
        Discogs.remaining_requests = remaining
        assert Discogs.is_throttled() == expected


class TestRequest:
    """Tests for Discogs.request method"""

    def test_successful_request(self, mocker):
        """Test successful API request with normal rate limit"""
        mock_response = mocker.Mock(spec=requests.Response)
        mock_response.status_code = 200
        mock_response.headers = {"x-discogs-ratelimit-remaining": "5"}
        mock_response.json.return_value = {"data": "test"}

        mock_get = mocker.patch("requests.get", return_value=mock_response)
        result = Discogs.request("/test")

        assert result == {"data": "test"}
        mock_get.assert_called_once()

    def test_request_with_throttling(self, mocker):
        """Test request handling when rate limited"""
        mock_response = mocker.Mock(spec=requests.Response)
        mock_response.status_code = 200
        mock_response.headers = {"x-discogs-ratelimit-remaining": "1"}
        mock_response.json.return_value = {"data": "test"}

        mock_sleep = mocker.patch("time.sleep")
        mocker.patch("requests.get", return_value=mock_response)

        result = Discogs.request("/test")

        assert result == {"data": "test"}
        mock_sleep.assert_called_once_with(5)

    def test_failed_request(self, mocker):
        """Test handling of failed API requests"""
        mock_response = mocker.Mock(spec=requests.Response)
        mock_response.status_code = 404
        mock_response.headers = {"x-discogs-ratelimit-remaining": "5"}

        mocker.patch("requests.get", return_value=mock_response)

        with pytest.raises(requests.exceptions.RequestException):
            Discogs.request("/test")


class TestGetItemId:
    """Test suite for Discogs.get_item_id method"""

    @pytest.mark.parametrize(
        "name,item_type,artist,expected",
        [
            ("", "release", "Artist", None),
            ("Album", "", "Artist", None),
            (None, "release", "Artist", None),
            ("Album", None, "Artist", None),
        ],
    )
    def test_invalid_inputs(self, name, item_type, artist, expected):
        """Test that invalid or empty inputs return None"""
        result = Discogs.get_item_id(name=name, item_type=item_type, artist=artist)
        assert result == expected

    def test_successful_release_search(self, mocker):
        """Test successful release search with valid response"""
        title = "Test Album"
        mock_response = {
            "results": [{"id": "123456", "title": title, "format": ["Vinyl"]}]
        }
        mocker.patch.object(Discogs, "request", return_value=mock_response)

        result = Discogs.get_item_id(
            name=title, item_type="release", artist="Test Artist"
        )
        assert result == "123456"

    def test_skip_bluray_release(self, mocker):
        """Test that Blu-ray releases are skipped and next valid release is returned"""
        title = "Test Album"
        mock_response = {
            "results": [
                {"id": "111", "title": title, "format": ["Blu-ray"]},
                {"id": "222", "title": title, "format": ["Vinyl"]},
            ]
        }
        mocker.patch.object(Discogs, "request", return_value=mock_response)

        result = Discogs.get_item_id(
            name=title, item_type="release", artist="Test Artist"
        )
        assert result == "222"

    def test_successful_non_release_search(self, mocker):
        """Test successful search for non-release items (artist, label)"""
        mock_response = {"results": [{"id": "789012", "format": "CD"}]}
        mocker.patch.object(Discogs, "request", return_value=mock_response)

        result = Discogs.get_item_id(name="Test Artist", item_type="artist")
        assert result == "789012"

    def test_empty_results(self, mocker):
        """Test handling of empty results"""
        mock_response = {"results": []}
        mocker.patch.object(Discogs, "request", return_value=mock_response)

        result = Discogs.get_item_id(
            name="Nonexistent Album", item_type="release", artist="Nonexistent Artist"
        )
        assert result is None

    def test_malformed_response(self, mocker):
        """Test handling of malformed API response"""
        mock_response = {"wrong_key": []}
        mocker.patch.object(Discogs, "request", return_value=mock_response)

        result = Discogs.get_item_id(
            name="Test Album", item_type="release", artist="Test Artist"
        )
        assert result is None

    def test_request_exception(self, mocker):
        """Test handling of request exceptions"""
        mocker.patch.object(Discogs, "request", side_effect=requests.RequestException)

        result = Discogs.get_item_id(
            name="Test Album", item_type="release", artist="Test Artist"
        )
        assert result is None


class TestGetItemImageUrl:
    """Test suite for Discogs.get_item_image_url method"""

    @pytest.mark.parametrize(
        "response,expected",
        [
            (
                {
                    "results": [
                        {"cover_image": "https://example.com/h:500/w:500/image.jpg"}
                    ]
                },
                "https://example.com/h:500/w:500/image.jpg",
            ),
            (
                {
                    "results": [
                        {"cover_image": "https://example.com/h:300/w:500/image.jpg"},
                        {"cover_image": "https://example.com/h:400/w:400/image2.jpg"},
                    ]
                },
                "https://example.com/h:400/w:400/image2.jpg",
            ),
            ({"results": []}, None),
            (None, None),
        ],
    )
    def test_with_various_responses(self, mocker, response, expected):
        """
        Test get_item_image_url with different API responses:
        - Response with square image
        - Response with non-square image followed by square image
        - Empty results
        - None response
        """
        mocker.patch.object(Discogs, "request", return_value=response)
        result = Discogs.get_item_image_url("/test/endpoint")
        assert result == expected

    def test_with_invalid_dimensions(self, mocker):
        """
        Test handling of images with invalid dimension formats in URL
        """
        mock_response = {
            "results": [{"cover_image": "https://example.com/invalid/format/image.jpg"}]
        }
        mocker.patch.object(Discogs, "request", return_value=mock_response)
        result = Discogs.get_item_image_url("/test/endpoint")
        assert result is None

    def test_request_exception(self, mocker):
        """
        Test handling of request exceptions
        """
        mocker.patch.object(Discogs, "request", side_effect=requests.RequestException)
        result = Discogs.get_item_image_url("/test/endpoint")
        assert result is None

    @pytest.mark.parametrize(
        "image_url",
        [
            "https://example.com/h:500/w:500/image.jpg",
            "https://example.com/h:1000/w:1000/image.jpg",
            "https://example.com/h:200/w:200/image.jpg",
        ],
    )
    def test_different_dimensions(self, mocker, image_url):
        """
        Test handling of different square image dimensions
        """
        mock_response = {"results": [{"cover_image": image_url}]}
        mocker.patch.object(Discogs, "request", return_value=mock_response)
        result = Discogs.get_item_image_url("/test/endpoint")
        assert result == image_url

    def test_missing_cover_image(self, mocker):
        """
        Test handling of results missing cover_image field
        """
        mock_response = {"results": [{"other_field": "value"}]}
        mocker.patch.object(Discogs, "request", return_value=mock_response)
        result = Discogs.get_item_image_url("/test/endpoint")
        assert result is None


class TestFindImage:
    @pytest.mark.parametrize(
        "search_results, expected",
        [
            (None, None),
            ({}, None),
            ({"images": []}, None),
        ],
    )
    def test_empty_inputs(self, search_results, expected):
        """Test find_image with empty or None inputs returns None"""
        assert Discogs.find_image(search_results) == expected

    def test_square(self):
        """Test find_image returns first square image found"""
        mock_results = {
            "images": [
                {"uri": "non-square.jpg", "height": 100, "width": 200},
                {"uri": "square.jpg", "height": 300, "width": 300},
                {"uri": "another-square.jpg", "height": 400, "width": 400},
            ]
        }
        assert Discogs.find_image(mock_results) == "square.jpg"

    def test_no_square_returns_first(self):
        """Test find_image returns first image when no square images exist"""
        mock_results = {
            "images": [
                {"uri": "first.jpg", "height": 100, "width": 200},
                {"uri": "second.jpg", "height": 300, "width": 400},
            ]
        }
        assert Discogs.find_image(mock_results) == "first.jpg"

    def test_missing_dimensions(self):
        """Test find_image handles missing height/width gracefully"""
        mock_results = {
            "images": [
                {"uri": "image1.jpg"},
                {"uri": "image2.jpg", "height": 300, "width": 300},
            ]
        }
        assert Discogs.find_image(mock_results) == "image2.jpg"

    @pytest.mark.parametrize(
        "malformed_data",
        [
            {"wrong_key": []},
            {"images": "not_a_list"},
            {"images": [{"no_uri": "test"}]},
        ],
    )
    def test_malformed_data(self, malformed_data):
        """Test find_image handles malformed data structures gracefully"""
        assert Discogs.find_image(malformed_data) is None

    def test_single_image(self):
        """Test find_image with single image in results"""
        mock_results = {"images": [{"uri": "only.jpg", "height": 100, "width": 200}]}
        assert Discogs.find_image(mock_results) == "only.jpg"

    def test_multiple_square_images(self):
        """Test find_image returns first square image when multiple exist"""
        mock_results = {
            "images": [
                {"uri": "rectangle.jpg", "height": 100, "width": 200},
                {"uri": "square1.jpg", "height": 300, "width": 300},
                {"uri": "square2.jpg", "height": 400, "width": 400},
            ]
        }
        assert Discogs.find_image(mock_results) == "square1.jpg"


class TestGetReleaseImageUrl:
    """Test suite for Discogs.get_release_image_url method"""

    @pytest.mark.parametrize(
        "name,artist",
        [
            (None, "artist"),
            ("name", None),
            (123, "artist"),
            ("name", 123),
            ("", "artist"),
            ("name", ""),
        ],
    )
    def test_invalid_inputs(self, name, artist):
        """Test that invalid inputs return None"""
        result = Discogs.get_release_image_url(name=name, artist=artist)
        assert result is None

    def test_successful_image_retrieval(self, mocker):
        """Test successful retrieval of image"""
        expected_url = "http://example.com/image1.jpg"
        mocker.patch.object(Discogs, "get_item_id", return_value="123")
        mocker.patch.object(Discogs, "request", return_value={"some": "data"})
        mocker.patch.object(Discogs, "find_image", return_value=expected_url)

        result = Discogs.get_release_image_url(name="Test Album", artist="Test Artist")
        assert result == expected_url

    def test_no_release_id_found(self, mocker):
        """Test when no release ID is found"""
        mocker.patch.object(Discogs, "get_item_id", return_value=False)
        result = Discogs.get_release_image_url(name="Test Album", artist="Test Artist")
        assert result is None

    def test_request_exception(self, mocker):
        """Test handling of request exceptions"""
        mocker.patch.object(Discogs, "get_item_id", return_value="123")
        mocker.patch.object(Discogs, "request", side_effect=requests.RequestException)
        result = Discogs.get_release_image_url(name="Test Album", artist="Test Artist")
        assert result is None


class TestGetArtistImageUrl:
    """Test suite for Discogs.get_artist_image_url method"""

    @pytest.mark.parametrize("artist_name", [None, "", 123, [], {}])
    def test_invalid_input(self, artist_name):
        """Test that invalid input types return None"""
        result = Discogs.get_artist_image_url(artist_name)
        assert result is None

    def test_artist_not_found(self, mocker):
        """Test behavior when no artist ID is found"""
        mocker.patch.object(Discogs, "get_item_id", return_value=False)
        result = Discogs.get_artist_image_url("Nonexistent Artist")
        assert result is None

    def test_request_exception(self, mocker):
        """Test handling of request exceptions"""
        mocker.patch.object(Discogs, "get_item_id", return_value="123")
        mocker.patch.object(
            Discogs, "request", side_effect=requests.exceptions.RequestException
        )
        result = Discogs.get_artist_image_url("Test Artist")
        assert result is None

    def test_successful_image_retrieval(self, mocker):
        """Test successful retrieval of artist image URL"""
        mock_response = {
            "images": [
                {"uri": "http://example.com/image.jpg", "height": 500, "width": 500}
            ]
        }
        mocker.patch.object(Discogs, "get_item_id", return_value="123")
        mocker.patch.object(Discogs, "request", return_value=mock_response)
        mocker.patch.object(
            Discogs, "find_image", return_value="http://example.com/image.jpg"
        )

        result = Discogs.get_artist_image_url("Valid Artist")
        assert result == "http://example.com/image.jpg"

    def test_integration_flow(self, mocker):
        """Test the complete integration flow with all components"""
        artist_id = "123"
        image_url = "http://example.com/artist.jpg"

        mocker.patch.object(Discogs, "get_item_id", return_value=artist_id)
        mocker.patch.object(
            Discogs, "request", return_value={"images": [{"uri": image_url}]}
        )
        mocker.patch.object(Discogs, "find_image", return_value=image_url)

        result = Discogs.get_artist_image_url("Test Artist")

        assert result == image_url
        Discogs.get_item_id.assert_called_once_with(
            name="Test Artist", item_type="artist"
        )
        Discogs.request.assert_called_once_with(f"/artists/{artist_id}")


class TestGetLabelImageUrl:
    """Test suite for Discogs.get_label_image_url method"""

    @pytest.mark.parametrize("label_name", [None, "", 123, [], {}])
    def test_invalid_input(self, label_name):
        """Test that invalid input types return None"""
        result = Discogs.get_label_image_url(label_name)
        assert result is None

    def test_label_not_found(self, mocker):
        """Test behavior when no label ID is found"""
        mocker.patch.object(Discogs, "get_item_id", return_value=False)
        result = Discogs.get_label_image_url("Nonexistent Label")
        assert result is None

    def test_request_exception(self, mocker):
        """Test handling of request exceptions"""
        mocker.patch.object(Discogs, "get_item_id", return_value="123")
        mocker.patch.object(
            Discogs, "request", side_effect=requests.exceptions.RequestException
        )
        result = Discogs.get_label_image_url("Test Label")
        assert result is None

    def test_successful_image_retrieval(self, mocker):
        """Test successful retrieval of label image URL"""
        mock_response = {
            "images": [
                {"uri": "http://example.com/image.jpg", "height": 500, "width": 500}
            ]
        }
        mocker.patch.object(Discogs, "get_item_id", return_value="123")
        mocker.patch.object(Discogs, "request", return_value=mock_response)
        mocker.patch.object(
            Discogs, "find_image", return_value="http://example.com/image.jpg"
        )

        result = Discogs.get_label_image_url("Valid Label")
        assert result == "http://example.com/image.jpg"

    def test_integration_flow(self, mocker):
        """Test the complete integration flow with all components"""
        label_id = "123"
        image_url = "http://example.com/label.jpg"

        mocker.patch.object(Discogs, "get_item_id", return_value=label_id)
        mocker.patch.object(
            Discogs, "request", return_value={"images": [{"uri": image_url}]}
        )
        mocker.patch.object(Discogs, "find_image", return_value=image_url)

        result = Discogs.get_label_image_url("Test Label")

        assert result == image_url
        Discogs.get_item_id.assert_called_once_with(
            name="Test Label", item_type="label"
        )
        Discogs.request.assert_called_once_with(f"/labels/{label_id}")
