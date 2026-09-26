"""Durable deployment preferences; read per new beat, never rewrite artifacts."""
import os
import tempfile
from pathlib import Path

from ..config import settings
from ..domain.media_language import MediaLanguage


def _path() -> Path:
    return settings.data_path / ".private" / "media-language.json"


def read_language_settings() -> MediaLanguage:
    path = _path()
    try:
        return MediaLanguage.model_validate_json(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return MediaLanguage(video_language=settings.video_language, subtitle_language=settings.subtitle_language)


def save_language_settings(value: MediaLanguage) -> MediaLanguage:
    path = _path()
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temporary = tempfile.mkstemp(prefix=".language-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(value.model_dump_json())
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return value
