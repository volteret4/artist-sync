# artist-sync

Comparador interactivo de artistas entre **Muspy** (seguidos), **Airsonic**
(biblioteca local), **qBittorrent** (descargas, vía tags FLAC) y **Last.fm**
(escuchados). Pensado para revisar de un vistazo qué artistas tienes en cada
sitio y decidir a cuáles seguir o dejar de seguir en Muspy — que es la fuente
que luego consumen tus bots.

## Setup

```bash
pip install -r requirements.txt
```

Variables de entorno (via `.env` local, o `.encrypted.env` + sops si se
integra en tumtumpa):

```bash
# Muspy — sitio "canónico" a seguir/dejar de seguir
MUSPY_USERNAME=...
MUSPY_PASSWORD=...

# Airsonic / Subsonic
AIRSONIC_URL=http://localhost:4040
AIRSONIC_USER=admin
AIRSONIC_PASSWORD=...

# Last.fm
LASTFM_API_KEY=...
LASTFM_USERNAME=...
LASTFM_MIN_PLAYCOUNT=5   # umbral al escanear; el filtro fino se ajusta en la web

# qBittorrent WebUI
QB_HOST=localhost
QB_PORT=8080
QB_USER=admin
QB_PASS=...
QB_CATEGORY=             # opcional, vacío = todos los torrents
# No hay QB_MUSIC_PATH aquí: los tags FLAC se leen por la ruta que reporta la
# propia API de qBittorrent. En Docker (tumtumpa) eso se resuelve montando
# ARTIST_SYNC_QB_MUSIC_PATH 1:1 (mismo path dentro y fuera del contenedor) —
# ver docker-compose.yml. En local basta con correr esta app en el mismo
# host que qBittorrent.

# MusicBrainz (para resolver MBIDs de artistas nuevos al seguir en Muspy)
MB_EMAIL=tu@email.com

SETTINGS_PASSWORD=...     # protege el panel ⚙ de la web
```

Cualquier fuente sin credenciales se omite en el escaneo sin dar error.

## Uso

```bash
python scan.py            # sincroniza las 4 fuentes en artist_sync.db
python scan.py --only muspy,lastfm   # solo algunas

python app.py             # sirve la web en 0.0.0.0:5000
```

También puede lanzarse la sincronización desde la propia web (botón
"↻ Sincronizar"), que ejecuta `scan.py` como subproceso.

## Cómo funciona

- **`scan.py`** llama a cada cliente en `clients/`, normaliza el nombre de
  cada artista (minúsculas, sin acentos/puntuación, sin "The " inicial) y
  sincroniza la tabla `presence` de `artist_sync.db`: un artista puede tener
  una fila por fuente en la que aparece.
- **qBittorrent** no tiene metadata de "artista" propia: se listan las rutas
  de contenido de cada torrent vía su API y se leen los tags `albumartist`/
  `artist` de los FLAC que haya dentro (misma lógica que `trasvase/scan.py`).
  Requiere que esta app corra en el mismo host que qBittorrent (acceso directo
  al filesystem).
- **`app.py`** sirve la tabla comparativa y expone `/api/muspy/follow` y
  `/api/muspy/unfollow`: si el artista no tiene MBID conocido (por venir de
  Airsonic/qBittorrent/Last.fm sin uno), se resuelve por nombre vía
  MusicBrainz antes de llamar a la API de Muspy.
- El umbral de scrobbles de Last.fm es ajustable en vivo en la web (slider)
  sin necesidad de re-escanear — se trae todo por encima de
  `LASTFM_MIN_PLAYCOUNT` y se filtra en el cliente.
