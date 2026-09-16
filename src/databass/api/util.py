import datetime
from os import getenv
from pathlib import Path
from typing import Literal, Optional
from uuid import uuid4
import requests
from dotenv import load_dotenv

load_dotenv()
VERSION = getenv("VERSION")

JPEG_HEADER = b"\xff\xd8\xff"
PNG_HEADER = b"\x89PNG\r\n\x1a\n"

VALID_TYPES = frozenset(["release", "artist", "label"])
VALID_DATE_TYPES = frozenset(["begin", "end"])

YEAR_FORMAT = "%Y"
MONTH_FORMAT = "%Y-%m"
DAY_FORMAT = "%Y-%m-%d"

SUPPORTED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
}
IMG_BASE_PATH = "./databass/static/img"


class TimeoutException(Exception):
    pass


def timeout_handler(signum, frame):
    raise TimeoutException("Request timed out")


class Util:
    """
    Collection of generic utility functions used by other parts of the app
    """

    @staticmethod
    def to_begin_or_end(option: str) -> datetime.date:
        match option:
            case "begin":
                return datetime.date(year=1, month=1, day=1)
            case "end":
                return datetime.date(year=9999, month=12, day=31)
            case _:
                raise ValueError(
                    f"Invalid option: {option} - should be 'begin' or 'end'"
                )

    @staticmethod
    def to_date(begin_or_end: Optional[str], date_str: Optional[str]) -> datetime.date:
        """
        Convert a date string to a datetime.date object.
        If the date string is empty, will default to either 0001/01/01 (begin) or
        9999/12/31 (end)
        """
        if date_str is None and begin_or_end is None:
            raise ValueError(
                "Must be used with either begin_or_end or date_str, or both"
            )
        if date_str is None:
            return Util.to_begin_or_end(begin_or_end)
        match len(date_str):
            case 4:
                date = datetime.datetime.strptime(date_str, YEAR_FORMAT)
            case 7:
                date = datetime.datetime.strptime(date_str, MONTH_FORMAT)
            case 10:
                date = datetime.datetime.strptime(date_str, DAY_FORMAT)
            case _:
                raise ValueError(f"Unexpected date string format: {date_str}")

        return date.date()

    @staticmethod
    def today() -> str:
        """Returns current day formatted as YYYY-MM-DD string"""
        return datetime.datetime.today().strftime("%Y-%m-%d")

    @staticmethod
    def get_image_type_from_url(url: str) -> str:
        """
        Determine the image file extension from the URL of an image file.
        """
        url = url.lower()
        for ext in SUPPORTED_EXTENSIONS:
            if ext in url:
                return ext

        raise ValueError(f"ERROR: No supported image type found in URL: {url}")

    @staticmethod
    def get_image_type_from_bytes(bytestr: bytes) -> str:
        """
        Determine the image file extension from the byte representation of an image file.
        """
        if len(bytestr) < 8:
            raise ValueError("bytestr must be at least 8 bytes.")
        if bytestr.startswith(JPEG_HEADER):
            return ".jpg"
        if bytestr.startswith(PNG_HEADER):
            return ".png"
        raise ValueError(
            f"Unsupported file type (signature: {bytestr[:8].hex()}). Supported types: jpg, png"
        )

    @staticmethod
    def get_image_from_url(url: str, entity_type: Literal["release", "artist", "label"]):
        if entity_type not in VALID_TYPES:
            raise ValueError(
                f"Invalid entity_type: {entity_type}. "
                f"Must be one of the following strings: {', '.join(VALID_TYPES)}"
            )
        response = requests.get(
            url,
            headers={
                "User-Agent": f"databass/{VERSION} (https://github.com/chunned/databass)"
            },
            timeout=30,
        )
        if response:
            Path(f"{IMG_BASE_PATH}/{entity_type}").mkdir(parents=True, exist_ok=True)
            ext = Util.get_image_type_from_url(url)
            img_filepath = IMG_BASE_PATH + f"/{entity_type}/" + str(uuid4()) + ext
            with open(img_filepath, "wb") as img_file:
                img_file.write(response.content)
            return img_filepath.replace("databass/", "")

    @staticmethod
    def img_exists(item_id: int, item_type: str) -> Optional[str]:
        """
        Check if a local image exists for the given entity.

        Args:
            item_id: Unique identifier for the item
            item_type: Type of item ('release', 'artist', or 'label')

        Returns:
            str: Path to the image if found
            bool: False if no image exists

        Raises:
            TypeError: If parameters are of incorrect type
            ValueError: If item_type is invalid or item_id is negative
        """
        if not isinstance(item_id, int):
            raise TypeError("item_id must be a positive integer.")
        if not isinstance(item_type, str):
            raise TypeError("item_type must be a string.")
        if item_id < 0:
            raise ValueError("item_id must be a positive integer")

        item_type = item_type.lower()
        if item_type not in VALID_TYPES:
            raise ValueError(
                f"Invalid item_type: {item_type}. "
                f"Must be one of the following strings: {', '.join(VALID_TYPES)}"
            )

        base_path = Path("static/img")
        result = list(base_path.joinpath(item_type).glob(f"{item_id}.*"))
        if result:
            url = "/" + str(result[0]).replace("databass/", "")
            return url
        return None
