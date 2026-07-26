"""Resuelve el MBID de un artista por nombre — necesario para poder seguirlo en
Muspy cuando viene de Airsonic/qBittorrent/Last.fm sin MBID conocido."""
import requests

SEARCH_URL = "https://musicbrainz.org/ws/2/artist/"


def search_mbid(artist_name, contact_email="admin@localhost"):
    headers = {"User-Agent": f"RepeatOne/1.0 ({contact_email})"}
    params = {"query": f"artist:{artist_name}", "fmt": "json", "limit": 1}
    resp = requests.get(SEARCH_URL, params=params, headers=headers, timeout=10)
    resp.raise_for_status()
    artists = resp.json().get("artists", [])
    if not artists:
        return None
    return artists[0].get("id")
