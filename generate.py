#!/usr/bin/env python3
"""
YouTube Live → M3U Auto Updater
- Binabasa ang streams.txt
- Kinukuha ang current HLS link gamit ang yt-dlp
- Kapag hindi na live, automatic na aalisin o papalitan ng offline
"""

import subprocess
import json
import os
import re
from datetime import datetime, timezone

STREAMS_FILE = "streams.txt"
OUTPUT_M3U = "playlist.m3u"
OFFLINE_PLACEHOLDER = "https://raw.githubusercontent.com/benmoose39/YouTube_to_m3u/main/assets/offline.mp4"  # optional fallback

def parse_streams():
    streams = []
    if not os.path.exists(STREAMS_FILE):
        print(f"[!] {STREAMS_FILE} not found")
        return streams

    with open(STREAMS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "|" in line:
                parts = line.split("|", 1)
                name = parts[0].strip()
                url = parts[1].strip()
                if name and url:
                    streams.append({"name": name, "url": url})
            else:
                # pure URL lang
                streams.append({"name": "Live Stream", "url": line})
    return streams


def get_stream_info(yt_url: str):
    """Gamitin ang yt-dlp para kunin ang current stream info"""
    try:
        cmd = [
            "yt-dlp",
            "--dump-json",
            "--no-download",
            "--no-warnings",
            "--quiet",
            yt_url
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
        if result.returncode != 0:
            print(f"  [!] yt-dlp failed: {result.stderr.strip()[:200]}")
            return None

        data = json.loads(result.stdout)

        is_live = data.get("is_live", False) or data.get("live_status") in ("is_live", "is_upcoming")
        title = data.get("title", "Live")
        thumbnail = data.get("thumbnail")
        channel = data.get("channel") or data.get("uploader") or "YouTube"

        # Kunin ang best HLS format
        m3u8_url = None
        formats = data.get("formats") or []
        for f in reversed(formats):  # prefer higher quality
            if f.get("protocol") in ("m3u8", "m3u8_native", "http_dash_segments") and f.get("url"):
                url = f["url"]
                if ".m3u8" in url or "manifest" in url.lower():
                    m3u8_url = url
                    break

        # fallback: direct url kung mayroon
        if not m3u8_url and data.get("url"):
            m3u8_url = data["url"]

        return {
            "is_live": bool(is_live),
            "title": title,
            "thumbnail": thumbnail,
            "channel": channel,
            "m3u8": m3u8_url,
            "original": yt_url
        }
    except Exception as e:
        print(f"  [!] Error: {e}")
        return None


def generate_m3u(streams_data):
    lines = [
        "#EXTM3U",
        f"# Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
        "# Auto-updated by GitHub Actions",
        ""
    ]

    active_count = 0
    for s in streams_data:
        name = s["name"]
        info = s.get("info")

        if info and info.get("is_live") and info.get("m3u8"):
            logo = info.get("thumbnail") or ""
            title = info.get("title") or name
            channel = info.get("channel") or "YouTube"

            lines.append(
                f'#EXTINF:-1 tvg-id="{name}" tvg-name="{name}" '
                f'tvg-logo="{logo}" group-title="LIVE",{name} • {title}'
            )
            lines.append(info["m3u8"])
            lines.append("")
            active_count += 1
            print(f"  ✅ LIVE: {name}")
        else:
            # Offline - optional placeholder
            lines.append(
                f'#EXTINF:-1 tvg-id="{name}" tvg-name="{name}" '
                f'group-title="OFFLINE",{name} [OFFLINE]'
            )
            lines.append(OFFLINE_PLACEHOLDER)
            lines.append("")
            print(f"  ❌ OFFLINE: {name}")

    with open(OUTPUT_M3U, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"\n[+] Generated {OUTPUT_M3U} — {active_count} active live stream(s)")
    return active_count


def main():
    print("=" * 50)
    print("YouTube Live → M3U Auto Updater")
    print("=" * 50)

    streams = parse_streams()
    if not streams:
        print("[!] Walang stream sa streams.txt")
        # Gumawa pa rin ng empty playlist
        with open(OUTPUT_M3U, "w") as f:
            f.write("#EXTM3U\n# Walang active live\n")
        return

    print(f"[*] Checking {len(streams)} stream(s)...\n")

    for s in streams:
        print(f"→ {s['name']}")
        print(f"  URL: {s['url']}")
        info = get_stream_info(s["url"])
        s["info"] = info

    generate_m3u(streams)
    print("\nDone.")


if __name__ == "__main__":
    main()
