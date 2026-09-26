"""Durable, byte-preserving transport for generated image references.

Published identities still refer to the same asset. This cache changes only
where a provider downloads its bytes, never the character or snapshot.
"""
from __future__ import annotations

import asyncio
import hashlib
import os
import uuid

import httpx

from ..config import settings

MAX_IMAGE_BYTES = 50 * 1024 * 1024


class ReferenceImageError(RuntimeError):
    pass


def _extension(content: bytes) -> str:
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if content.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if content.startswith(b"RIFF") and content[8:12] == b"WEBP":
        return "webp"
    raise ReferenceImageError("reference response is not a PNG, JPEG or WebP image")


def _record(source: str, content: bytes, extension: str) -> dict:
    source_hash = hashlib.sha256(source.encode()).hexdigest()
    return {"source_url_sha256": source_hash,
            "url": f"/files/reference-images/{source_hash}.{extension}",
            "sha256": hashlib.sha256(content).hexdigest(), "bytes": len(content)}


def cached_image(source: str) -> dict | None:
    stem = hashlib.sha256(source.encode()).hexdigest()
    for extension in ("png", "jpg", "webp"):
        target = settings.data_path / "reference-images" / f"{stem}.{extension}"
        if target.is_file():
            content = target.read_bytes()
            if _extension(content) != extension:
                raise ReferenceImageError("cached reference has an invalid image format")
            return _record(source, content, extension)
    return None


def store_image(source: str, content: bytes, *, expected_sha256: str | None = None) -> dict:
    """Import originals or downloaded bytes atomically, without replacing a cache entry."""
    if not content or len(content) > MAX_IMAGE_BYTES:
        raise ReferenceImageError("reference image is empty or exceeds 50 MB")
    record = _record(source, content, _extension(content))
    if expected_sha256 and record["sha256"] != expected_sha256:
        raise ReferenceImageError("reference image does not match the recorded original hash")
    existing = cached_image(source)
    if existing:
        if existing["sha256"] != record["sha256"]:
            raise ReferenceImageError("reference image bytes changed for an archived source")
        return existing
    target = settings.data_path / record["url"].removeprefix("/files/")
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_bytes(content)
        try:
            os.link(temporary, target)
        except FileExistsError:
            if hashlib.sha256(target.read_bytes()).hexdigest() != record["sha256"]:
                raise ReferenceImageError("concurrent reference archive contains different bytes") from None
    finally:
        temporary.unlink(missing_ok=True)
    return record


async def archive_image(source: str) -> dict:
    cached = await asyncio.to_thread(cached_image, source)
    if cached:
        return cached
    if not source.startswith(("https://", "http://")):
        raise ReferenceImageError("reference source must be an HTTP image URL")
    content = bytearray()
    try:
        async with httpx.AsyncClient(timeout=45, follow_redirects=True) as client:
            async with client.stream("GET", source, headers={"User-Agent": "Mozilla/5.0"}) as response:
                response.raise_for_status()
                async for chunk in response.aiter_bytes():
                    content.extend(chunk)
                    if len(content) > MAX_IMAGE_BYTES:
                        raise ReferenceImageError("reference image exceeds 50 MB")
    except httpx.HTTPStatusError as exc:
        raise ReferenceImageError(f"reference download failed (HTTP {exc.response.status_code})") from None
    except httpx.RequestError:
        raise ReferenceImageError("reference download failed (network error)") from None
    return await asyncio.to_thread(store_image, source, bytes(content))
