@echo off
setlocal
cd /d "%~dp0"
if not exist "dist\MediaDownloader\MediaDownloader.exe" call build.bat
if errorlevel 1 exit /b 1
set "ISCC=tools\inno\ISCC.exe"
if exist "%ISCC%" goto compile
set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if exist "%ISCC%" goto compile
set "ISCC=%ProgramFiles%\Inno Setup 7\ISCC.exe"
if exist "%ISCC%" goto compile
echo Install Inno Setup from https://jrsoftware.org/isdl.php or set up tools\inno\ISCC.exe.
exit /b 1
:compile
"%ISCC%" installer\MediaDownloader.iss
exit /b %errorlevel%
