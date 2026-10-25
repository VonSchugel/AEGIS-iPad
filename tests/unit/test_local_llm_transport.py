"""Real loopback HTTP and worker tests; no Ollama model or device is required."""
import asyncio
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import sys
import threading
import time

import pytest

from aegis.adapters.local_llm import LocalLLMError, LocalLLMProvider, MAX_RESPONSE_BYTES


@contextmanager
def local_server(*, payload=b'{"models":[{"name":"qwen3:0.6b"}]}', trickle=False, redirect=False):
    """Bounded test-owned server; every accepted connection is loopback."""
    entered, stop = threading.Event(), threading.Event()
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            requests.append(self.path)
            entered.set()
            if redirect:
                self.send_response(302)
                self.send_header("Location", "/must-not-be-requested")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(10000 if trickle else len(payload)))
            self.end_headers()
            try:
                if trickle:
                    # Regular activity prevents an inactivity timeout. Only the
                    # parent's total deadline or cancellation can stop the read.
                    for _ in range(100):
                        self.wfile.write(b" ")
                        self.wfile.flush()
                        if stop.wait(0.04):
                            break
                else:
                    self.wfile.write(payload)
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    thread = threading.Thread(target=lambda: server.serve_forever(poll_interval=0.02), daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", entered, requests
    finally:
        stop.set()
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def track_workers(monkeypatch):
    original = asyncio.create_subprocess_exec
    workers, arguments = [], []

    async def start(*args, **kwargs):
        process = await original(*args, **kwargs)
        workers.append(process)
        arguments.append(args)
        return process

    monkeypatch.setattr(asyncio, "create_subprocess_exec", start)
    return workers, arguments


@pytest.mark.parametrize("host,expected", [
    ("http://localhost:11434", "http://127.0.0.1:11434/api/tags"),
    ("http://127.0.0.2:11434/", "http://127.0.0.2:11434/api/tags"),
    ("http://[::1]:11434", "http://[::1]:11434/api/tags"),
])
def test_only_pinned_numeric_loopback_destinations(host, expected):
    assert LocalLLMProvider(host=host)._endpoint("/api/tags") == expected


@pytest.mark.parametrize("host", [
    "http://192.0.2.1:11434", "http://example.org", "http://127.0.0.1:0",
    "http://127.0.0.1:65536", "http://127.0.0.1:11434/path", "http://localhost?x=1",
    "http://u:p@localhost", "http://[::1%zone]:11434", "http://localhost:11434/#fragment",
    "http://localhost\n", "https://localhost:11434",
])
def test_invalid_destinations_never_start_worker(host, monkeypatch):
    monkeypatch.setattr(asyncio, "create_subprocess_exec", lambda *args, **kwargs: pytest.fail("Invalid destination reached a worker"))
    with pytest.raises(LocalLLMError, match="invalid_local_endpoint"):
        LocalLLMProvider(host=host)


async def test_real_status_worker_ignores_ambient_proxies(monkeypatch):
    for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
        monkeypatch.setenv(name, "http://127.0.0.1:1")
    with local_server() as (host, entered, paths):
        workers, arguments = track_workers(monkeypatch)
        result = await LocalLLMProvider(host=host, timeout=3).status()
        assert result["status"] == "ready" and entered.is_set()
        assert paths == ["/api/tags"]
        assert len(workers) == 1 and workers[0].returncode == 0
        assert arguments[0] == (sys.executable, "-m", "aegis.adapters.local_llm_worker")


async def test_total_deadline_terminates_a_slowly_streaming_worker(monkeypatch):
    with local_server(trickle=True) as (host, entered, paths):
        workers, _ = track_workers(monkeypatch)
        started = time.monotonic()
        with pytest.raises(LocalLLMError, match="service_timeout"):
            await LocalLLMProvider(host=host, timeout=0.8)._request_http_json("/api/tags")
        assert entered.is_set() and paths == ["/api/tags"]
        assert time.monotonic() - started < 2.8
        assert len(workers) == 1 and workers[0].returncode is not None


async def test_cancellation_stops_worker_without_waiting_for_http_thread(monkeypatch):
    with local_server(trickle=True) as (host, entered, _):
        workers, _ = track_workers(monkeypatch)
        task = asyncio.create_task(LocalLLMProvider(host=host, timeout=10)._request_http_json("/api/tags"))
        try:
            for _ in range(100):
                if entered.is_set():
                    break
                await asyncio.sleep(0.02)
            assert entered.is_set(), "The actual worker never reached the test server"
            started = time.monotonic()
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await asyncio.wait_for(task, 2)
            assert time.monotonic() - started < 2
            assert len(workers) == 1 and workers[0].returncode is not None
        finally:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass


async def test_worker_rejects_redirect_without_requesting_destination():
    with local_server(redirect=True) as (host, _, paths):
        with pytest.raises(LocalLLMError, match="redirect_rejected"):
            await LocalLLMProvider(host=host, timeout=3)._request_http_json("/api/tags")
        assert paths == ["/api/tags"]


@pytest.mark.parametrize("payload,code", [
    (b'{"padding":"' + b"x" * MAX_RESPONSE_BYTES + b'"}', "response_too_large"),
    (b'{"counter":' + b"9" * 5000 + b'}', "invalid_response"),
    (b'{"models":[],"models":[]}', "invalid_response"),
    (b'{"models":NaN}', "invalid_response"),
], ids=["oversized", "integer-limit", "duplicate-key", "nonfinite"])
async def test_worker_normalizes_invalid_http_responses(payload, code):
    with local_server(payload=payload) as (host, _, _):
        with pytest.raises(LocalLLMError, match=code):
            await LocalLLMProvider(host=host, timeout=3)._request_http_json("/api/tags")


@pytest.mark.parametrize("packet,error", [(b"not-json", "invalid_request"), (b"x" * 32769, "input_too_large")], ids=["invalid-json", "oversized-input"])
async def test_worker_protocol_rejects_unbounded_or_invalid_stdin(packet, error):
    process = await asyncio.create_subprocess_exec(sys.executable, "-m", "aegis.adapters.local_llm_worker",
                                               stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
                                               stderr=asyncio.subprocess.PIPE)
    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(packet), 3)
        assert process.returncode == 0 and stderr == b""
        assert json.loads(stdout) == {"ok": False, "error": error}
    finally:
        if process.returncode is None:
            process.kill()
            await process.wait()
