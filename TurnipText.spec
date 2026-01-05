# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for TurnipText
Build with: pyinstaller TurnipText.spec
Output: dist/TurnipText.exe
"""

import sys
from pathlib import Path

# Get the directory containing this spec file
spec_dir = Path(SPECPATH)

a = Analysis(
    ['app.py'],
    pathex=[str(spec_dir)],
    binaries=[],
    datas=[
        ('favicon.ico', '.'),  # Include favicon.ico in the bundle root
    ],
    hiddenimports=[
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude test dependencies to reduce size
        'pytest',
        'pytest_qt',
        '_pytest',
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='TurnipText',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,  # Compress if UPX is available
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window (windowed mode)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='favicon.ico',  # Application icon
)
