"""
Image-fetching orchestration: pulls cover art from CoverArtArchive/Discogs
and writes it to disk. Kept separate from util.py so that Util can stay a
leaf module with no dependency on MusicBrainz/Discogs.
"""

import signal
from pathlib import Path
from typing import Literal, Optional
from uuid import uuid4
import requests
from .discogs import Discogs
from .musicbrainz import MusicBrainz
from .util import (
    IMG_BASE_PATH,
    VALID_TYPES,
    VERSION,
    Util,
    timeout_handler,
)


def get_caa_image(mbid: str) -> dict:
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
            "No image returned by CoverArtArchive, or an error was encountered"
            " when fetching the image."
        )
    return {"image": img, "type": img_type}


valid_entity_types = Literal["release", "artist", "label"]


def get_discogs_image(
    entity_type: valid_entity_types,
    release_name: Optional[str],
    artist_name: Optional[str],
    label_name: Optional[str],
) -> dict:
    """Fetch an image from Discogs"""
    img_url = Discogs.resolve_image_url(
        entity_type, release_name, artist_name, label_name
    )
    print(f"Image URL: {img_url}")
    if img_url is None:
        return {}
    print("Attempting to fetch...")
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
    print("Discogs image fetch successful")
    return {"image": img, "type": img_type}


def write_image(
    entity_type: valid_entity_types, img_type: str, img_bytes: bytes
) -> str:
    """Writes `img_bytes` to `entity_type`'s image directory as an `img_type` file"""
    file_name = str(uuid4()) + img_type
    file_path = IMG_BASE_PATH + "/" + entity_type + "/" + file_name
    with open(file_path, "wb") as img_file:
        img_file.write(img_bytes)
    print(f"Image saved to {file_path}")
    return file_path.replace("databass/", "")


def fetch_image(
    entity_type: valid_entity_types,
    mbid: Optional[str],
    release_name: Optional[str],
    artist_name: Optional[str],
    label_name: Optional[str],
) -> Optional[str]:
    """Fetch a cover/entity image from CoverArtArchive (releases only) or
    Discogs, and write it to disk. For images already at a URL, use
    Util.get_image_from_url instead."""
    if entity_type not in VALID_TYPES:
        raise ValueError(f"Unexpected entity_type: {entity_type}")
    Path(f"{IMG_BASE_PATH}/{entity_type}").mkdir(parents=True, exist_ok=True)

    img = img_type = None

    fetched_from_caa = False
    if mbid is not None and entity_type == "release":
        try:
            caa_image = get_caa_image(mbid=mbid)
            img = caa_image.get("image")
            img_type = caa_image.get("type")
            fetched_from_caa = True
        except Exception:
            print("Image not found on CAA, checking Discogs")

    if not fetched_from_caa:
        print(f"Attempting to fetch {entity_type} image from Discogs")
        try:
            discogs_image = get_discogs_image(
                entity_type=entity_type,
                release_name=release_name,
                artist_name=artist_name,
                label_name=label_name,
            )
        except Exception as err:
            print(f"WARNING: Could not fetch {entity_type} image from Discogs: {err}")
            return None
        img = discogs_image.get("image")
        img_type = discogs_image.get("type")

    if img is not None and img_type is not None:
        return write_image(
            entity_type=entity_type,
            img_bytes=img,
            img_type=img_type,
        )
    return None
