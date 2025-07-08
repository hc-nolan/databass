import requests
import datetime
import signal
from os import getenv
from pathlib import Path
from typing import Optional, Literal
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
                return datetime.datetime(year=1, month=1, day=1)
            case "end":
                return datetime.datetime(year=9999, month=12, day=31)
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
        else:
            raise ValueError(
                f"Unsupported file type (signature: {bytestr[:8].hex()}). Supported types: jpg, png"
            )

    @staticmethod
    def get_image_from_url(url: str, entity_type: str, entity_id: int | int):
        response = requests.get(
            url,
            headers={
                "User-Agent": f"databass/{VERSION} (https://github.com/chunned/databass)"
            },
        )
        if response:
            ext = Util.get_image_type_from_url(url)
            img_filepath = IMG_BASE_PATH + f"/{entity_type}/" + str(entity_id) + ext
            with open(img_filepath, "wb") as img_file:
                img_file.write(response.content)
            return img_filepath.replace("databass/", "")

    @staticmethod
    def get_caa_image(mbid: str) -> dict:
        from .musicbrainz import MusicBrainz

        """Get image from CoverArtArchive"""
        print(f"Attempting to fetch image from CoverArtArchive: {mbid}")

        timeout_duration = 5
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout_duration)

        img = MusicBrainz.get_image(mbid)
        if img is not None:
            print("CoverArtArchive image found")
            # CAA returns the raw image data
            img_type = Util.get_image_type_from_bytes(img)
        else:
            raise ValueError(
                "No image returned by CoverArtArchive, or an error was encountered when fetching the image."
            )
        return {"image": img, "type": img_type}

    @staticmethod
    def get_discogs_image(
        entity_type: str,
        release_name: Optional[str],
        artist_name: Optional[str],
        label_name: Optional[str],
    ) -> dict:
        from .discogs import Discogs

        match entity_type:
            case "release":
                img_url = Discogs.get_release_image_url(
                    name=release_name, artist=artist_name
                )
            case "artist":
                img_url = Discogs.get_artist_image_url(name=artist_name)
            case "label":
                img_url = Discogs.get_label_image_url(name=label_name)
            case _:
                return {}
        if img_url is None:
            return {}
        response = requests.get(
            img_url,
            headers={
                "Accept": "application/json",
                "User-Agent": f"databass/{VERSION} (https://github.com/hc-nolan/databass)",
            },
            timeout=60,
        )
        img = response.content
        img_type = Util.get_image_type_from_bytes(img)
        return {"image": img, "type": img_type}

    @staticmethod
    def get_image(
        entity_type: str,
        entity_id: str | int,
        mbid: Optional[str],
        release_name: Optional[str],
        artist_name: Optional[str],
        label_name: Optional[str],
        url: Optional[str],
    ):
        if entity_type not in VALID_TYPES:
            raise ValueError(f"Unexpected entity_type: {entity_type}")
        if url:
            return Util.get_image_from_url(
                entity_id=entity_id, entity_type=entity_type, url=url
            )
        Path(f"{IMG_BASE_PATH}/{entity_type}").mkdir(parents=True, exist_ok=True)

        if mbid is not None and entity_type == "release":
            try:
                caa_image = Util.get_caa_image(mbid=mbid)
                img = caa_image.get("image")
                img_type = caa_image.get("type")
            except Exception:
                print("Image not found on CAA, checking Discogs")
                Util.get_image(
                    url=None,
                    mbid=None,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    release_name=release_name,
                    artist_name=artist_name,
                    label_name=label_name,
                )
        else:
            print(f"Attempting to fetch {entity_type} image from Discogs")
            discogs_image = Util.get_discogs_image()
            img = discogs_image.get("image")
            img_type = discogs_image.get("type")

        if img is not None and img_type is not None:
            return Util.write_image(
                entity_type=entity_type,
                entity_id=entity_id,
                img_bytes=img,
                img_type=img_type,
            )

    @staticmethod
    def write_image(
        entity_id: int, entity_type: str, img_type: str, img_bytes: bytes
    ) -> str:
        file_name = str(entity_id) + img_type
        file_path = IMG_BASE_PATH + "/" + entity_type + "/" + file_name
        with open(file_path, "wb") as img_file:
            img_file.write(img_bytes)
        print(f"Image saved to {file_path}")
        return file_path.replace("databass/", "")

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
