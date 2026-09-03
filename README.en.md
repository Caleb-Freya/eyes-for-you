# eyes-for-you

*[中文版 → README.md](README.md)*

A self-hosted location backend (OwnTracks-compatible). Your phone reports its location to **your own** server — no third-party company involved, ever. The data lives only on your machine.

Give your AI (or yourself) a pair of eyes that can always see where your loved one is.

> Why this exists: every mainstream location-sharing service hands your whereabouts to someone else's cloud. This one doesn't — a single Python file, zero dependencies, local storage only. Once set up, your AI companion/assistant learns where you are by reading one local file, without a single outbound request.

## Who can use it

| Your setup | Works? |
|---|---|
| iPhone | ✅ OwnTracks has an iOS app (App Store) |
| Android | ✅ Google Play; phones without Google services can install the APK from [F-Droid](https://f-droid.org/packages/org.owntracks.android/) or [GitHub Releases](https://github.com/owntracks/android/releases) |
| AI is Claude | ✅ reads the local file: `python3 where.py` |
| AI is GPT / anything else | ✅ AI-agnostic — anything with web access can `GET /latest?token=KEY` for JSON; wire a custom GPT Action to that URL; or just paste `where.py` output into the chat |
| API relay only, **no server of your own** | ⚠️ Not for you (yet). This requires a machine you own (a cheap VPS / mini PC / Raspberry Pi) — the entire point is that your location stays *in your own hands*. Don't let someone else host it for you: your whereabouts would live on their machine |

## Features

- **Zero third parties** — locations are written to local files only (`data/latest.json` + `data/history.jsonl`); the backend makes no outbound requests
- **Zero dependencies** — Python 3 standard library only; runs on any VPS / mini PC / Raspberry Pi
- **Binds 127.0.0.1 only** — public entry goes through a tunnel / reverse proxy: one layer of HTTPS, one layer of key
- **Dual-channel auth** — URL `?token=` or Basic-Auth password, either one passes (constant-time comparison)
- **OwnTracks-compatible** — the phone side is the open-source [OwnTracks](https://owntracks.org/) app (iOS/Android), reporting in the battery-friendly way Apple officially sanctions
- **Local reverse geocoding** — coordinates → "near Central Park (120m)" resolved **on your own machine**: download your city's public map names (OSM) once, and lookups never leave home; optionally add an Amap key for shop-level precision (China)

## Architecture

```
📱 OwnTracks ──HTTPS──▶ 🔒 tunnel/proxy ──▶ 🗄️ server.py (127.0.0.1:8098) ──▶ 👁️ you / your AI (local read)
```

## Quick start (~20 minutes)

### 1. Backend (~10 min)

```bash
git clone https://github.com/45694354xm/eyes-for-you.git ~/geo-track
cd ~/geo-track
bash start.sh

# First start generates your key — note it down (the phone needs it):
cat data/token.txt
```

### 2. Public entry (~5 min)

The backend binds localhost only; give it an HTTPS entry. Pick one:

**A · Cloudflare Tunnel (easiest)** — Zero Trust → Tunnels → add a Public Hostname:
- subdomain `track`, Service type **HTTP** (not HTTPS, or you'll get 502), URL `127.0.0.1:8098`

**B · Server with a public IP** — two lines of Caddy give you auto-HTTPS:
```
track.yourdomain.com { reverse_proxy 127.0.0.1:8098 }
```

Verify: open `https://track.yourdomain.com/health` on your phone — `{"ok":true}` means you're through.

### 3. Phone (the tricky part — 3 pitfalls)

Install [OwnTracks](https://owntracks.org/) (free, open source), then in Settings:

| Field | Value |
|---|---|
| Mode | **HTTP** (not MQTT) |
| URL | `https://track.yourdomain.com/pub?token=YOUR_KEY` |
| User ID | anything (e.g. `me`) |

**⚠️ Three pitfalls (we hit them so you don't have to):**

1. **Leave the "Secret encryption key" field EMPTY** — it is *not* a password; it is an end-to-end encryption key. If you fill it, your locations are sent as `_type:encrypted` blobs the server cannot read. Auth is already handled by `?token=` in the URL.
2. **Auth via URL; don't fight Basic-Auth** — the auth/password toggles can be on or off; as long as the URL carries `?token=`, the backend lets you in (the code accepts either channel).
3. **Don't stay in "Manual" mode** — the row at the top of the map page reads `Quiet / Manual / Significant / Move`. Stuck on Manual = it never reports on its own. Tap **Move** for periodic reporting (expert settings: `monitoring=2`, `locatorInterval=300` s, `locatorDisplacement=100` m). The blue arrow is just "center on me" and the top-right square is the iOS share sheet — neither sends your location.

After that, tap Move on the map page or take a few steps — your first fix will land.

### 4. Read "where is she/he"

```bash
python3 where.py
```

```
📍 Latest fix
   time:  2026-09-03 12:23:05 (43 seconds ago)
   coords: 39.9087, 116.3975
   accuracy: ±8 m
   battery: 50%
   nearby: Tiananmen Square (120m)
   map: https://maps.google.com/?q=39.9087,116.3975
```

To let an AI read it proactively: feed it `python3 where.py` output, or `GET /latest?token=YOUR_KEY` for raw JSON.

## Reverse geocoding (recommended, 5 min)

Raw coordinates are hard to read. Two layers, use what you need:

**Layer 1 — local map data (free, zero-leak, recommended)**

Download your city's public place names (OpenStreetMap, ODbL) once; all lookups stay local:

```bash
# bbox of your city: south west north east (see the Export tab on openstreetmap.org)
python3 fetch_pois.py 40.60 -74.10 40.90 -73.80
```

This downloads only "which streets and landmarks exist here" — **nothing about you**. The script rotates across three Overpass mirrors automatically (the main one is often overloaded). You'll get streets, landmarks, major buildings; small shops may be missing.

**Layer 2 — Amap fallback (optional, China, shop-level precision)**

Register a free developer key at [lbs.amap.com](https://lbs.amap.com), create an app → add a Key → platform **"Web服务" (Web service)**, leave the IP allowlist **empty** (home IPs are dynamic; filling it in causes mysterious breakage later). Then:

```bash
echo "your-key" > data/amap.key && chmod 600 data/amap.key
```

`where.py` picks it up automatically. Trade-off to know: **Amap sees the queried coordinates** (occasional points from your server's IP, not your full track). Skip this layer if that bothers you. The code already handles the WGS-84 → GCJ-02 datum conversion (skipping it puts you a few hundred meters off in China) and always connects directly, bypassing any proxy env vars.

## API

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/pub` | ✅ | OwnTracks report endpoint, returns `[]` |
| GET | `/latest` | ✅ | latest fix (JSON) |
| GET | `/health` | — | health check `{"ok":true}` |

## Security notes (not optional)

- **The key is the whole gate** — never post your token in group chats, public repos, or screenshots. If it leaks, rotate it: delete `data/token.txt` and restart
- **Never expose the backend directly** — it binds 127.0.0.1; the outside world only gets tunnel + token
- **`data/` *is* your movement history** — mind the file permissions and never sync it into any public repo
- Battery-friendliness is a feature, not a bug: Move mode stays silent while you're still and reports while you move (default 5 min / 100 m)

## License

MIT

---

*made with 📍 by Caleb · for Freya, and for everyone who wants to be seen by their own AI*
