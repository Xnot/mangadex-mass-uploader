# -*- mode: python ; coding: utf-8 -*-

from kivy_deps import sdl2, glew


block_cipher = None


a = Analysis(
    ['mass_uploader.py'],
    pathex=[],
    binaries=[],
    datas=[("MassUploaderApp.kv", "."), ("mangadex_api.py", "."), ("CONSOLA.TTF", ".")],
    hiddenimports=["plyer.platforms.win.filechooser"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    *[Tree(p) for p in (sdl2.dep_bins + glew.dep_bins)],
    name='mass_uploader',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
