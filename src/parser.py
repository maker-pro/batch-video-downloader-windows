from __future__ import annotations

import html
import random
import re
import time
from dataclasses import replace
from typing import Iterable
from urllib.parse import unquote, urljoin, urlparse

import requests

try:
    from bs4 import BeautifulSoup
except Exception:  # pragma: no cover - optional dependency
    BeautifulSoup = None

from .models import AppSettings, PageVideo, VideoCandidate
from .utils import (
    extension_from_url,
    is_m3u8_url,
    is_supported_media_url,
    same_host_score,
    sanitize_filename,
)


USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
]

MEDIA_URL_RE = re.compile(
    r"""(?P<url>(?:https?:)?//[^"'\\<>\s]+?\.(?:m3u8|mp4|m4v|mov|webm|flv|mkv|avi)(?:\?[^"'\\<>\s]*)?|/[^"'\\<>\s]+?\.(?:m3u8|mp4|m4v|mov|webm|flv|mkv|avi)(?:\?[^"'\\<>\s]*)?)""",
    re.IGNORECASE,
)

JSON_ESCAPED_URL_RE = re.compile(
    r"""https?:\\?/\\?/[^"'<>]+?\.(?:m3u8|mp4|m4v|mov|webm|flv|mkv|avi)(?:\\?\?[^"'<>]*)?""",
    re.IGNORECASE,
)


class VideoParseError(RuntimeError):
    pass


class RenderedPage:
    def __init__(self, html_text: str = "", network_candidates: list[VideoCandidate] | None = None):
        self.html_text = html_text
        self.network_candidates = network_candidates or []


def build_headers(page_url: str | None = None) -> dict[str, str]:
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.7",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }
    if page_url:
        headers["Referer"] = page_url
    return headers


def proxies_for(settings: AppSettings) -> dict[str, str] | None:
    if not settings.proxy:
        return None
    return {"http": settings.proxy, "https": settings.proxy}


def parse_page_video(page_url: str, settings: AppSettings) -> PageVideo:
    page_url = page_url.strip()
    if not page_url:
        raise VideoParseError("URL is empty")

    if is_supported_media_url(page_url):
        title = title_from_url(page_url)
        media_type = "m3u8" if is_m3u8_url(page_url) else extension_from_url(page_url).lstrip(".")
        candidate = VideoCandidate(page_url, "direct-url", media_type, score=100)
        if is_m3u8_url(page_url):
            candidate = best_m3u8_variant(candidate, page_url, settings)
        return PageVideo(page_url=page_url, title=title, selected=candidate, candidates=[candidate])

    session = requests.Session()
    response = fetch_with_retries(session, page_url, settings)
    content_type = response.headers.get("content-type", "")
    if "video/" in content_type or is_supported_media_url(response.url):
        title = title_from_url(response.url)
        media_type = "m3u8" if is_m3u8_url(response.url) else extension_from_url(response.url).lstrip(".")
        candidate = VideoCandidate(response.url, "redirected-direct", media_type, score=100, content_type=content_type)
        return PageVideo(response.url, title, candidate, [candidate])

    text = response.text
    title = extract_title(text, page_url)
    candidates = list(extract_candidates(text, page_url))

    if settings.enable_playwright:
        rendered = fetch_rendered_page(page_url, settings)
        if rendered.html_text and not candidates:
            title = extract_title(rendered.html_text, page_url) or title
            candidates = list(extract_candidates(rendered.html_text, page_url))
        candidates = merge_candidates(candidates, rendered.network_candidates)

    if not candidates:
        raise VideoParseError("No m3u8/mp4 media link was found in the page HTML or browser Network requests")

    candidates = enrich_candidates(session, page_url, candidates, settings)
    selected = select_best_candidate(candidates)
    if selected.media_type == "m3u8":
        selected = best_m3u8_variant(selected, page_url, settings)
    return PageVideo(page_url=page_url, title=title, selected=selected, candidates=candidates)


