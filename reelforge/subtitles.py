"""Subtitle generation with correct libass rendering.

The classic pitfall: ffmpeg's ``subtitles`` filter converts SRT to ASS with
*no* PlayRes header, so libass falls back to its default 384x288 canvas.
On a 720x1280 video that makes text ~4.4x too big and pushes Alignment=2
text into the middle of the frame. The fix used here: hand-write .ass files
with PlayResX/PlayResY matching the real video size and burn them with the
``ass=`` filter. Deterministic placement, every time.
"""

import re
import subprocess

# Verified good defaults at true 1280 height (bottom-anchored, phone-friendly).
# They scale automatically with the output height.
_REF_H = 1280
_REF_W = 720
_REF_FONTSIZE = 96
_REF_MARGIN_V = 100
_REF_MARGIN_LR = 40

# Font preference chain. Noto Nastaliq Urdu does NOT render in many
# ffmpeg/libass stacks (tofu boxes); Noto Naskh Arabic Bold is the
# verified working traditional Urdu look. Noto Sans Arabic also works.
_FONT_PREFERENCE = [
    "Noto Naskh Arabic",
    "Noto Sans Arabic",
    "DejaVu Sans",
]

_URDU_PUNCT = "۔،؟؛"


def detect_font():
    """Return the best available subtitle font family name.

    Walks the preference chain via fc-list; falls back to the first
    preferred name even if nothing matches (libass will substitute).
    """
    try:
        out = subprocess.run(
            ["fc-list", ":", "family"], capture_output=True, text=True
        ).stdout.lower()
    except (FileNotFoundError, OSError):
        out = ""
    for fam in _FONT_PREFERENCE:
        if fam.lower() in out:
            return fam
    return _FONT_PREFERENCE[0]


def split_long_lines(text, max_chars=40):
    """Split a paragraph into subtitle lines of <= max_chars.

    Splits greedily at word boundaries, preferring breaks after
    sentence-ending punctuation (Urdu + Latin). Keeps every line on
    at most ~2 wrapped rows at phone sizes.
    """
    words = text.split()
    lines, cur = [], ""
    for w in words:
        trial = f"{cur} {w}".strip()
        if len(trial) <= max_chars:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
        # Prefer a break right after sentence-ending punctuation.
        if cur and cur[-1] in _URDU_PUNCT + ".!?":
            lines.append(cur)
            cur = ""
    if cur:
        lines.append(cur)
    # Merge a tiny trailing fragment into the previous line when safe.
    if len(lines) >= 2 and len(lines[-1]) < max_chars // 3:
        prev = lines.pop()
        if len(lines[-1]) + 1 + len(prev) <= max_chars:
            lines[-1] = f"{lines[-1]} {prev}"
        else:
            lines.append(prev)
    return lines


def auto_timings(lines, total_duration, lead_in=0.8, tail=0.4, min_line=1.6):
    """Distribute subtitle timings proportionally to line length.

    Every line gets at least ``min_line`` seconds; the last line never
    runs past ``total_duration - tail``. Returns [(start, end, text)].
    """
    total_chars = sum(len(l) for l in lines) or 1
    usable = max(min_line, total_duration - lead_in - tail)
    events, t = [], lead_in
    for i, line in enumerate(lines):
        dur = max(min_line, usable * len(line) / total_chars)
        end = t + dur
        if i == len(lines) - 1:
            end = min(end, total_duration - tail)
        events.append((round(t, 2), round(end, 2), line))
        t = end
    return events


def _ass_timestamp(t):
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def _ass_header(width, height, font, font_size, margin_v, margin_lr, bold=True):
    return f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font},{font_size},&H00FFFFFF,&H000000FF,&H90000000,&H00000000,{"-1" if bold else "0"},0,0,0,100,100,0,0,1,2,0,2,{margin_lr},{margin_lr},{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def write_ass(events, path, width=720, height=1280, font=None,
              font_size=None, margin_v=None, margin_lr=None):
    """Write an .ass subtitle file with correct PlayRes for the video size.

    ``events``: iterable of (start_sec, end_sec, text). Sizes default to
    the verified 720x1280 look and scale with ``height``/``width``.
    Burn the result with the ``ass=`` filter (see :mod:`reelforge.video`).
    """
    font = font or detect_font()
    scale = height / _REF_H
    font_size = font_size or max(8, int(_REF_FONTSIZE * scale))
    margin_v = margin_v if margin_v is not None else int(_REF_MARGIN_V * scale)
    margin_lr = margin_lr if margin_lr is not None else int(_REF_MARGIN_LR * (width / _REF_W))

    with open(path, "w", encoding="utf-8") as f:
        f.write(_ass_header(width, height, font, font_size, margin_v, margin_lr))
        for start, end, text in events:
            safe = text.replace("\n", "\\N")
            f.write(
                f"Dialogue: 0,{_ass_timestamp(start)},{_ass_timestamp(end)},"
                f"Default,,0,0,0,,{safe}\n"
            )
    return path


def srt_to_events(srt_path):
    """Parse an .srt file into [(start, end, text)] events."""
    with open(srt_path, encoding="utf-8") as f:
        content = f.read()
    blocks = re.split(r"\n\s*\n", content.strip())
    events = []
    for block in blocks:
        lines = block.strip().splitlines()
        if len(lines) < 3:
            continue
        m = re.match(
            r"(\d+):(\d+):([\d.,]+)\s*-->\s*(\d+):(\d+):([\d.,]+)", lines[1]
        )
        if not m:
            continue
        def _sec(h, mi, s):
            return int(h) * 3600 + int(mi) * 60 + float(s.replace(",", "."))
        start = _sec(*m.groups()[:3])
        end = _sec(*m.groups()[3:])
        text = " ".join(l.strip() for l in lines[2:])
        events.append((start, end, text))
    return events


def srt_to_ass(srt_path, ass_path, width=720, height=1280, **kwargs):
    """Convert .srt to a correctly-rendered .ass (fixes the 384x288 bug)."""
    return write_ass(srt_to_events(srt_path), ass_path, width, height, **kwargs)
