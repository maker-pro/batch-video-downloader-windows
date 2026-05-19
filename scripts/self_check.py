from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.models import VideoCandidate
from src.parser import extract_candidates, extract_title, merge_candidates
from src.utils import sanitize_filename


def main() -> None:
    html = """
    <html>
      <head><title>Test: Video/Title?</title></head>
      <body>
        <video src="/media/720p.mp4"></video>
        <script>window.__DATA__ = {"hls":"https:\\/\\/cdn.example.com\\/master.m3u8"}</script>
      </body>
    </html>
    """
    title = extract_title(html, "https://example.com/watch/123")
    candidates = list(extract_candidates(html, "https://example.com/watch/123"))
    network = [
        VideoCandidate(
            url="https://stream.example.com/live/index.m3u8?quality=best",
            source="network-response",
            media_type="m3u8",
        )
    ]
    merged = merge_candidates(candidates, network)

    assert title == sanitize_filename("Test: Video/Title?")
    assert any(item.url == "https://example.com/media/720p.mp4" for item in merged)
    assert any(item.url == "https://cdn.example.com/master.m3u8" for item in merged)
    assert any(item.source == "network-response" for item in merged)
    print("self_check passed")


if __name__ == "__main__":
    main()
