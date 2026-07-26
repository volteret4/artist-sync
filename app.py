#!/usr/bin/env python3
"""
Flask app — comparador de artistas entre Muspy, Airsonic, qBittorrent y Last.fm.
Muspy es la fuente "canonica" a seguir/dejar de seguir; el resto son solo lectura.
"""
import os
import sqlite3
import subprocess

from flask import Flask, jsonify, render_template, request

from clients import muspy_client
from clients.musicbrainz_client import search_mbid
from config import DB_PATH, MB_EMAIL, MUSPY_PASSWORD, MUSPY_USERNAME
from plain_env import read_env_file, write_env_file
from scan import init_db

app = Flask(__name__)

# ── Panel de configuracion (⚙) — mismo patron que trasvase/dieta_sonora ────
SETTINGS_ENV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
SETTINGS_ROOT_ENV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "root.env")
SETTINGS_PASSWORD = os.environ.get("SETTINGS_PASSWORD", "")
# "live": True = solo lo usa scan.py, que se relanza como subproceso nuevo en
# cada sync y relee config.py (que a su vez relee el .env plano, ver
# plain_env.py) -- efecto inmediato con solo guardar + pulsar "Sincronizar",
# sin tocar el contenedor. Sin ese flag (MUSPY_*, MB_EMAIL) el valor lo usa
# tambien este mismo proceso Flask de larga duracion (para /api/muspy/*), que
# lo fijo una vez al arrancar -- ahi si hace falta recrear el contenedor.
VARS_SPEC = [
    {"name": "MUSPY_USERNAME", "secret": False, "help": "Usuario de Muspy"},
    {"name": "MUSPY_PASSWORD", "secret": True, "help": "Contraseña de Muspy"},
    {"name": "AIRSONIC_URL", "secret": False, "live": True, "help": "URL base de Airsonic"},
    {"name": "AIRSONIC_USER", "secret": False, "live": True, "help": "Usuario Airsonic"},
    {"name": "AIRSONIC_PASSWORD", "secret": True, "live": True, "help": "Contraseña Airsonic"},
    {"name": "AIRSONIC_API_VERSION", "secret": False, "live": True,
     "help": "Versión de API Subsonic a declarar (ej. 1.15.0) — súbela solo si tu Airsonic la soporta; "
             "una versión mas nueva que la suya da 'Incompatible Airsonic REST protocol version' "
             "(aunque esto ya se autodetecta solo en el siguiente sync)"},
    {"name": "LASTFM_API_KEY", "secret": True, "live": True, "help": "API key de Last.fm"},
    {"name": "LASTFM_USERNAME", "secret": False, "live": True, "help": "Usuario de Last.fm a comparar"},
    {"name": "LASTFM_MIN_PLAYCOUNT", "secret": False, "live": True,
     "help": "Umbral minimo de scrobbles al escanear (el filtro fino se ajusta luego en la web)"},
    {"name": "QB_HOST", "secret": False, "live": True, "help": "Host/IP de qBittorrent"},
    {"name": "QB_PORT", "secret": False, "live": True, "default": "8080", "help": "Puerto WebUI de qBittorrent"},
    {"name": "QB_USER", "secret": False, "live": True, "help": "Usuario WebUI de qBittorrent"},
    {"name": "QB_PASS", "secret": True, "live": True, "help": "Contraseña WebUI de qBittorrent"},
    {"name": "QB_CATEGORY", "secret": False, "live": True,
     "help": "Categoria de qBittorrent a escanear (vacio = todos los torrents)"},
    {"name": "QB_REMOTE_PATH", "secret": False, "live": True,
     "help": "Solo si qBittorrent corre en SU PROPIO contenedor: la ruta tal cual la reporta su API "
             "(ej. /downloads). Se reescribe por la ruta local antes de leer los FLAC. Vacío si "
             "qBittorrent corre directamente en este mismo host/filesystem"},
    {"name": "ARTIST_SYNC_QB_MUSIC_PATH", "secret": False, "location": "root",
     "help": "Ruta host donde qBittorrent guarda las descargas, montada en /mnt/music/qbittorrent "
             "dentro de este contenedor (bind mount — requiere recrear el contenedor)"},
    {"name": "MB_EMAIL", "secret": False,
     "help": "Email de contacto para la API de MusicBrainz (lo piden en el User-Agent)"},
]
_HAS_SECRETS = any(v.get("secret") for v in VARS_SPEC)


