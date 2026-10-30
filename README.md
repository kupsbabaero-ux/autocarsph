# YouTube Live → M3U Auto Updater

Automatic na nag-uupdate ng M3U playlist mula sa YouTube Live links.  
Kapag **tapos na ang live**, automatic na magiging OFFLINE ang entry.

## Paano gamitin

### 1. I-upload ito sa GitHub
1. Gumawa ng bagong repository (hal. `my-live-m3u`)
2. I-upload lahat ng files dito (o extract ang zip at `git push`)

### 2. I-enable ang GitHub Actions
- Pumunta sa **Actions** tab
- I-enable ang workflows kung naka-disable

### 3. Maglagay ng Live Links
I-edit ang `streams.txt`:

```txt
# Format: Channel Name | YouTube URL
NBA Finals | https://www.youtube.com/watch?v=XXXXX
Boxing | https://www.youtube.com/@Channel/live
```

Pag-save at push → automatic na tatakbo ang updater.

### 4. Gamitin ang M3U sa player
```
https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_REPO/main/playlist.m3u
```

Mas mabilis (CDN):
```
https://cdn.jsdelivr.net/gh/YOUR_USERNAME/YOUR_REPO@main/playlist.m3u
```

## Schedule
- Automatic every **20 minutes**
- Pwede ring i-manual run sa Actions tab → "Update YouTube Live M3U" → Run workflow

## Notes
- Gumagamit ng **yt-dlp** (pinakareliable para sa YouTube)
- Kapag hindi na live → lalabas bilang `[OFFLINE]`
- Pwede mong baguhin ang offline placeholder sa `generate.py`

## Files
| File | Description |
|------|-------------|
| `streams.txt` | Dito ka maglalagay ng YouTube links |
| `generate.py` | Script na kumukuha ng stream |
| `playlist.m3u` | Output na playlist (auto-generated) |
| `.github/workflows/update.yml` | GitHub Actions scheduler |
