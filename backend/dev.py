"""Start the local API, training worker and React UI with one command."""
import argparse
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import urlopen
import uuid

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "backend/storage"
STATE = RUNTIME / "run-state.json"


def get_json(url):
    with urlopen(url, timeout=1) as response:
        return json.load(response)


def read_state():
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def ready(state):
    try:
        health = get_json(state["api_url"] + "/api/health")
        with urlopen(state["url"], timeout=1) as response:
            return health.get("instance") == state["instance"] and health.get("application") == "pulsar-research" and response.status == 200
    except (KeyError, OSError, URLError, ValueError):
        return False


def free_port(first):
    for port in range(first, first + 20):
        with socket.socket() as connection:
            try:
                connection.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError(f"No local port available near {first}")


def run_child(args, log, environment, cwd=ROOT):
    return subprocess.Popen(args, cwd=cwd, env=environment, stdout=log, stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)


def serve():
    RUNTIME.mkdir(parents=True, exist_ok=True)
    logs = RUNTIME / "logs"
    logs.mkdir(exist_ok=True)
    lock = (RUNTIME / "launcher.lock").open("a+b")
    if lock.tell() == 0:
        lock.write(b"0"); lock.flush()
    lock.seek(0)
    try:
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        lock.close()
        raise RuntimeError("Another application launcher is already running; use python -m backend.dev --status")
    children, streams = [], []
    instance = uuid.uuid4().hex
    state = {"pid": os.getpid(), "instance": instance, "status": "starting"}
    try:
        node = shutil.which("node")
        vite = ROOT / "frontend/node_modules/vite/bin/vite.js"
        if not node or not vite.is_file():
            raise RuntimeError("Frontend dependencies missing. Install Node.js and run npm ci in frontend.")
        # Migrations finish before either process can initialize/use the schema.
        subprocess.run([sys.executable, "-m", "alembic", "-c", "backend/alembic.ini", "upgrade", "head"], cwd=ROOT, check=True)
        api_port, ui_port = free_port(8000), 7351
        state.update(api_url=f"http://127.0.0.1:{api_port}", url=f"http://127.0.0.1:{ui_port}")
        STATE.write_text(json.dumps(state), encoding="utf-8")
        environment = {**os.environ, "PYTHONUNBUFFERED": "1", "PULSAR_INSTANCE": instance,
                       "ENABLE_LOCAL_SETUP": "true", "API_PROXY_TARGET": state["api_url"],
                       "CORS_ORIGINS": f"{state['url']},http://localhost:{ui_port}"}
        commands = [
            ("api", [sys.executable, "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", str(api_port)], ROOT),
            ("worker", [sys.executable, "-m", "backend.worker"], ROOT),
            ("frontend", [node, str(vite), "--host", "127.0.0.1", "--port", str(ui_port), "--strictPort"], ROOT / "frontend"),
        ]
        for name, command, cwd in commands:
            stream = (logs / f"{name}.log").open("a", encoding="utf-8")
            streams.append(stream)
            children.append((name, run_child(command, stream, environment, cwd)))
        deadline = time.monotonic() + 90
        while not ready(state):
            for name, child in children:
                if child.poll() is not None:
                    raise RuntimeError(f"{name} exited ({child.returncode}). See {logs / (name + '.log')}")
            if time.monotonic() > deadline:
                raise RuntimeError(f"Startup timed out. Inspect logs in {logs}")
            time.sleep(.3)
        state["status"] = "ready"
        STATE.write_text(json.dumps(state), encoding="utf-8")
        print(f"PULSAR is ready: {state['url']}\nFirst run: create your Admin account in the browser.\nLogs: {logs}", flush=True)
        while True:
            for name, child in children:
                if child.poll() is not None:
                    raise RuntimeError(f"{name} stopped ({child.returncode}). See {logs / (name + '.log')}")
            time.sleep(1)
    finally:
        for _, child in reversed(children):
            child.terminate()
        for _, child in children:
            try:
                child.wait(timeout=8)
            except subprocess.TimeoutExpired:
                child.kill()
        for stream in streams:
            stream.close()
        if read_state().get("instance") == instance:
            STATE.unlink(missing_ok=True)
        lock.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--detach", action="store_true", help="Start in background and wait for readiness")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--stop", action="store_true", help="Stop only this project's background launcher")
    parser.add_argument("--serve", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    current = read_state()
    if args.status:
        print(json.dumps({**current, "ready": ready(current)}, indent=2))
        return
    if args.stop:
        pid = int(current.get("pid", 0))
        if pid <= 0:
            parser.error("No launcher state found")
        if os.name == "nt":
            # Check the command before stopping a PID to avoid killing a reused PID.
            command = f"$p = Get-CimInstance Win32_Process -Filter 'ProcessId = {pid}'; if ($p.CommandLine -match '-m backend.dev --serve') {{ taskkill.exe /PID {pid} /T /F }} else {{ exit 2 }}"
            subprocess.run(["powershell.exe", "-NoProfile", "-Command", command], check=True)
        else:
            if b"backend.dev" not in Path(f"/proc/{pid}/cmdline").read_bytes():
                parser.error("PID no longer belongs to this launcher")
            os.kill(pid, signal.SIGTERM)
        STATE.unlink(missing_ok=True)
        return
    if ready(current):
        print(f"PULSAR is already running: {current['url']}")
        return
    if args.detach:
        RUNTIME.mkdir(parents=True, exist_ok=True)
        with (RUNTIME / "launcher.log").open("a", encoding="utf-8") as log:
            process = subprocess.Popen([sys.executable, "-m", "backend.dev", "--serve"], cwd=ROOT,
                stdout=log, stderr=subprocess.STDOUT,
                creationflags=(subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP) if os.name == "nt" else 0,
                start_new_session=os.name != "nt")
        deadline = time.monotonic() + 100
        while time.monotonic() < deadline:
            state = read_state()
            if ready(state):
                print(f"PULSAR is ready: {state['url']}\nCreate your first Admin account in the browser if prompted.")
                return
            if process.poll() is not None:
                parser.error(f"Launcher stopped. See {RUNTIME / 'launcher.log'}")
            time.sleep(.5)
        parser.error(f"Startup not confirmed; inspect {RUNTIME / 'launcher.log'}")
    try:
        serve()
    except KeyboardInterrupt:
        print("PULSAR stopped.")


if __name__ == "__main__":
    main()
