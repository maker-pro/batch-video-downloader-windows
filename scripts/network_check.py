from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys
import threading

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.models import AppSettings
from src.parser import parse_page_video


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/":
            body = b"""
            <html>
              <head><title>Network Only Video</title></head>
              <body>
                <button class="play">Play</button>
                <script>
                  document.querySelector('.play').addEventListener('click', function () {
                    fetch('/video/' + 'small' + '.m3u8');
                    fetch('/video/' + 'large' + '.m3u8');
                  });
                </script>
              </body>
            </html>
            """
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(body)
            return

        if self.path == "/video/small.m3u8":
            body = b"#EXTM3U\n#EXT-X-VERSION:3\n#EXTINF:1,\nsmall.ts\n"
            self.send_response(200)
            self.send_header("Content-Type", "application/vnd.apple.mpegurl")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if self.path == "/video/large.m3u8":
            body = b"#EXTM3U\n#EXT-X-VERSION:3\n" + (b"#EXTINF:1,\nlarge.ts\n" * 20)
            self.send_response(200)
            self.send_header("Content-Type", "application/vnd.apple.mpegurl")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        self.send_response(404)
        self.end_headers()

    def log_message(self, format: str, *args) -> None:
        return


def main() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        url = f"http://127.0.0.1:{server.server_port}/"
        settings = AppSettings(output_dir=ROOT / "downloads", m3u8dl_path=ROOT / "tools" / "N_m3u8DL-CLI.exe")
        video = parse_page_video(url, settings)
        assert video.selected.url.endswith("/video/large.m3u8")
        assert video.selected.source.startswith("network")
        assert video.selected.content_length is not None
        print("network_check passed")
    finally:
        server.shutdown()


if __name__ == "__main__":
    main()
