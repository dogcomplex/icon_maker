# 🎨 Icon Maker

Create beautiful custom icons for Windows drives and folders from emojis or images! Also generates macOS-compatible icon sets.

WIP but basic functionality is there.  Another Claude-3.5-sonnet creation.

## ✨ Features

- 🖼️ Create icons from:
  - Any Unicode emoji
  - Local images (PNG, JPEG, WEBP, etc.)
- 💾 Supports:
  - Windows drive icons (.VolumeIcon.ico + autorun.inf)
  - Windows folder icons (folder.ico + desktop.ini)
  - macOS icon sets (.iconset format)
- 🛠️ Advanced features:
  - Automatic admin elevation when needed
  - Windows icon cache refresh
  - Registry optimization for drive icons

## 🚀 Quick Start (Windows one-click install)

1) Double-click `install_iconify.cmd`

2) Open a **new** terminal and run:

```bat
iconify
```

This launches an interactive step-by-step wizard.

Installer details:
- Writes the executable to `%LOCALAPPDATA%\\iconify\\iconify.exe`
- Drops a small `iconify.cmd` shim into `%USERPROFILE%\\.local\\bin` (**already on PATH for many dev setups**) so `iconify` works everywhere without editing PATH manually.

## 🚀 Quick Start (from source checkout)

If you just cloned this repo and want to run without installing:

```bat
python icon_maker.py --wizard
```

```bash
# Create icons from a Twemoji emoji (high quality SVG -> PNG -> ICO)
python icon_maker.py --emoji fox --output icon_output

# Create icons from Emojipedia (best-effort, prefers larger artwork)
python icon_maker.py --emojipedia fox --output icon_output

# Apply to a folder
python icon_maker.py --emoji fox --output icon_output --apply "path\\to\\folder"

# Apply to a drive root (may require admin for best persistence)
python icon_maker.py --emoji fox --output icon_output --apply "G:\\" --drive --force

# Force Windows to refresh icons (careful! this is a bit of a cudgel)
python icon_maker.py --refresh --force
```

## 📋 Requirements

- Python 3.8+
- Pillow
- cairosvg
- requests

## 🧰 CLI

After installing, you’ll have a global `iconify` command.

Common examples:

```bat
iconify
iconify --emoji fox --apply "C:\\path\\to\\folder"
iconify --emojipedia lotus --result 0 --emojipedia-art twemoji
iconify --emojipedia lotus --result 0 --emojipedia-art design --design 0
iconify --emojipedia lotus --pick --emojipedia-art design
iconify --emoji fox --no-apply
```

## 🔧 Installation

```bash
pip install Pillow cairosvg requests
```

## 🎯 Usage Examples

1. Create fox icons:
   ```bash
   python icon_maker.py --emoji fox
   ```

2. Apply to drive G:
   ```bash
   python icon_maker.py --apply G: --drive --force
   ```

3. Use custom image:
   ```bash
   python icon_maker.py --image my_logo.png
   ```

## 🔍 Notes

- Some operations require administrator privileges
- For macOS icons:
  1. Transfer the 'mac' folder to a Mac
  2. Rename it to 'icon.iconset'
  3. Run: `iconutil -c icns icon.iconset`

## 📄 License

MIT License

Copyright (c) 2024 Warren Koch (warrenkoch@gmail.com)

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
