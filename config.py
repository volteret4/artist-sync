import os
from plain_env import read_env_file
from sops_env import load_sops_env

try:
    load_sops_env()
except FileNotFoundError:
    # En Docker las variables llegan ya descifradas vía docker-compose (scripts/up.sh)
    print("Aviso: no se encontró .encrypted.env; usando variables de entorno ya exportadas")

# Sobrescribe con el .env plano que escribe el panel ⚙ (app.py) -- Docker solo
# inyecta env_file al CREAR el contenedor, así que sin esto un cambio guardado
# en el panel se queda sin efecto hasta recrear el contenedor. scan.py se
# relanza como subproceso nuevo en cada sync, así que esto basta para que
# recoja cambios de configuración sin rebuild ni restart.
os.environ.update(read_env_file(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")))

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "artist_sync.db")

FLASK_HOST = os.environ.get("FLASK_HOST", "0.0.0.0")
FLASK_PORT = int(os.environ.get("FLASK_PORT", 5000))

# Muspy — https://muspy.com, sitio "canonico" a seguir/dejar de seguir artistas
MUSPY_USERNAME = os.environ.get("MUSPY_USERNAME", "")
MUSPY_PASSWORD = os.environ.get("MUSPY_PASSWORD", "")

# Airsonic / Subsonic API — mismo nombre AIRSONIC_API_VERSION que
# dieta_sonora_stats, para reutilizar el valor via up.sh (algunos Airsonic
# rechazan versiones de protocolo mas nuevas que la suya con "Incompatible
# Airsonic REST protocol version").
AIRSONIC_URL          = os.environ.get("AIRSONIC_URL", "http://localhost:4040")
AIRSONIC_USER         = os.environ.get("AIRSONIC_USER", "admin")
AIRSONIC_PASSWORD     = os.environ.get("AIRSONIC_PASSWORD", "")
AIRSONIC_API_VERSION  = os.environ.get("AIRSONIC_API_VERSION", "1.15.0")

# Last.fm — si el espejo compartido de tumtumpa esta disponible (servicio
# lastfm-scrobbles, volumen lastfm_data montado en /data), scan.py lo usa en
# vez de llamar a la API: mas rapido, sin limite de paginacion, e incluye
# escuchas de ListenBrainz que la API de Last.fm no ve. LASTFM_API_KEY/
# LASTFM_USERNAME quedan como fallback para cuando no hay espejo (ej. esta
# app corriendo suelta, fuera de tumtumpa).
LASTFM_SCROBBLES_DB = os.environ.get("LASTFM_SCROBBLES_DB", "/data/lastfm_stats.db")
LASTFM_API_KEY  = os.environ.get("LASTFM_API_KEY", "")
LASTFM_USERNAME = os.environ.get("LASTFM_USERNAME", "")
# Umbral minimo de scrobbles para traer un artista al escanear (evita paginar
# miles de artistas de una sola escucha si se usa la API directa); el filtro
# fino y ajustable en vivo se hace luego en la propia web.
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
# Ruta FIJA dentro del contenedor donde esta app tiene montada la carpeta de
# descargas -- igual que COLLECTION_1_PATH en trasvase, la ruta real del host
# se elige con ARTIST_SYNC_QB_MUSIC_PATH en el .env raiz de tumtumpa (ver
# docker-compose.yml).
QB_LOCAL_PATH = "/mnt/music/qbittorrent"
# Si qBittorrent corre en SU PROPIO contenedor, las rutas que devuelve su API
# (content_path/save_path) son las que VE ESE contenedor (p.ej. "/downloads"),
# no las de este. QB_REMOTE_PATH es ese prefijo tal cual lo reporta la API de
# qBittorrent; flac_scan.py lo reemplaza por QB_LOCAL_PATH antes de leer
# nada. Vacio (por defecto) = no reescribe, asume que qBittorrent corre
# directamente en este mismo host/filesystem (sin contenedor propio).
QB_REMOTE_PATH = os.environ.get("QB_REMOTE_PATH", "")

# MusicBrainz (para resolver MBIDs al seguir un artista nuevo en Muspy) —
# mismo nombre MB_EMAIL que dieta_sonora_stats, para reutilizar el valor.
MB_EMAIL = os.environ.get("MB_EMAIL", "admin@localhost")

SETTINGS_PASSWORD = os.environ.get("SETTINGS_PASSWORD", "")
