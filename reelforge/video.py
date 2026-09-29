"""Video helpers: probing, concatenation, and subtitle burning (ffmpeg)."""

import os
import subprocess
import tempfile


def _run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(
            f"ffmpeg failed: {' '.join(cmd[:6])}...\n{r.stderr[-2000:]}"
        )
    return r


def probe_duration(path):
    """Media duration in seconds (ffprobe)."""
    r = _run([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "csv=p=0", path,
    ])
    return float(r.stdout.strip())


def probe_size(path):
    """(width, height) of the first video stream."""
    r = _run([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height", "-of", "csv=p=0", path,
    ])
    w, h = r.stdout.strip().split(",")
    return int(w), int(h)


def concat(parts, out):
    """Stitch video parts end-to-end (stream copy, no re-encode)."""
    with tempfile.NamedTemporaryFile(
        "w", suffix=".txt", delete=False, encoding="utf-8"
    ) as f:
        for p in parts:
            f.write(f"file '{os.path.abspath(p)}'\n")
        list_path = f.name
    try:
        _run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat",
              "-safe", "0", "-i", list_path, "-c", "copy", out])
    finally:
        os.unlink(list_path)
    return out


def burn(video, ass_path, out, crf=20, preset="fast", fps=25):
    """Burn .ass subtitles into a video (the ``ass=`` filter, not ``subtitles``).

    The .ass file must carry PlayResX/PlayResY matching the video —
    use :func:`reelforge.subtitles.write_ass` to generate it.
    """
    _run([
        "ffmpeg", "-y", "-loglevel", "error", "-i", video,
        "-vf", f"ass={os.path.abspath(ass_path)},format=yuv420p",
        "-c:v", "libx264", "-preset", preset, "-crf", str(crf),
        "-r", str(fps), "-c:a", "copy", out,
    ])
    return out