def fetch_with_retries(session: requests.Session, url: str, settings: AppSettings) -> requests.Response:
    last_error: Exception | None = None
    for index in range(3):
        try:
            if index:
                time.sleep(0.8 + index * 0.7)
            response = session.get(
                url,
                headers=build_headers(url),
                proxies=proxies_for(settings),
                timeout=settings.request_timeout,
                allow_redirects=True,
            )
            response.raise_for_status()
            return response
        except Exception as exc:
            last_error = exc
    raise VideoParseError(f"Page request failed: {last_error}") from last_error


def extract_title(text: str, page_url: str) -> str:
    title = ""
    if BeautifulSoup:
        soup = BeautifulSoup(text, "lxml")
        if soup.title and soup.title.string:
            title = soup.title.string
        if not title:
            og = soup.find("meta", attrs={"property": "og:title"}) or soup.find("meta", attrs={"name": "title"})
            if og:
                title = og.get("content", "")
    if not title:
        match = re.search(r"<title[^>]*>(.*?)</title>", text, re.I | re.S)
        if match:
            title = re.sub(r"\s+", " ", match.group(1)).strip()
    if not title:
        match = re.search(
            r"""<meta[^>]+(?:property|name)=["'](?:og:title|title)["'][^>]+content=["']([^"']+)["']""",
            text,
            re.I | re.S,
        )
        if match:
            title = match.group(1)
    return sanitize_filename(html.unescape(title), fallback=title_from_url(page_url))


def title_from_url(url: str) -> str:
    parsed = urlparse(url)
    last = unquote(parsed.path.rstrip("/").split("/")[-1])
    if "." in last:
        last = last.rsplit(".", 1)[0]
    return sanitize_filename(last or parsed.hostname or "video")


def extract_candidates(text: str, page_url: str) -> Iterable[VideoCandidate]:
    seen: set[str] = set()

    if BeautifulSoup:
        soup = BeautifulSoup(text, "lxml")
        for tag in soup.find_all(["video", "source", "a", "meta"]):
            attrs = ["src", "href", "content", "data-src", "data-url", "poster"]
            for attr in attrs:
                raw = tag.get(attr)
                if raw:
                    yield from candidate_from_raw(raw, page_url, f"{tag.name}.{attr}", seen)
    else:
        for match in re.finditer(
            r"""(?:src|href|content|data-src|data-url|poster)\s*=\s*["']([^"']+)["']""",
            text,
            re.I,
        ):
            yield from candidate_from_raw(match.group(1), page_url, "attr-regex", seen)

    for match in MEDIA_URL_RE.finditer(text):
        yield from candidate_from_raw(match.group("url"), page_url, "html-regex", seen)

    for match in JSON_ESCAPED_URL_RE.finditer(text):
        raw = match.group(0).replace("\\/", "/")
        yield from candidate_from_raw(raw, page_url, "json-escaped", seen)

    unescaped = html.unescape(text).replace("\\u002F", "/").replace("\\/", "/")
    if unescaped != text:
        for match in MEDIA_URL_RE.finditer(unescaped):
            yield from candidate_from_raw(match.group("url"), page_url, "unescaped-html", seen)


def candidate_from_raw(raw: str, page_url: str, source: str, seen: set[str]) -> Iterable[VideoCandidate]:
    raw = html.unescape(str(raw)).strip().strip('"').strip("'")
    raw = raw.replace("\\/", "/").replace("\\u0026", "&")
    if raw.startswith("//"):
        raw = "https:" + raw
    url = urljoin(page_url, raw)
    if not is_supported_media_url(url) or url in seen:
        return
    seen.add(url)
    media_type = "m3u8" if is_m3u8_url(url) else extension_from_url(url).lstrip(".")
    yield VideoCandidate(url=url, source=source, media_type=media_type)


def merge_candidates(current: list[VideoCandidate], incoming: Iterable[VideoCandidate]) -> list[VideoCandidate]:
    seen = {item.url for item in current}
    merged = list(current)
    for item in incoming:
        if item.url in seen:
            continue
        seen.add(item.url)
        merged.append(item)
    return merged


