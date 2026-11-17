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
AIRSONIC_API_VERSION=1.15.0   # baja el numero si tu Airsonic es viejo y da
                               # "Incompatible Airsonic REST protocol version"

# Last.fm — si esta app corre dentro de tumtumpa y el volumen lastfm_data
# esta montado en /data (servicio lastfm-scrobbles, ya sincroniza Last.fm +
# ListenBrainz deduplicados a diario), scan.py lo usa directamente y estas
# dos variables no hacen falta. Son solo el fallback para correr esta app
# suelta, fuera de tumtumpa.
LASTFM_API_KEY=...
LASTFM_USERNAME=...
LASTFM_MIN_PLAYCOUNT=5   # umbral al escanear; el filtro fino se ajusta en la web
LASTFM_SCROBBLES_DB=/data/lastfm_stats.db   # ruta del espejo compartido, si existe

# qBittorrent WebUI
# "localhost" solo vale si esta app corre FUERA de Docker en el mismo host
# que qBittorrent. Si corre dentro de un contenedor (tumtumpa) y qBittorrent
# no esta en el mismo docker-compose, "localhost" apunta al propio
# contenedor -> usa host.docker.internal (el servicio ya declara
# extra_hosts: host-gateway) o la IP LAN del host.
QB_HOST=host.docker.internal
QB_PORT=8080
QB_USER=admin
QB_PASS=...
QB_CATEGORY=             # opcional, vacío = todos los torrents
# Si qBittorrent corre directamente en este mismo host/filesystem, deja esto
# vacío: los tags FLAC se leen tal cual por la ruta que reporta su API.
# Si qBittorrent corre en SU PROPIO contenedor, su API reporta rutas de SU
# contenedor (ej. "/downloads"), no de este — QB_REMOTE_PATH le dice a
# flac_scan.py que reescriba ese prefijo por la ruta local (fija,
# /mnt/music/qbittorrent en Docker; ver docker-compose.yml y
# ARTIST_SYNC_QB_MUSIC_PATH para la ruta real del host).
QB_REMOTE_PATH=          # ej. /downloads — vacío si qBittorrent no está en su propio contenedor

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
- **Last.fm/ListenBrainz**: si `LASTFM_SCROBBLES_DB` existe (montado desde el
  volumen `lastfm_data` de tumtumpa), `clients/lastfm_mirror_client.py` lee
  directamente esa base de datos compartida en vez de llamar a la API de
  Last.fm — más rápido, sin límite de paginación, e incluye escuchas que solo
  vengan de ListenBrainz (el espejo ya las deduplica entre sí). Si no existe,
  cae al cliente de API de siempre (`LASTFM_API_KEY`/`LASTFM_USERNAME`).

## Instalación con Docker Compose

```bash
cp .env.example .env
```

Rellena `.env` (credenciales y carpetas de tu equipo) y arranca:

```bash
docker compose up -d --build
```

Los datos que genera (bases, cachés) se quedan en esta misma carpeta, fuera de git.

## Actualizaciones automáticas

El `docker-compose.yml` trae su propia [Ofelia](https://github.com/mcuadros/ofelia), que lanza dentro del contenedor los mismos trabajos y a las mismas horas que en REPEAT-ONE (formato con segundos: `seg min hora día mes día-semana`, hora de `TZ`, por defecto Europe/Madrid):

| Trabajo | Cuándo | Qué lanza |
|---|---|---|
| `artist-sync-scan` | `0 15 0 * * *` | `python3 scan.py` |

Para cambiar una hora, edita su etiqueta `ofelia.job-exec.<trabajo>.schedule` en `docker-compose.yml` y vuelve a hacer `docker compose up -d`. Para lanzarlo a mano: `docker compose exec <servicio> <orden>`. Para no tener actualizaciones automáticas: `docker compose stop ofelia`.

Esta Ofelia solo ve los contenedores de este repo (etiqueta `repeat-one.ofelia`), así que puedes tener varios módulos instalados por separado sin que se pisen. Necesita el socket de Docker en solo lectura.
