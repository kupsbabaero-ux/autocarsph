#!/usr/bin/env python3
"""
YouTube Live → M3U Auto Updater (Search by Name)
- Ilagay mo lang ang pangalan sa streams.txt
- Automatic na maghahanap ng matching YouTube Live
- Kapag tapos na ang live → OFFLINE
"""

import subprocess
import json
import os#!/usr/bin/env python3
"""
YouTube Live → M3U (Search by Name) - LOCAL VERSION
- Ilagay mo lang ang pangalan sa streams.txt
- Automatic maghahanap ng matching YouTube Live
- Naglalagay ng DIREKTANG m3u8 (hindi youtube.com/watch link)
- Para sa IPTV players
"""

import subprocess
import json
import os
import sys
from datetime import datetime, timezone

STREAMS_FILE = "streams.txt"
OUTPUT_M3U = "playlist.m3u"
OFFLINE_PLACEHOLDER = "https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8"  # public test stream


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


def get_stream_info(yt_url: str):
    """Kunin ang detailed info + DIRECT m3u8 ng isang video"""
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
        title = data.get("title", "Live")
        thumbnail = data.get("thumbnail")
        channel = data.get("channel") or data.get("uploader") or "YouTube"

        m3u8_url = None
        formats = data.get("formats") or []

        # 1. Prefer pure HLS (m3u8)
        for f in reversed(formats):
            proto = (f.get("protocol") or "").lower()
            url = f.get("url") or ""
            if "m3u8" in proto or ".m3u8" in url.lower():
                # iwasan ang youtube.com/watch o googlevideo na hindi m3u8
                if "manifest" in url or ".m3u8" in url:
                    m3u8_url = url
                    break

        # 2. Fallback: any format that looks like HLS
        if not m3u8_url:
            for f in reversed(formats):
                url = f.get("url") or ""
                if ".m3u8" in url:
                    m3u8_url = url
                    break

        # 3. Last resort
        if not m3u8_url and data.get("url") and ".m3u8" in str(data.get("url")):
            m3u8_url = data["url"]

        # CRITICAL: huwag kailanman maglagay ng youtube.com/watch link
        if m3u8_url and ("youtube.com/watch" in m3u8_url or "youtu.be/" in m3u8_url):
            m3u8_url = None

        return {
            "is_live": bool(is_live),
            "title": title,
            "thumbnail": thumbnail,
            "channel": channel,
            "m3u8": m3u8_url,
            "original": yt_url,
            "id": data.get("id")
        }
    except Exception as e:
        print(f"    [debug] get_stream_info error: {e}")
        return None


def search_live(query: str, max_results: int = 10):
    """Maghanap ng YouTube Live gamit ang yt-dlp"""
    search_query = f"ytsearch{max_results}:{query} live"

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
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=70)

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
            except json.JSONDecodeError:
                continue

        if not candidates:
            print("  [!] Walang result")
            return None

        # Tingnan isa-isa kung LIVE + may valid m3u8
        for item in candidates:
            video_id = item.get("id")
            if not video_id:
                continue

            url = f"https://www.youtube.com/watch?v={video_id}"
            info = get_stream_info(url)

            if info and info.get("is_live") and info.get("m3u8"):
                # double check na hindi youtube watch link
                if "youtube.com/watch" not in info["m3u8"] and "youtu.be/" not in info["m3u8"]:
                    print(f"  ✅ LIVE: {info['title'][:65]}")
                    print(f"     → {info['m3u8'][:80]}...")
                    return info

        print("  [!] Walang active live na may valid m3u8")
        return None

    except Exception as e:
        print(f"  [!] Error: {e}")
        return None


def generate_m3u(results):
    lines = [
        "#EXTM3U",
        f"# Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
        "# Direct m3u8 links only (IPTV compatible)",
        ""
    ]

    active = 0
    for item in results:
        name = item["name"]
        info = item.get("info")

        if info and info.get("is_live") and info.get("m3u8"):
            logo = info.get("thumbnail") or ""
            title = info.get("title") or name

            # Clean title (alisin special chars na minsan nakakasira)
            clean_title = title.replace(",", " -").replace('"', "'")

            lines.append(
                f'#EXTINF:-1 tvg-id="{name}" tvg-name="{name}" '
                f'tvg-logo="{logo}" group-title="LIVE",{name} • {clean_title}'
            )
            lines.append(info["m3u8"])
            lines.append("")
            active += 1
        else:
            lines.append(
                f'#EXTINF:-1 tvg-id="{name}" tvg-name="{name}" '
                f'group-title="OFFLINE",{name} [OFFLINE]'
            )
            lines.append(OFFLINE_PLACEHOLDER)
            lines.append("")

    with open(OUTPUT_M3U, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"\n[+] Generated {OUTPUT_M3U} — {active} active live stream(s)")
    print(f"[+] File location: {os.path.abspath(OUTPUT_M3U)}")
    return active


