"""ReelForge command-line interface."""

import argparse
import sys

from . import subtitles as S
from . import video as V
from . import audio as A


def cmd_subs(args):
    with open(args.text, encoding="utf-8") as f:
        raw = f.read()
    lines = []
    for para in raw.split("\n\n"):
        para = " ".join(para.split())
        if para:
            lines.extend(S.split_long_lines(para, args.max_chars))
    events = S.auto_timings(lines, args.duration,
                            lead_in=args.lead_in, tail=args.tail)
    S.write_ass(events, args.out, width=args.width, height=args.height,
                font=args.font)
    print(f"wrote {args.out} ({len(events)} cues)")


def cmd_burn(args):
    V.burn(args.video, args.subs, args.out, crf=args.crf, preset=args.preset)
    print(f"wrote {args.out}")


def cmd_mix(args):
    A.mix(args.video, args.narration, args.out, score=args.score,
          duration=args.duration, narr_delay=args.narr_delay,
          score_gain=args.score_gain)
    print(f"wrote {args.out}")


def cmd_concat(args):
    V.concat(args.parts, args.out)
    print(f"wrote {args.out}")


def build_parser():
    p = argparse.ArgumentParser(
        prog="reelforge",
        description="Toolkit for vertical (9:16) short-video production.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("subs", help="text paragraphs -> timed .ass subtitles")
    s.add_argument("--text", required=True, help="input .txt (blank line = paragraph)")
    s.add_argument("--duration", type=float, required=True, help="video length, seconds")
    s.add_argument("--out", required=True, help="output .ass path")
    s.add_argument("--width", type=int, default=720)
    s.add_argument("--height", type=int, default=1280)
    s.add_argument("--font", default=None, help="font family (auto-detected if omitted)")
    s.add_argument("--max-chars", type=int, default=40)
    s.add_argument("--lead-in", type=float, default=0.8)
    s.add_argument("--tail", type=float, default=0.4)
    s.set_defaults(func=cmd_subs)

    b = sub.add_parser("burn", help="burn .ass subtitles into a video")
    b.add_argument("--video", required=True)
    b.add_argument("--subs", required=True, help=".ass file (use `subs` to make one)")
    b.add_argument("--out", required=True)
    b.add_argument("--crf", type=int, default=20)
    b.add_argument("--preset", default="fast")
    b.set_defaults(func=cmd_burn)

    m = sub.add_parser("mix", help="mux narration (+ score) under a video")
    m.add_argument("--video", required=True)
    m.add_argument("--narration", required=True)
    m.add_argument("--out", required=True)
    m.add_argument("--score", default=None, help="ambient music, looped quietly")
    m.add_argument("--duration", type=float, default=None)
    m.add_argument("--narr-delay", type=float, default=0.8)
    m.add_argument("--score-gain", type=float, default=0.12)
    m.set_defaults(func=cmd_mix)

    c = sub.add_parser("concat", help="stitch parts end-to-end (no re-encode)")
    c.add_argument("--parts", nargs="+", required=True)
    c.add_argument("--out", required=True)
    c.set_defaults(func=cmd_concat)

    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        args.func(args)
    except RuntimeError as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
