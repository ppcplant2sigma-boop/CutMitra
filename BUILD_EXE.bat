@echo off
REM Build the offline Windows executable for CutMitra.
REM Requires: Python 3.10+ and PyInstaller  (pip install pyinstaller pymupdf)
cd /d "%~dp0src"
pyinstaller --onefile --windowed cutlist_optimizer.py --name "CutMitra" --distpath ..\dist --icon ..\assets\logo.ico --version-file ..\version_info.txt --add-data "..\assets\logo.png;assets"
echo.
echo Done. The exe is in the dist\ folder.
pause
