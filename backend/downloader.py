from __future__ import annotations

import os
import shutil
from pathlib import Path
from threading import Lock, Thread
from typing import Any, Callable
from uuid import uuid4

import yt_dlp

from .models import DownloadJob
from .postprocessors import IPhoneM4APostProcessor
from .runtime import require_ffmpeg
from .security import validate_destination, validate_youtube_url


RESOLUTIONS = [2160, 1440, 1080, 720, 480, 360, 240, 144]


class CancelledDownload(Exception):
    pass


def human_bytes(value: float | None) -> str | None:
    if value is None:
        return None
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(value)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.1f} {unit}"
        size /= 1024
    return None


def format_duration(seconds: int | float | None) -> str:
    if seconds is None:
        return "—"
    seconds = int(seconds)
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours}:{minutes:02d}:{secs:02d}" if hours else f"{minutes}:{secs:02d}"


class DownloadManager:
    def __init__(
        self,
        ydl_factory: Callable[..., Any] = yt_dlp.YoutubeDL,
        ffmpeg_resolver: Callable[[], Path] = require_ffmpeg,
    ) -> None:
        self.ydl_factory = ydl_factory
        self.ffmpeg_resolver = ffmpeg_resolver
        self.jobs: dict[str, DownloadJob] = {}
        self._lock = Lock()

    def analyze(self, raw_url: str) -> dict[str, Any]:
        url = validate_youtube_url(raw_url)
        options = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "noplaylist": True,
            "socket_timeout": 20,
        }
        try:
            with self.ydl_factory(options) as ydl:
                info = ydl.extract_info(url, download=False)
        except Exception as exc:
            raise RuntimeError(self._friendly_error(exc)) from exc

        if info.get("_type") == "playlist":
            raise RuntimeError("Usa la URL de un vídeo individual, no una lista de reproducción.")

        heights = {
            int(fmt["height"])
            for fmt in info.get("formats", [])
            if fmt.get("height") and fmt.get("vcodec", "none") != "none"
        }
        available = [height for height in RESOLUTIONS if height in heights]
        if not available and heights:
            available = sorted(heights, reverse=True)

        thumbnails = info.get("thumbnails") or []
        thumbnail = info.get("thumbnail") or (thumbnails[-1].get("url") if thumbnails else None)
        return {
            "id": info.get("id"),
            "title": info.get("title") or "Vídeo sin título",
            "channel": info.get("channel") or info.get("uploader") or "Canal desconocido",
            "duration": info.get("duration"),
            "duration_text": format_duration(info.get("duration")),
            "thumbnail": thumbnail,
            "resolutions": available,
            "audio_available": any(fmt.get("acodec", "none") != "none" for fmt in info.get("formats", [])),
        }

    def start(self, raw_url: str, quality: str, audio_format: str, destination: str) -> DownloadJob:
        url = validate_youtube_url(raw_url)
        dest = validate_destination(destination)
        if quality != "audio":
            try:
                height = int(quality)
            except ValueError as exc:
                raise ValueError("Calidad no válida.") from exc
            if height not in RESOLUTIONS:
                raise ValueError("Calidad no válida.")
        if audio_format not in {"mp3", "m4a"}:
            raise ValueError("Formato de audio no válido.")
        try:
            ffmpeg_path = self.ffmpeg_resolver()
        except RuntimeError as exc:
            raise ValueError(str(exc)) from exc

        job = DownloadJob(str(uuid4()), url, quality, audio_format, str(dest))
        with self._lock:
            self.jobs[job.id] = job
        Thread(target=self._run, args=(job, ffmpeg_path), daemon=True, name=f"download-{job.id[:8]}").start()
        return job

    def get(self, job_id: str) -> DownloadJob | None:
        with self._lock:
            return self.jobs.get(job_id)

    def cancel(self, job_id: str) -> bool:
        job = self.get(job_id)
        if not job or job.finished:
            return False
        job.cancel_event.set()
        job.update(status="cancelling", status_text="Cancelando...")
        return True

    def cancel_all(self) -> None:
        with self._lock:
            jobs = list(self.jobs.values())
        for job in jobs:
            if not job.finished:
                job.cancel_event.set()

    def _run(self, job: DownloadJob, ffmpeg_path: Path) -> None:
        temp_dir = Path(job.destination) / ".ytdl-temp" / job.id
        temp_dir.mkdir(parents=True, exist_ok=True)

        def progress_hook(data: dict[str, Any]) -> None:
            if job.cancel_event.is_set():
                raise CancelledDownload("Descarga cancelada.")
            status = data.get("status")
            if status == "downloading":
                downloaded = data.get("downloaded_bytes")
                total = data.get("total_bytes") or data.get("total_bytes_estimate")
                percentage = (downloaded / total * 100) if downloaded is not None and total else job.progress
                job.update(
                    status="downloading",
                    status_text="Descargando...",
                    progress=min(percentage, 99.0),
                    speed=human_bytes(data.get("speed")) + "/s" if data.get("speed") else None,
                    downloaded=downloaded,
                    total=total,
                )
            elif status == "finished":
                processing_text = "Convirtiendo audio..." if job.quality == "audio" else "Combinando vídeo y audio..."
                job.update(status="processing", status_text=processing_text, progress=99.0)

        output_template = str(Path(job.destination) / "%(title).180B [%(id)s].%(ext)s")
        options: dict[str, Any] = {
            "outtmpl": output_template,
            "paths": {"temp": str(temp_dir), "home": job.destination},
            "noplaylist": True,
            "restrictfilenames": False,
            "windowsfilenames": True,
            "trim_file_name": 200,
            "progress_hooks": [progress_hook],
            "overwrites": False,
            "continuedl": True,
            "quiet": True,
            "no_warnings": True,
            "socket_timeout": 30,
            "ffmpeg_location": str(ffmpeg_path.parent),
        }
        if job.quality == "audio":
            options["format"] = "bestaudio/best"
            if job.audio_format == "mp3":
                options["postprocessors"] = [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "0",
                }]
        else:
            height = int(job.quality)
            options["format"] = (
                f"bestvideo[height={height}]+bestaudio/"
                f"best[height={height}]"
            )
            options["merge_output_format"] = "mp4"

        try:
            job.update(status="preparing", status_text="Preparando descarga...")
            with self.ydl_factory(options) as ydl:
                if job.quality == "audio" and job.audio_format == "m4a":
                    ydl.add_post_processor(IPhoneM4APostProcessor(ydl), when="post_process")
                info = ydl.extract_info(job.url, download=True)
                if job.cancel_event.is_set():
                    raise CancelledDownload("Descarga cancelada.")
                requested = info.get("requested_downloads") or []
                candidate = requested[-1].get("filepath") if requested else None
                if not candidate:
                    candidate = ydl.prepare_filename(info)
                final_path = self._locate_final_file(Path(candidate), Path(job.destination), info.get("id"))
            job.update(
                status="completed",
                status_text="Completado",
                progress=100.0,
                filename=final_path.name if final_path else Path(candidate).name,
                finished=True,
                speed=None,
            )
        except CancelledDownload:
            job.update(status="cancelled", status_text="Descarga cancelada", error=None, finished=True, speed=None)
        except Exception as exc:
            if job.cancel_event.is_set():
                job.update(status="cancelled", status_text="Descarga cancelada", error=None, finished=True, speed=None)
            else:
                job.update(status="error", status_text="Error", error=self._friendly_error(exc), finished=True, speed=None)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
            try:
                temp_dir.parent.rmdir()
            except OSError:
                pass

    @staticmethod
    def _locate_final_file(candidate: Path, destination: Path, video_id: str | None) -> Path | None:
        if candidate.exists():
            return candidate
        if video_id:
            matches = sorted(destination.glob(f"*[{video_id}].*"), key=os.path.getmtime, reverse=True)
            return matches[0] if matches else None
        return None

    @staticmethod
    def _friendly_error(exc: Exception) -> str:
        message = str(exc).replace("ERROR: ", "").strip()
        lowered = message.lower()
        if "private video" in lowered:
            return "Este vídeo es privado y no se puede acceder sin autorización."
        if "video unavailable" in lowered or "not available" in lowered:
            return "El vídeo no está disponible o tiene restricciones de acceso."
        if "sign in" in lowered or "age" in lowered:
            return "YouTube requiere iniciar sesión para acceder a este vídeo."
        if "ffmpeg" in lowered:
            return "El FFmpeg incluido no está disponible o no pudo ejecutar el procesamiento. Reinstala la aplicación."
        return message[:500] or "No se pudo completar la operación."
