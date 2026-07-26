import os
from sops_env import load_sops_env

try:
    load_sops_env()
except FileNotFoundError:
    # En Docker las variables llegan ya descifradas vía docker-compose (scripts/up.sh)
    print("Aviso: no se encontró .encrypted.env; usando variables de entorno ya exportadas")

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "repeat_one.db")

FLASK_HOST = os.environ.get("FLASK_HOST", "0.0.0.0")
FLASK_PORT = int(os.environ.get("FLASK_PORT", 5000))

# Muspy — https://muspy.com, sitio "canonico" a seguir/dejar de seguir artistas
MUSPY_USERNAME = os.environ.get("MUSPY_USERNAME", "")
MUSPY_PASSWORD = os.environ.get("MUSPY_PASSWORD", "")

# Airsonic / Subsonic API
AIRSONIC_URL      = os.environ.get("AIRSONIC_URL", "http://localhost:4040")
AIRSONIC_USER     = os.environ.get("AIRSONIC_USER", "admin")
AIRSONIC_PASSWORD = os.environ.get("AIRSONIC_PASSWORD", "")

# Last.fm
LASTFM_API_KEY  = os.environ.get("LASTFM_API_KEY", "")
LASTFM_USERNAME = os.environ.get("LASTFM_USERNAME", "")
# Umbral minimo de scrobbles para traer un artista al escanear (evita paginar
# miles de artistas de una sola escucha); el filtro fino y ajustable en vivo
# se hace luego en la propia web.
LASTFM_MIN_PLAYCOUNT = int(os.environ.get("LASTFM_MIN_PLAYCOUNT", "5"))

# qBittorrent WebUI
QB_HOST = os.environ.get("QB_HOST", "http://localhost:8080")
QB_USER = os.environ.get("QB_USER", "admin")
QB_PASS = os.environ.get("QB_PASS", "")
# Categoria opcional de qBittorrent para limitar el escaneo (vacio = todos los torrents)
QB_CATEGORY = os.environ.get("QB_CATEGORY", "")
# Ruta FIJA dentro del contenedor donde qBittorrent guarda las descargas -- la
# ruta real del host se elige con QB_MUSIC_PATH en el .env raiz de tumtumpa
# (ver docker-compose.yml), igual que TRASVASE_COLLECTION_*_PATH en trasvase.
QB_MUSIC_PATH = os.environ.get("QB_MUSIC_PATH", "/mnt/music/qbittorrent")

# MusicBrainz (para resolver MBIDs al seguir un artista nuevo en Muspy)
MB_CONTACT_EMAIL = os.environ.get("MB_CONTACT_EMAIL", "admin@localhost")

SETTINGS_PASSWORD = os.environ.get("SETTINGS_PASSWORD", "")
