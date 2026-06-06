"""AutoChat service manager. Usage: python manage_services.py start|stop"""
import os
import socket
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
BE_DIR = os.path.join(ROOT, "backend")
FE_DIR = os.path.join(ROOT, "frontend-react")
PG_CTL = os.environ.get("AUTOCHAT_PG_CTL", "pg_ctl")
PG_DATA = os.environ.get("AUTOCHAT_PG_DATA", os.path.join(ROOT, ".pgdata"))
REDIS = os.environ.get("AUTOCHAT_REDIS_SERVER", "redis-server")
REDIS_CLI = os.environ.get("AUTOCHAT_REDIS_CLI", "redis-cli")
CREATE_NEW_CONSOLE = 0x00000010
DET = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP


def port_ok(port):
    for host in ("127.0.0.1", "::1"):
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return True
        except OSError:
            pass
    return False


def wait_port(port, secs=15):
    t = time.time() + secs
    while time.time() < t:
        if port_ok(port):
            return True
        time.sleep(0.3)
    return False


def run(cmd, timeout=10):
    try:
        return subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=timeout)
    except Exception:
        return None


def backend_command():
    return subprocess.list2cmdline(
        [
            sys.executable,
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


def frontend_command():
    return subprocess.list2cmdline(
        [
            "npm",
            "run",
            "dev",
            "--",
            "--host",
            "127.0.0.1",
            "--port",
            "5174",
        ]
    )


def open_console(title, command, cwd):
    subprocess.Popen(["cmd", "/k", f"title {title} && {command}"], cwd=cwd, creationflags=CREATE_NEW_CONSOLE)


def start():
    print("=" * 30)
    print("  AutoChat - Start")
    print("=" * 30, flush=True)

    print("[1/4] PostgreSQL...", flush=True)
    r = run([PG_CTL, "-D", PG_DATA, "status"])
    if r and r.returncode == 0:
        print("      already running", flush=True)
    else:
        run([PG_CTL, "-D", PG_DATA, "start"], timeout=15)
        print("      started" if wait_port(5432, 15) else "      FAILED", flush=True)

    print("[2/4] Redis...", flush=True)
    if port_ok(6379):
        print("      already running", flush=True)
    else:
        subprocess.Popen([REDIS], creationflags=DET, close_fds=True)
        print("      started" if wait_port(6379, 5) else "      FAILED", flush=True)

    print("[3/4] Backend...", flush=True)
    open_console("AutoChat Backend", backend_command(), BE_DIR)
    print("      started" if wait_port(8000, 60) else "      timeout", flush=True)

    print("[4/4] Frontend...", flush=True)
    open_console("AutoChat Frontend", frontend_command(), FE_DIR)
    print("      started" if wait_port(5174, 60) else "      timeout", flush=True)

    print()
    print("=" * 30)
    print("  Backend: http://localhost:8000")
    print("  Frontend: http://localhost:5174")
    print("=" * 30, flush=True)

def stop():
    print("=" * 30)
    print("  AutoChat - Stop")
    print("=" * 30, flush=True)

    for name, port in [("Backend", 8000), ("Frontend", 5174)]:
        print(f"  Stopping {name}...", flush=True)
        try:
            out = subprocess.check_output(
                f'netstat -aon | findstr ":{port}" | findstr "LISTENING"',
                shell=True, timeout=5, stderr=subprocess.DEVNULL
            ).decode()
            for line in out.strip().splitlines():
                pid = line.split()[-1]
                subprocess.run(["taskkill", "/F", "/T", "/PID", pid], capture_output=True, timeout=5)
        except Exception:
            pass
        print("      stopped", flush=True)

    print("  Stopping Redis...", flush=True)
    run([REDIS_CLI, "shutdown"], timeout=3)
    print("      stopped", flush=True)

    print("  Stopping PostgreSQL...", flush=True)
    run([PG_CTL, "-D", PG_DATA, "stop", "-m", "fast"], timeout=15)
    print("      stopped", flush=True)

    print()
    print("=" * 30)
    print("  All stopped")
    print("=" * 30, flush=True)

if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else ""
    if action == "start":
        start()
    elif action == "stop":
        stop()
    else:
        print(f"Usage: python {sys.argv[0]} start|stop")
