@echo off
setlocal

set "INSTALL_DIR=%LOCALAPPDATA%\iconify"
set "LOCALBIN_SHIM=%USERPROFILE%\.local\bin\iconify.cmd"
set "WINAPPS_SHIM=%LOCALAPPDATA%\Microsoft\WindowsApps\iconify.cmd"

echo Removing App Paths registration...
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\App Paths\iconify.exe" /f >nul 2>nul

echo Removing WindowsApps shim...
del /F /Q "%WINAPPS_SHIM%" >nul 2>nul

echo Removing localbin shim...
del /F /Q "%LOCALBIN_SHIM%" >nul 2>nul

echo Removing install dir: "%INSTALL_DIR%"
if exist "%INSTALL_DIR%" rmdir /S /Q "%INSTALL_DIR%"

echo Done.
exit /b 0

