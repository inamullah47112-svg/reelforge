"""Audio helpers: narration + ambient score mixing (ffmpeg)."""

import os
import subprocess


def _run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(
            f"ffmpeg failed: {' '.join(cmd[:6])}...\n{r.stderr[-2000:]}"
        )
    return r


def mix(video, narration, out, score=None, duration=None,
        narr_delay=0.8, score_gain=0.12):
    """Mux narration (+ optional looping score) under a video.

    - narration starts after ``narr_delay`` seconds and is padded to the
      full duration;
    - score loops and sits quietly under the voice at ``score_gain``;
    - output keeps the video stream untouched (``-c:v copy``).
    """
    from .video import probe_duration
    duration = duration or probe_duration(video)
    score = os.path.abspath(score) if score else None

    inputs = ["-i", video, "-i", narration]
    if score:
        inputs += ["-stream_loop", "-1", "-i", score]

    fc = (
        f"[1:a]adelay={int(narr_delay * 1000)}|{int(narr_delay * 1000)},"
        f"apad,atrim=0:{duration}[narr]"
    )
    if score:
        fc += (
            f";[2:a]atrim=0:{duration},volume={score_gain}[score];"
            "[narr][score]amix=inputs=2:duration=first:"
            "dropout_transition=0[a]"
        )
        amap = "[a]"
    else:
        amap = "[narr]"

    _run(["ffmpeg", "-y", "-loglevel", "error", *inputs,
          "-filter_complex", fc,
          "-map", "0:v", "-map", amap,
          "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
          "-ar", "44100", "-ac", "2",
          "-t", str(duration), "-shortest", out])
    return out
