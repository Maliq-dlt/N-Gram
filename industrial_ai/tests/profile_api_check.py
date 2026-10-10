"""Run .venv/Scripts/python tests/profile_api_check.py; private profile persistence check."""

import io
import secrets
import sys
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image

import access
import runtime
from storage import Store

root = runtime.ROOT / ".tmp" / ("profile_api_" + uuid4().hex)
root.mkdir(parents=True)
runtime.JOBS = root / "jobs"
database = Store(access.database_path())
access._stores[access.database_path()] = database
password = secrets.token_urlsafe(24)
owner = database.bootstrap("owner", password)
database.create_user("viewer", password, "viewer", owner["workspace_id"])
app = FastAPI()
access.install(app, 250 * 1024 * 1024)

with TestClient(app) as client:
    assert client.get("/api/auth/avatar").status_code == 401

    def login(name):
        response = client.post(
            "/api/auth/login",
            json={"username": name, "password": password},
            headers={"Origin": "http://testserver"},
        )
        assert response.status_code == 200
        client.headers.update(
            {"Origin": "http://testserver", "X-CSRF-Token": response.json()["csrf_token"]}
        )
        return response.json()

    initial = login("viewer")
    assert initial["user"]["display_name"] == "viewer"
    assert initial["user"]["avatar_url"] is None
    assert (
        client.patch(
            "/api/auth/profile", json={"display_name": "Test"}, headers={"X-CSRF-Token": "invalid"}
        ).status_code
        == 403
    )
    for name in (" ", "x\n", "a" * 81, "a\x7fb"):
        assert client.patch("/api/auth/profile", json={"display_name": name}).status_code == 422
    saved = client.patch("/api/auth/profile", json={"display_name": "  Maliq  "})
    assert saved.status_code == 200 and saved.json()["user"]["display_name"] == "Maliq"
    image = Image.new("RGB", (640, 320), (22, 100, 180))
    encoded = io.BytesIO()
    image.save(encoded, "JPEG", comment=b"private metadata")
    uploaded = client.put(
        "/api/auth/avatar", files={"file": ("../photo.jpg", encoded.getvalue(), "image/jpeg")}
    )
    assert uploaded.status_code == 200, uploaded.text
    assert uploaded.json()["user"]["avatar_url"].startswith("/api/auth/avatar?v=")
    response = client.get(uploaded.json()["user"]["avatar_url"])
    assert response.status_code == 200 and response.headers["cache-control"] == "no-store"
    with Image.open(io.BytesIO(response.content)) as normalized:
        assert normalized.format == "PNG" and normalized.size == (512, 256)
        assert not normalized.info
    assert (
        client.put(
            "/api/auth/avatar", files={"file": ("fake.png", b"<svg/>", "image/png")}
        ).status_code
        == 422
    )
    assert (
        client.put(
            "/api/auth/avatar",
            files={"file": ("huge.png", b"x" * (access.MAX_AVATAR + 1), "image/png")},
        ).status_code
        == 413
    )
    oversized = io.BytesIO()
    Image.new("RGB", (2100, 2100)).save(oversized, "PNG")
    assert (
        client.put(
            "/api/auth/avatar", files={"file": ("pixels.png", oversized.getvalue(), "image/png")}
        ).status_code
        == 422
    )
    gif = io.BytesIO()
    image.save(gif, "GIF")
    assert (
        client.put(
            "/api/auth/avatar", files={"file": ("photo.gif", gif.getvalue(), "image/gif")}
        ).status_code
        == 422
    )
    persisted = Store(database.path).profile(saved.json()["user"]["id"])
    assert persisted["display_name"] == "Maliq" and persisted["avatar"] == response.content
    login("owner")
    assert client.get("/api/auth/avatar").status_code == 404
    assert client.get("/api/auth/session").json()["user"]["display_name"] == "owner"
    login("viewer")
    assert client.get("/api/auth/session").json()["user"]["display_name"] == "Maliq"
    assert client.request("DELETE", "/api/auth/avatar", json={}).status_code == 200
    assert client.get("/api/auth/avatar").status_code == 404
    assert client.get("/api/auth/session").json()["csrf_token"] == client.headers["x-csrf-token"]
assert database.verify_audit()
print("PASS: private viewer profile persistence, CSRF, normalized images, limits and audit")
