@echo off
pushd "%~dp0"
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\restore_theme.ps1"
set "cursorExit=%errorlevel%"
popd
pause
exit /b %cursorExit%
