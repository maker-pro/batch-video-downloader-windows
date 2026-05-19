from __future__ import annotations

import queue
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Iterable

from .downloader import DownloadCancelled, Downloader
from .models import AppSettings, TaskStatus, TaskUpdate
from .parser import parse_page_video


class BatchRunner:
    def __init__(self, settings: AppSettings):
        self.settings = settings
        self.updates: queue.Queue[TaskUpdate] = queue.Queue()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def start(self, urls: Iterable[str]) -> None:
        if self.running:
            return
        self._stop_event.clear()
        clean_urls = [url.strip() for url in urls if url.strip()]
        self._thread = threading.Thread(target=self._run, args=(clean_urls,), daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()

    def _emit(self, update: TaskUpdate) -> None:
        self.updates.put(update)

    def _run(self, urls: list[str]) -> None:
        if not urls:
            return
        concurrency = max(1, min(self.settings.concurrency, 16))
        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = [executor.submit(self._handle_one, url) for url in urls]
            for future in as_completed(futures):
                if self._stop_event.is_set():
                    break
                try:
                    future.result()
                except Exception:
                    pass

    def _handle_one(self, url: str) -> None:
        if self._stop_event.is_set():
            self._emit(TaskUpdate(url, TaskStatus.CANCELLED, "任务已取消"))
            return
        try:
            self._emit(TaskUpdate(url, TaskStatus.PARSING, "正在解析页面"))
            video = parse_page_video(url, self.settings)
            self._emit(
                TaskUpdate(
                    url,
                    TaskStatus.DOWNLOADING,
                    f"选中：{video.selected.media_type} {video.selected.url}",
                )
            )
            downloader = Downloader(self.settings, self._emit, self._stop_event.is_set)
            output = downloader.download(video)
            self._emit(TaskUpdate(url, TaskStatus.DONE, f"已保存：{output}", 1.0, output))
        except DownloadCancelled as exc:
            self._emit(TaskUpdate(url, TaskStatus.CANCELLED, str(exc)))
        except Exception as exc:
            self._emit(TaskUpdate(url, TaskStatus.FAILED, str(exc)))
