"""Real HTTP deployment smoke; run with the application's installed Python."""

from __future__ import annotations

import http.cookiejar
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import HTTPCookieProcessor, Request, build_opener
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from storage import Store


def main():
    base = ROOT / ".tmp" / ("deployment-" + uuid4().hex)
    base.mkdir(parents=True)
    data = base / "data"
    data.mkdir()
    env = dict(os.environ, INSIGHT_DATA_ROOT=str(data), PYTHONDONTWRITEBYTECODE="1")
    for name in ("TEMP", "TMP", "TMPDIR"):
        env[name] = str(base)
    origin = "http://127.0.0.1:8877"
    env.pop("INSIGHT_PUBLIC_URL", None)
    env["INSIGHT_HOSTS"] = "127.0.0.1,localhost"
    resolved = subprocess.run(
        [sys.executable, "-c", "import runtime; print(runtime.JOBS.parent)"],
        cwd=ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if Path(resolved).resolve() != data.resolve():
        raise RuntimeError("Runtime must honor INSIGHT_DATA_ROOT before deployment checks can run.")
    subprocess.run(
        [sys.executable, "access.py", "init", "--username", "deployment-owner", "--generate"],
        cwd=ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    credentials = (data / "security" / "first-access.txt").read_text(encoding="utf-8")
    password = next(
        line.removeprefix("Password: ")
        for line in credentials.splitlines()
        if line.startswith("Password: ")
    )
    database = Store(data / "security" / "studio.sqlite3")
    database.create_user(
        "deployment-viewer", "viewer-long-password", "viewer", database.workspace()
    )
    # Avoid accidentally exercising an unrelated server already bound to this port.
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 8877))
    jar = http.cookiejar.CookieJar()
    client = build_opener(HTTPCookieProcessor(jar))
    checks = []

    def request(path, payload=None, csrf=None, origin_header=origin):
        headers = {}
        if payload is not None:
            headers.update({"Content-Type": "application/json", "Origin": origin_header})
        if csrf is not None:
            headers["X-CSRF-Token"] = csrf
        query = Request(
            origin + path,
            data=json.dumps(payload).encode() if payload is not None else None,
            headers=headers,
        )
        try:
            response = client.open(query, timeout=5)
        except HTTPError as error:
            response = error
        with response:
            return response.status, json.loads(response.read()), response.headers

    def check(condition, name):
        if not condition:
            raise AssertionError(name)
        checks.append(name)

    with (base / "server.log").open("w", encoding="utf-8") as log:
        server = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app:app", "--host", "127.0.0.1", "--port", "8877"],
            cwd=ROOT,
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
        )
        try:
            deadline = time.monotonic() + 30
            while True:
                if server.poll() is not None:
                    raise RuntimeError("Server exited; inspect " + str(base / "server.log"))
                try:
                    if request("/healthz")[0] == 200:
                        break
                except (URLError, TimeoutError, ConnectionError):
                    pass
                if time.monotonic() >= deadline:
                    raise TimeoutError(
                        "Server failed to start; inspect " + str(base / "server.log")
                    )
                time.sleep(0.2)
            check(request("/api/jobs")[0] == 401, "anonymous jobs denied")
            status, owner, headers = request(
                "/api/auth/login", {"username": "deployment-owner", "password": password}
            )
            check(status == 200 and bool(owner["csrf_token"]), "owner login")
            check(
                "HttpOnly" in headers.get("Set-Cookie", "")
                and "SameSite=strict" in headers.get("Set-Cookie", ""),
                "cookie protection",
            )
            check(request("/api/admin/users")[0] == 200, "owner administration")
            check(request("/api/auth/logout", {})[0] == 403, "missing csrf denied")
            check(
                request("/api/auth/logout", {}, owner["csrf_token"], "http://foreign.example")[0]
                == 403,
                "foreign origin denied",
            )
            check(request("/api/auth/logout", {}, owner["csrf_token"])[0] == 200, "owner logout")
            check(request("/api/jobs")[0] == 401, "revoked session denied")
            status, viewer, _ = request(
                "/api/auth/login",
                {"username": "deployment-viewer", "password": "viewer-long-password"},
            )
            check(status == 200, "viewer login")
            check(request("/api/admin/users")[0] == 403, "viewer administration denied")
            check(
                request("/api/jobs", {}, viewer["csrf_token"])[0] == 403,
                "viewer upload denied before model work",
            )
            check(request("/api/auth/session")[1]["user"]["role"] == "viewer", "viewer session")
            check(database.verify_audit(), "HTTP audit verified")
        finally:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait(timeout=5)
    (base / "verification.json").write_text(
        json.dumps({"checks": checks, "count": len(checks)}, indent=2), encoding="utf-8"
    )
    print(f"Deployment HTTP checks passed: {len(checks)}; report {base / 'verification.json'}")


if __name__ == "__main__":
    main()
