#!/usr/bin/env python3
"""
Consulta las 4 fuentes (Muspy, Airsonic, qBittorrent+FLAC, Last.fm), normaliza
nombres de artista y sincroniza la tabla `presence` de artist_sync.db.

Uso:
    python scan.py                    # sincroniza todo lo configurado
    python scan.py --only muspy,lastfm
"""
import argparse
import sqlite3
import sys

from clients import airsonic_client, flac_scan, lastfm_client, muspy_client, qbittorrent_client
from clients.normalize import normalize
from config import (
    AIRSONIC_API_VERSION, AIRSONIC_PASSWORD, AIRSONIC_URL, AIRSONIC_USER,
    DB_PATH,
    LASTFM_API_KEY, LASTFM_MIN_PLAYCOUNT, LASTFM_USERNAME,
    MUSPY_PASSWORD, MUSPY_USERNAME,
    QB_CATEGORY, QB_HOST, QB_LOCAL_PATH, QB_PASS, QB_PORT, QB_REMOTE_PATH, QB_USER,
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS artists (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    name      TEXT NOT NULL,
    norm_name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS presence (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    artist_id  INTEGER NOT NULL REFERENCES artists(id) ON DELETE CASCADE,
    source     TEXT NOT NULL CHECK(source IN ('muspy', 'airsonic', 'qbittorrent', 'lastfm')),
    raw_name   TEXT NOT NULL,
    mbid       TEXT,
    playcount  INTEGER,
    count      INTEGER,
    UNIQUE(artist_id, source)
);

CREATE INDEX IF NOT EXISTS idx_presence_source ON presence(source);
"""


def init_db(conn):
    conn.executescript(SCHEMA)
    conn.commit()


def upsert_artist(conn, name):
    norm = normalize(name)
    if not norm:
        return None
    conn.execute(
        "INSERT INTO artists(name, norm_name) VALUES(?, ?) ON CONFLICT(norm_name) DO NOTHING",
        (name, norm),
    )
    return conn.execute("SELECT id FROM artists WHERE norm_name=?", (norm,)).fetchone()[0]


def replace_source(conn, source, rows):
    """rows: [{name, mbid?, playcount?, count?}, ...]. Reemplaza por completo
    lo que hubiera antes para esa fuente (borra + inserta), asi los artistas
    que ya no aparecen en la fuente desaparecen tambien de aqui."""
    conn.execute("DELETE FROM presence WHERE source=?", (source,))
    for row in rows:
        artist_id = upsert_artist(conn, row["name"])
        if artist_id is None:
            continue
        conn.execute(
            """INSERT INTO presence(artist_id, source, raw_name, mbid, playcount, count)
               VALUES(?, ?, ?, ?, ?, ?)
               ON CONFLICT(artist_id, source) DO UPDATE SET
                   raw_name=excluded.raw_name, mbid=excluded.mbid,
                   playcount=excluded.playcount, count=excluded.count""",
            (artist_id, source, row["name"], row.get("mbid"), row.get("playcount"), row.get("count")),
        )
    conn.commit()
    print(f"  [{source}] {len(rows)} artistas")


def sync_muspy(conn):
    if not (MUSPY_USERNAME and MUSPY_PASSWORD):
        print("  [muspy] sin credenciales, omitido")
        return
    user_id = muspy_client.get_user_id(MUSPY_USERNAME, MUSPY_PASSWORD)
    artists = muspy_client.list_followed_artists(MUSPY_USERNAME, MUSPY_PASSWORD, user_id)
    rows = [{"name": a["name"], "mbid": a.get("mbid")} for a in artists]
    replace_source(conn, "muspy", rows)


def sync_airsonic(conn):
    if not AIRSONIC_PASSWORD:
        print("  [airsonic] sin credenciales, omitido")
        return
    artists = airsonic_client.list_artists(AIRSONIC_URL, AIRSONIC_USER, AIRSONIC_PASSWORD, AIRSONIC_API_VERSION)
    rows = [{"name": a["name"], "count": a.get("albumCount")} for a in artists]
    replace_source(conn, "airsonic", rows)


def sync_lastfm(conn, min_playcount=None):
    if not (LASTFM_API_KEY and LASTFM_USERNAME):
        print("  [lastfm] sin credenciales, omitido")
        return
    if min_playcount is None:
        min_playcount = LASTFM_MIN_PLAYCOUNT
    artists = lastfm_client.top_artists(LASTFM_API_KEY, LASTFM_USERNAME, min_playcount=min_playcount)
    rows = [{"name": a["name"], "mbid": a.get("mbid"), "playcount": a["playcount"]} for a in artists]
    replace_source(conn, "lastfm", rows)


def sync_qbittorrent(conn):
    if not QB_PASS:
        print("  [qbittorrent] sin credenciales, omitido")
        return
    paths = qbittorrent_client.list_content_paths(
        QB_HOST, QB_PORT, QB_USER, QB_PASS, QB_CATEGORY, QB_REMOTE_PATH, QB_LOCAL_PATH
    )
    counts = flac_scan.scan_artist_track_counts(paths)
    rows = [{"name": name, "count": count} for name, count in counts.items()]
    replace_source(conn, "qbittorrent", rows)


SYNCERS = {
    "muspy": sync_muspy,
    "airsonic": sync_airsonic,
    "lastfm": sync_lastfm,
    "qbittorrent": sync_qbittorrent,
}


def main():
    parser = argparse.ArgumentParser(description="Sincroniza artistas de las 4 fuentes")
    parser.add_argument("--only", help="Lista separada por comas: muspy,airsonic,lastfm,qbittorrent")
    args = parser.parse_args()

    sources = list(SYNCERS)
    if args.only:
        sources = [s.strip() for s in args.only.split(",") if s.strip()]
        unknown = set(sources) - set(SYNCERS)
        if unknown:
            print(f"Fuentes desconocidas: {unknown}", file=sys.stderr)
            sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    init_db(conn)

    for source in sources:
        print(f"Sincronizando {source}...")
        try:
            SYNCERS[source](conn)
        except Exception as exc:
            print(f"  [{source}] ERROR: {exc}", file=sys.stderr)

    conn.close()


if __name__ == "__main__":
    main()
