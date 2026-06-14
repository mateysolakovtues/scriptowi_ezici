# Building the standalone app

Wok of the Warrior can be packaged into a single Windows executable that runs
without Python installed.

## Build it

```bash
pip install pyinstaller
pyinstaller wok.spec
```

The result is **`dist/WokOfTheWarrior.exe`** — one self-contained file. That's
the file to upload/share for download. Players just double-click it; no Python,
no install, no dependencies.

## Notes

- **Saves**: the packaged game writes progress to
  `%USERPROFILE%\.wok_of_the_warrior\saves.json` (a writable user folder), since
  the bundle itself is read-only. Deleting that file resets progress.
- **The API server is not included.** `api.py` is a development-only save server;
  the game falls back to a local save file, so the standalone build needs no
  server. (`fastapi`/`uvicorn` are excluded from the bundle to keep it small.)
- **Seeing errors while testing**: set `console=False` to `True` in `wok.spec`
  to keep a terminal window open so any runtime errors are visible.
- **Antivirus / SmartScreen**: unsigned PyInstaller exes can trigger a Windows
  SmartScreen warning ("More info" → "Run anyway"). Code-signing removes this but
  requires a certificate.
- **Smaller/faster startup**: onefile extracts to a temp dir on each launch. For
  a faster-starting (but multi-file) build, change the spec to a `COLLECT` /
  onedir layout and zip the `dist/WokOfTheWarrior/` folder instead.

## Cross-platform

PyInstaller builds for the OS it runs on. Build on Windows for a `.exe`, on
macOS for a `.app`, on Linux for an ELF binary. The same `wok.spec` works on all
three.
