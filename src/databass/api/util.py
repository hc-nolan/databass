import datetime
import urllib.parse
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

# The only image hosts the app is allowed to download from. Restricting
# `get_image_from_url` here (rather than at individual call sites) keeps every
# flow — the /api/submit art choice, release editing, etc. — from being able
# to fetch an arbitrary URL, which would otherwise write internal bytes to a
# publicly served path (and potentially exfil them). CoverArtArchive stores
# its full-size images on archive.org and serves them via redirect.
KNOWN_IMAGE_HOSTS = frozenset(
    ["coverartarchive.org", "i.discogs.com", "img.discogs.com", "archive.org"]
)
IMAGE_REDIRECT_LIMIT = 5


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
        if bytestr.startswith(b"RIFF") and bytestr[8:12] == b"WEBP":
            return ".webp"
        raise ValueError(
            f"Unsupported file type (signature: {bytestr[:8].hex()}). Supported types: jpg, png, webp"
        )

    @staticmethod
    def _is_known_image_host(hostname: Optional[str]) -> bool:
        """Whether a hostname matches one of the app's known image hosts."""
        hostname = (hostname or "").lower()
        return any(
            hostname == base or hostname.endswith(f".{base}")
            for base in KNOWN_IMAGE_HOSTS
        )

    @staticmethod
    def get_image_from_url(url: str, entity_type: Literal["release", "artist", "label"]):
        if entity_type not in VALID_TYPES:
            raise ValueError(
                f"Invalid entity_type: {entity_type}. "
                f"Must be one of the following strings: {', '.join(VALID_TYPES)}"
            )

        # Fetch with redirects followed one hop at a time so the final URL is
        # always validated against the known-image-host allowlist. This keeps a
        # crafted or compromised image URL from pointing the download at an
        # arbitrary (e.g. internal) address.
        final_url = url
        redirects = 0
        while redirects <= IMAGE_REDIRECT_LIMIT:
            parsed = urllib.parse.urlparse(final_url)
            if parsed.scheme != "https" or not Util._is_known_image_host(
                parsed.hostname
            ):
                raise ValueError(
                    f"Image URL must be https and hosted by a known provider: {final_url}"
                )
            response = requests.get(
                final_url,
                headers={
                    "User-Agent": f"databass/{VERSION} "
                    "(https://github.com/chunned/databass)"
                },
                timeout=30,
                allow_redirects=False,
            )
            if response.status_code not in (301, 302, 303, 307, 308):
                break
            location = response.headers.get("Location")
            if not location:
                raise ValueError("Image URL redirected without a Location header")
            final_url = urllib.parse.urljoin(final_url, location)
            redirects += 1
        else:
            raise ValueError("Too many redirects while fetching image URL")

        if response:
            Path(f"{IMG_BASE_PATH}/{entity_type}").mkdir(parents=True, exist_ok=True)
            # Some image hosts (e.g. CoverArtArchive) serve images at URLs
            # without a file extension, so fall back to sniffing the bytes.
            try:
                ext = Util.get_image_type_from_url(final_url)
            except ValueError:
                ext = Util.get_image_type_from_bytes(response.content)
            img_filepath = IMG_BASE_PATH + f"/{entity_type}/" + str(uuid4()) + ext
            with open(img_filepath, "wb") as img_file:
                img_file.write(response.content)
            return img_filepath.replace("databass/", "")
