"""ReelForge — toolkit for vertical (9:16) short-video production.

Burn subtitles correctly, stitch parts, and mix narration over a score,
with ffmpeg doing the heavy lifting.
"""

__version__ = "0.1.0"

from .subtitles import write_ass, auto_timings, split_long_lines, detect_font
from .video import probe_duration, probe_size, concat, burn
from .audio import mix

__all__ = [
    "write_ass",
    "auto_timings",
    "split_long_lines",
    "detect_font",
    "probe_duration",
    "probe_size",
    "concat",
    "burn",
    "mix",
]