def _settings_path(spec):
    return SETTINGS_ROOT_ENV_PATH if spec.get("location") == "root" else SETTINGS_ENV_PATH


def _current_value(spec):
    path = _settings_path(spec)
    file_vals = read_env_file(path)
    if spec["name"] in file_vals:
        return file_vals[spec["name"]]
    return os.environ.get(spec["name"], spec.get("default", ""))


def _check_auth(password):
    if not SETTINGS_PASSWORD:
        return not _HAS_SECRETS
    return password == SETTINGS_PASSWORD


@app.route("/api/settings", methods=["POST"])
def api_settings():
    d = request.get_json(silent=True) or {}
    password = d.get("password") or ""
    requires = bool(SETTINGS_PASSWORD) or _HAS_SECRETS
    authorized = _check_auth(password)
    if requires and not authorized:
        error = "Contraseña incorrecta" if password else None
        if not SETTINGS_PASSWORD:
            error = "Este servicio tiene credenciales pero no hay SETTINGS_PASSWORD configurada. Añádela al .env y reinicia el contenedor."
        return jsonify({"requires_password": True, "authorized": False, "error": error})
    vars_out = [
        {"name": v["name"], "value": _current_value(v), "secret": v["secret"], "help": v.get("help", "")}
        for v in VARS_SPEC
    ]
    return jsonify({"requires_password": requires, "authorized": True, "vars": vars_out})


@app.route("/api/settings/save", methods=["POST"])
def api_settings_save():
    d = request.get_json(silent=True) or {}
    if not _check_auth(d.get("password") or ""):
        return jsonify({"error": "Contraseña incorrecta"}), 403
    by_name = {v["name"]: v for v in VARS_SPEC}
    updates = {k: v for k, v in (d.get("values") or {}).items() if k in by_name}
    if not updates:
        return jsonify({"error": "Nada que guardar"}), 400
    by_path = {}
    for k, v in updates.items():
        path = _settings_path(by_name[k])
        by_path.setdefault(path, {})[k] = v
    for path, vals in by_path.items():
        write_env_file(path, vals)
    touched_root = any(_settings_path(by_name[k]) == SETTINGS_ROOT_ENV_PATH for k in updates)
    needs_restart = any(not by_name[k].get("live") for k in updates)
    if touched_root:
        message = ("Guardado. ARTIST_SYNC_QB_MUSIC_PATH es una ruta de bind mount — hace falta "
                    "RECREAR el contenedor (docker compose up -d --build), no basta con reiniciarlo.")
    elif needs_restart:
        message = "Guardado. Reinicia el contenedor para aplicar los cambios."
    else:
        message = "Guardado. Ya tiene efecto en la próxima sincronización (botón \"Sincronizar\"), sin tocar el contenedor."
    return jsonify({"ok": True, "message": message})


# ---------------------------------------------------------------------------
# DB helper
# ---------------------------------------------------------------------------

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


with get_db() as _conn:
    init_db(_conn)


# ---------------------------------------------------------------------------
# Frontend
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


# ---------------------------------------------------------------------------
# API — sync
# ---------------------------------------------------------------------------

@app.route("/api/sync", methods=["POST"])
def api_sync():
    """Relanza scan.py (todas las fuentes o una lista via ?only=muspy,lastfm)."""
    only = request.args.get("only")
    scan_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scan.py")
    cmd = ["python3", scan_script]
    if only:
        cmd += ["--only", only]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    except subprocess.TimeoutExpired:
        return jsonify({"error": "La sincronizacion tardo demasiado (timeout)"}), 500
    return jsonify({
        "success": res.returncode == 0,
        "log": (res.stdout + "\n" + res.stderr)[-4000:],
    })


# ---------------------------------------------------------------------------
# API — artistas
# ---------------------------------------------------------------------------

@app.route("/api/artists")
def api_artists():
    conn = get_db()
    artists = conn.execute("SELECT id, name FROM artists ORDER BY name COLLATE NOCASE").fetchall()
    presence = conn.execute(
        "SELECT artist_id, source, raw_name, mbid, playcount, count FROM presence"
    ).fetchall()
    conn.close()

    by_artist = {}
    for row in presence:
        by_artist.setdefault(row["artist_id"], {})[row["source"]] = {
            "raw_name": row["raw_name"],
            "mbid": row["mbid"],
            "playcount": row["playcount"],
            "count": row["count"],
        }

    result = []
    for a in artists:
        sources = by_artist.get(a["id"], {})
        if not sources:
            continue
        result.append({"id": a["id"], "name": a["name"], "sources": sources})

    return jsonify(result)


