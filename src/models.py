from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


class TaskStatus(str, Enum):
    PENDING = "等待中"
    PARSING = "解析中"
    DOWNLOADING = "下载中"
    DONE = "完成"
    FAILED = "失败"
    CANCELLED = "已取消"


@dataclass
class VideoCandidate:
    url: str
    source: str
    media_type: str
    score: int = 0
    content_type: str = ""
    content_length: Optional[int] = None
    resolution: Optional[str] = None


@dataclass
class PageVideo:
    page_url: str
    title: str
    selected: VideoCandidate
    candidates: list[VideoCandidate] = field(default_factory=list)


@dataclass
class AppSettings:
    output_dir: Path
    m3u8dl_path: Path
    proxy: str = ""
    concurrency: int = 2
    use_system_proxy: bool = True
    enable_playwright: bool = True
    request_timeout: int = 20
    max_direct_retries: int = 3


@dataclass
class TaskUpdate:
    url: str
    status: TaskStatus
    message: str = ""
    progress: Optional[float] = None
    output_path: Optional[Path] = None
