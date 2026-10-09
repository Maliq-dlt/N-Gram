"""Run: .venv/Scripts/python tests/security_check.py. No production data or ML inference."""

from __future__ import annotations

import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import runtime

root = runtime.ROOT / ".tmp" / ("security_check_" + str(uuid4()))
from access_fixture import AccessFixture
from fastapi.testclient import TestClient

import access

fixture = AccessFixture(root)
runtime.JOBS = fixture.jobs
access._stores[access.database_path()] = fixture.store
import app

app.training_root = fixture.trainings
own_job = fixture.resource("job", fixture.owner)
other_job = fixture.resource("job", fixture.other)
other_training = fixture.resource("training", fixture.other)
checks = []


def check(condition, label):
    assert condition, label
    checks.append(label)
    print("PASS:", label, flush=True)


with TestClient(app.app) as anonymous:
    for route in app.app.routes:
        if (
            not getattr(route, "path", "").startswith("/api/")
            or route.path.startswith("/api/auth/")
            or route.path == "/api/health"
        ):
            continue
        path = (
            route.path.replace("{job_id}", own_job.name)
            .replace("{training_id}", other_training.name)
            .replace("{session_id}", str(uuid4()))
            .replace("{revision}", "1")
            .replace("{frame_index}", "0")
            .replace("{name}", "upload.bin")
        )
        for method in route.methods:
            response = anonymous.request(method, path)
            check(response.status_code == 401, f"anonymous {method} {path}: {response.status_code}")
    check(
        anonymous.post(
            "/api/auth/login",
            json={"username": "owner", "password": fixture.password},
            headers={"Origin": "https://evil.invalid"},
        ).status_code
        == 403,
        "login rejects foreign origin",
    )
    check(
        anonymous.post(
            "/api/auth/login", json={"username": "owner", "password": fixture.password}
        ).status_code
        == 403,
        "login requires Origin",
    )

with TestClient(app.app) as reviewer:
    session = fixture.login(reviewer, "reviewer")
    check(session["user"]["role"] == "reviewer", "reviewer session role")
    check(reviewer.get("/api/admin/users").status_code == 403, "reviewer cannot administer users")
    token = reviewer.cookies.get(access.COOKIE)
    user = fixture.store.session(token)
    background = []
    finished = Event()

    def capture_actor(folder):
        try:
            background.append(access.actor())
        finally:
            app.finish_work(folder)
            finished.set()

    context = access.principal.set(user)
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            app.submit_work(pool, capture_actor, own_job)
            check(finished.wait(5), "background worker completed")
    finally:
        access.principal.reset(context)
    check(
        background[0]["id"] == user["id"] and background[0]["workspace_id"] == user["workspace_id"],
        "worker preserves authenticated workspace context",
    )
    response = reviewer.get("/api/jobs")
    check(
        response.status_code == 200 and {job["id"] for job in response.json()} == {own_job.name},
        "list contains only own workspace",
    )
    check(
        reviewer.get(f"/api/jobs/{own_job.name}/media/original.mp4").status_code == 200,
        "own media readable",
    )
    for path in [
        f"/api/jobs/{other_job.name}",
        f"/api/jobs/{other_job.name}/media/original.mp4",
        f"/api/training/{other_training.name}",
    ]:
        check(reviewer.get(path).status_code == 404, "cross workspace denied " + path)
    response = reviewer.post(f"/api/jobs/{own_job.name}/cancel", headers={"X-CSRF-Token": "wrong"})
    check(response.status_code == 403, "mutation rejects incorrect CSRF")
    csrf = reviewer.headers.pop("X-CSRF-Token")
    check(
        reviewer.post(f"/api/jobs/{own_job.name}/cancel").status_code == 403,
        "mutation requires CSRF",
    )
    reviewer.headers["X-CSRF-Token"] = csrf
    check(
        reviewer.post(
            f"/api/jobs/{own_job.name}/cancel", headers=[(b"X-CSRF-Token", b"\xff")]
        ).status_code
        == 403,
        "non ASCII CSRF rejected safely",
    )
    request = reviewer.build_request("POST", f"/api/jobs/{own_job.name}/cancel")
    request.headers.pop("Content-Length", None)
    check(reviewer.send(request).status_code == 411, "mutation requires declared body length")
    check(
        reviewer.post(
            f"/api/jobs/{own_job.name}/cancel", headers={"Content-Length": str(1024 * 1024 + 1)}
        ).status_code
        == 413,
        "oversized non upload request rejected",
    )
    check(
        reviewer.post(
            f"/api/jobs/{own_job.name}/cancel", headers={"Origin": "https://evil.invalid"}
        ).status_code
        == 403,
        "authenticated mutation rejects foreign Origin",
    )
    check(
        reviewer.post(f"/api/jobs/{own_job.name}/cancel").status_code == 200,
        "reviewer can cancel own job",
    )
    response = reviewer.post(
        f"/api/jobs/{own_job.name}/retry", json={"model_id": other_training.name}
    )
    check(response.status_code == 404, "cross workspace model ID rejected")
    check(reviewer.post("/api/auth/logout").status_code == 200, "logout succeeds")
    check(reviewer.get("/api/jobs").status_code == 401, "logout revokes session")

