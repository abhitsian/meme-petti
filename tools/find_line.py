#!/usr/bin/env python3
"""Find a dialogue's timestamp by searching YouTube scene videos' Tamil captions.

  python3 tools/find_line.py targets.json   # [{"id", "queries": [...], "keys": [tamil words]}]

Prints, per target, each caption hit as  <video id> <m:ss> <line>  with one line of
context either side, so the clip window can be read off and added to clips.json.
"""
import json, re, subprocess, sys, tempfile
from pathlib import Path


def search(q, n=10):
    out = subprocess.run(["yt-dlp", "--no-update", "--flat-playlist", "--print",
                          "%(id)s\t%(duration)s\t%(title)s", f"ytsearch{n}:{q}"],
                         capture_output=True, text=True).stdout
    for line in out.splitlines():
        vid, dur, title = (line.split("\t", 2) + ["", ""])[:3]
        if dur not in ("NA", "None", "") and 20 <= float(dur) <= 1800:
            yield vid, title


def captions(vid, tmp):
    subprocess.run(["yt-dlp", "--no-update", "-q", "--skip-download", "--write-auto-subs",
                    "--write-subs", "--sub-langs", "ta", "--sub-format", "vtt",
                    "-o", f"{tmp}/{vid}.%(ext)s", "--", f"https://www.youtube.com/watch?v={vid}"],
                   capture_output=True)
    f = Path(tmp) / f"{vid}.ta.vtt"
    if not f.exists():
        return []
    rows, seen, t = [], set(), None
    for line in f.read_text(encoding="utf-8").splitlines():
        m = re.match(r"(\d+):(\d+):(\d+)\.(\d+) -->", line)
        if m:
            t = int(m[1]) * 3600 + int(m[2]) * 60 + int(m[3]) + int(m[4]) / 1000; continue
        txt = re.sub(r"<[^>]+>", "", line).strip()
        if txt and t is not None and txt not in seen and not txt.startswith(("Kind:", "Language:")):
            seen.add(txt); rows.append((t, txt))
    return rows


def main():
    for target in json.loads(Path(sys.argv[1]).read_text()):
        print(f"\n##### {target['id']}")
        seen, found = set(), 0
        with tempfile.TemporaryDirectory() as tmp:
            for q in target["queries"]:
                for vid, title in search(q):
                    if vid in seen or found >= 3:
                        continue
                    seen.add(vid)
                    rows = captions(vid, tmp)
                    hits = [i for i, (_, txt) in enumerate(rows) if any(k in txt for k in target["keys"])]
                    if not hits:
                        continue
                    found += 1
                    print(f"--- {vid}  {title[:90]}")
                    for i in hits[:4]:
                        for t, txt in rows[max(0, i - 1): i + 2]:
                            print(f"   {int(t // 60)}:{t % 60:04.1f}  {txt}")
                        print("   ·")
        if not found:
            print("   no caption hit")


if __name__ == "__main__":
    main()
