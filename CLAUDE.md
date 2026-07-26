# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Interactive artist comparator across 4 sources: Muspy (followed), Airsonic
(library), qBittorrent (downloads, via FLAC tags), Last.fm (listened). Muspy
is the canonical "follow" source — the whole point of the tool is deciding
who to follow/unfollow there after seeing the other 3.

## File Structure

- **`config.py`** — all credentials/paths, env-var overrideable, loads `.encrypted.env` via `sops_env.py`
- **`clients/`** — one module per external API (`muspy_client`, `airsonic_client`, `lastfm_client`, `qbittorrent_client`, `musicbrainz_client`), plus `flac_scan.py` (mutagen tag reading) and `normalize.py` (cross-source artist-name matching key)
- **`scan.py`** — orchestrates all 4 clients, upserts into `repeat_one.db`
- **`app.py`** — Flask: serves the page + REST API + settings panel (`⚙`, shared pattern with `trasvase`/`dieta_sonora`)
- **`templates/index.html`** — single-page comparator table (vanilla JS, no build step)

## Database Schema (`repeat_one.db`, SQLite)

```sql
artists(id, name, norm_name UNIQUE)   -- norm_name = normalize(name), the cross-source join key
presence(id, artist_id FK, source IN (muspy|airsonic|qbittorrent|lastfm),
         raw_name, mbid, playcount, count)   -- one row per (artist, source) it appears in
```

`scan.py` does a full `DELETE ... WHERE source=?` + re-insert per source on
each sync — artists that vanished from a source (e.g. unfollowed elsewhere)
drop out automatically. No column is source-exclusive by design: `mbid` is
populated for muspy (and sometimes lastfm), `count` is albums (airsonic) or
tracks (qbittorrent), `playcount` is lastfm-only.

## Key Logic Notes

- **Artist matching**: `clients/normalize.py` strips accents, casing,
  punctuation and a leading "The " — this is the only thing that ties an
  artist across sources with differently-formatted names. If cross-source
  matches look wrong, this is where to look first.
- **qBittorrent has no artist metadata natively**: `flac_scan.py` walks each
  torrent's content path (from the WebUI API) and reads the `albumartist`/
  `artist` FLAC tag off one file per folder, matching `trasvase/scan.py`'s
  approach. Assumes same-host filesystem access — no path remapping.
- **Muspy follow/unfollow**: `POST /api/muspy/follow` needs an MBID; it
  reuses any MBID already known for that artist (from a `muspy` or `lastfm`
  presence row) and falls back to a MusicBrainz name search otherwise. Basic
  auth (`MUSPY_USERNAME`/`MUSPY_PASSWORD`) is used for all Muspy calls, same
  pattern as `music-fuzzy`'s `muspy_manager.py`.
- **Last.fm threshold is two-layered**: `LASTFM_MIN_PLAYCOUNT` (scan-time,
  env var) keeps the sync fast by not paginating through thousands of
  one-play artists; the web UI's slider then filters further, live, from
  what's already in the DB — no re-scan needed to tighten the threshold.

## Related / sibling projects (same author, same conventions)

- `../trasvase` — near-identical stack (Flask + SQLite + mutagen + Airsonic +
  sops secrets + `settings-panel.js`); this project's scan/settings-panel
  code was bootstrapped from it.
- `../music-fuzzy/modules/submodules/muspy/muspy_manager.py` — the
  known-working Muspy API auth pattern this project's `muspy_client.py` follows.
- `../tumtumpa` — the orchestration repo (git submodules + docker-compose +
  reverse proxy) that runs all these sibling web apps in production. Not yet
  wired in for repeat-one — see README/ask-the-user before adding a
  `services/repeat-one` submodule + docker-compose profile there.
