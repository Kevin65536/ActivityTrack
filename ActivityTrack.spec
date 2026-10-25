# -*- mode: python ; coding: utf-8 -*-
# Use `python build.py` for an isolated build and package validation.
from pathlib import Path

root = Path(SPECPATH)
a = Analysis(
    [str(root / 'main.py')],
    pathex=[str(root)],
    binaries=[],
    datas=[(str(root / 'resources' / 'icon.ico'), 'resources')],
    hiddenimports=['win32timezone', 'scipy.ndimage', 'PySide6.QtCharts'],
    hookspath=[],
    hooksconfig={'matplotlib': {'backends': ['QtAgg']}},
    runtime_hooks=[],
    excludes=['tkinter', 'PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets', 'PySide6.QtWebEngineQuick'],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [], exclude_binaries=True, name='ActivityTrack',
    debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
    console=False, disable_windowed_traceback=False,
    icon=str(root / 'resources' / 'icon.ico'),
    version=str(root / 'resources' / 'version_info.txt'),
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='ActivityTrack')
