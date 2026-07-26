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


def _raw_call(base_url, user, password, version, endpoint, **kwargs):
    url = f"{base_url}/rest/{endpoint}.view"
    resp = requests.get(url, params=_params(user, password, version, **kwargs), timeout=15)
    resp.raise_for_status()
    return resp.json().get("subsonic-response", {})


def _call(base_url, user, password, version, endpoint, **kwargs):
    """Llama al endpoint con `version`. Si el servidor responde error 30
    ("Server must upgrade" -- la version que pedimos es mas nueva de lo que
    soporta) reintenta UNA vez con la version que el propio servidor reporta
    en su respuesta, en vez de obligar a adivinar AIRSONIC_API_VERSION a mano."""
    data = _raw_call(base_url, user, password, version, endpoint, **kwargs)
    if data.get("status") != "ok":
        err = data.get("error", {})
        if err.get("code") == 30:
            server_version = data.get("version")
            if server_version and server_version != version:
                print(f"  [airsonic] version {version} rechazada, reintentando con {server_version} "
                      f"(guarda AIRSONIC_API_VERSION={server_version} para saltarte este reintento)")
                data = _raw_call(base_url, user, password, server_version, endpoint, **kwargs)
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
