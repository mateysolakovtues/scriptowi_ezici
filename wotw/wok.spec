# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for Wok of the Warrior.
# Build with:  pyinstaller wok.spec
# Output:      dist/WokOfTheWarrior.exe  (single-file, no Python needed)

from PyInstaller.utils.hooks import collect_all

# Bundle the game's own assets.
datas = [("assets", "assets")]
binaries = []
hiddenimports = []

# arcade ships its own PyInstaller hook (arcade/__pyinstaller) which collects
# arcade's data correctly, so we must NOT collect_all('arcade') as well — doing
# both produces a broken 'arcade/VERSION/VERSION' entry. We only help with
# arcade's dependencies that need their data / native libs bundled.
for pkg in ("pyglet", "pymunk", "PIL"):
    pkg_datas, pkg_binaries, pkg_hidden = collect_all(pkg)
    datas += pkg_datas
    binaries += pkg_binaries
    hiddenimports += pkg_hidden


a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["fastapi", "uvicorn", "starlette"],  # the API server is dev-only
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="WokOfTheWarrior",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # no terminal window; set True to see errors while testing
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="wok_icon.ico",    # app/Start-menu icon
)
