import importlib
import socket
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

manage_services = importlib.import_module("manage_services")


def test_run_discards_output_without_capture_pipes(monkeypatch):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append((cmd, kwargs))
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(manage_services.subprocess, "run", fake_run)

    result = manage_services.run(["pg_ctl", "status"], timeout=7)

    assert result.returncode == 0
    assert calls == [
        (
            ["pg_ctl", "status"],
            {
                "stdout": subprocess.DEVNULL,
                "stderr": subprocess.DEVNULL,
                "timeout": 7,
            },
        )
    ]


def test_port_ok_accepts_ipv6_loopback_listener():
    try:
        server = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
    except OSError:
        pytest.skip("IPv6 is not available on this host")

    with server:
        try:
            server.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
            server.bind(("::1", 0))
        except OSError:
            pytest.skip("IPv6 loopback is not available on this host")
        server.listen(1)
        port = server.getsockname()[1]

        assert manage_services.port_ok(port)


def test_backend_command_uses_current_python_without_nested_conda(monkeypatch):
    python = "python-test.exe"
    monkeypatch.setattr(manage_services.sys, "executable", python)

    command = manage_services.backend_command()

    assert command == subprocess.list2cmdline(
        [
            python,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
            "--reload",
        ]
    )
    assert "conda run" not in command


@pytest.mark.parametrize("batch_file", ["start-all.bat", "stop-all.bat"])
def test_batch_entrypoints_stream_conda_output(batch_file):
    text = (ROOT / batch_file).read_text(encoding="utf-8")
    normalized = " ".join(text.lower().split())

    assert "call conda run" in normalized
    assert "--no-capture-output" in text
    assert "python -u" in text