def select_best_candidate(candidates: list[VideoCandidate]) -> VideoCandidate:
    network_m3u8 = [
        item
        for item in candidates
        if item.source.startswith("network") and item.media_type == "m3u8"
    ]
    network_m3u8_with_size = [item for item in network_m3u8 if item.content_length]
    if network_m3u8_with_size:
        return max(network_m3u8_with_size, key=lambda item: (item.content_length or 0, item.score))
    if network_m3u8:
        return max(network_m3u8, key=lambda item: item.score)
    return max(candidates, key=lambda item: item.score)


def enrich_candidates(
    session: requests.Session,
    page_url: str,
    candidates: list[VideoCandidate],
    settings: AppSettings,
) -> list[VideoCandidate]:
    enriched: list[VideoCandidate] = []
    for item in candidates:
        score = base_score(page_url, item) + item.score
        content_type = item.content_type
        content_length = item.content_length
        try:
            response = session.head(
                item.url,
                headers=build_headers(page_url),
                proxies=proxies_for(settings),
                timeout=min(settings.request_timeout, 12),
                allow_redirects=True,
            )
            response.raise_for_status()
            content_type = response.headers.get("content-type", content_type)
            length = response.headers.get("content-length")
            if length and length.isdigit():
                content_length = int(length)
            if "mpegurl" in content_type or "application/vnd.apple" in content_type:
                score += 25
            elif content_type.startswith("video/"):
                score += 25
            if content_length:
                score += min(content_length // (1024 * 1024), 60)
        except Exception:
            pass

        resolution = item.resolution or resolution_from_url(item.url)
        if resolution:
            score += resolution_score(resolution)

        enriched.append(
            replace(
                item,
                score=score,
                content_type=content_type,
                content_length=content_length,
                resolution=resolution,
            )
        )
    return enriched


def base_score(page_url: str, item: VideoCandidate) -> int:
    url_lower = item.url.lower()
    score = 35 if item.media_type == "m3u8" else 25
    score += same_host_score(page_url, item.url)
    if item.source.startswith("network"):
        score += 30
    for token in ("master", "playlist", "index", "video", "play", "source", "main"):
        if token in url_lower:
            score += 5
    for token in ("thumb", "poster", "preview", "ad.", "/ads/", "avatar"):
        if token in url_lower:
            score -= 25
    return score


def resolution_from_url(url: str) -> str | None:
    match = re.search(r"(?<!\d)(2160|1440|1080|720|540|480|360|240)p?(?!\d)", url, re.I)
    if match:
        return match.group(1) + "p"
    match = re.search(r"(?<!\d)(\d{3,4})x(\d{3,4})(?!\d)", url, re.I)
    if match:
        return f"{match.group(1)}x{match.group(2)}"
    return None


def resolution_score(resolution: str) -> int:
    numbers = [int(value) for value in re.findall(r"\d+", resolution)]
    if not numbers:
        return 0
    height = min(numbers) if "x" in resolution else numbers[0]
    return min(height // 24, 90)


def best_m3u8_variant(candidate: VideoCandidate, page_url: str, settings: AppSettings) -> VideoCandidate:
    try:
        response = requests.get(
            candidate.url,
            headers=build_headers(page_url),
            proxies=proxies_for(settings),
            timeout=min(settings.request_timeout, 12),
        )
        response.raise_for_status()
    except Exception:
        return candidate

    lines = response.text.splitlines()
    variants: list[tuple[int, str, str | None]] = []
    for index, line in enumerate(lines):
        if not line.startswith("#EXT-X-STREAM-INF"):
            continue
        bandwidth = 0
        resolution = None
        bw_match = re.search(r"BANDWIDTH=(\d+)", line, re.I)
        res_match = re.search(r"RESOLUTION=(\d+x\d+)", line, re.I)
        if bw_match:
            bandwidth = int(bw_match.group(1))
        if res_match:
            resolution = res_match.group(1)
        for next_line in lines[index + 1 : index + 5]:
            next_line = next_line.strip()
            if next_line and not next_line.startswith("#"):
                variants.append((bandwidth, urljoin(candidate.url, next_line), resolution))
                break

    if not variants:
        return candidate

    bandwidth, url, resolution = max(variants, key=lambda item: item[0])
    return replace(
        candidate,
        url=url,
        source=candidate.source + "+best-variant",
        score=candidate.score + min(bandwidth // 100000, 60),
        resolution=resolution,
    )


def fetch_rendered_page(page_url: str, settings: AppSettings) -> RenderedPage:
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        return RenderedPage()

    network_by_url: dict[str, VideoCandidate] = {}
    network_candidates: list[VideoCandidate] = []

    def remember_url(
        raw_url: str,
        source: str,
        content_type: str = "",
        content_length: int | None = None,
    ) -> None:
        if not raw_url:
            return
        lowered = raw_url.lower()
        looks_like_media = is_supported_media_url(raw_url) or "mpegurl" in content_type or content_type.startswith("video/")
        if not looks_like_media:
            return

        existing = network_by_url.get(raw_url)
        if existing:
            if content_type and not existing.content_type:
                existing.content_type = content_type
            if content_length and not existing.content_length:
                existing.content_length = content_length
            if source == "network-response" and existing.source == "network-request":
                existing.source = source
            return

        media_type = "m3u8" if is_m3u8_url(raw_url) or "mpegurl" in content_type else extension_from_url(raw_url).lstrip(".")
        if not media_type and content_type.startswith("video/"):
            media_type = content_type.split("/", 1)[1].split(";", 1)[0]
        candidate = VideoCandidate(
            url=raw_url,
            source=source,
            media_type=media_type or "video",
            score=45 if "m3u8" in lowered or "mpegurl" in content_type else 35,
            content_type=content_type,
            content_length=content_length,
        )
        network_by_url[raw_url] = candidate
        network_candidates.append(candidate)

    launch_args = ["--disable-blink-features=AutomationControlled"]
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=launch_args)
        context_kwargs = {
            "user_agent": random.choice(USER_AGENTS),
            "locale": "zh-CN",
            "viewport": {"width": 1366, "height": 768},
        }
        if settings.proxy:
            context_kwargs["proxy"] = {"server": settings.proxy}
        context = browser.new_context(**context_kwargs)
        page = context.new_page()
        page.on("request", lambda request: remember_url(request.url, "network-request"))

        def on_response(response) -> None:
            content_type = response.headers.get("content-type", "").lower()
            length = parse_content_length(response.headers.get("content-length", ""))
            remember_url(response.url, "network-response", content_type, length)

        page.on("response", on_response)
        try:
            page.goto(page_url, wait_until="domcontentloaded", timeout=settings.request_timeout * 1000)
            click_video_like_elements(page)
            try:
                page.wait_for_load_state("networkidle", timeout=min(settings.request_timeout * 1000, 15000))
            except Exception:
                pass
            page.wait_for_timeout(2500)
            return RenderedPage(page.content(), network_candidates)
        finally:
            context.close()
            browser.close()


def fetch_rendered_html(page_url: str, settings: AppSettings) -> str:
    return fetch_rendered_page(page_url, settings).html_text


def parse_content_length(value: str) -> int | None:
    value = value.strip()
    if not value.isdigit():
        return None
    return int(value)


def click_video_like_elements(page) -> None:
    selectors = [
        "video",
        "button[aria-label*='play' i]",
        "button[title*='play' i]",
        ".play",
        ".player",
        "[class*='play' i]",
    ]
    for selector in selectors:
        try:
            locator = page.locator(selector).first
            if locator.count():
                locator.click(timeout=1200, force=True)
                page.wait_for_timeout(800)
                return
        except Exception:
            continue
