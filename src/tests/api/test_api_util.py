from pathlib import Path
import datetime
import pytest
from databass.api.util import Util

VALID_JPEG_BYTES = bytes([0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46])
VALID_PNG_BYTES = bytes([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A])
INVALID_BYTES = bytes([0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])


class TestToDate:
    """Tests for the Util.to_date() function"""

    @pytest.mark.parametrize(
        "begin_or_end, expected",
        [("begin", datetime.date(1, 1, 1)), ("end", datetime.date(9999, 12, 31))],
    )
    def test_begin_end_without_date(self, begin_or_end, expected):
        """Test conversion when only begin_or_end is provided"""
        result = Util.to_date(begin_or_end=begin_or_end, date_str=None)
        assert result == expected

    @pytest.mark.parametrize(
        "date_str, expected",
        [
            ("2023", datetime.date(2023, 1, 1)),
            ("2023-06", datetime.date(2023, 6, 1)),
            ("2023-06-15", datetime.date(2023, 6, 15)),
        ],
    )
    def test_valid_date_formats(self, date_str, expected):
        """Test conversion of various valid date string formats"""
        result = Util.to_date(begin_or_end=None, date_str=date_str)
        assert result == expected

    def test_invalid_begin_end_value(self):
        """Test that invalid begin_or_end values raise ValueError"""
        with pytest.raises(ValueError, match="Invalid option:"):
            Util.to_date(begin_or_end="invalid", date_str=None)

    def test_missing_both_parameters(self):
        """Test that providing neither parameter raises ValueError"""
        with pytest.raises(
            ValueError, match="Must be used with either begin_or_end or date_str"
        ):
            Util.to_date(begin_or_end=None, date_str=None)

    @pytest.mark.parametrize(
        "invalid_date",
        [
            "202",  # Too short year
            "20234",  # Too long year
            "2023-6",  # Invalid month format
            "2023-13",  # Invalid month value
            "2023-06-1",  # Invalid day format
            "2023-06-32",  # Invalid day value
            "2023/06/15",  # Wrong separator
            "invalid",  # Non-date string
        ],
    )
    def test_invalid_date_formats(self, invalid_date):
        """Test that invalid date string formats raise ValueError"""
        with pytest.raises(ValueError):
            Util.to_date(begin_or_end=None, date_str=invalid_date)

    @pytest.mark.parametrize(
        "begin_or_end, date_str, expected",
        [
            ("begin", "2023", datetime.date(2023, 1, 1)),
            ("end", "2023-06", datetime.date(2023, 6, 1)),
            ("begin", "2023-06-15", datetime.date(2023, 6, 15)),
        ],
    )
    def test_both_parameters(self, begin_or_end, date_str, expected):
        """Test that providing both parameters works correctly and date_str takes precedence"""
        result = Util.to_date(begin_or_end=begin_or_end, date_str=date_str)
        assert result == expected


class TestGetImageTypeFromUrl:
    """Tests for Util.get_image_type_from_url method."""

    def test_standard_image_urls(self):
        """Test detection of image types from standard URLs with extensions at the end."""
        test_cases = {
            "https://example.com/image.jpg": ".jpg",
            "https://example.com/photo.png": ".png",
            "https://example.com/avatar.webp": ".webp",
        }
        for url, expected in test_cases.items():
            assert Util.get_image_type_from_url(url) == expected

    def test_uppercase_extensions(self):
        """Test that uppercase extensions are correctly identified."""
        test_cases = {
            "https://example.com/image.JPG": ".jpg",
            "https://example.com/photo.PNG": ".png",
            "https://example.com/avatar.WEBP": ".webp",
        }
        for url, expected in test_cases.items():
            assert Util.get_image_type_from_url(url) == expected

    def test_extension_in_path(self):
        """Test URLs where the extension appears in the middle of the path."""
        test_cases = {
            "https://example.com/photos/image.jpg/download": ".jpg",
            "https://example.com/image.png/thumbnail": ".png",
            "https://example.com/avatar.webp/small": ".webp",
        }
        for url, expected in test_cases.items():
            assert Util.get_image_type_from_url(url) == expected

    def test_invalid_url(self):
        """Test that invalid URLs raise ValueError."""
        invalid_urls = [
            "https://example.com/image",
            "https://example.com/photo.invalid",
            "https://example.com/picture.doc",
        ]
        for url in invalid_urls:
            with pytest.raises(ValueError):
                Util.get_image_type_from_url(url)

    def test_all_supported_formats(self):
        """Test all supported image formats."""
        formats = [".jpg", ".jpeg", ".png", ".webp"]
        for fmt in formats:
            url = f"https://example.com/image{fmt}"
            assert Util.get_image_type_from_url(url) == fmt


