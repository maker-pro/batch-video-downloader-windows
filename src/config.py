from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .models import AppSettings


def app_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


APP_ROOT = app_root()
CONFIG_PATH = APP_ROOT / "config.json"
DEFAULT_DOWNLOAD_DIR = APP_ROOT / "downloads"
DEFAULT_M3U8DL_PATH = APP_ROOT / "tools" / "N_m3u8DL-CLI" / "N_m3u8DL-CLI.exe"


def project_path(value: str | Path, fallback: Path) -> Path:
    if not value:
        return fallback
    path = Path(value).expanduser()
    if path.is_absolute():
        return path
    return APP_ROOT / path


def load_settings() -> AppSettings:
    default_m3u8dl = find_default_m3u8dl()
    if not CONFIG_PATH.exists():
        return AppSettings(
            output_dir=DEFAULT_DOWNLOAD_DIR,
            m3u8dl_path=default_m3u8dl,
        )

    data: dict[str, Any] = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    return AppSettings(
        output_dir=project_path(data.get("output_dir", ""), DEFAULT_DOWNLOAD_DIR),
        m3u8dl_path=project_path(data.get("m3u8dl_path", ""), default_m3u8dl),
        proxy=data.get("proxy", ""),
        concurrency=int(data.get("concurrency", 2)),
        use_system_proxy=bool(data.get("use_system_proxy", True)),
        enable_playwright=bool(data.get("enable_playwright", True)),
        request_timeout=int(data.get("request_timeout", 20)),
        max_direct_retries=int(data.get("max_direct_retries", 3)),
    )


def find_default_m3u8dl() -> Path:
    if DEFAULT_M3U8DL_PATH.exists():
        return DEFAULT_M3U8DL_PATH
    tools_dir = APP_ROOT / "tools"
    if tools_dir.exists():
        matches = sorted(tools_dir.rglob("N_m3u8DL-CLI*.exe"))
        if matches:
            return matches[0]
    return DEFAULT_M3U8DL_PATH


def save_settings(settings: AppSettings) -> None:
    CONFIG_PATH.write_text(
        json.dumps(asdict(settings), ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
