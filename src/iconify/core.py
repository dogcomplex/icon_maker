from __future__ import annotations

import io
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import requests
from PIL import Image

from .windows import (
    clear_path_attributes,
    is_windows,
    safe_create_dir,
    safe_remove,
    set_drive_attributes,
    set_folder_attributes,
)


SourceKind = Literal["path", "url", "bytes"]


@dataclass(frozen=True)
class IconSource:
    kind: SourceKind
    value: object  # Path | str | bytes
    label: str = ""
    frame: int = 0


def _read_path_bytes(path: Path) -> bytes:
    return path.read_bytes()


def _download_bytes(url: str, timeout_s: int = 30) -> bytes:
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=timeout_s)
    r.raise_for_status()
    return r.content


def _to_png_bytes_from_raster_bytes(raster: bytes, *, frame: int = 0) -> bytes:
    with Image.open(io.BytesIO(raster)) as img:
        # Animated GIF/WEBP/etc: select a frame (default 0)
        if getattr(img, "is_animated", False):
            try:
                img.seek(max(0, int(frame)))
            except Exception:
                try:
                    img.seek(0)
                except Exception:
                    pass
        if img.mode != "RGBA":
            img = img.convert("RGBA")
        out = io.BytesIO()
        img.save(out, format="PNG")
        return out.getvalue()


def source_to_png_bytes(source: IconSource, render_size: int = 1024) -> bytes:
    """
    Convert an IconSource to PNG bytes (RGBA).
    - SVG URLs are rendered to PNG via cairosvg at render_size x render_size.
    - Raster images are normalized to PNG.
    """
    if source.kind == "path":
        path = Path(str(source.value))
        raster = _read_path_bytes(path)
        return _to_png_bytes_from_raster_bytes(raster, frame=int(getattr(source, "frame", 0)))

    if source.kind == "bytes":
        return _to_png_bytes_from_raster_bytes(bytes(source.value), frame=int(getattr(source, "frame", 0)))

    if source.kind == "url":
        url = str(source.value)
        if url.lower().endswith(".svg"):
            import cairosvg

            return cairosvg.svg2png(url=url, output_width=render_size, output_height=render_size)
        raster = _download_bytes(url)
        return _to_png_bytes_from_raster_bytes(raster, frame=int(getattr(source, "frame", 0)))

    raise ValueError(f"Unsupported source kind: {source.kind}")

def _trim_to_content(img: Image.Image, *, bg_tolerance: int = 10, alpha_threshold: int = 8) -> Image.Image:
    """
    Trim borders so the icon fills more of the canvas.
    - If image has transparency: crop to alpha bbox.
    - Else: treat top-left pixel as background and crop to pixels that differ beyond tolerance.
    """
    rgba = img.convert("RGBA")
    w, h = rgba.size
    pixels = rgba.load()
    if pixels is None:
        return rgba

    # Alpha-based bbox
    alpha = rgba.getchannel("A")
    bbox = alpha.point(lambda a: 255 if a > alpha_threshold else 0).getbbox()
    if bbox:
        cropped = rgba.crop(bbox)
        if cropped.size[0] > 0 and cropped.size[1] > 0:
            return cropped

    # Background-diff bbox (for non-transparent social images)
    bg = pixels[0, 0]  # (r,g,b,a)

    def differs(px: tuple[int, int, int, int]) -> bool:
        return (
            abs(px[0] - bg[0]) > bg_tolerance
            or abs(px[1] - bg[1]) > bg_tolerance
            or abs(px[2] - bg[2]) > bg_tolerance
        )

    min_x, min_y = w, h
    max_x, max_y = -1, -1
    for y in range(h):
        for x in range(w):
            if differs(pixels[x, y]):
                if x < min_x:
                    min_x = x
                if y < min_y:
                    min_y = y
                if x > max_x:
                    max_x = x
                if y > max_y:
                    max_y = y
    if max_x >= 0 and max_y >= 0:
        return rgba.crop((min_x, min_y, max_x + 1, max_y + 1))

    return rgba


