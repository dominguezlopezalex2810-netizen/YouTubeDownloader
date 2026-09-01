from __future__ import annotations

import asyncio
import json
import os
import subprocess
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .downloader import DownloadManager
from .runtime import resource_root


manager = DownloadManager()


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    manager.cancel_all()


app = FastAPI(title="YouTube Video Downloader", docs_url=None, redoc_url=None, lifespan=lifespan)


class AnalyzeRequest(BaseModel):
    url: str = Field(min_length=1, max_length=2048)


class DownloadRequest(AnalyzeRequest):
    quality: str
    audio_format: str = "m4a"
    destination: str = Field(min_length=1, max_length=1000)


class PathRequest(BaseModel):
    path: str = Field(min_length=1, max_length=1000)


@app.post("/api/analyze")
async def analyze(request: AnalyzeRequest):
    try:
        return await asyncio.to_thread(manager.analyze, request.url)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/downloads", status_code=202)
async def create_download(request: DownloadRequest):
    try:
        job = manager.start(request.url, request.quality, request.audio_format, request.destination)
        return job.snapshot()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/downloads/{job_id}")
async def get_download(job_id: str):
    job = manager.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Descarga no encontrada.")
    return job.snapshot()


@app.get("/api/downloads/{job_id}/events")
async def download_events(job_id: str):
    job = manager.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Descarga no encontrada.")

    async def stream():
        last = None
        while True:
            payload = job.snapshot()
            encoded = json.dumps(payload, ensure_ascii=False)
            if encoded != last:
                yield f"data: {encoded}\n\n"
                last = encoded
            if payload["finished"]:
                break
            await asyncio.sleep(0.35)

    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


@app.post("/api/downloads/{job_id}/cancel")
async def cancel_download(job_id: str):
    if not manager.cancel(job_id):
        raise HTTPException(status_code=409, detail="La descarga ya terminó o no existe.")
    return {"ok": True}


@app.post("/api/select-folder")
async def select_folder():
    def choose() -> str | None:
        try:
            import webview
            if webview.windows:
                result = webview.windows[0].create_file_dialog(webview.FOLDER_DIALOG)
                return result[0] if result else None
        except Exception:
            pass
        return None

    return {"path": await asyncio.to_thread(choose)}


@app.post("/api/open-folder")
async def open_folder(request: PathRequest):
    path = Path(request.path).resolve()
    if not path.exists() or not path.is_dir():
        raise HTTPException(status_code=400, detail="La carpeta no existe.")
    if os.name == "nt":
        os.startfile(path)  # type: ignore[attr-defined]
    elif os.sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])
    return {"ok": True}


frontend = resource_root() / "frontend"
app.mount("/static", StaticFiles(directory=frontend), name="static")


@app.get("/")
async def index():
    return FileResponse(frontend / "index.html")
