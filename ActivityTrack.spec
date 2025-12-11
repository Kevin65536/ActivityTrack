# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for ActivityTrack
Build command: pyinstaller ActivityTrack.spec
"""
import os

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('config.json', '.'),  # Include default configuration
        ('resources/icon.ico', 'resources'),  # Include icon file
    ],
    hiddenimports=[
        # PySide6
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        # pywin32
        'win32api',
        'win32con',
        'win32gui',
        'win32process',
        'pywintypes',
        'win32timezone',
        # psutil
        'psutil',
        # matplotlib and dependencies
        'matplotlib',
        'matplotlib.backends.backend_qt5agg',
        'numpy',
        'numpy.core',
        'numpy.core._multiarray_umath',
        # scipy (if used)
        'scipy',
        'scipy.ndimage',
        'scipy.ndimage._ni_support',
        # Standard library modules needed by numpy/scipy
        'email',
        'email.mime',
        'email.mime.text',
        'unittest',
        'unittest.mock',
        'xml',
        'xml.etree',
        'xml.etree.ElementTree',
        'importlib.metadata',
        # Other potential hidden imports
        'sqlite3',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',  # We use PySide6, not tkinter
        # DO NOT exclude unittest, email, xml - numpy/scipy dependencies need them!
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ActivityTrack',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,  # Compress with UPX if available
    console=False,  # Windowed application (no console)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(SPECPATH, 'resources', 'icon.ico'),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ActivityTrack',
)
