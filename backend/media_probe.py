from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any


def probe_audio(path: Path, ffprobe: Path) -> dict[str, Any]:
    command = [
        str(ffprobe), "-v", "error", "-select_streams", "a:0",
        "-show_entries", "stream=codec_name,profile,sample_rate,channels,bit_rate:format=format_name,duration:format_tags",
        "-of", "json", str(path),
    ]
    process = subprocess.run(command, capture_output=True, check=False, timeout=30)
    if process.returncode != 0:
        error = process.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"FFprobe no pudo validar el audio: {error[-300:]}")
    payload = json.loads(process.stdout.decode("utf-8", errors="strict"))
    streams = payload.get("streams") or []
    if not streams:
        raise RuntimeError("FFprobe no encontró una pista de audio en el archivo final.")
    stream = streams[0]
    container = (payload.get("format") or {}).get("format_name", "")
    duration = float((payload.get("format") or {}).get("duration") or 0)
    return {
        "container": container,
        "codec": stream.get("codec_name"),
        "profile": stream.get("profile"),
        "sample_rate": int(stream.get("sample_rate") or 0),
        "channels": int(stream.get("channels") or 0),
        "bit_rate": int(stream.get("bit_rate") or 0),
        "duration": duration,
        "metadata": (payload.get("format") or {}).get("tags") or {},
    }


def validate_iphone_m4a(path: Path, ffprobe: Path) -> dict[str, Any]:
    details = probe_audio(path, ffprobe)
    containers = set(details["container"].split(","))
    if not containers.intersection({"mov", "mp4", "m4a", "3gp", "3g2", "mj2"}):
        raise RuntimeError(f"Contenedor M4A no válido: {details['container'] or 'desconocido'}.")
    if details["codec"] != "aac":
        raise RuntimeError(f"El códec final no es AAC: {details['codec'] or 'desconocido'}.")
    if details["profile"] not in {"LC", "AAC LC"}:
        raise RuntimeError(f"El perfil AAC final no es LC: {details['profile'] or 'desconocido'}.")
    if details["sample_rate"] != 44100:
        raise RuntimeError(f"La frecuencia final no es 44.100 Hz: {details['sample_rate']} Hz.")
    if details["channels"] != 2:
        raise RuntimeError(f"La salida final no es estéreo: {details['channels']} canales.")
    if details["duration"] <= 0:
        raise RuntimeError("El archivo final no contiene una duración válida.")
    return details
