# TurnipText Executable

This folder contains the Windows executable for TurnipText.

## Building the Executable

Since PyInstaller creates platform-specific executables, you need to build on Windows:

1. **Prerequisites**:
   - Python 3.11+ with PyQt6 installed
   - PyInstaller (`pip install pyinstaller`)

2. **Build**:
   ```batch
   cd TurnipText
   build_exe.bat
   ```

   Or manually:
   ```batch
   pyinstaller TurnipText.spec --noconfirm
   copy dist\TurnipText.exe bin\
   ```

3. **Output**: `bin/TurnipText.exe`

## File Association

To associate `.tabs` files with TurnipText:

1. Right-click any `.tabs` file
2. Select "Open with" → "Choose another app"
3. Click "More apps" → "Look for another app on this PC"
4. Browse to `TurnipText.exe`
5. Check "Always use this app to open .tabs files"

## Pinning to Taskbar

1. Run `TurnipText.exe` once
2. Right-click the icon in the taskbar
3. Select "Pin to taskbar"
