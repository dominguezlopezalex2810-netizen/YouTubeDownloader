from __future__ import annotations

import ipaddress
from pathlib import Path
from urllib.parse import urlparse


ALLOWED_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com", "youtu.be"}


def validate_youtube_url(value: str) -> str:
    value = value.strip()
    if len(value) > 2048:
        raise ValueError("La URL es demasiado larga.")
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Introduce una URL completa de YouTube.")
    host = parsed.hostname.lower().rstrip(".")
    try:
        ipaddress.ip_address(host)
        raise ValueError("No se permiten direcciones IP.")
    except ValueError as exc:
        if str(exc) == "No se permiten direcciones IP.":
            raise
    if host not in ALLOWED_HOSTS and not host.endswith(".youtube.com"):
        raise ValueError("La URL debe pertenecer a YouTube o youtu.be.")
    if parsed.username or parsed.password:
        raise ValueError("La URL contiene credenciales no permitidas.")
    return value


def validate_destination(value: str) -> Path:
    path = Path(value).expanduser().resolve()
    if not path.exists() or not path.is_dir():
        raise ValueError("La carpeta de destino no existe.")
    return path

