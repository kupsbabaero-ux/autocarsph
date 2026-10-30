# YouTube Live → M3U (Search by Name)

**Ilagay mo lang ang pangalan** ng match/stream.  
Automatic na maghahanap ng matching YouTube Live.

Kapag **tapos na ang live** → automatic magiging `[OFFLINE]`.

---

## Paano gamitin

### 1. I-upload sa GitHub
1. Gumawa ng bagong repository
2. I-upload lahat ng files (extract zip → upload)
3. Pumunta sa **Actions** tab → i-enable ang workflow

### 2. Maglagay ng pangalan
I-edit ang `streams.txt`:

```txt
NBA Finals Game 1
UFC 309
Manny Pacquiao
Lakers vs Celtics Live
Boxing Championship
```

**Hindi na kailangan ng YouTube link.**  
Save + push → automatic tatakbo.

### 3. Gamitin ang M3U
```
https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_REPO/main/playlist.m3u
```

Mas mabilis (CDN):
```
https://cdn.jsdelivr.net/gh/YOUR_USERNAME/YOUR_REPO@main/playlist.m3u
```

---

## Schedule
- Automatic every **20 minutes**
- Pwede ring i-manual run sa Actions tab

## Tips para mas accurate ang search
- Mas specific ang pangalan = mas accurate  
  Halimbawa: `NBA Finals 2026 Game 3` mas maganda kaysa `NBA`
- Pwede mong isama ang "Live", "vs", year, etc.

## Files
| File | Description |
|------|-------------|
| `streams.txt` | Dito ka maglalagay ng **pangalan lang** |
| `generate.py` | Script na naghahanap + gumagawa ng M3U |
| `playlist.m3u` | Output (auto-generated) |
| `.github/workflows/update.yml` | Scheduler |

---

Gawa ni Grok • Free to use
