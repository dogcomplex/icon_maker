# 🎨 Icon Maker

Create beautiful custom icons for Windows drives and folders from emojis or images! Also generates macOS-compatible icon sets.

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

## 🚀 Quick Start

```bash
# Create icons from an emoji
python icon_maker.py --emoji fox

# Create icons from an image
python icon_maker.py --image path/to/image.png

# Apply to a drive
python icon_maker.py --apply G: --drive

# Apply to a folder
python icon_maker.py --apply "path/to/folder"

# List available emojis
python icon_maker.py --list

# Force Windows to refresh icons
python icon_maker.py --refresh
```

## 📋 Requirements

- Python 3.7+
- Pillow
- cairosvg
- requests

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
