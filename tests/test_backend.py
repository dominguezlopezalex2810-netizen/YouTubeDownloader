import os
import subprocess
from pathlib import Path
from time import sleep

import yt_dlp
from fastapi.testclient import TestClient
from yt_dlp.postprocessor.ffmpeg import FFmpegMergerPP

from backend.downloader import DownloadManager
from backend.media_probe import probe_audio, validate_iphone_m4a
from backend.postprocessors import IPhoneM4APostProcessor, audio_metadata_args
from backend import runtime
from backend.runtime import locate_ffmpeg
from backend.security import validate_youtube_url
from backend.server import app


INFO = {
    "id": "abc123",
    "title": "Vídeo de prueba",
    "channel": "Canal de prueba",
    "duration": 125,
    "thumbnail": "https://i.ytimg.com/vi/abc123/maxresdefault.jpg",
    "formats": [
        {"height": 1080, "vcodec": "avc1", "acodec": "none"},
        {"height": 720, "vcodec": "avc1", "acodec": "mp4a"},
        {"vcodec": "none", "acodec": "mp4a"},
    ],
}


class FakeYDL:
    last_options = None
    def __init__(self, options):
        self.options = options
        type(self).last_options = options
    def __enter__(self): return self
    def __exit__(self, *_): return False
    def extract_info(self, url, download=False):
        if not download: return INFO.copy()
        target = Path(self.options["outtmpl"].replace("%(title).180B", "Vídeo de prueba").replace("%(id)s", "abc123").replace("%(ext)s", "mp4"))
        target.parent.mkdir(parents=True, exist_ok=True)
        hook = self.options["progress_hooks"][0]
        hook({"status":"downloading", "downloaded_bytes":50, "total_bytes":100, "speed":1024})
        target.write_bytes(b"test")
        hook({"status":"finished", "filename":str(target)})
        return {**INFO, "requested_downloads":[{"filepath":str(target)}]}
    def prepare_filename(self, info): return "unused.mp4"


class SlowFakeYDL(FakeYDL):
    def extract_info(self, url, download=False):
        if not download: return INFO.copy()
        hook = self.options["progress_hooks"][0]
        for downloaded in range(1, 101):
            sleep(.005)
            hook({"status":"downloading", "downloaded_bytes":downloaded, "total_bytes":100, "speed":100})
        return INFO.copy()


def test_url_validation():
    assert validate_youtube_url("https://youtu.be/abc123") == "https://youtu.be/abc123"
    for invalid in ["https://example.com/watch?v=x", "file:///etc/passwd", "http://127.0.0.1/x"]:
        try: validate_youtube_url(invalid)
        except ValueError: pass
        else: raise AssertionError(f"URL insegura aceptada: {invalid}")


def test_analyze_detects_only_real_resolutions():
    manager = DownloadManager(FakeYDL)
    info = manager.analyze("https://www.youtube.com/watch?v=abc123")
    assert info["resolutions"] == [1080, 720]
    assert info["duration_text"] == "2:05"
    assert info["audio_available"] is True


def test_download_progress_and_cleanup(tmp_path):
    manager = DownloadManager(FakeYDL, ffmpeg_resolver=lambda: locate_ffmpeg())
    job = manager.start("https://youtu.be/abc123", "1080", "m4a", str(tmp_path))
    for _ in range(100):
        if job.finished: break
        sleep(.01)
    snapshot = job.snapshot()
    assert snapshot["status"] == "completed"
    assert snapshot["progress"] == 100
    assert snapshot["filename"] == "Vídeo de prueba [abc123].mp4"
    assert Path(FakeYDL.last_options["ffmpeg_location"]) == locate_ffmpeg().parent
    assert not (tmp_path / ".ytdl-temp" / job.id).exists()


def test_cancel_stops_job_and_cleans_temp(tmp_path):
    manager = DownloadManager(SlowFakeYDL, ffmpeg_resolver=lambda: locate_ffmpeg())
    job = manager.start("https://youtu.be/abc123", "720", "m4a", str(tmp_path))
    sleep(.03)
    assert manager.cancel(job.id) is True
    for _ in range(100):
        if job.finished: break
        sleep(.01)
    assert job.snapshot()["status"] == "cancelled"
    assert not (tmp_path / ".ytdl-temp" / job.id).exists()


def test_bundled_ffmpeg_is_independent_of_working_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    executable = locate_ffmpeg()
    assert executable is not None
    assert executable.name == "ffmpeg.exe"
    assert executable.parent.name == "bin"
    result = subprocess.run([str(executable), "-version"], capture_output=True, check=True)
    assert b"ffmpeg version" in result.stdout


