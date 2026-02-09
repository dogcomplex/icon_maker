@echo off
setlocal

REM One-click installer for Windows: builds iconify.exe and registers it via App Paths (no PATH edits).

set "ROOT=%~dp0"
set "INSTALL_DIR=%LOCALAPPDATA%\iconify"
set "VENV_DIR=%INSTALL_DIR%\venv"
set "EXE_PATH=%INSTALL_DIR%\iconify.exe"
set "WINAPPS_DIR=%LOCALAPPDATA%\Microsoft\WindowsApps"
set "LOCALBIN_DIR=%USERPROFILE%\.local\bin"
set "SHIM_PATH=%LOCALBIN_DIR%\iconify.cmd"
set "WINAPPS_SHIM_PATH=%WINAPPS_DIR%\iconify.cmd"
set "LOG_PATH=%INSTALL_DIR%\install.log"

echo Installing to: "%INSTALL_DIR%"
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"
echo.>"%LOG_PATH%"
echo iconify install log > "%LOG_PATH%"
echo ROOT=%ROOT%>>"%LOG_PATH%"
echo INSTALL_DIR=%INSTALL_DIR%>>"%LOG_PATH%"
echo VENV_DIR=%VENV_DIR%>>"%LOG_PATH%"
echo EXE_PATH=%EXE_PATH%>>"%LOG_PATH%"

REM Prefer py.exe if present, otherwise fall back to python.exe
set "PY=py -3"
where py >nul 2>nul
if errorlevel 1 set "PY=python"
echo Using Python launcher: %PY%
echo PY=%PY%>>"%LOG_PATH%"

echo Creating venv...
%PY% -m venv "%VENV_DIR%" 1>>"%LOG_PATH%" 2>>&1 || goto :fail

echo Upgrading pip tooling...
"%VENV_DIR%\Scripts\python.exe" -m pip install -U pip setuptools wheel 1>>"%LOG_PATH%" 2>>&1 || goto :fail

echo Installing build deps (PyInstaller)...
"%VENV_DIR%\Scripts\python.exe" -m pip install -U pyinstaller 1>>"%LOG_PATH%" 2>>&1 || goto :fail

echo Installing iconify package from repo...
REM Avoid quoted paths ending with '\' (can confuse Windows arg parsing). Use trailing '.'
"%VENV_DIR%\Scripts\python.exe" -m pip install -U "%ROOT%." 1>>"%LOG_PATH%" 2>>&1 || goto :fail

echo Building iconify.exe (onefile)...
pushd "%ROOT%." >nul
REM Use a stable entry script so PyInstaller doesn't need module-mode tricks
"%VENV_DIR%\Scripts\pyinstaller.exe" --noconfirm --clean --onefile --name iconify "tools\iconify_entry.py" 1>>"%LOG_PATH%" 2>>&1 || goto :failpop
popd >nul

echo Copying exe to install dir...
copy /Y "%ROOT%dist\iconify.exe" "%EXE_PATH%" >nul 2>>&1 || goto :fail

echo Registering App Paths...
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\App Paths\iconify.exe" /ve /d "%EXE_PATH%" /f >nul || goto :fail

echo Writing shim to a PATH directory (so iconify works in cmd/powershell without PATH edits)...
if not exist "%LOCALBIN_DIR%" mkdir "%LOCALBIN_DIR%" >nul 2>>&1
(
  echo @echo off
  echo REM iconify shim installed by install_iconify.cmd
  echo if exist "%EXE_PATH%" ^(
  echo   "%EXE_PATH%" %%*
  echo   exit /b %%errorlevel%%
  echo ^)
  echo "%VENV_DIR%\Scripts\python.exe" -m iconify %%*
  echo exit /b %%errorlevel%%
) > "%SHIM_PATH%"

REM Also write into WindowsApps (sometimes on PATH, sometimes not)
if not exist "%WINAPPS_DIR%" mkdir "%WINAPPS_DIR%" >nul 2>>&1
copy /Y "%SHIM_PATH%" "%WINAPPS_SHIM_PATH%" >nul 2>>&1

echo.
echo Done.
echo Try in a new terminal: iconify
echo Log: "%LOG_PATH%"
exit /b 0

:failpop
popd >nul
:fail
echo.
echo Install failed.
echo Log: "%LOG_PATH%"
echo (Tip) Run this from an existing cmd window to see output:
echo   cmd /c "%ROOT%install_iconify.cmd"
pause
exit /b 1

