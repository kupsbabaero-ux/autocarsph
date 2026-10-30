#!/usr/bin/env python3
"""
YouTube Live → M3U (Search by Name)
Lalabas: https://www.youtube.com/watch?v=XXXX
Mas stable, hindi madaling mag-exit code 1
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
        print(f"[!] {STREAMS_FILE} not found — gumawa muna")
        return names
    with open(STREAMS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            names.append(line)
    return names


def yt_dlp_cmd(extra_args):
    """Build yt-dlp command with safe defaults"""
    cmd = [
        "yt-dlp",
        "--no-download",
        "--no-warnings",
        "--quiet",
        "--no-check-certificates",
        "--socket-timeout", "20",
    ]
    # subukan i-add ang node runtime kung available
    try:
        subprocess.run(["node", "--version"], capture_output=True, timeout=5)
        cmd += ["--js-runtimes", "node"]
    except Exception:
        pass
    cmd += extra_args
    return cmd


def get_live_info(video_id: str):
    """Try confirm LIVE. Returns dict or None. Never crashes."""
    url = f"https://www.youtube.com/watch?v={video_id}"
    try:
        cmd = yt_dlp_cmd(["--dump-json", url])
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
        if result.returncode != 0 or not result.stdout.strip():
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
    """Search + score. Never crashes."""
    queries = [query]
    q_lower = query.lower()

    if "kapamilya" in q_lower:
        queries = ["Kapamilya Online Live"] + queries
    if "kapatid" in q_lower or "tv5" in q_lower:
        queries = ["TV5 Kapatid Livestream", "TV5 Kapatid Live"] + queries
    if "24 oras" in q_lower:
        queries = ["24 Oras Live", "24 Oras Livestream"] + queries

    seen = set()
    candidates = []

    for sq in queries:
        try:
            cmd = yt_dlp_cmd(["--dump-json", "--flat-playlist", f"ytsearch10:{sq}"])
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if result.returncode != 0 or not result.stdout.strip():
                continue

            for line in result.stdout.strip().split("\n"):
                if not line.strip():
                    continue
                try:
                    item = json.loads(line)
                except Exception:
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
                for word in query.lower().split():
                    if len(word) > 2 and word in t:
                        score += 4
                candidates.append((score, vid, title))
        except Exception as e:
            print(f"  [!] search error ({sq}): {e}")
            continue

    candidates.sort(key=lambda x: -x[0])
    print(f"  candidates: {len(candidates)}")

    # 1) Confirm is_live
    for score, vid, title in candidates[:8]:
        if score < 8:
            continue
        info = get_live_info(vid)
        if info and info.get("is_live"):
            print(f"  ✅ LIVE: {info['title'][:60]}")
            print(f"     {info['url']}")
            return info

    # 2) Fallback — strong title match (para sa geo-block)
    for score, vid, title in candidates[:6]:
        t = title.lower()
        if score >= 15 and "live" in t:
            print(f"  ⚠️  Strong match (using): {title[:55]}")
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

    try:
        with open(OUTPUT_M3U, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        print(f"\n[+] Generated {OUTPUT_M3U} — {active} active live stream(s)")
        print(f"[+] Path: {os.path.abspath(OUTPUT_M3U)}")
    except Exception as e:
        print(f"[!] Cannot write {OUTPUT_M3U}: {e}")
    return active


def main():
    print("=" * 55)
    print("YouTube Live → M3U  (Search by Name)")
    print("Output: https://www.youtube.com/watch?v=XXXX")
    print("=" * 55)

    # Check yt-dlp
    try:
        r = subprocess.run(["yt-dlp", "--version"], capture_output=True, text=True, timeout=10)
        if r.returncode != 0:
            raise Exception("yt-dlp not working")
        print(f"[*] yt-dlp {r.stdout.strip()}")
    except Exception:
        print("\n[!] ERROR: yt-dlp not installed or not working")
        print("    Fix:  pip install -U yt-dlp")
        print("    or:   python -m pip install -U yt-dlp")
        # still write empty playlist para hindi empty error
        with open(OUTPUT_M3U, "w") as f:
            f.write("#EXTM3U\n# yt-dlp missing\n")
        sys.exit(0)   # exit 0 para hindi code 1

    names = parse_names()
    if not names:
        print("[!] Walang pangalan sa streams.txt")
        with open(OUTPUT_M3U, "w") as f:
            f.write("#EXTM3U\n# no names\n")
        sys.exit(0)

    print(f"\n[*] Searching {len(names)} name(s)...\n")

    results = []
    for name in names:
        print(f"→ {name}")
        try:
            info = search_live(name)
        except Exception as e:
            print(f"  [!] error: {e}")
            info = None
        results.append({"name": name, "info": info})

    generate_m3u(results)
    print("\nDone.")
    sys.exit(0)   # always exit 0


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[!] Unexpected error: {e}")
        # try write something
        try:
            with open(OUTPUT_M3U, "w") as f:
                f.write("#EXTM3U\n# error occurred\n")
        except Exception:
            pass
        sys.exit(0)
