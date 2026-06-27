# -*- mode: python ; coding: utf-8 -*-
"""CortexPad PyInstaller config"""

import os
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None

hiddenimports = [
    'uvicorn',
    'uvicorn.logging',
    'uvicorn.loops',
    'uvicorn.loops.auto',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.websockets',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.loops.selector',
    'fastapi',
    'fastapi.responses',
    'starlette',
    'starlette.websockets',
    'websockets',
    'websockets.legacy',
    'websockets.legacy.client',
    'websockets.legacy.server',
    'pyautogui',
    'pyautogui._pyautogui_win',
    'pyperclip',
    'pygetwindow',
    'pystray',
    'pystray._win32',
    'PIL',
    'PIL.Image',
    'psutil',
    'qrcode',
    'qrcode.image',
    'qrcode.image.svg',
    'pycaw',
    'comtypes',
    'comtypes.client',
    'screen_brightness_control',
    'faster_whisper',
    'ctranslate2',
    'keyboard',
    'keyboard._winkeyboard',
    'pyaudio',
    'audio_sink',
    'numpy',
    'numpy.core',
    'numpy.core._methods',
    'numpy.lib',
    'numpy.lib.format',
]

datas = [
    ('static/index.html', 'static'),
    ('icon.png', '.'),
]

binaries = []

excludes = [
    'matplotlib',
    'scipy',
    'pandas',
    'pytest',
    'tkinter',
    'IPython',
    'jupyter',
    'notebook',
    'wx',
    'PyQt5',
    'PyQt6',
    'PySide2',
    'PySide6',
    'vtkmodules',
    'vtk',
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='CortexPad',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    uac_admin=True,
    icon='icon.png',
)

