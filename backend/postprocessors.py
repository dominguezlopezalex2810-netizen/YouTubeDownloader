from __future__ import annotations

import os
from pathlib import Path

from yt_dlp.postprocessor.ffmpeg import FFmpegPostProcessor
from yt_dlp.utils import PostProcessingError, prepend_extension, replace_extension

from .media_probe import validate_iphone_m4a


def audio_metadata_args(information: dict) -> list[str]:
    fields = {
        "title": information.get("track") or information.get("title"),
        "artist": (
            information.get("artist")
            or information.get("creator")
            or information.get("channel")
            or information.get("uploader")
        ),
        "album": information.get("album"),
    }
    raw_date = information.get("release_date") or information.get("upload_date")
    if raw_date and len(str(raw_date)) == 8 and str(raw_date).isdigit():
        value = str(raw_date)
        fields["date"] = f"{value[:4]}-{value[4:6]}-{value[6:]}"
    elif information.get("release_year"):
        fields["date"] = str(information["release_year"])

    args: list[str] = []
    for key, value in fields.items():
        if value is not None and str(value).strip():
            args.extend(["-metadata", f"{key}={str(value).strip()}"])
    return args


class IPhoneM4APostProcessor(FFmpegPostProcessor):
    """Always transcode to a deterministic iPhone-compatible AAC-LC/M4A file."""

    def run(self, information):
        source = information["filepath"]
        target = replace_extension(source, "m4a", information.get("ext"))
        temporary = prepend_extension(target, "temp")
        original_to_delete = source
        try:
            ffmpeg_options = [
                "-vn",
                "-c:a", "aac",
                "-profile:a", "aac_low",
                "-ar", "44100",
                "-ac", "2",
                "-b:a", "160k",
                "-movflags", "+faststart",
            ]
            ffmpeg_options.extend(audio_metadata_args(information))
            self.run_ffmpeg(source, temporary, ffmpeg_options)
            validate_iphone_m4a(Path(temporary), Path(self.probe_executable))
            if target == source:
                original_to_delete = prepend_extension(source, "orig")
                os.replace(source, original_to_delete)
            os.replace(temporary, target)
        except Exception as exc:
            try:
                Path(temporary).unlink(missing_ok=True)
            except OSError:
                pass
            if isinstance(exc, PostProcessingError):
                raise
            raise PostProcessingError(str(exc)) from exc

        information["filepath"] = target
        information["ext"] = "m4a"
        information["acodec"] = "aac"
        return [original_to_delete], information
