# ReelForge

**Repository:** https://github.com/inamullah47112-svg/reelforge

A Python toolkit for producing vertical (9:16) short videos — the kind you post as Reels, Shorts, and TikToks. It handles the three jobs every faceless-story / documentary pipeline repeats:

1. **Subtitles that actually render correctly** — burned in, bottom-anchored, readable on phones, with proper Urdu/Arabic font handling.
2. **Part assembly** — stitch clips end-to-end without re-encoding.
3. **Audio mixing** — narration over a quiet looping score, synced to the video length.

Built from a real production pipeline that shipped a 3.6-minute vertical documentary. Requires `ffmpeg` + `ffprobe` on your PATH.

## Why not just use ffmpeg's `subtitles` filter?

Because it silently breaks positioning. The `subtitles` filter converts SRT to ASS with **no PlayRes header**, so libass falls back to its default **384×288 canvas** regardless of your video size. On a 720×1280 video that means:

- text renders ~4.4× too big, and
- `Alignment=2` + `MarginV` lands the text in the **middle** of the frame, over your subject.

`original_size=` doesn't fix it cleanly. ReelForge hand-writes `.ass` files with `PlayResX`/`PlayResY` matching your real video size and burns them with the **`ass=`** filter — deterministic placement, every time. Verified values at true 1280 height: `FontSize=96`, `Alignment=2`, `MarginV=100`, bottom-anchored and phone-friendly.

Related gotcha, also handled: **Noto Nastaliq Urdu does not render** in many ffmpeg/libass stacks (tofu boxes). ReelForge auto-detects fonts and prefers **Noto Naskh Arabic Bold** — the verified working traditional Urdu look — with sane fallbacks.

## Install

```bash
pip install .
# needs ffmpeg + ffprobe on PATH, and fonts-noto for Urdu/Arabic subs
```

## Quickstart

```bash
# 1. narration text -> timed, correctly-rendered subtitles
reelforge subs --text script.txt --duration 29 --out subs.ass

# 2. burn them into the clip
reelforge burn --video part.mp4 --subs subs.ass --out part_subbed.mp4

# 3. mix narration (+ quiet score) under it
reelforge mix --video part_subbed.mp4 --narration narration.mp3 \
    --score score.wav --out part_final.mp4

# 4. stitch finished parts (no re-encode)
reelforge concat --parts part1_final.mp4 part2_final.mp4 --out full.mp4
```

`script.txt` is plain paragraphs separated by blank lines — long lines are auto-split at natural joints (≤ 40 chars) and timed proportionally to the video length.

Or do it from Python — see [`examples/quickstart.py`](examples/quickstart.py):

```python
from reelforge import split_long_lines, auto_timings, write_ass, probe_duration
from reelforge.video import burn
from reelforge.audio import mix

lines = split_long_lines(open("script.txt", encoding="utf-8").read())
events = auto_timings(lines, probe_duration("part.mp4"))
write_ass(events, "subs.ass", width=720, height=1280)
burn("part.mp4", "subs.ass", "part_subbed.mp4")
mix("part_subbed.mp4", "narration.mp3", "part_final.mp4", score="score.wav")
```

## API

| Function | What it does |
|---|---|
| `subtitles.write_ass(events, path, width, height, ...)` | Write a correct `.ass` file (PlayRes set, bottom-anchored style) |
| `subtitles.srt_to_ass(srt, ass, ...)` | Convert SRT → correctly-rendered ASS (fixes the 384×288 bug) |
| `subtitles.auto_timings(lines, duration, ...)` | Proportional subtitle timing with lead-in/tail guards |
| `subtitles.split_long_lines(text, max_chars=40)` | Split paragraphs at natural joints, Urdu punctuation aware |
| `subtitles.detect_font()` | Best available subtitle font (Noto Naskh Arabic → Noto Sans Arabic → DejaVu) |
| `video.concat(parts, out)` | Stitch parts, stream copy |
| `video.burn(video, ass, out, ...)` | Burn `.ass` subs via the `ass=` filter |
| `audio.mix(video, narration, out, score, ...)` | Narration + looping score under video |
| `video.probe_duration / probe_size` | ffprobe helpers |

## Roadmap

- Keyframe-anchored multi-character scene prompts (text-to-video)
- Word-level karaoke timing from TTS output
- Auto caption styling presets (documentary / comedy / horror)

## License

MIT — see [LICENSE](LICENSE).
