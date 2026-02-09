from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from .core import IconSource, apply_icons, create_icon_outputs
from .emoji_sources import (
    emojipedia_best_artwork_url,
    emojipedia_search,
    parse_emoji_argument,
    twemoji_svg_url,
)
from .windows import elevate_if_needed, is_windows, refresh_windows_icons


def _prompt(msg: str, default: str | None = None) -> str:
    suffix = f" [{default}]" if default is not None else ""
    v = input(f"{msg}{suffix}: ").strip()
    return v if v else (default or "")


def _prompt_choice(msg: str, options: list[str], default_idx: int = 0) -> int:
    print(msg)
    for i, opt in enumerate(options, start=1):
        d = " (default)" if (i - 1) == default_idx else ""
        print(f"  {i}. {opt}{d}")
    while True:
        raw = input(f"Choose 1-{len(options)} [{default_idx+1}]: ").strip()
        if not raw:
            return default_idx
        if raw.isdigit():
            idx = int(raw) - 1
            if 0 <= idx < len(options):
                return idx


def wizard() -> int:
    print("iconify wizard")
    print("=============")

    target_mode = _prompt_choice(
        "What do you want to do?",
        ["Generate icons only (no apply)", "Apply icon to a folder", "Apply icon to a drive root"],
        default_idx=1,
    )
    target_path: Path | None = None
    is_drive = False
    if target_mode in (1, 2):
        is_drive = target_mode == 2
        tp = _prompt("Target path", default="G:\\" if is_drive and is_windows() else str(Path.cwd()))
        target_path = Path(tp)

    source_mode = _prompt_choice(
        "Pick icon source",
        ["Emojipedia search (best quality)", "Twemoji by name/code/emoji char", "Local image file", "Image/SVG URL"],
        default_idx=0,
    )

    if source_mode == 0:
        q = _prompt("Search Emojipedia for", default="fox")
        results = emojipedia_search(q, limit=10)
        if not results:
            print("No Emojipedia results found; falling back to Twemoji.")
            emoji_code = parse_emoji_argument(q)
            source = IconSource(kind="url", value=twemoji_svg_url(emoji_code), label=f"Twemoji:{q}")
        else:
            print("\nResults:")
            for i, r in enumerate(results, start=1):
                print(f"  {i}. {r.title} ({r.path})")
            pick_raw = _prompt("Pick result number", default="1")
            try:
                pick_n = int(pick_raw)
            except ValueError:
                pick_n = 1
            pick = max(1, min(len(results), pick_n)) - 1
            # Second-level: pick a vendor design (default) or Twemoji
            emoji_slug = results[pick].path.strip("/").split("/", 1)[0]
            try:
                from .emoji_sources import emojipedia_list_designs

                designs = emojipedia_list_designs(emoji_slug)
            except Exception:
                designs = []

            if designs:
                print("\nDesigns:")
                print("  0. Twemoji (vector, recommended)")
                for i, d in enumerate(designs, start=1):
                    extra = f" — {d.item_title}" if d.item_title else ""
                    print(f"  {i}. {d.vendor_title}{extra}")
                d_raw = _prompt("Pick design number", default="1")
                try:
                    d_n = int(d_raw)
                except ValueError:
                    d_n = 1
                if d_n <= 0:
                    from .emoji_sources import emojipedia_pick_source

                    picked = emojipedia_pick_source(results[pick].title, alt=0, art="twemoji")
                    if picked is None:
                        emoji_code = parse_emoji_argument(results[pick].title)
                        source = IconSource(kind="url", value=twemoji_svg_url(emoji_code), label=f"Twemoji:{results[pick].title}")
                    else:
                        source = picked
                else:
                    d_idx = max(0, min(len(designs) - 1, d_n - 1))
                    d = designs[d_idx]
                    source = IconSource(kind="url", value=d.source_url, label=f"Emojipedia(design:{d.vendor_title}):{results[pick].title}")
            else:
                # Fallback to our prior auto logic
                art_url = emojipedia_best_artwork_url(results[pick].url)
                if not art_url:
                    print("Could not extract artwork; falling back to Twemoji.")
                    emoji_code = parse_emoji_argument(results[pick].title)
                    art_url = twemoji_svg_url(emoji_code)
                source = IconSource(kind="url", value=art_url, label=f"Emojipedia:{results[pick].title}")
    elif source_mode == 1:
        e = _prompt("Emoji (e.g. fox, 1f98a, 🦊)", default="fox")
        emoji_code = parse_emoji_argument(e)
        source = IconSource(kind="url", value=twemoji_svg_url(emoji_code), label=f"Twemoji:{e}")
    elif source_mode == 2:
        p = _prompt("Image path", default=str(Path.cwd()))
        source = IconSource(kind="path", value=str(Path(p)), label=f"Image:{p}")
    else:
        u = _prompt("Image/SVG URL")
        source = IconSource(kind="url", value=u, label=f"URL:{u}")

    out_dir = Path(_prompt("Output directory", default=str(Path.cwd() / "icon_output")))
    outputs = create_icon_outputs(source, output_dir=out_dir)
    print(f"\nGenerated icons in: {outputs.output_dir}")

    if target_path is not None:
        try:
            apply_icons(outputs, target_path, is_drive=is_drive, windows=True, mac=False)
            print(f"Applied icon to: {target_path}")
        except PermissionError as e:
            print("\nCould not apply icon (permission denied).")
            print(f"Target: {target_path}")
            print("Tip: pick a writable folder or re-run with `--apply <path>`.")
            print("Tip: for drives or protected locations, try `--force` to elevate.")
            return 2
        if is_windows():
            if _prompt("Refresh Windows icon cache now? (y/n)", default="n").lower().startswith("y"):
                refresh_windows_icons()

    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="iconify", description="Create and apply custom icons for Windows drives and folders.")
    p.add_argument("--wizard", action="store_true", help="Run the interactive step-by-step wizard (default).")
    p.add_argument("--emoji", help="Twemoji: name/code/emoji char to use as icon source.")
    p.add_argument("--emojipedia", help="Emojipedia search query (best-effort auto-pick).")
    p.add_argument("--alt", type=int, default=0, help="For --emojipedia: pick the Nth search result (0-based). Default: 0")
    p.add_argument("--result", type=int, help="Alias for --alt (0-based search result index).")
    p.add_argument(
        "--emojipedia-art",
        choices=["auto", "twemoji", "social", "design"],
        default="auto",
        help="For --emojipedia: choose artwork source. auto=best effort (prefers Twemoji if Emojipedia only gives social banners).",
    )
    p.add_argument("--design", type=int, default=0, help="For --emojipedia-art design: pick the Nth vendor design (0-based).")
    p.add_argument("--pick", action="store_true", help="Interactive picker for --emojipedia results (useful for browsing).")
    p.add_argument("--image", help="Local image path (PNG/JPEG/WEBP/etc).")
    p.add_argument("--url", help="Image or SVG URL.")
    p.add_argument("--frame", type=int, default=0, help="For animated images (GIF/WebP): which frame to use. Default: 0")
    p.add_argument("--output", default="icon_output", help="Output directory. Default: icon_output")
    p.add_argument("--apply", help="Apply icons to PATH (drive root or folder).")
    p.add_argument("--drive", action="store_true", help="Treat --apply target as a drive root.")
    p.add_argument("--no-apply", action="store_true", help="Do not apply icons automatically (even if --apply omitted).")
    p.add_argument("--refresh", action="store_true", help="Refresh Windows icon cache (Windows-only).")
    p.add_argument("--force", action="store_true", help="Attempt elevation when applying/refreshing on Windows.")
    return p


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.result is not None:
        args.alt = args.result

    if args.force and (args.apply or args.refresh) and is_windows():
        ok = elevate_if_needed([sys.argv[0], *argv])
        if not ok:
            return 0

    if args.refresh:
        refresh_windows_icons()
        return 0

    # Default behavior: wizard unless a non-wizard source flag is provided
    non_wizard = any([args.emoji, args.emojipedia, args.image, args.url, args.apply])
    if args.wizard or not non_wizard:
        return wizard()

    source: IconSource
    if args.emojipedia:
        # auto-pick first match; wizard provides interactive picker
        from .emoji_sources import emojipedia_pick_source

        if args.pick:
            # lightweight interactive picker without full wizard
            results = emojipedia_search(args.emojipedia, limit=20)
            if not results:
                s = None
            else:
                print("\nEmojipedia results:")
                for i, r in enumerate(results, start=0):
                    print(f"  {i}: {r.title} ({r.url})")
                pick_raw = input(f"Pick alt [0-{len(results)-1}] (default {args.alt}): ").strip()
                try:
                    pick_alt = int(pick_raw) if pick_raw else int(args.alt)
                except ValueError:
                    pick_alt = int(args.alt)
                # Second-level picker: vendor designs on the emoji page
                if args.emojipedia_art == "design":
                    from .emoji_sources import emojipedia_list_designs

                    emoji_slug = results[max(0, min(len(results) - 1, pick_alt))].path.strip("/").split("/", 1)[0]
                    designs = emojipedia_list_designs(emoji_slug)
                    if designs:
                        print("\nDesigns:")
                        for i, d in enumerate(designs, start=0):
                            extra = f" — {d.item_title}" if d.item_title else ""
                            print(f"  {i}: {d.vendor_title}{extra}")
                        d_raw = input(f"Pick design [0-{len(designs)-1}] (default {args.design}): ").strip()
                        try:
                            d_pick = int(d_raw) if d_raw else int(args.design)
                        except ValueError:
                            d_pick = int(args.design)
                        s = emojipedia_pick_source(args.emojipedia, alt=pick_alt, art="design", design=d_pick)
                    else:
                        s = emojipedia_pick_source(args.emojipedia, alt=pick_alt, art="twemoji")
                else:
                    s = emojipedia_pick_source(args.emojipedia, alt=pick_alt, art=args.emojipedia_art, design=args.design)
        else:
            s = emojipedia_pick_source(args.emojipedia, alt=args.alt, art=args.emojipedia_art, design=args.design)
        if s is None:
            emoji_code = parse_emoji_argument(args.emojipedia)
            source = IconSource(kind="url", value=twemoji_svg_url(emoji_code), label=f"Twemoji:{args.emojipedia}")
        else:
            source = s
    elif args.emoji:
        emoji_code = parse_emoji_argument(args.emoji)
        source = IconSource(kind="url", value=twemoji_svg_url(emoji_code), label=f"Twemoji:{args.emoji}")
    elif args.image:
        source = IconSource(kind="path", value=args.image, label=f"Image:{args.image}", frame=int(args.frame))
    elif args.url:
        source = IconSource(kind="url", value=args.url, label=f"URL:{args.url}", frame=int(args.frame))
    else:
        return wizard()

    outputs = create_icon_outputs(source, output_dir=Path(args.output))

    # Default apply behavior:
    # - if --apply provided: apply there
    # - else if user supplied a source flag: apply to current folder (unless --no-apply)
    if not args.no_apply:
        try:
            if args.apply:
                apply_icons(outputs, Path(args.apply), is_drive=bool(args.drive), windows=True, mac=False)
            else:
                apply_icons(outputs, Path.cwd(), is_drive=False, windows=True, mac=False)
        except PermissionError:
            print("Permission denied while applying icon.")
            if args.apply:
                print(f"Target: {args.apply}")
            else:
                print(f"Target: {Path.cwd()}")
            print(f"Icons were still generated in: {Path(args.output).resolve()}")
            print("Next steps:")
            print('  - re-run with `--apply \"C:\\\\some\\\\writable\\\\folder\"`')
            print("  - or use `--no-apply` to only generate icons")
            print("  - for protected locations, try `--force` to elevate")
            return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

