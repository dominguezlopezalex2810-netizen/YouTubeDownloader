from __future__ import annotations

import sys
from pathlib import Path


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def application_root() -> Path:
    """Directory beside the executable, or the project root when running from source."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return project_root()


def resource_root() -> Path:
    """PyInstaller data directory, or the project root when running from source."""
    return Path(getattr(sys, "_MEIPASS", project_root())).resolve()


def locate_ffmpeg() -> Path | None:
    candidates = [application_root() / "bin" / "ffmpeg.exe"]
    bundled = resource_root() / "bin" / "ffmpeg.exe"
    if bundled not in candidates:
        candidates.append(bundled)
    return next((path for path in candidates if path.is_file()), None)


def locate_ffprobe() -> Path | None:
    ffmpeg = locate_ffmpeg()
    if ffmpeg is None:
        return None
    ffprobe = ffmpeg.with_name("ffprobe.exe")
    return ffprobe if ffprobe.is_file() else None


def require_ffmpeg() -> Path:
    executable = locate_ffmpeg()
    if executable is None:
        expected = application_root() / "bin" / "ffmpeg.exe"
        raise RuntimeError(
            "La instalación está incompleta: no se encontró FFmpeg en "
            f"{expected}. Reinstala la aplicación con el instalador oficial."
        )
    if locate_ffprobe() is None:
        expected = executable.with_name("ffprobe.exe")
        raise RuntimeError(
            "La instalación está incompleta: no se encontró FFprobe en "
            f"{expected}. Reinstala la aplicación con el instalador oficial."
        )
    return executable
