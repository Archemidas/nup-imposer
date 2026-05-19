@echo off
REM Local Windows build script for Nup Imposer.
REM Run from a Developer Command Prompt or normal cmd with Python on PATH.

setlocal

echo === Nup Imposer: Windows build ===
echo.

REM 1. Create / activate venv
if not exist .venv (
    echo Creating virtual environment...
    python -m venv .venv
)
call .venv\Scripts\activate.bat

REM 2. Install dependencies
echo Installing dependencies...
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller

REM 3. Run tests
echo Running tests...
pip install pytest
pytest tests
if errorlevel 1 (
    echo Tests failed. Aborting build.
    exit /b 1
)

REM 4. Build with PyInstaller
echo Building executable...
pyinstaller nup_imposer.spec --noconfirm
if errorlevel 1 (
    echo PyInstaller build failed.
    exit /b 1
)

REM 5. Package as zip
echo Packaging zip...
powershell -Command "Compress-Archive -Path dist\NupImposer\* -DestinationPath dist\NupImposer-Windows.zip -Force"

echo.
echo === Build complete ===
echo Executable: dist\NupImposer\NupImposer.exe
echo Zip:        dist\NupImposer-Windows.zip
echo.

endlocal
