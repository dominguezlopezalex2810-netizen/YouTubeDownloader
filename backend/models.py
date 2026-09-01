from __future__ import annotations

from dataclasses import dataclass, field
from threading import Event, Lock
from typing import Any


@dataclass
class DownloadJob:
    id: str
    url: str
    quality: str
    audio_format: str
    destination: str
    status: str = "queued"
    status_text: str = "Preparando descarga..."
    progress: float = 0.0
    speed: str | None = None
    downloaded: int | None = None
    total: int | None = None
    filename: str | None = None
    error: str | None = None
    finished: bool = False
    cancel_event: Event = field(default_factory=Event, repr=False)
    lock: Lock = field(default_factory=Lock, repr=False)

    def update(self, **changes: Any) -> None:
        with self.lock:
            for key, value in changes.items():
                setattr(self, key, value)

    def snapshot(self) -> dict[str, Any]:
        with self.lock:
            return {
                "id": self.id,
                "status": self.status,
                "status_text": self.status_text,
                "progress": round(self.progress, 1),
                "speed": self.speed,
                "downloaded": self.downloaded,
                "total": self.total,
                "filename": self.filename,
                "error": self.error,
                "finished": self.finished,
            }

