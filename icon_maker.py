"""
Legacy entrypoint kept for backwards compatibility.

Prefer:
  - `iconify` (after running install_iconify.cmd), or
  - `python -m iconify.cli`
"""

from pathlib import Path
import sys

# Allow running from a source checkout without installing (src/ layout).
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from iconify.cli import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())

