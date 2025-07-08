"""
Implements Discogs API-related functions via Discogs class methods
"""

from os import getenv
from typing import Dict, Optional, Any
from urllib.parse import urljoin, urlencode
import time
import re
import requests
from dotenv import load_dotenv


load_dotenv()
DISCOGS_KEY = getenv("DISCOGS_KEY")
DISCOGS_SECRET = getenv("DISCOGS_SECRET")
VERSION = getenv("VERSION")
RATE_LIMIT_THRESHOLD: float = 1.1
DIMENSIONS_PATTERN = r"/h:\d+/w:\d+/"
HEIGHT_PATTERN = r"/h:(\d+)/.*"
WIDTH_PATTERN = r".*/w:(\d+)/.*"
DISAMBIG_PATTERN = r"\s*\(\d+\)\s*$"


class Discogs:
    """
    Discogs API client class
    Attributes:
        url (str): The base URL for the Discogs API
        headers (dict): The headers to use for the requests
        remaining_requests (int): The number of remaining requests
    """

    url: str = "https://api.discogs.com"
    headers: Dict[str, str] = {
        "User-Agent": f"Databass/{VERSION} +https://github.com/chunned/databass",
        "Authorization": f"Discogs key={DISCOGS_KEY}, secret={DISCOGS_SECRET}",
    }
    remaining_requests: Optional[int] = None

    @classmethod
    def update_rate_limit(cls, response: requests.Response):
        """
        Updates rate limit remaining requests based on response header
        """
        limit = response.headers.get("x-discogs-ratelimit-remaining")
        cls.remaining_requests = int(limit)

    @classmethod
    def is_throttled(cls) -> bool:
        """
        Checks if we have enough remaining requests to make new request per rate limiting guidelines
        If remaining_requests is None, no requests have been sent yet and thus we are not throttled
        If we have 1.1 or fewer remaining requests, we are throttled
        """
        return (
            cls.remaining_requests is not None
            and cls.remaining_requests <= RATE_LIMIT_THRESHOLD
        )

    @staticmethod
    def request(endpoint: str) -> Dict[str, Any]:
        """
        Sends request to an endpoint then updates rate limit count
        Returns json if response code is 200
        """
        resp = requests.get(
            urljoin(Discogs.url, endpoint), headers=Discogs.headers, timeout=60
        )
        Discogs.update_rate_limit(resp)
        if Discogs.is_throttled() is True:
            time.sleep(5)  # Sleep for 5s to avoid exceeding rate limit
        if resp.status_code == 200:
            return resp.json()

        raise requests.exceptions.RequestException(f"Status code != 200: {resp}")

    @staticmethod
    def get_item_id(name: str, item_type: str, artist: str = None) -> Optional[str]:
        """
        Gets the ID for the specified item type and name.

        Args:
            name (str): The name of the item to search for.
            item_type (str): The type of item to search for, e.g. 'release'.
            artist (str, optional): The artist name to filter the search by.

        Returns:
            str or None: The ID of the item if found, None otherwise.
        """
        if not name or not item_type:
            return None
        print(f"Getting ID for {item_type}: {name}")
        if item_type == "release":
            query_params = {"q": artist, "type": "release", "release_title": name}
        else:
            query_params = {"q": name, "type": item_type}
        encoded_params = urlencode(query_params)
        endpoint = f"/database/search?{encoded_params}"
        print(f"Search endpoint: {endpoint}")

        try:
            res = Discogs.request(endpoint)
        except requests.RequestException:
            return None

        item_id = None
        results = res.get("results")
        for result in results:
            result_title = result.get("title")
            if result_title is None:
                continue
            # remove disambiguation chars
            # e.g. "Future (4)" -> "Future"
            result_title = re.sub(DISAMBIG_PATTERN, "", result_title)
            if result_title == name:
                format = result.get("format")
                if "Blu-ray" in format:
                    continue
                else:
                    item_id = result.get("id")
                    break

        if item_id:
            print(f"ID for {item_type} {name}: {item_id}")
            return item_id

        return None

    @staticmethod
    def get_item_image_url(endpoint: str) -> Optional[str]:
        """
        Attempts to find the first square image URL from the provided Discogs API endpoint.

        Args:
            endpoint (str): The Discogs API endpoint to fetch image data from.

        Returns:
            Optional[str]:  The URL of the first square image found,
                            or None if no square images are found.
        """

        try:
            response = Discogs.request(endpoint)
            results = response["results"]
        except (TypeError, requests.RequestException):
            return None
        for item in results:
            image_url = item.get("cover_image")
            try:
                # Attempt to determine image dimensions from the URL
                # Should contain a string like /h:500/w:500/ to denote the height and width
                # Below regex first extracts that entire substring;
                # the next extract the height and width themselves

                # IN: https://........../h:250/w:500/......  OUT: "/h:250/w:500"
                dimensions = re.findall(DIMENSIONS_PATTERN, image_url)[0]
                # IN: "/h:250/w:500"                         OUT: 250
                height = int(re.sub(HEIGHT_PATTERN, r"\1", dimensions))
                # IN: "/h:250/w:500"                         OUT: 500
                width = int(re.sub(WIDTH_PATTERN, r"\1", dimensions))

                # Make sure image is square; if not, try next result
                if height == width:
                    return image_url
            except Exception:
                continue
        print("INFO: No square images found.")

    @staticmethod
    def find_image(search_results: Dict[str, Any]) -> Optional[str]:
        """
        Finds the first square image from the provided search results.

        Args:
            search_results (requests.Response): The search results containing image data.

        Returns:
            Optional[str]: The URL of the first square image found, or None if no square images are found.
        """
        if (
            not search_results
            or "images" not in search_results.keys()
            or not isinstance(search_results["images"], list)
        ):
            return None
        try:
            print(f"{len(search_results['images'])} candidates found")
            for image in search_results["images"]:
                image_url = image["uri"]
                try:
                    height = image["height"]
                    width = image["width"]
                    # Make sure image is square; if not, try next result
                    if height == width:
                        print(f"Square image found: {image_url}")
                        return image_url
                    print(f"Non-square image: H:{height}/W:{width} | {image_url}")
                except KeyError:
                    pass
            try:
                print("No square images found. Returning first image result")
                return search_results["images"][0]["uri"]
            except IndexError:
                return None
        except KeyError:
            print("No images found in search results.")
            return None

    @staticmethod
    def get_release_image_url(name: str, artist: str) -> Optional[str]:
        """
        Retrieves the URL of the image associated with the specified Discogs release.

        Args:
            name (str): The name of the Discogs release to search for.
            artist (str): The name of the Discogs artist associated with the release.

        Returns:
            Optional[str]:  The URL of the image associated with the release,
                            or None if no image is found or an error occurs.
        """
        if (
            not name
            or not isinstance(name, str)
            or not artist
            or not isinstance(artist, str)
        ):
            return None

        release_id = Discogs.get_item_id(name=name, artist=artist, item_type="release")
        if release_id:
            print("Got release ID. Checking for images...")
            endpoint = f"/releases/{release_id}"
            try:
                res = Discogs.request(endpoint)
                img = Discogs.find_image(res)
                return img if img else None
            except requests.exceptions.RequestException:
                return None
        else:
            print("No search results found.")
            return None

    @staticmethod
    def get_artist_image_url(name: str) -> Optional[str]:
        """
        Retrieves the URL of the image associated with the specified Discogs artist.

        Args:
            name (str): The name of the Discogs artist to search for.

        Returns:
            Optional[str]: The URL of the image associated with the artist,
                            or None if no image is found or an error occurs.
        """
        if not name or not isinstance(name, str):
            return None
        artist_id = Discogs.get_item_id(name=name, item_type="artist")
        if artist_id:
            endpoint = f"/artists/{artist_id}"
            try:
                res = Discogs.request(endpoint)
                return Discogs.find_image(res)
            except requests.exceptions.RequestException:
                return None
        else:
            print("No search results found.")
            return None

    @staticmethod
    def get_label_image_url(name: str) -> Optional[str]:
        """
        Retrieves the URL of the image associated with the specified Discogs label.

        Args:
            name (str): The name of the Discogs label to search for.

        Returns:
            Optional[str]: The URL of the image associated with the label,
                            or None if no image is found or an error occurs.
        """
        if not name or not isinstance(name, str):
            return None
        label_id = Discogs.get_item_id(name=name, item_type="label")
        if label_id:
            endpoint = f"/labels/{label_id}"
            try:
                res = Discogs.request(endpoint)
                return Discogs.find_image(res)
            except requests.exceptions.RequestException:
                return None
        else:
            print("No search results found.")
            return None
