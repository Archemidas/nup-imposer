@echo off
REM Local Windows build script for Nup Imposer.
REM Run from a Developer Command Prompt or normal cmd with Python on PATH.
REM Output: dist\NupImposer.exe  (single portable exe, no installer needed)

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
pip install "pyinstaller>=6.0"

REM 3. Run tests
echo Running tests...
pip install pytest
pytest tests
if errorlevel 1 (
    echo Tests failed. Aborting build.
    exit /b 1
)

REM 4. Build with PyInstaller (single-file exe)
echo Building single-file executable...
pyinstaller nup_imposer.spec --noconfirm
if errorlevel 1 (
    echo PyInstaller build failed.
    exit /b 1
)

REM 5. Verify
if not exist dist\NupImposer.exe (
    echo ERROR: dist\NupImposer.exe not found after build.
    exit /b 1
)

REM 6. Package as zip (exe at root so it's right there when extracted)
echo Packaging zip...
powershell -Command "Compress-Archive -Path dist\NupImposer.exe -DestinationPath dist\NupImposer-Windows.zip -Force"

echo.
echo === Build complete ===
echo Executable : dist\NupImposer.exe
echo Zip        : dist\NupImposer-Windows.zip
echo.
echo Double-click NupImposer.exe to launch the GUI.
echo No installation, no DLL folder, no terminal needed.
echo.

endlocal
