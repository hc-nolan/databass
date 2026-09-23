"""Small client for the public ListenBrainz user and statistics APIs."""

from __future__ import annotations

import os
from typing import Any

import requests


BASE_URL = "https://api.listenbrainz.org"


class ListenBrainz:
    """ListenBrainz HTTP client with normalized responses for the app."""

    @staticmethod
    def _headers() -> dict[str, str]:
        version = os.getenv("VERSION", "dev")
        headers = {"User-Agent": f"Databass/{version} (https://github.com/hc-nolan/databass)"}
        token = os.getenv("LISTENBRAINZ_TOKEN")
        if token:
            headers["Authorization"] = f"Token {token}"
        return headers

    @classmethod
    def _get(cls, path: str, params: dict[str, Any] | None = None) -> Any:
        response = requests.get(
            f"{BASE_URL}{path}", headers=cls._headers(), params=params, timeout=10
        )
        if response.status_code == 204:
            return None
        response.raise_for_status()
        return response.json()

    @classmethod
    def fetch_listens(
        cls,
        username: str,
        *,
        min_ts: int | None = None,
        max_ts: int | None = None,
        count: int = 1000,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"count": min(max(count, 1), 1000)}
        if min_ts is not None:
            params["min_ts"] = min_ts
        if max_ts is not None:
            params["max_ts"] = max_ts
        payload = cls._get(f"/1/user/{username}/listens", params) or {}
        return [cls.normalize_listen(item) for item in payload.get("payload", {}).get("listens", [])]

    @staticmethod
    def normalize_listen(item: dict[str, Any]) -> dict[str, Any]:
        metadata = item.get("track_metadata") or {}
        additional = metadata.get("additional_info") or {}
        # ListenBrainz payloads carry MBIDs either under `mbids` (submitted
        # directly) or `mbid_mapping` (matched server-side); accept both.
        mbid_data = metadata.get("mbids") or metadata.get("mbid_mapping") or {}
        artist_mbids = mbid_data.get("artist_mbids") or []
        return {
            "listened_at": int(item.get("listened_at", 0)),
            "artist_name": metadata.get("artist_name", ""),
            "artist_mbid": artist_mbids[0] if artist_mbids else None,
            "release_name": metadata.get("release_name", ""),
            "release_mbid": mbid_data.get("release_mbid"),
            "release_group_mbid": mbid_data.get("release_group_mbid"),
            "recording_mbid": additional.get("recording_mbid")
            or mbid_data.get("recording_mbid"),
            "track_name": metadata.get("track_name", ""),
        }

    @classmethod
    def fetch_fresh_releases(cls, username: str) -> list[dict[str, Any]]:
        payload = cls._get(f"/1/user/{username}/fresh_releases") or {}
        payload = payload.get("payload", payload)
        return payload.get("releases", []) if isinstance(payload, dict) else []

    @classmethod
    def fetch_stats(cls, username: str, range_: str = "all_time") -> dict[str, Any]:
        paths = {
            "artists": "artists",
            "releases": "releases",
            "release_groups": "release-groups",
            "recordings": "recordings",
            "listening_activity": "listening-activity",
            "daily_activity": "daily-activity",
            "artist_map": "artist-map",
        }
        result: dict[str, Any] = {"range": range_}
        for key, endpoint in paths.items():
            response = cls._get(f"/1/stats/user/{username}/{endpoint}", {"range": range_})
            payload = response.get("payload", response) if response else {}
            result[key] = payload
        count = cls._get(f"/1/user/{username}/listen-count") or {}
        result["listen_count"] = (count.get("payload") or {}).get("count", 0)
        return result