def test_missing_ffmpeg_reports_incomplete_installation(tmp_path, monkeypatch):
    monkeypatch.setattr(runtime, "application_root", lambda: tmp_path)
    monkeypatch.setattr(runtime, "resource_root", lambda: tmp_path)
    try:
        runtime.require_ffmpeg()
    except RuntimeError as exc:
        assert "instalación está incompleta" in str(exc)
        assert str(tmp_path / "bin" / "ffmpeg.exe") in str(exc)
    else:
        raise AssertionError("No se detectó la ausencia de FFmpeg")


def test_ytdlp_merges_separate_video_and_audio_with_bundled_ffmpeg(tmp_path):
    ffmpeg = locate_ffmpeg()
    assert ffmpeg is not None
    video = tmp_path / "video.mp4"
    audio = tmp_path / "audio.m4a"
    output = tmp_path / "merged.mp4"
    subprocess.run([
        str(ffmpeg), "-hide_banner", "-loglevel", "error", "-f", "lavfi",
        "-i", "color=c=black:s=320x180:d=1", "-c:v", "mpeg4", str(video),
    ], check=True)
    subprocess.run([
        str(ffmpeg), "-hide_banner", "-loglevel", "error", "-f", "lavfi",
        "-i", "sine=frequency=440:duration=1", "-c:a", "aac", str(audio),
    ], check=True)
    with yt_dlp.YoutubeDL({"quiet": True, "ffmpeg_location": str(ffmpeg.parent)}) as ydl:
        merger = FFmpegMergerPP(ydl)
        deleted, info = merger.run({
            "filepath": str(output),
            "__files_to_merge": [str(video), str(audio)],
            "requested_formats": [
                {"filepath": str(video), "vcodec": "mpeg4", "acodec": "none", "protocol": "file"},
                {"filepath": str(audio), "vcodec": "none", "acodec": "aac", "protocol": "file"},
            ],
        })
    assert output.is_file() and output.stat().st_size > 0
    assert deleted == [str(video), str(audio)]
    assert info["filepath"] == str(output)


def test_m4a_mode_reencodes_to_iphone_compatible_aac_lc(tmp_path):
    ffmpeg = locate_ffmpeg()
    assert ffmpeg is not None
    ffprobe = ffmpeg.parent / "ffprobe.exe"
    source = tmp_path / "source.wav"
    subprocess.run([
        str(ffmpeg), "-hide_banner", "-loglevel", "error", "-f", "lavfi",
        "-i", "anoisesrc=color=pink:duration=3", "-ar", "32000", "-ac", "1", str(source),
    ], check=True)
    before = probe_audio(source, ffprobe)
    assert before["codec"] == "pcm_s16le"
    assert before["sample_rate"] == 32000
    assert before["channels"] == 1

    with yt_dlp.YoutubeDL({"quiet": True, "ffmpeg_location": str(ffmpeg.parent)}) as ydl:
        processor = IPhoneM4APostProcessor(ydl)
        deleted, info = processor.run({
            "filepath": str(source),
            "ext": "wav",
            "title": "Título de prueba",
            "channel": "Canal de prueba",
            "album": "Álbum de prueba",
            "upload_date": "20260831",
        })

    output = tmp_path / "source.m4a"
    details = validate_iphone_m4a(output, ffprobe)
    assert details["container"].split(",")[0] in {"mov", "mp4", "m4a"}
    assert details["codec"] == "aac"
    assert details["profile"] in {"LC", "AAC LC"}
    assert details["sample_rate"] == 44100
    assert details["channels"] == 2
    assert 2.9 <= details["duration"] <= 3.1
    assert 120_000 <= details["bit_rate"] <= 190_000
    assert details["metadata"]["title"] == "Título de prueba"
    assert details["metadata"]["artist"] == "Canal de prueba"
    assert details["metadata"]["album"] == "Álbum de prueba"
    assert details["metadata"]["date"] == "2026-08-31"
    subprocess.run([
        str(ffmpeg), "-hide_banner", "-loglevel", "error", "-i", str(output),
        "-f", "null", "-",
    ], check=True)
    assert deleted == [str(source)]
    assert info["filepath"] == str(output)


def test_audio_metadata_uses_only_available_youtube_fields():
    args = audio_metadata_args({
        "title": "Vídeo",
        "channel": "Canal",
        "upload_date": "20240109",
    })
    pairs = dict(value.split("=", 1) for flag, value in zip(args[::2], args[1::2]) if flag == "-metadata")
    assert pairs == {"title": "Vídeo", "artist": "Canal", "date": "2024-01-09"}
    assert "album" not in pairs


def test_api_rejects_invalid_url():
    client = TestClient(app)
    response = client.post("/api/analyze", json={"url":"https://example.com/video"})
    assert response.status_code == 400
    assert "YouTube" in response.json()["detail"]