with TestClient(app.app) as viewer:
    fixture.login(viewer, "viewer")
    check(viewer.get(f"/api/jobs/{own_job.name}").status_code == 200, "viewer reads job")
    for path in [
        "/api/jobs",
        "/api/training",
        f"/api/jobs/{own_job.name}/cancel",
        f"/api/jobs/{own_job.name}/annotations",
        f"/api/jobs/{own_job.name}/tracking",
        f"/api/jobs/{own_job.name}/reanalyze",
    ]:
        check(viewer.post(path, json={}).status_code == 403, "viewer mutation denied " + path)
    response = viewer.post("/api/chat", json={"message": "cara menggunakan aplikasi"})
    check(
        response.status_code == 200 and response.json()["mode"] == "guide",
        "viewer factual chat allowed without model inference",
    )

with TestClient(app.app) as admin:
    fixture.login(admin, "owner")
    response = admin.get("/api/admin/users")
    check(
        response.status_code == 200
        and {user["username"] for user in response.json()} == {"owner", "reviewer", "viewer"},
        "admin lists only own workspace users",
    )
with TestClient(app.app) as current, TestClient(app.app) as second:
    fixture.login(current, "viewer")
    fixture.login(second, "viewer")
    replacement = fixture.password + "_new"
    check(
        current.post(
            "/api/auth/password",
            json={"current_password": "wrong-password", "new_password": replacement},
        ).status_code
        == 403,
        "password change requires current password",
    )
    check(
        current.post(
            "/api/auth/password",
            json={"current_password": fixture.password, "new_password": replacement},
        ).status_code
        == 200,
        "password change succeeds",
    )
    check(current.get("/api/jobs").status_code == 200, "password change retains current session")
    check(second.get("/api/jobs").status_code == 401, "password change revokes other sessions")
    check(fixture.store.authenticate("viewer", fixture.password) is None, "old password rejected")
