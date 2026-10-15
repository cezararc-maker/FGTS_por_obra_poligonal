from __future__ import annotations

import argparse
import json
import secrets
import subprocess
import sys
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from .excel_reader import ler_planilha

MAX_XLSX_BYTES = 5_000_000
IDLE_SECONDS = 2 * 60 * 60


def _save_imported_xlsx(data: bytes, downloads: Path) -> Path:
    if not data or len(data) > MAX_XLSX_BYTES:
        raise ValueError("A planilha está vazia ou excede 5 MB.")
    downloads.mkdir(parents=True, exist_ok=True)
    path = downloads / f"FGTS_Extrator_integrado_{secrets.token_hex(5)}.xlsx"
    with path.open("xb") as target:
        target.write(data)
    try:
        result = ler_planilha(path)
        if not result.valida or not result.itens:
            raise ValueError("Planilha inválida: " + "; ".join(result.erros))
        final = downloads / f"FGTS_Extrator_{result.competencia.replace('/', '')}_{secrets.token_hex(4)}.xlsx"
        path.rename(final)
        return final
    except Exception:
        path.unlink(missing_ok=True)
        raise


def _handler(html: Path, token: str, launch, downloads: Path):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def _json(self, status: int, payload: dict) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            self.server.last_activity = time.monotonic()
            url = urlsplit(self.path)
            if url.path != "/" or parse_qs(url.query).get("token") != [token]:
                self.send_error(404)
                return
            body = html.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            self.server.last_activity = time.monotonic()
            expected_origin = f"http://127.0.0.1:{self.server.server_port}"
            if (self.path != "/api/import" or
                    self.headers.get("Origin") != expected_origin or
                    self.headers.get("X-FGTS-Token") != token or
                    self.headers.get("Content-Type") != "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"):
                self._json(403, {"error": "Solicitação de integração não autorizada."})
                return
            try:
                size = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                size = 0
            if size <= 0 or size > MAX_XLSX_BYTES:
                self._json(413, {"error": "A planilha está vazia ou excede 5 MB."})
                return
            self.connection.settimeout(15)
            try:
                path = _save_imported_xlsx(self.rfile.read(size), downloads)
                launch(path)
            except Exception as exc:
                self._json(422, {"error": str(exc)})
                return
            self._json(200, {"ok": True, "file": path.name})

    return Handler


def launch_fgts(path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    subprocess.Popen(
        [sys.executable, "-m", "fgts_obra.app_final", "--planilha", str(path)],
        cwd=root,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def serve(reader_html: Path, *, launch=launch_fgts, downloads: Path | None = None,
          open_browser=webbrowser.open, idle_seconds: int = IDLE_SECONDS) -> None:
    reader_html = reader_html.resolve()
    if reader_html.name != "Leitor_FGTS.html" or not reader_html.is_file():
        raise FileNotFoundError("Leitor_FGTS.html não encontrado.")
    token = secrets.token_urlsafe(24)
    handler = _handler(reader_html, token, launch, downloads or Path.home() / "Downloads")
    with HTTPServer(("127.0.0.1", 0), handler) as server:
        server.timeout = 1
        open_browser(f"http://127.0.0.1:{server.server_port}/?token={token}")
        server.last_activity = time.monotonic()
        while time.monotonic() - server.last_activity < idle_seconds:
            server.handle_request()


def main() -> None:
    parser = argparse.ArgumentParser(description="Abre o leitor com integração local ao FGTS por Obra.")
    parser.add_argument("--reader", type=Path, required=True)
    args = parser.parse_args()
    serve(args.reader)


if __name__ == "__main__":
    main()
