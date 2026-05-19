from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Callable

import requests

from .models import AppSettings, PageVideo, TaskStatus, TaskUpdate
from .parser import build_headers, proxies_for
from .utils import extension_from_url, sanitize_filename

UpdateCallback = Callable[[TaskUpdate], None]


class DownloadCancelled(RuntimeError):
    pass


class Downloader:
    def __init__(self, settings: AppSettings, on_update: UpdateCallback, should_stop: Callable[[], bool]):
        self.settings = settings
        self.on_update = on_update
        self.should_stop = should_stop

    def download(self, video: PageVideo) -> Path:
        self.settings.output_dir.mkdir(parents=True, exist_ok=True)
        if video.selected.media_type == "m3u8":
            return self._download_m3u8(video)
        return self._download_direct(video)

    def _download_direct(self, video: PageVideo) -> Path:
        url = video.selected.url
        suffix = extension_from_url(url) or f".{video.selected.media_type or 'mp4'}"
        target = unique_path(self.settings.output_dir / f"{sanitize_filename(video.title)}{suffix}")
        temp = target.with_suffix(target.suffix + ".part")
        headers = build_headers(video.page_url)

        for attempt in range(1, self.settings.max_direct_retries + 1):
            if self.should_stop():
                raise DownloadCancelled("任务已取消")
            try:
                with requests.get(
                    url,
                    headers=headers,
                    proxies=proxies_for(self.settings),
                    timeout=self.settings.request_timeout,
                    stream=True,
                ) as response:
                    response.raise_for_status()
                    total = int(response.headers.get("content-length") or 0)
                    downloaded = 0
                    with temp.open("wb") as file:
                        for chunk in response.iter_content(chunk_size=1024 * 256):
                            if self.should_stop():
                                raise DownloadCancelled("任务已取消")
                            if not chunk:
                                continue
                            file.write(chunk)
                            downloaded += len(chunk)
                            progress = downloaded / total if total else None
                            self.on_update(
                                TaskUpdate(
                                    video.page_url,
                                    TaskStatus.DOWNLOADING,
                                    f"直链下载中 {downloaded / 1024 / 1024:.1f} MB",
                                    progress,
                                )
                            )
                temp.replace(target)
                return target
            except DownloadCancelled:
                if temp.exists():
                    temp.unlink(missing_ok=True)
                raise
            except Exception as exc:
                if attempt >= self.settings.max_direct_retries:
                    raise RuntimeError(f"直链下载失败：{exc}") from exc
                time.sleep(attempt * 1.5)
        return target

    def _download_m3u8(self, video: PageVideo) -> Path:
        exe = self.settings.m3u8dl_path
        if not exe.exists():
            raise FileNotFoundError(f"找不到 N_m3u8DL-CLI：{exe}")

        save_name = sanitize_filename(video.title)
        command = [
            str(exe),
            video.selected.url,
            "--workDir",
            str(self.settings.output_dir),
            "--saveName",
            save_name,
            "--enableDelAfterDone",
            "--enableMuxFastStart",
            "--disableDateInfo",
            "--headers",
            headers_for_cli(video.page_url),
        ]
        if self.settings.proxy:
            command.extend(["--proxyAddress", self.settings.proxy])
        elif not self.settings.use_system_proxy:
            command.append("--noProxy")

        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(self.settings.output_dir),
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
        )
        assert process.stdout is not None
        try:
            for line in process.stdout:
                if self.should_stop():
                    process.terminate()
                    raise DownloadCancelled("任务已取消")
                line = line.strip()
                if line:
                    self.on_update(TaskUpdate(video.page_url, TaskStatus.DOWNLOADING, line))
            exit_code = process.wait()
        finally:
            if process.poll() is None:
                process.terminate()

        if exit_code != 0:
            raise RuntimeError(f"N_m3u8DL-CLI 退出码 {exit_code}")

        return find_output_file(self.settings.output_dir, save_name)


def headers_for_cli(page_url: str) -> str:
    headers = build_headers(page_url)
    return "|".join(f"{key}:{value}" for key, value in headers.items())


def unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    for index in range(1, 1000):
        candidate = path.with_name(f"{stem}_{index}{suffix}")
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"无法生成唯一文件名：{path}")


def find_output_file(output_dir: Path, save_name: str) -> Path:
    candidates = sorted(output_dir.glob(f"{save_name}*"), key=lambda item: item.stat().st_mtime, reverse=True)
    for candidate in candidates:
        if candidate.suffix.lower() in {".mp4", ".mkv", ".ts", ".m4a"}:
            return candidate
    return output_dir / f"{save_name}.mp4"
