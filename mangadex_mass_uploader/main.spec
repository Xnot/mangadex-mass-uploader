# -*- mode: python ; coding: utf-8 -*-
import PyInstaller.config
PyInstaller.config.CONF["workpath"] = "../build"
PyInstaller.config.CONF["distpath"] = "../dist"

from kivy_deps import sdl2, glew


block_cipher = None


a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=[
        ("../assets/mangadex.png", "./assets/"),
        ("../assets/mass_editor.ico", "./assets/"),
        ("../assets/mass_editor.png", "./assets/"),
        ("../assets/mass_editor.svg", "./assets/"),
        ("../assets/mass_uploader.ico", "./assets/"),
        ("../assets/mass_uploader.png", "./assets/"),
        ("../assets/mass_uploader.svg", "./assets/"),
        ("../assets/NotoSansJP-Regular.ttf", "./assets/"),
        ("chapter_parser.py", "./"),
        ("kivy_config.py", "./"),
        ("main.kv", "./"),
        ("mangadex_api.py", "./"),
        ("mass_editor.py", "./"),
        ("mass_editor.kv", "./"),
        ("mass_uploader.py", "./"),
        ("mass_uploader.kv", "./"),
        ("utils.py", "./"),
        ("widgets/app_screen.py", "./widgets"),
        ("widgets/chapter_info_input.py", "./widgets"),
        ("widgets/chapter_info_input.kv", "./widgets"),
        ("widgets/log_output.py", "./widgets"),
        ("widgets/log_output.kv", "./widgets"),
        ("widgets/login_screen.py", "./widgets"),
        ("widgets/login_screen.kv", "./widgets"),
        ("widgets/preview_output.py", "./widgets"),
        ("widgets/preview_output.kv", "./widgets"),
        ("widgets/scrollbar_view.py", "./widgets"),
        ("widgets/scrollbar_view.kv", "./widgets"),

    ],
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
    pyz, #Tree("./"),
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    *[Tree(p) for p in (sdl2.dep_bins + glew.dep_bins)],
    name="mass_uploader",
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
    icon="../assets/mass_uploader.ico"
)
