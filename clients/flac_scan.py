"""Extrae el artista (albumartist/artist) de archivos FLAC bajo una serie de
rutas raiz (una por torrent de qBittorrent), contando pistas por artista."""
import os
from collections import Counter

from mutagen import MutagenError
from mutagen.flac import FLAC


def _tag(audio, *keys):
    for key in keys:
        for variant in (key.upper(), key.lower(), key.title()):
            val = audio.get(variant)
            if val:
                return str(val[0]).strip()
    return None


def _read_artist(flac_path):
    try:
        audio = FLAC(flac_path)
    except (MutagenError, OSError):
        return None
    return _tag(audio, "albumartist", "artist")


def scan_artist_track_counts(root_paths):
    """root_paths: iterable de rutas (carpeta de contenido de cada torrent).
    Devuelve {artist_name: track_count}."""
    counts = Counter()

    for root in root_paths:
        if not root:
            continue
        if os.path.isfile(root):
            if root.lower().endswith(".flac"):
                artist = _read_artist(root)
                if artist:
                    counts[artist] += 1
            continue
        if not os.path.isdir(root):
            continue
        for dirpath, _dirs, files in os.walk(root):
            flac_files = [f for f in files if f.lower().endswith(".flac")]
            if not flac_files:
                continue
            artist = _read_artist(os.path.join(dirpath, flac_files[0]))
            if not artist:
                continue
            counts[artist] += len(flac_files)

    return dict(counts)