def _pad_to_square(img: Image.Image, *, pad_ratio: float = 0.10) -> Image.Image:
    rgba = img.convert("RGBA")
    w, h = rgba.size
    side = max(w, h)
    pad = int(side * pad_ratio)
    side2 = side + 2 * pad
    out = Image.new("RGBA", (side2, side2), (0, 0, 0, 0))
    out.paste(rgba, ((side2 - w) // 2, (side2 - h) // 2), mask=rgba)
    return out


@dataclass(frozen=True)
class IconOutputs:
    output_dir: Path
    drive_dir: Path
    folder_dir: Path
    mac_dir: Path


def _write_drive_files(img: Image.Image, drive_dir: Path) -> None:
    # Drive icon: 256x256 primary size
    resized = img.resize((256, 256), Image.Resampling.LANCZOS)
    if resized.mode != "RGBA":
        resized = resized.convert("RGBA")
    resized.save(drive_dir / ".VolumeIcon.ico", format="ICO", sizes=[(256, 256)], optimize=False)

    (drive_dir / "autorun.inf").write_text("[autorun]\nicon=.VolumeIcon.ico\n", encoding="utf-8")


def _write_folder_files(img: Image.Image, folder_dir: Path) -> None:
    sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    base = img.convert("RGBA")
    # Pillow can embed multiple sizes in ICO when sizes=... is provided; it will rescale automatically.
    base.save(folder_dir / "folder.ico", format="ICO", sizes=sizes, optimize=False)
    # A desktop.ini is written/encoded by windows.set_folder_attributes; write a basic one for portability.
    (folder_dir / "desktop.ini").write_text(
        "[.ShellClassInfo]\nIconResource=folder.ico,0\n[ViewState]\nMode=\nVid=\nFolderType=Generic\n",
        encoding="utf-8",
    )


def _write_mac_pngs(img: Image.Image, mac_dir: Path) -> None:
    icns_sizes = [
        (16, "16x16"),
        (32, "16x16@2x"),
        (32, "32x32"),
        (64, "32x32@2x"),
        (128, "128x128"),
        (256, "128x128@2x"),
        (256, "256x256"),
        (512, "256x256@2x"),
        (512, "512x512"),
        (1024, "512x512@2x"),
    ]
    for size, name in icns_sizes:
        resized = img.resize((size, size), Image.Resampling.LANCZOS)
        resized.save(mac_dir / f"icon_{name}.png", format="PNG")


def create_icon_outputs(
    source: IconSource,
    output_dir: Path = Path("icon_output"),
    render_size: int = 1024,
) -> IconOutputs:
    """
    Generate Windows drive/folder icons and macOS icon PNG set under output_dir.
    Returns paths to output folders.
    """
    output_dir = Path(output_dir)
    drive_dir = output_dir / "drive"
    folder_dir = output_dir / "folder"
    mac_dir = output_dir / "mac"

    safe_create_dir(output_dir)
    for p in (drive_dir, folder_dir, mac_dir):
        safe_create_dir(p)

    # Clean prior outputs
    for p in [
        drive_dir / ".VolumeIcon.ico",
        drive_dir / "autorun.inf",
        folder_dir / "folder.ico",
        folder_dir / "desktop.ini",
    ]:
        safe_remove(p)

    png_bytes = source_to_png_bytes(source, render_size=render_size)
    img = Image.open(io.BytesIO(png_bytes))
    # Make icons "fill" the canvas (prevents tiny-looking emoji icons)
    img = _pad_to_square(_trim_to_content(img))
    # Ensure a reasonably large base canvas so we can embed 256x256 ICO entries.
    # (Some vendor assets can be small; upscaling doesn't add detail but prevents missing sizes.)
    min_side = max(512, 256)
    if img.size[0] < min_side:
        img = img.resize((min_side, min_side), Image.Resampling.LANCZOS)

    _write_drive_files(img, drive_dir)
    _write_folder_files(img, folder_dir)
    _write_mac_pngs(img, mac_dir)

    return IconOutputs(output_dir=output_dir, drive_dir=drive_dir, folder_dir=folder_dir, mac_dir=mac_dir)


def apply_icons(
    outputs: IconOutputs,
    target_path: Path,
    *,
    is_drive: bool = False,
    windows: bool = True,
    mac: bool = False,
) -> None:
    target_path = Path(target_path)
    if windows and is_windows():
        if is_drive:
            # Clear attributes / overwrite safely
            for p in (target_path / ".VolumeIcon.ico", target_path / "autorun.inf"):
                clear_path_attributes(p)
                safe_remove(p)
            shutil.copy2(outputs.drive_dir / ".VolumeIcon.ico", target_path / ".VolumeIcon.ico")
            shutil.copy2(outputs.drive_dir / "autorun.inf", target_path / "autorun.inf")
            set_drive_attributes(target_path)
        else:
            for p in (target_path / "folder.ico", target_path / "desktop.ini"):
                clear_path_attributes(p)
                safe_remove(p)
            shutil.copy2(outputs.folder_dir / "folder.ico", target_path / "folder.ico")
            shutil.copy2(outputs.folder_dir / "desktop.ini", target_path / "desktop.ini")
            set_folder_attributes(target_path)

    if mac:
        iconset_path = target_path / ".iconset"
        safe_create_dir(iconset_path)
        for png_file in outputs.mac_dir.glob("icon_*.png"):
            shutil.copy2(png_file, iconset_path / png_file.name)

