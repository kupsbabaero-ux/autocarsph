#!/usr/bin/env python3
"""
YouTube Live → M3U (Search by Name)
Lalabas: https://www.youtube.com/watch?v=XXXX
Optimized para sa Kapamilya / TV5 / 24 Oras
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


def yt_dlp_base():
    """Common yt-dlp args"""
    return [
        "yt-dlp",
        "--js-runtimes", "node",
        "--no-download",
        "--no-warnings",
        "--quiet",
        "--no-check-certificates",
    ]


def get_live_info(video_id: str):
    """Try to confirm if LIVE. Returns info or None."""
    url = f"https://www.youtube.com/watch?v={video_id}"
    try:
        cmd = yt_dlp_base() + ["--dump-json", url]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=40)
        if result.returncode != 0:
            # Geo-block or other error — return None, caller decides
            return None

        data = json.loads(result.stdout)
        is_live = data.get("is_live", False) or data.get("live_status") == "is_live"
        if not is_live:
            return None

        return {
            "is_live": True,
            "title": data.get("title", "Live"),
            "thumbnail": data.get("thumbnail") or "",
            "channel": data.get("channel") or data.get("uploader") or "YouTube",
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "id": video_id
        }
    except Exception:
        return None


def search_live(query: str):
    """Search YouTube, prioritize strong LIVE matches"""
    queries = [query]

    q_lower = query.lower()
    if "kapamilya" in q_lower:
        queries = ["Kapamilya Online Live"] + queries
    if "kapatid" in q_lower or "tv5" in q_lower:
        queries = ["TV5 Kapatid Livestream", "TV5 Kapatid Live"] + queries
    if "24 oras" in q_lower:
        queries = ["24 Oras Live", "24 Oras Livestream"] + queries

    seen = set()
    candidates = []  # (score, video_id, title)

    for sq in queries:
        try:
            cmd = yt_dlp_base() + ["--dump-json", "--flat-playlist", f"ytsearch12:{sq}"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=55)
            if result.returncode != 0:
                continue

            for line in result.stdout.strip().split("\n"):
                if not line.strip():
                    continue
                try:
                    item = json.loads(line)
                except:
                    continue

                vid = item.get("id")
                title = (item.get("title") or "").strip()
                if not vid or vid in seen:
                    continue
                seen.add(vid)

                t = title.lower()
                score = 0
                if "live" in t:
                    score += 15
                if "livestream" in t or "live stream" in t:
                    score += 10
                # exact-ish match boost
                for word in query.lower().split():
                    if len(word) > 2 and word in t:
                        score += 4
                candidates.append((score, vid, title))

        except Exception:
            continue

    candidates.sort(key=lambda x: -x[0])

    print(f"  top candidates: {len(candidates)}")

    # 1) Try to confirm is_live on top candidates
    for score, vid, title in candidates[:8]:
        if score < 10:
            continue
        info = get_live_info(vid)
        if info and info.get("is_live"):
            print(f"  ✅ CONFIRMED LIVE: {info['title'][:60]}")
            print(f"     {info['url']}")
            return info

    # 2) Fallback: if title looks very much like a live of this show,
    #    accept it even if is_live check failed (geo-block common)
    for score, vid, title in candidates[:5]:
        t = title.lower()
        if score >= 15 and "live" in t:
            print(f"  ⚠️  Using strong match (is_live check failed, possible geo):")
            print(f"     {title[:60]}")
            print(f"     https://www.youtube.com/watch?v={vid}")
            return {
                "is_live": True,
                "title": title,
                "thumbnail": "",
                "channel": "YouTube",
                "url": f"https://www.youtube.com/watch?v={vid}",
                "id": vid
            }

    print("  [!] Walang active live")
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

        if info and info.get("url"):
            logo = info.get("thumbnail") or ""
            title = (info.get("title") or name).replace(",", " -").replace('"', "'")

            lines.append(
                f'#EXTINF:-1 tvg-id="{name}" tvg-name="{name}" '
                f'tvg-logo="{logo}" group-title="LIVE",{name} • {title}'
            )
            lines.append(info["url"])
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
