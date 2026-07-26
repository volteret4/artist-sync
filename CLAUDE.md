# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Interactive artist comparator across 4 sources: Muspy (followed), Airsonic
(library), qBittorrent (downloads, via FLAC tags), Last.fm (listened). Muspy
is the canonical "follow" source — the whole point of the tool is deciding
who to follow/unfollow there after seeing the other 3.

## File Structure

- **`config.py`** — all credentials/paths, env-var overrideable, loads `.encrypted.env` via `sops_env.py`
- **`clients/`** — one module per external API (`muspy_client`, `airsonic_client`, `lastfm_client`, `lastfm_mirror_client`, `qbittorrent_client`, `musicbrainz_client`), plus `flac_scan.py` (mutagen tag reading) and `normalize.py` (cross-source artist-name matching key)
- **`scan.py`** — orchestrates all 4 clients, upserts into `artist_sync.db`
- **`app.py`** — Flask: serves the page + REST API + settings panel (`⚙`, shared pattern with `trasvase`/`dieta_sonora`)
- **`templates/index.html`** — single-page comparator table (vanilla JS, no build step)

## Database Schema (`artist_sync.db`, SQLite)

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
- **Last.fm source prefers a shared mirror over the API**: `scan.py`'s
  `sync_lastfm` checks `lastfm_mirror_client.available(LASTFM_SCROBBLES_DB)`
  first — if tumtumpa's `lastfm-scrobbles` service has populated the
  `lastfm_data` volume (`/data/lastfm_stats.db`, Last.fm + ListenBrainz
  already deduplicated by that service, see its
  `services/dieta_sonora/estadisticas/lastfm/extraer_scrobbles.py`), it reads
  straight from that SQLite file instead of calling `lastfm_client`/the
  Last.fm API. `LASTFM_API_KEY`/`LASTFM_USERNAME` are only a fallback for
  running this app outside tumtumpa. The mirror is strictly better data too:
  it includes ListenBrainz-only listens the Last.fm API alone would miss.

## Related / sibling projects (same author, same conventions)

- `../trasvase` — near-identical stack (Flask + SQLite + mutagen + Airsonic +
  sops secrets + `settings-panel.js`); this project's scan/settings-panel
  code was bootstrapped from it.
- `../music-fuzzy/modules/submodules/muspy/muspy_manager.py` — the
  known-working Muspy API auth pattern this project's `muspy_client.py` follows.
- `../tumtumpa` — the orchestration repo (its actual GitHub remote is
  `volteret4/repeat-one` — "tumtumpa" is just the local directory nickname,
  don't confuse it with this project) that runs all these sibling web apps
  in production via git submodules + docker-compose + reverse proxy. This
  project is wired in as `services/artist-sync`.
