#!/usr/bin/env python3
"""
YouTube Live → M3U (Search by Name)
- Ilagay mo lang ang pangalan sa streams.txt
- Lalabas ang link na ganito: https://www.youtube.com/watch?v=XXXX
- Kapag offline → hindi isinasama
"""

import subprocess
import json
import os
import sys
from datetime import datetime, timezone

STREAMS_FILE = "streams.txt"
OUTPUT_M3U = "playlist.m3u"


def parse_names():
    names = []
    if not os.path.exists(STREAMS_FILE):
        print(f"[!] {STREAMS_FILE} not found")
        return names
    with open(STREAMS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            names.append(line)
    return names


def get_live_video_id(yt_url: str):
    """Kunin ang video ID kung LIVE talaga"""
    try:
        cmd = [
            "yt-dlp",
            "--dump-json",
            "--no-download",
            "--no-warnings",
            "--quiet",
            "--no-check-certificates",
            yt_url
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
        if result.returncode != 0:
            return None

        data = json.loads(result.stdout)

        is_live = data.get("is_live", False) or data.get("live_status") == "is_live"
        if not is_live:
            return None

        video_id = data.get("id")
        title = data.get("title", "Live")
        thumbnail = data.get("thumbnail") or ""
        channel = data.get("channel") or data.get("uploader") or "YouTube"

        if not video_id:
            return None

        # Clean YouTube watch link
        watch_url = f"https://www.youtube.com/watch?v={video_id}"

        return {
            "is_live": True,
            "title": title,
            "thumbnail": thumbnail,
            "channel": channel,
            "url": watch_url,
            "id": video_id
        }
    except Exception:
        return None


def search_live(query: str, max_results: int = 12):
    """Maghanap ng live sa YouTube"""
    search_query = f"ytsearch{max_results}:{query}"

    try:
        cmd = [
            "yt-dlp",
            "--dump-json",
            "--flat-playlist",
            "--no-download",
            "--no-warnings",
            "--quiet",
            search_query
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=80)

        if result.returncode != 0:
            print(f"  [!] Search failed")
            return None

        candidates = []
        for line in result.stdout.strip().split("\n"):
            if not line.strip():
                continue
            try:
                data = json.loads(line)
                candidates.append(data)
            except:
                continue

        if not candidates:
            print("  [!] Walang result")
            return None

        for item in candidates:
            video_id = item.get("id")
            if not video_id:
                continue

            url = f"https://www.youtube.com/watch?v={video_id}"
            info = get_live_video_id(url)

            if info and info.get("is_live") and info.get("url"):
                print(f"  ✅ LIVE: {info['title'][:60]}")
                print(f"     {info['url']}")
                return info

        print("  [!] Walang active live")
        return None

    except Exception as e:
        print(f"  [!] Error: {e}")
        return None


def generate_m3u(results):
    lines = [
        "#EXTM3U",
        f"# Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
        "# YouTube watch links (https://www.youtube.com/watch?v=XXXX)",
        ""
    ]

    active = 0
    for item in results:
        name = item["name"]
        info = item.get("info")

        if info and info.get("is_live") and info.get("url"):
            logo = info.get("thumbnail") or ""
            title = (info.get("title") or name).replace(",", " -").replace('"', "'")

            lines.append(
                f'#EXTINF:-1 tvg-id="{name}" tvg-name="{name}" '
                f'tvg-logo="{logo}" group-title="LIVE",{name} • {title}'
            )
            lines.append(info["url"])   # <-- https://www.youtube.com/watch?v=XXXX
            lines.append("")
            active += 1
        else:
            print(f"  (skipped offline: {name})")

    with open(OUTPUT_M3U, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"\n[+] Generated {OUTPUT_M3U} — {active} active live stream(s)")
    print(f"[+] Path: {os.path.abspath(OUTPUT_M3U)}")
    return active


def main():
    print("=" * 55)
    print("YouTube Live → M3U  (Search by Name)")
    print("Output: https://www.youtube.com/watch?v=XXXX")
    print("=" * 55)

    try:
        subprocess.run(["yt-dlp", "--version"], capture_output=True, check=True)
    except Exception:
        print("\n[!] ERROR: yt-dlp not installed!")
        print("    Run:  pip install -U yt-dlp")
        sys.exit(1)

    names = parse_names()
    if not names:
        print("[!] Walang pangalan sa streams.txt")
        with open(OUTPUT_M3U, "w") as f:
            f.write("#EXTM3U\n")
        return

    print(f"\n[*] Searching {len(names)} name(s)...\n")

    results = []
    for name in names:
        print(f"→ {name}")
        info = search_live(name)
        results.append({"name": name, "info": info})

    generate_m3u(results)
    print("\nDone.")


if __name__ == "__main__":
    main()