with TestClient(app.app) as durable:
    fixture.login(durable, "reviewer")
    state_path = own_job / "state.json"
    original_state = fixture.store.get_document(state_path)
    state_path.write_text(json.dumps({**original_state, "status": "tampered"}), encoding="utf-8")
    check(
        durable.get(f"/api/jobs/{own_job.name}").json()["status"] == "error",
        "SQLite state ignores tampered mirror",
    )
    state_path.unlink()
    check(
        durable.get(f"/api/jobs/{own_job.name}").status_code == 200,
        "SQLite state survives removed mirror",
    )
    check(
        any(job["id"] == own_job.name for job in durable.get("/api/jobs").json()),
        "job list survives removed state mirror",
    )
    state_path.write_text(json.dumps(original_state), encoding="utf-8")
    summary = {
        "occupancy": [],
        "frames": 1,
        "fps": 1,
        "duration": 1,
        "source": "SQL authority fixture",
    }
    fixture.store.put_document(own_job / "summary.json", summary)
    (own_job / "summary.json").write_text(json.dumps({"source": "tampered file"}), encoding="utf-8")
    response = durable.get(f"/api/jobs/{own_job.name}/media/summary.json")
    check(
        response.status_code == 200 and response.json()["source"] == summary["source"],
        "summary media uses SQLite authority",
    )
    fixture.store.put_document(state_path, {**original_state, "status": "done"})
    annotations = {"revision": 3, "frames": []}
    fixture.store.put_document(own_job / "annotations.json", annotations)
    (own_job / "annotations.json").write_text("{}", encoding="utf-8")
    (own_job / "annotations.json").unlink()
    check(
        durable.get(f"/api/jobs/{own_job.name}/annotations").json() == annotations,
        "SQLite annotations survive removed mirror",
    )
    missing = other_job / "overlays.json"
    missing.write_text(json.dumps({"revision": 7, "frames": []}), encoding="utf-8")
    access.migrate_existing(fixture.trainings)
    check(
        fixture.store.get_document(missing)["revision"] == 7,
        "migration retries missing document for existing resource",
    )
    check(
        fixture.store.require_resource("job", other_job.name, fixture.other["workspace_id"])
        is not None,
        "migration preserves existing workspace ownership",
    )
    missing.write_text(json.dumps({"revision": 999}), encoding="utf-8")
    access.migrate_existing(fixture.trainings)
    check(
        fixture.store.get_document(missing)["revision"] == 7
        and fixture.store.get_document(state_path)["status"] == "done",
        "repeat migration never overwrites SQLite documents",
    )
    response = durable.get("/api/jobs", headers={"Host": "evil.invalid"})
    check(
        response.status_code == 400
        and response.headers.get("X-Content-Type-Options") == "nosniff"
        and response.headers.get("Cache-Control") == "no-store",
        "untrusted Host rejection retains security headers",
    )

old_public_url = os.environ.get("INSIGHT_PUBLIC_URL")
try:
    os.environ["INSIGHT_PUBLIC_URL"] = "http://studio.example.invalid"
    try:
        access.public_url()
    except RuntimeError:
        check(True, "non loopback deployment requires HTTPS")
    else:
        check(False, "non loopback deployment requires HTTPS")
    os.environ["INSIGHT_PUBLIC_URL"] = "https://studio.example.invalid"
    check(
        access.public_url() == "https://studio.example.invalid", "HTTPS deployment origin accepted"
    )
finally:
    if old_public_url is None:
        os.environ.pop("INSIGHT_PUBLIC_URL", None)
    else:
        os.environ["INSIGHT_PUBLIC_URL"] = old_public_url
with TestClient(app.app) as limited:
    responses = [
        limited.post(
            "/api/auth/login",
            json={"username": "missing", "password": "invalid-password"},
            headers={"Origin": "http://testserver"},
        )
        for _ in range(15)
    ]
    blocked = next((response for response in responses if response.status_code == 429), None)
    check(
        blocked is not None and int(blocked.headers["Retry-After"]) > 0,
        "login rate limit includes Retry-After",
    )
    check(
        blocked.headers.get("X-Content-Type-Options") == "nosniff"
        and blocked.headers.get("Cache-Control") == "no-store",
        "rate limit has security headers",
    )

check(fixture.store.verify_audit(), "audit chain valid after accepted and rejected requests")
with fixture.store.connection() as database:
    rows = database.execute("SELECT password FROM users").fetchall()
    check(all(row[0] != fixture.password for row in rows), "passwords stored as hashes")

with TestClient(app.app, client=("203.0.113.10", 50000)) as remote:
    response = remote.get("/")
    check(
        response.status_code == 403 and response.headers.get("X-Content-Type-Options") == "nosniff",
        "plain HTTP refuses nonloopback clients even with a forged allowed Host",
    )

print(json.dumps({"passed": len(checks), "artifact_root": str(root)}))
