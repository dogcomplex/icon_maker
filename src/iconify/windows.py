from __future__ import annotations

import ctypes
import os
import sys
from pathlib import Path


def is_windows() -> bool:
    return os.name == "nt"


def is_admin() -> bool:
    """Check if the process has admin rights (Windows-only)."""
    if not is_windows():
        return False
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def elevate_if_needed(argv: list[str] | None = None) -> bool:
    """Re-run the process with admin rights if needed (Windows-only)."""
    if not is_windows():
        return True
    if is_admin():
        return True

    args = " ".join(argv if argv is not None else sys.argv)
    try:
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, args, None, 1)
        return False  # parent should exit
    except Exception:
        return False


def refresh_windows_icons() -> None:
    """Force Windows to refresh icon cache (best-effort)."""
    if not is_windows():
        return

    # Kill explorer
    os.system("taskkill /f /im explorer.exe")

    cache_paths = [
        r"%LOCALAPPDATA%\IconCache.db",
        r"%LOCALAPPDATA%\Microsoft\Windows\Explorer\iconcache*",
        r"%LOCALAPPDATA%\Microsoft\Windows\Explorer\thumbcache*",
    ]
    for path in cache_paths:
        os.system(f"del /f /s /q {path}")

    os.system("ipconfig /flushdns")
    os.system("start explorer.exe")
    os.system("ie4uinit.exe -show")
    os.system("ie4uinit.exe -ClearIconCache")


def safe_remove(path: Path) -> None:
    """Safely remove a file by removing system/hidden attributes first."""
    try:
        if path.exists() and is_windows():
            os.system(f'attrib -s -h "{path}"')
        if path.exists():
            path.unlink()
    except Exception:
        pass


def clear_path_attributes(path: Path) -> None:
    """Best-effort clear of common Windows attributes that block overwrites."""
    if not is_windows():
        return
    # For files and directories, clear read-only/system/hidden.
    os.system(f'attrib -r -s -h "{path}"')


def safe_create_dir(path: Path) -> None:
    """Safely create directory by removing attributes first."""
    try:
        if path.exists() and is_windows():
            os.system(f'attrib -r -s -h "{path}"')
        path.mkdir(parents=True, exist_ok=True)
    except Exception:
        path.mkdir(parents=True, exist_ok=True)


def set_drive_attributes(drive_root: Path) -> None:
    """Set file attributes and registry hints for drive icon files."""
    if not is_windows():
        return

    drive_letter = str(drive_root)[0].upper()
    os.system(f'attrib +s +h "{drive_root / ".VolumeIcon.ico"}"')
    os.system(f'attrib +s +h "{drive_root / "autorun.inf"}"')

    # HKCU generally does not require admin; HKLM/HKCR often do. We only attempt system-wide keys if elevated.
    reg_commands = [
        r'reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Policies\Explorer" /v "NoDriveTypeAutoRun" /t REG_DWORD /d 0 /f',
        f'reg add "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\DriveIcons\\{drive_letter}" /ve /d "" /f',
        f'reg add "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\DriveIcons\\{drive_letter}\\DefaultIcon" /ve /d "{drive_root}\\\.VolumeIcon.ico" /f',
    ]
    if is_admin():
        reg_commands += [
            f'reg add "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Explorer\\DriveIcons\\{drive_letter}" /ve /d "" /f',
            f'reg add "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Explorer\\DriveIcons\\{drive_letter}\\DefaultIcon" /ve /d "{drive_root}\\\.VolumeIcon.ico" /f',
            f'reg add "HKCR\\Drive\\shell\\{drive_letter}" /v "Icon" /d "{drive_root}\\\.VolumeIcon.ico" /f',
        ]
    for cmd in reg_commands:
        os.system(cmd)


def write_desktop_ini(folder_path: Path) -> None:
    desktop_ini_content = """[.ShellClassInfo]
IconResource=folder.ico,0
IconFile=folder.ico
IconIndex=0
ConfirmFileOp=0
[ViewState]
Mode=
Vid=
FolderType=Pictures
[{BE098140-A513-11D0-A3A4-00C04FD706EC}]
IconArea_Image=folder.ico
Attributes=1"""

    # Windows prefers UTF-16 LE for desktop.ini
    (folder_path / "desktop.ini").write_text(desktop_ini_content, encoding="utf-16-le")


def set_folder_attributes(folder_path: Path) -> None:
    """Set attributes for folder icon files (Windows-only)."""
    if not is_windows():
        return

    os.system(f'attrib -r -s "{folder_path}"')
    os.system(f'attrib +s "{folder_path}"')

    os.system(f'attrib -r -s -h "{folder_path / "desktop.ini"}"')
    os.system(f'attrib -r -s -h "{folder_path / "folder.ico"}"')

    write_desktop_ini(folder_path)

    os.system(f'attrib +s +h "{folder_path / "folder.ico"}"')
    os.system(f'attrib +s +h "{folder_path / "desktop.ini"}"')

