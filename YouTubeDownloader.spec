# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
import shutil

project = Path(SPECPATH)
ffmpeg = project / "bin" / "ffmpeg.exe"
ffprobe = project / "bin" / "ffprobe.exe"
if not ffmpeg.exists():
    raise FileNotFoundError("Falta bin/ffmpeg.exe. Ejecuta prepare_ffmpeg.ps1 antes de compilar.")

a = Analysis(
    [str(project / "run_app.py")],
    pathex=[str(project)],
    binaries=[],
    datas=[(str(project / "frontend"), "frontend")],
    hiddenimports=["webview.platforms.edgechromium", "webview.platforms.winforms"],
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [],
    name="YouTube Video Downloader",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    exclude_binaries=True,
)
coll = COLLECT(
    exe, a.binaries, a.datas,
    strip=False,
    upx=False,
    name="YouTube Video Downloader",
)

# PyInstaller 6 coloca binaries dentro de _internal. FFmpeg debe permanecer junto
# al ejecutable para que la distribución tenga una ruta estable y transparente.
target_bin = Path(DISTPATH) / "YouTube Video Downloader" / "bin"
target_bin.mkdir(parents=True, exist_ok=True)
shutil.copy2(ffmpeg, target_bin / "ffmpeg.exe")
if ffprobe.exists():
    shutil.copy2(ffprobe, target_bin / "ffprobe.exe")
license_file = project / "bin" / "FFMPEG-LICENSE.txt"
if license_file.exists():
    shutil.copy2(license_file, target_bin / "FFMPEG-LICENSE.txt")
