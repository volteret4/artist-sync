import os
from sops_env import load_sops_env

try:
    load_sops_env()
except FileNotFoundError:
    # En Docker las variables llegan ya descifradas vía docker-compose (scripts/up.sh)
    print("Aviso: no se encontró .encrypted.env; usando variables de entorno ya exportadas")

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "artist_sync.db")

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

# qBittorrent WebUI — mismo QB_HOST/QB_PORT/QB_USER/QB_PASS que dieta_sonora,
# para que tumtumpa/scripts/up.sh reutilice las credenciales ya introducidas
# ahi en vez de volver a preguntarlas.
QB_HOST = os.environ.get("QB_HOST", "localhost")
QB_PORT = os.environ.get("QB_PORT", "8080")
QB_USER = os.environ.get("QB_USER", "admin")
QB_PASS = os.environ.get("QB_PASS", "")
# Categoria opcional de qBittorrent para limitar el escaneo (vacio = todos los torrents)
QB_CATEGORY = os.environ.get("QB_CATEGORY", "")
# No hay una variable QB_MUSIC_PATH aqui a proposito: flac_scan.py usa tal
# cual las rutas que devuelve la propia API de qBittorrent (content_path /
# save_path+name), no una ruta fija propia. En Docker, eso exige montar el
# mismo path absoluto que ve qBittorrent dentro de este contenedor -- lo
# gestiona ARTIST_SYNC_QB_MUSIC_PATH en el .env raiz de tumtumpa (ver
# docker-compose.yml), montado 1:1 (sin remapear), no como
# TRASVASE_COLLECTION_*_PATH -> COLLECTION_*_PATH en trasvase.

# MusicBrainz (para resolver MBIDs al seguir un artista nuevo en Muspy) —
# mismo nombre MB_EMAIL que dieta_sonora_stats, para reutilizar el valor.
MB_EMAIL = os.environ.get("MB_EMAIL", "admin@localhost")

SETTINGS_PASSWORD = os.environ.get("SETTINGS_PASSWORD", "")