def main():
    print("=" * 55)
    print("YouTube Live → M3U  (Search by Name) - LOCAL")
    print("Direktang m3u8 lang ang ilalagay (IPTV friendly)")
    print("=" * 55)

    # Check yt-dlp
    try:
        subprocess.run(["yt-dlp", "--version"], capture_output=True, check=True)
    except Exception:
        print("\n[!] ERROR: yt-dlp is not installed!")
        print("    Install:  pip install -U yt-dlp")
        print("    or:       sudo apt install yt-dlp")
        sys.exit(1)

    names = parse_names()
    if not names:
        print("[!] Walang pangalan sa streams.txt")
        with open(OUTPUT_M3U, "w") as f:
            f.write("#EXTM3U\n# Walang stream\n")
        return

    print(f"\n[*] Searching {len(names)} name(s)...\n")

    results = []
    for name in names:
        print(f"→ {name}")
        info = search_live(name)
        results.append({"name": name, "info": info})
        if not info:
            print(f"  ❌ OFFLINE / Not found")

    generate_m3u(results)
    print("\nDone. Gamitin ang playlist.m3u sa IPTV player mo.")


if __name__ == "__main__":
    main()

from datetime import datetime, timezone

STREAMS_FILE = "streams.txt"
OUTPUT_M3U = "playlist.m3u"
OFFLINE_PLACEHOLDER = "https://raw.githubusercontent.com/benmoose39/YouTube_to_m3u/main/assets/offline.mp4"


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


def search_live(query: str, max_results: int = 8):
    """Maghanap ng YouTube Live gamit ang yt-dlp search"""
    search_query = f"ytsearch{max_results}:{query} live"

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
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

        if result.returncode != 0:
            print(f"  [!] Search failed: {result.stderr.strip()[:150]}")
            return None

        candidates = []
        for line in result.stdout.strip().split("\n"):
            if not line.strip():
                continue
            try:
                data = json.loads(line)
                candidates.append(data)
            except json.JSONDecodeError:
                continue

        if not candidates:
            print("  [!] Walang result")
            return None

        # Tingnan isa-isa kung live talaga
        for item in candidates:
            video_id = item.get("id")
            title = item.get("title", "")
            url = item.get("url") or item.get("webpage_url") or f"https://www.youtube.com/watch?v={video_id}"

            if not video_id:
                continue

            # Kunin ang detailed info para malaman kung live
            info = get_stream_info(url)
            if info and info.get("is_live") and info.get("m3u8"):
                print(f"  ✅ Found LIVE: {info['title'][:70]}")
                return info

        print("  [!] Walang active live sa search results")
        return None

    except Exception as e:
        print(f"  [!] Error: {e}")
        return None


def get_stream_info(yt_url: str):
    """Kunin ang detailed info + m3u8 ng isang video"""
    try:
        cmd = [
            "yt-dlp",
            "--dump-json",
            "--no-download",
            "--no-warnings",
            "--quiet",
            yt_url
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=40)
        if result.returncode != 0:
            return None

        data = json.loads(result.stdout)

        is_live = data.get("is_live", False) or data.get("live_status") == "is_live"
        title = data.get("title", "Live")
        thumbnail = data.get("thumbnail")
        channel = data.get("channel") or data.get("uploader") or "YouTube"

        m3u8_url = None
        formats = data.get("formats") or []

        # Prefer HLS
        for f in reversed(formats):
            proto = f.get("protocol", "")
            url = f.get("url", "")
            if "m3u8" in proto or ".m3u8" in url:
                m3u8_url = url
                break

        if not m3u8_url:
            for f in reversed(formats):
                if f.get("url"):
                    m3u8_url = f["url"]
                    break

        if not m3u8_url and data.get("url"):
            m3u8_url = data["url"]

        return {
            "is_live": bool(is_live),
            "title": title,
            "thumbnail": thumbnail,
            "channel": channel,
            "m3u8": m3u8_url,
            "original": yt_url,
            "id": data.get("id")
        }
    except Exception:
        return None


def generate_m3u(results):
    lines = [
        "#EXTM3U",
        f"# Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
        "# Auto-updated by GitHub Actions (Search by Name)",
        ""
    ]

    active = 0
    for item in results:
        name = item["name"]
        info = item.get("info")

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
            active += 1
        else:
            lines.append(
                f'#EXTINF:-1 tvg-id="{name}" tvg-name="{name}" '
                f'group-title="OFFLINE",{name} [OFFLINE]'
            )
            lines.append(OFFLINE_PLACEHOLDER)
            lines.append("")

    with open(OUTPUT_M3U, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"\n[+] Generated {OUTPUT_M3U} — {active} active live stream(s)")
    return active


def main():
    print("=" * 55)
    print("YouTube Live → M3U  (Search by Name)")
    print("=" * 55)

    names = parse_names()
    if not names:
        print("[!] Walang pangalan sa streams.txt")
        with open(OUTPUT_M3U, "w") as f:
            f.write("#EXTM3U\n# Walang stream\n")
        return

    print(f"[*] Searching {len(names)} name(s)...\n")

    results = []
    for name in names:
        print(f"→ Searching: {name}")
        info = search_live(name)
        results.append({"name": name, "info": info})
        if not info:
            print(f"  ❌ OFFLINE / Not found")

    generate_m3u(results)
    print("\nDone.")


if __name__ == "__main__":
    main()
