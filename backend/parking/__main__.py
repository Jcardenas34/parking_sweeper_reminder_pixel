"""Build-time asset generator: `python -m parking --export-android RES_DIR --export-web DIR`."""

from __future__ import annotations

import argparse
from pathlib import Path

from .android_art import export_android_art, export_web_art
from .audio import export_jingles


def main() -> None:
    parser = argparse.ArgumentParser(prog="pixel-parking")
    parser.add_argument("--export-android", type=Path, metavar="RES_DIR",
                        help="write jingles, launcher/notification icons and splash into an Android res/ dir")
    parser.add_argument("--export-web", type=Path, metavar="DIR",
                        help="write the header street and car sprite sheet for the web UI")
    parser.add_argument("--hd-sample", type=Path, metavar="PNG",
                        help="write a high-resolution sample of the 45-degree street scene")
    parser.add_argument("--hd-scale", type=int, default=3, metavar="K",
                        help="how many times the app header's resolution for --hd-sample (default 3)")
    args = parser.parse_args()
    if not (args.export_android or args.export_web or args.hd_sample):
        parser.error("nothing to do: pass --export-android, --export-web and/or --hd-sample")

    if args.hd_sample:
        from .imaging.hires import rear_scene_hd

        args.hd_sample.parent.mkdir(parents=True, exist_ok=True)
        rear_scene_hd(args.hd_scale).save(args.hd_sample)
        print(f"wrote {args.hd_scale}x 45-degree sample to {args.hd_sample}")

    if args.export_web:
        export_web_art(args.export_web)
        print(f"wrote web art to {args.export_web}")
    if args.export_android:
        export_jingles(args.export_android / "raw")
        export_android_art(args.export_android)
        print(f"wrote Android jingles, icons and splash to {args.export_android}")


if __name__ == "__main__":
    main()
