#!/usr/bin/env python3
"""Find, cut and encode meme clips listed in clips.json.

For each clip: use `url` (+ optional `start`/`end`) if given, otherwise search
YouTube with `query` and pick the shortest short video whose title matches.
Writes public/clips/<id>.mp3 and public/clips.js (the board's manifest).

  python3 tools/fetch.py            # fetch missing clips
  python3 tools/fetch.py --force id # re-fetch one clip
"""
import hashlib, json, re, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLIPS = ROOT / "public" / "clips"
MAX_SECONDS = 12
CACHE = ROOT / ".cache"


def search(query, n=15):
    out = subprocess.run(
        ["yt-dlp", "--no-update", "--flat-playlist", "--print",
         "%(id)s\t%(duration)s\t%(title)s", f"ytsearch{n}:{query}"],
        capture_output=True, text=True).stdout
    rows = []
    for line in out.splitlines():
        parts = line.split("\t", 2)
        if len(parts) == 3 and parts[1] not in ("NA", "None"):
            rows.append((parts[0], float(parts[1]), parts[2]))
    return rows


def pick(clip):
    """Return the shortest video whose title contains a match word, or None."""
    words = [w.lower() for w in clip.get("match", [])]
    base = clip["query"].replace("meme template", "").strip()
    for q in (clip["query"], base + " shorts", base + " comedy"):
        rows = [r for r in search(q) if 2 <= r[1] <= 25 and r[0] not in clip.get("avoid", [])
                and any(w in r[2].lower() for w in words)]
        if rows:
            return min(rows, key=lambda r: r[1]), True
    return None


def seconds(ts):
    """'1:19.5' -> 79.5"""
    total = 0.0
    for part in str(ts).split(":"):
        total = total * 60 + float(part)
    return total


def download(url):
    """Full audio of a video, cached so several clips from one scene download once."""
    CACHE.mkdir(exist_ok=True)
    vid = re.search(r"(?:v=|youtu\.be/|shorts/)([\w-]{11})", url)
    key = vid.group(1) if vid else hashlib.sha1(url.encode()).hexdigest()[:11]
    hit = next(CACHE.glob(f"{key}.*"), None)
    if not hit:
        subprocess.run(["yt-dlp", "--no-update", "-q", "-f", "bestaudio/best",
                        "-o", str(CACHE / f"{key}.%(ext)s"), "--", url], check=True)
        hit = next(CACHE.glob(f"{key}.*"))
    return hit


def cut(url, dest, start=None, end=None):
    src = download(url)
    if start is not None:
        # Exact window from captions: cut precisely, keep the edges as given.
        s, e = seconds(start), seconds(end)
        length = min(e - s, MAX_SECONDS)
        window, trim = ["-ss", str(s), "-t", str(length)], ""
    else:
        length = MAX_SECONDS
        window = ["-t", str(MAX_SECONDS)]
        trim = ("silenceremove=start_periods=1:start_threshold=-45dB,"
                "areverse,silenceremove=start_periods=1:start_threshold=-45dB,areverse,")
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", *window, "-i", str(src),
         "-af", trim + "loudnorm=I=-16:TP=-1.5,afade=t=out:st=%.2f:d=0.3" % (length - 0.3),
         "-ac", "1", "-ar", "44100", "-b:a", "64k", str(dest)],
        check=True)


def duration(path):
    if not Path(path).exists() or Path(path).stat().st_size == 0:
        return 0
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", str(path)], capture_output=True, text=True).stdout
    try:
        return round(float(out.strip()), 1)
    except ValueError:
        return 0


def main():
    force = set(sys.argv[2:]) if sys.argv[1:2] == ["--force"] else set()
    clips = json.loads((ROOT / "clips.json").read_text())
    meta_path = ROOT / "sources.json"
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    CLIPS.mkdir(parents=True, exist_ok=True)

    for c in clips:
        dest = CLIPS / f"{c['id']}.mp3"
        if dest.exists() and c["id"] not in force:
            continue
        try:
            if c.get("url"):
                url, info = c["url"], {"source": c["url"], "confident": True}
                cut(url, dest, c.get("start"), c.get("end"))
            else:
                found = pick(c)
                if not found:
                    print(f"  miss  {c['id']}: no results"); continue
                (vid, dur, title), confident = found
                url = f"https://www.youtube.com/watch?v={vid}"
                cut(url, dest)
                info = {"source": url, "title": title, "confident": confident}
            if duration(dest) < 1:
                dest.unlink(missing_ok=True)
                print(f"  fail  {c['id']}: no audio in {url}"); continue
            meta[c["id"]] = info
            print(f"  {'ok ' if info['confident'] else 'chk'}   {c['id']}  <- {info.get('title', url)}")
        except Exception as e:
            print(f"  fail  {c['id']}: {e}")

    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False))
    board = []
    for c in clips:
        f = CLIPS / f"{c['id']}.mp3"
        if f.exists():
            board.append({k: c[k] for k in ("id", "label", "actor", "movie") if k in c}
                         | {"file": f"clips/{c['id']}.mp3", "seconds": duration(f)})
    (ROOT / "public" / "clips.js").write_text(
        "window.CLIPS = " + json.dumps(board, indent=1, ensure_ascii=False) + ";\n")
    # New cache version whenever the clip set changes, so installed boards update.
    sw = ROOT / "public" / "sw.js"
    version = hashlib.sha1(json.dumps(board).encode()).hexdigest()[:8]
    sw.write_text(re.sub(r"const VERSION = '[^']*';", f"const VERSION = '{version}';", sw.read_text()))
    print(f"{len(board)} clips on the board")


if __name__ == "__main__":
    main()