class TestGetImageTypeFromBytes:
    # Test Util.get_image_type_from_bytes()
    def test_get_image_type_from_bytes_jpeg(self):
        """Test to verify JPEG bytes are correctly identified"""
        assert Util.get_image_type_from_bytes(VALID_JPEG_BYTES) == ".jpg"

    def test_get_image_type_from_bytes_png(self):
        """Test to verify PNG bytes are correctly identified"""
        assert Util.get_image_type_from_bytes(VALID_PNG_BYTES) == ".png"

    def test_get_image_type_from_bytes_invalid(self):
        """Test to verify ValueError is raised for invalid image bytes"""
        with pytest.raises(ValueError) as exc_info:
            Util.get_image_type_from_bytes(INVALID_BYTES)
        assert "Unsupported file type" in str(exc_info.value)

    def test_get_image_type_from_bytes_empty(self):
        """Test to verify ValueError is raised for empty bytes"""
        with pytest.raises(ValueError) as exc_info:
            Util.get_image_type_from_bytes(bytes())
        assert "must be at least 8 bytes" in str(exc_info.value)

    def test_get_image_type_from_bytes_partial_header(self):
        """Test to verify ValueError is raised for incomplete image headers"""
        partial_jpeg = VALID_JPEG_BYTES[:3]
        with pytest.raises(ValueError) as exc_info:
            Util.get_image_type_from_bytes(partial_jpeg)
        assert "must be at least 8 bytes" in str(exc_info.value)


# class TestGetImage:
# Tests for Util.get_image()


class TestImgExists:
    """Test suite for the img_exists utility function"""

    @pytest.mark.parametrize(
        "item_id,item_type,expected,extension",
        [
            (123, "release", "/static/img/release/123.jpg", "jpg"),
            (456, "artist", "/static/img/artist/456.png", "png"),
            (789, "label", "/static/img/label/789.jpg", "jpg"),
        ],
    )
    def test_existing_image(self, item_id, item_type, expected, extension, monkeypatch):
        """
        Test that the function returns the correct path when an image exists
        """

        def mock_glob(*args, **kwargs):
            return [Path(f"static/img/{item_type}/{item_id}.{extension}")]

        monkeypatch.setattr(Path, "glob", mock_glob)
        result = Util.img_exists(item_id, item_type)
        assert result == expected

    def test_nonexistent_image(self, monkeypatch):
        """
        Test that the function returns None when no image exists
        """

        def mock_glob(*args, **kwargs):
            return []

        monkeypatch.setattr(Path, "glob", mock_glob)
        result = Util.img_exists(123, "release")
        assert result is None

    @pytest.mark.parametrize("item_type", ["RELEASE", "ARTIST", "LABEL"])
    def test_case_insensitive_type(self, item_type, monkeypatch):
        """
        Test that the function handles case-insensitive item types correctly
        """

        def mock_glob(*args, **kwargs):
            return [Path(f"static/img/{item_type.lower()}/123.jpg")]

        monkeypatch.setattr(Path, "glob", mock_glob)
        result = Util.img_exists(123, item_type)
        assert result is not None

    @pytest.mark.parametrize(
        "invalid_type", ["album", "band", "invalid", "", "releases", "artists"]
    )
    def test_invalid_item_type(self, invalid_type):
        """
        Test that the function raises ValueError for invalid item types
        """
        with pytest.raises(ValueError) as exc:
            Util.img_exists(123, invalid_type)
        assert "Invalid item_type" in str(exc.value)

    @pytest.mark.parametrize("invalid_id", ["123", 1.23, -1, -100, None, [], {}])
    def test_invalid_item_id(self, invalid_id):
        """
        Test that the function raises appropriate errors for invalid item IDs
        """
        if isinstance(invalid_id, int) and invalid_id < 0:
            with pytest.raises(ValueError) as exc:
                Util.img_exists(invalid_id, "release")
            assert "must be a positive integer" in str(exc.value)
        else:
            with pytest.raises(TypeError) as exc:
                Util.img_exists(invalid_id, "release")
            assert "must be a positive integer" in str(exc.value)
