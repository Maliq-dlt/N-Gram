"""Real SQLite security fixtures; all artifacts stay inside the repository."""

from __future__ import annotations

import json
import secrets
from pathlib import Path
from uuid import uuid4

from storage import Store


class AccessFixture:
    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.store = Store(root / "access.sqlite3")
        self.password = secrets.token_urlsafe(24)
        self.owner = self.store.bootstrap("owner", self.password, "Workspace A")
        self.reviewer = self.store.create_user(
            "reviewer", self.password, "reviewer", self.owner["workspace_id"]
        )
        self.viewer = self.store.create_user(
            "viewer", self.password, "viewer", self.owner["workspace_id"]
        )
        workspace = self.store.create_workspace("Workspace B")
        self.other = self.store.create_user("other", self.password, "admin", workspace)
        self.jobs = root / "jobs"
        self.trainings = root / "trainings"
        self.jobs.mkdir()
        self.trainings.mkdir()

    def resource(self, kind: str, owner: dict) -> Path:
        folder = (self.jobs if kind == "job" else self.trainings) / str(uuid4())
        folder.mkdir()
        data = {
            "id": folder.name,
            "status": "error",
            "created_at": "2026-10-09T00:00:00+00:00",
            "filename": "fixture.bin",
            "message": "Security fixture: no inference requested",
        }
        (folder / "state.json").write_text(json.dumps(data), encoding="utf-8")
        self.store.put_document(folder / "state.json", data)
        self.store.register_resource(kind, folder.name, owner["workspace_id"], folder)
        if kind == "job":
            (folder / "original.mp4").write_bytes(b"security fixture - not a video")
        return folder

    def login(self, client, username: str):
        response = client.post(
            "/api/auth/login",
            json={"username": username, "password": self.password},
            headers={"Origin": "http://testserver"},
        )
        assert response.status_code == 200, response.text
        session = response.json()
        assert session["user"]["username"] == username
        assert session["csrf_token"]
        client.headers.update(
            {"X-CSRF-Token": session["csrf_token"], "Origin": "http://testserver"}
        )
        return session


def authorize(client):
    """Log legacy TestClient checks into their already-isolated real workspace database."""
    import access
    import app

    password = secrets.token_urlsafe(24)
    username = "test_" + uuid4().hex[:16]
    database = access.store()
    with database.connection() as db:
        initialized = db.execute("SELECT 1 FROM users LIMIT 1").fetchone() is not None
    if initialized:
        database.create_user(username, password, "admin", database.workspace("Local"))
    else:
        database.bootstrap(username, password, "Local")
    access.migrate_existing(app.training_root)
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
        headers={"Origin": "http://testserver"},
    )
    assert response.status_code == 200, response.text
    client.headers.update(
        {"Origin": "http://testserver", "X-CSRF-Token": response.json()["csrf_token"]}
    )
    access.principal.set(database.session(client.cookies.get(access.COOKIE)))
    return response.json()
