from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlparse


DIRECT_VIDEO_EXTENSIONS = {
    ".mp4",
    ".m4v",
    ".mov",
    ".webm",
    ".flv",
    ".avi",
    ".mkv",
}


def sanitize_filename(value: str, fallback: str = "video") -> str:
    value = re.sub(r"[\r\n\t]+", " ", value).strip()
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value)
    value = re.sub(r"\s+", " ", value).strip(" .")
    if not value:
        value = fallback
    return value[:150]


def extension_from_url(url: str) -> str:
    path = urlparse(url).path
    suffix = Path(path).suffix.lower()
    return suffix


def is_m3u8_url(url: str) -> bool:
    return ".m3u8" in url.lower().split("?", 1)[0]


def is_direct_video_url(url: str) -> bool:
    return extension_from_url(url) in DIRECT_VIDEO_EXTENSIONS


def is_supported_media_url(url: str) -> bool:
    return is_m3u8_url(url) or is_direct_video_url(url)


def same_host_score(page_url: str, media_url: str) -> int:
    page_host = urlparse(page_url).hostname or ""
    media_host = urlparse(media_url).hostname or ""
    if not page_host or not media_host:
        return 0
    if page_host == media_host:
        return 18
    if media_host.endswith("." + page_host) or page_host.endswith("." + media_host):
        return 10
    return 0