@app.route("/api/last-sync")
def api_last_sync():
    """mtime de la DB como aproximacion de 'ultima sincronizacion' — solo si
    ya hay algo sincronizado (si no, sqlite3.connect() habria creado un
    archivo vacio y daria una fecha enganosa)."""
    conn = get_db()
    has_data = conn.execute("SELECT 1 FROM presence LIMIT 1").fetchone() is not None
    conn.close()
    if not has_data or not os.path.exists(DB_PATH):
        return jsonify({"last_sync": None})
    return jsonify({"last_sync": os.path.getmtime(DB_PATH)})


# ---------------------------------------------------------------------------
# API — Muspy follow/unfollow
# ---------------------------------------------------------------------------

def _muspy_user_id():
    if not (MUSPY_USERNAME and MUSPY_PASSWORD):
        raise RuntimeError("Muspy no esta configurado")
    return muspy_client.get_user_id(MUSPY_USERNAME, MUSPY_PASSWORD)


@app.route("/api/muspy/follow", methods=["POST"])
def api_muspy_follow():
    d = request.get_json(silent=True) or {}
    artist_id = d.get("artist_id")
    if not artist_id:
        return jsonify({"error": "Falta artist_id"}), 400

    conn = get_db()
    artist = conn.execute("SELECT id, name FROM artists WHERE id=?", (artist_id,)).fetchone()
    if not artist:
        conn.close()
        return jsonify({"error": "Artista no encontrado"}), 404

    mbid_row = conn.execute(
        "SELECT mbid FROM presence WHERE artist_id=? AND mbid IS NOT NULL LIMIT 1", (artist_id,)
    ).fetchone()
    mbid = mbid_row["mbid"] if mbid_row else None

    try:
        if not mbid:
            mbid = search_mbid(artist["name"], MB_EMAIL)
        if not mbid:
            conn.close()
            return jsonify({"error": f"No se encontro MBID para '{artist['name']}' en MusicBrainz"}), 404

        user_id = _muspy_user_id()
        muspy_client.follow_artist(MUSPY_USERNAME, MUSPY_PASSWORD, user_id, mbid)

        conn.execute(
            """INSERT INTO presence(artist_id, source, raw_name, mbid)
               VALUES(?, 'muspy', ?, ?)
               ON CONFLICT(artist_id, source) DO UPDATE SET raw_name=excluded.raw_name, mbid=excluded.mbid""",
            (artist_id, artist["name"], mbid),
        )
        conn.commit()
        conn.close()
        return jsonify({"success": True, "mbid": mbid})
    except Exception as exc:
        conn.close()
        return jsonify({"error": str(exc)}), 502


@app.route("/api/muspy/unfollow", methods=["POST"])
def api_muspy_unfollow():
    d = request.get_json(silent=True) or {}
    artist_id = d.get("artist_id")
    if not artist_id:
        return jsonify({"error": "Falta artist_id"}), 400

    conn = get_db()
    row = conn.execute(
        "SELECT mbid FROM presence WHERE artist_id=? AND source='muspy'", (artist_id,)
    ).fetchone()
    if not row or not row["mbid"]:
        conn.close()
        return jsonify({"error": "Este artista no esta seguido en Muspy"}), 404

    try:
        user_id = _muspy_user_id()
        muspy_client.unfollow_artist(MUSPY_USERNAME, MUSPY_PASSWORD, user_id, row["mbid"])
        conn.execute("DELETE FROM presence WHERE artist_id=? AND source='muspy'", (artist_id,))
        conn.execute(
            "DELETE FROM artists WHERE id=? AND id NOT IN (SELECT DISTINCT artist_id FROM presence)",
            (artist_id,),
        )
        conn.commit()
        conn.close()
        return jsonify({"success": True})
    except Exception as exc:
        conn.close()
        return jsonify({"error": str(exc)}), 502


if __name__ == "__main__":
    from config import FLASK_HOST, FLASK_PORT
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=True)
