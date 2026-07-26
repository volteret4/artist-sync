"""Cliente qBittorrent WebUI API — lista las rutas de contenido de los torrents."""
import os

import requests


class QbittorrentError(Exception):
    pass


def _session(host, user, password):
    s = requests.Session()
    resp = s.post(f"{host}/api/v2/auth/login", data={"username": user, "password": password}, timeout=10)
    if resp.status_code != 200 or resp.text.strip() != "Ok.":
        raise QbittorrentError(f"Login fallido en qBittorrent: {resp.status_code} {resp.text}")
    return s


def list_content_paths(host, user, password, category=""):
    """Devuelve la lista de rutas (carpeta o archivo) de cada torrent, ya
    resueltas en el filesystem local (la app corre en el mismo host que
    qBittorrent, asi que no hace falta remapear rutas)."""
    s = _session(host, user, password)
    params = {"category": category} if category else {}
    resp = s.get(f"{host}/api/v2/torrents/info", params=params, timeout=20)
    resp.raise_for_status()
    torrents = resp.json()

    paths = []
    for t in torrents:
        content_path = t.get("content_path")
        if not content_path:
            content_path = os.path.join(t.get("save_path", ""), t.get("name", ""))
        paths.append(content_path)
    return paths
