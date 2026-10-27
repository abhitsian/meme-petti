# Meme Petti

A pocket soundboard of Tamil movie comedy dialogues. Tap a card to play it, tap ↗ to send the clip on WhatsApp, and add the page to your home screen to use it like an app, offline.

**Open it:** https://abhitsian.github.io/meme-petti/

## Add a clip

1. Add an entry to `clips.json`. Either give a `query` and `match` words (the script searches YouTube and picks the shortest video whose title matches), or a `url` with `start` and `end` (e.g. `"1:23"`).
2. Run `python3 tools/fetch.py` (needs `yt-dlp` and `ffmpeg`). Use `--force <id>` to re-fetch one clip.
3. Commit and push. GitHub Pages redeploys `public/`, and installed phones pick up the new clips.

Clips are short excerpts from Tamil films, shared for fun among friends. Rights belong to the film producers.
