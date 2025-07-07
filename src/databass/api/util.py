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


class TimeoutException(Exception):
    pass


def timeout_handler(signum, frame):
    raise TimeoutException("Request timed out")


# Collection of generic utility functions used by other parts of the app
class Util:
    @staticmethod
    def to_date(
        begin_or_end: Literal["begin", "end"] | None, date_str: str | None
    ) -> datetime.date:
        """
        Convert a date string or begin/end indicator to a datetime.date object.

        Args:
            begin_or_end (Literal['begin', 'end'] | None): Indicates whether to return the earliest or latest possible date.
            date_str (str | None): A date string in the format YYYY, YYYY-MM, or YYYY-MM-DD.

        Returns:
            datetime.date: The corresponding date object.

        Raises:
            ValueError: If `begin_or_end` is not 'begin' or 'end', or if `date_str` is in an unexpected format.
        """
        date = None
        if not date_str:
            if not begin_or_end:
                raise ValueError(
                    "Must be used with either begin_or_end or date_str, or both"
                )
            # No date in search results, return max/min date
            if begin_or_end not in VALID_DATE_TYPES:
                raise ValueError(f"Invalid begin_or_end value: {begin_or_end}")
            elif begin_or_end == "begin":
                date = datetime.datetime(year=1, month=1, day=1)
            elif begin_or_end == "end":
                date = datetime.datetime(year=9999, month=12, day=31)

        # Date found in search results
        elif len(date_str) == 4:
            date = datetime.datetime.strptime(date_str, YEAR_FORMAT)
        elif len(date_str) == 7:
            date = datetime.datetime.strptime(date_str, MONTH_FORMAT)
        elif len(date_str) == 10:
            date = datetime.datetime.strptime(date_str, DAY_FORMAT)

        if date is not None:
            return date.date()
        raise ValueError(f"Unexpected date string format: {date_str}")

    @staticmethod
    def today() -> str:
        """Returns current day formatted as YYYY-MM-DD string"""
        return datetime.datetime.today().strftime("%Y-%m-%d")

    @staticmethod
    def get_image_type_from_url(url: str) -> str:
        """
        Determine the image file extension from the URL of an image file.

        This function extracts the image format from a URL, supporting common web image formats
        and handling various URL patterns. The extension can appear anywhere in the URL path.

        Args:
            url (str): The URL of an image file.

        Returns:
            str: The file extension of the image (e.g. '.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp', '.tiff').

        Raises:
            ValueError: If no supported image extension is found in the URL.
        """
        # List of supported image extensions
        extensions = {
            ".jpg",
            ".jpeg",
            ".png",
            ".webp",
        }

        url = url.lower()
        for ext in extensions:
            if ext in url:
                return ext

        raise ValueError(f"ERROR: No supported image type found in URL: {url}")

    @staticmethod
    def get_image_type_from_bytes(bytestr: bytes) -> str:
        """
        Determine the image file extension from the byte representation of an image file.

        This function acts as an image format filter, returning the appropriate file extension
        based on the first few bytes of the input byte string.

        Args:
            bytestr (bytes): The byte representation of an image file.

        Returns:
            str: The file extension of the image, either '.jpg' or '.png'.

        Raises:
            ValueError: If the input byte string does not match the expected header for a
                supported image type (JPEG or PNG).
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
    def get_image(
        item_type: str,
        item_id: str | int,
        mbid: str = None,
        release_name: str = None,
        artist_name: str = None,
        label_name: str = None,
        url: str = None,
    ):
        # TODO: refactor
        if url:
            # if we are provided the url, just grab it, don't check APIs
            import requests

            response = requests.get(
                url,
                headers={
                    "User-Agent": f"databass/{VERSION} (https://github.com/chunned/databass)"
                },
            )
            if response:
                ext = Util.get_image_type_from_url(url)
                base_path = "./databass/static/img"
                img_filepath = base_path + f"/{item_type}/" + str(item_id) + ext
                with open(img_filepath, "wb") as img_file:
                    img_file.write(response.content)
                return img_filepath.replace("databass/", "")
        img = img_type = img_url = None
        base_path = "./databass/static/img"
        subdir = item_type
        try:
            # Create image subdirectory
            Path(f"{base_path}/{subdir}").mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f"Encountered exception while creating directory: {e}")

        if item_type not in ["release", "artist", "label"]:
            raise Exception(f"Unexpected item_type: {item_type}")

        from .discogs import Discogs

        if mbid is not None and item_type == "release":
            print(
                f"Item is a release and MBID is populated; attempting to fetch image from CoverArtArchive: {mbid}"
            )
            from .musicbrainz import MusicBrainz

            try:
                # Number of seconds to wait before raising a TimeoutException
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
            except Exception:
                print("Image not found on CAA, checking Discogs")
                try:
                    img_url = Discogs.get_release_image_url(
                        name=release_name, artist=artist_name
                    )
                except Exception as e:
                    print(f"Got an exception from Discogs: {e}")
        else:
            print(f"Attempting to fetch {item_type} image from Discogs")
            if item_type == "artist":
                img_url = Discogs.get_artist_image_url(name=artist_name)
            elif item_type == "label":
                img_url = Discogs.get_label_image_url(name=label_name)
        response = ""
        if img_url is not None and img_url is not False:
            import requests

            print(f"Discogs image URL: {img_url}")
            response = requests.get(
                img_url,
                headers={
                    "Accept": "application/json",
                    "User-Agent": f"databass/{VERSION} (https://github.com/chunned/databass)",
                },
                timeout=60,
            )
            img = response.content
            img_type = Util.get_image_type_from_bytes(img)

        if img is not None and img_type is not None:
            file_name = str(item_id) + img_type
            file_path = base_path + "/" + subdir + "/" + file_name
            with open(file_path, "wb") as img_file:
                img_file.write(img)
            print(f"Image saved to {file_path}")
            return file_path.replace("databass/", "")
        print(f"Discogs response: {response}")

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
