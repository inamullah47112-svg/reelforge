"""End-to-end example: one finished 9:16 part from raw assets.

Assets needed in this folder:
    part.mp4        - silent vertical clip (720x1280)
    narration.mp3   - voiceover
    score.wav       - ambient music (optional)
    script.txt      - narration text, blank line between paragraphs
"""
from reelforge import (
    split_long_lines, auto_timings, write_ass,
    probe_duration, probe_size,
)
from reelforge.video import burn
from reelforge.audio import mix

# 1. Subtitles: split into short lines, time them, write a correct .ass
with open("script.txt", encoding="utf-8") as f:
    paras = [p for p in f.read().split("\n\n") if p.strip()]
lines = []
for para in paras:
    lines.extend(split_long_lines(" ".join(para.split()), max_chars=40))

duration = probe_duration("part.mp4")
w, h = probe_size("part.mp4")
events = auto_timings(lines, duration)
write_ass(events, "subs.ass", width=w, height=h)
print(f"subtitles: {len(events)} cues -> subs.ass")

# 2. Burn subtitles into the video
burn("part.mp4", "subs.ass", "part_subbed.mp4")
print("video: part_subbed.mp4")

# 3. Mix narration (+ quiet looping score) under it
mix("part_subbed.mp4", "narration.mp3", "part_final.mp4",
    score="score.wav", duration=duration)
print("final: part_final.mp4")
