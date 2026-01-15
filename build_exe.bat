@echo off
REM Build TurnipText.exe using PyInstaller
REM Run this script from the TurnipText directory on Windows

echo Building TurnipText.exe...
echo.

REM Check if PyInstaller is installed
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo PyInstaller not found. Installing...
    pip install pyinstaller
    echo.
)

REM Clean previous builds
if exist "dist\TurnipText.exe" del "dist\TurnipText.exe"
if exist "build\TurnipText" rmdir /s /q "build\TurnipText"

REM Build the executable
pyinstaller TurnipText.spec --noconfirm

REM Check if build succeeded
if exist "dist\TurnipText.exe" (
    echo.
    echo ========================================
    echo Build successful!
    echo Output: dist\TurnipText.exe
    echo ========================================
    echo.

    REM Copy to project root so EXE shares icons folder with script
    copy "dist\TurnipText.exe" "TurnipText.exe"
    echo Copied to: TurnipText.exe in project root
) else (
    echo.
    echo Build FAILED. Check the output above for errors.
    exit /b 1
)

pause
