"""Cliente Subsonic API para Airsonic — lista artistas de la biblioteca."""
import hashlib
import secrets

import requests


class AirsonicError(Exception):
    pass


def _params(user, password, version, **extra):
    salt = secrets.token_hex(8)
    token = hashlib.md5((password + salt).encode()).hexdigest()
    return {"u": user, "t": token, "s": salt, "v": version, "c": "artist-sync", "f": "json", **extra}


def _call(base_url, user, password, version, endpoint, **kwargs):
    url = f"{base_url}/rest/{endpoint}.view"
    resp = requests.get(url, params=_params(user, password, version, **kwargs), timeout=15)
    resp.raise_for_status()
    data = resp.json().get("subsonic-response", {})
    if data.get("status") != "ok":
        err = data.get("error", {})
        raise AirsonicError(err.get("message", "Unknown Airsonic error"))
    return data


def list_artists(base_url, user, password, version="1.15.0"):
    """Devuelve [{name, id, albumCount}, ...] recorriendo getArtists.view."""
    data = _call(base_url, user, password, version, "getArtists")
    indexes = data.get("artists", {}).get("index", [])
    artists = []
    for index in indexes:
        for artist in index.get("artist", []):
            artists.append({
                "name": artist.get("name"),
                "id": artist.get("id"),
                "albumCount": artist.get("albumCount", 0),
            })
    return artists
