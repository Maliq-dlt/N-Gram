"""Single-process SQLite metadata, sessions and authenticated audit trail."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import ClassVar

ROLES = {"admin", "reviewer", "viewer"}


class Store:
    _locks: ClassVar[dict] = {}
    _locks_guard = threading.Lock()

    # ponytail: one serving process; use an external audit anchor and shared worker queue before scaling.
    def __init__(self, path):
        self.path = Path(path).resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.key_path = self.path.with_suffix(self.path.suffix + ".key")
        self.anchor_path = self.path.with_suffix(self.path.suffix + ".anchor")
        with self._locks_guard:
            self.lock = self._locks.setdefault(str(self.path), threading.RLock())
        self.init()

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA busy_timeout=10000")
        try:
            yield db
        finally:
            db.close()

    connect = connection

    def init(self):
        with self.lock, self.connection() as db:
            version = db.execute("PRAGMA user_version").fetchone()[0]
            if version > 1:
                raise RuntimeError("Database schema is newer than this application.")
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS workspaces(id TEXT PRIMARY KEY, name TEXT NOT NULL UNIQUE);
                CREATE TABLE IF NOT EXISTS users(
                    id TEXT PRIMARY KEY, username TEXT NOT NULL UNIQUE,
                    password TEXT NOT NULL, role TEXT NOT NULL CHECK(role IN ('admin','reviewer','viewer')),
                    workspace_id TEXT NOT NULL REFERENCES workspaces(id), active INTEGER NOT NULL DEFAULT 1);
                CREATE TABLE IF NOT EXISTS sessions(
                    digest TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id),
                    csrf TEXT NOT NULL, expires_at INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS resources(
                    kind TEXT NOT NULL CHECK(kind IN ('job','training')), id TEXT NOT NULL,
                    workspace_id TEXT NOT NULL REFERENCES workspaces(id), path TEXT NOT NULL UNIQUE,
                    PRIMARY KEY(kind,id));
                CREATE TABLE IF NOT EXISTS documents(
                    path TEXT PRIMARY KEY, data TEXT NOT NULL, revision INTEGER NOT NULL CHECK(revision>0));
                CREATE TABLE IF NOT EXISTS audit_events(
                    id INTEGER PRIMARY KEY, event TEXT NOT NULL, previous TEXT NOT NULL, mac TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS rate_counters(
                    key TEXT PRIMARY KEY, started INTEGER NOT NULL, count INTEGER NOT NULL);
            """)
            if version == 0:
                db.execute("PRAGMA user_version=1")
            if not self.key_path.exists():
                if db.execute("SELECT count(*) FROM audit_events").fetchone()[0]:
                    raise RuntimeError("Audit key missing; restore the original key.")
                with self.key_path.open("xb") as target:
                    target.write(secrets.token_bytes(32))
            self.key = self.key_path.read_bytes()
            if len(self.key) != 32:
                raise RuntimeError("Invalid audit key.")
            if not self.anchor_path.exists():
                if db.execute("SELECT count(*) FROM audit_events").fetchone()[0]:
                    raise RuntimeError("Audit checkpoint missing; restore the checkpoint.")
                self._anchor(0, "")
            if not self.verify_audit():
                raise RuntimeError(
                    "Audit verification failed; preserve data and restore a verified backup."
                )

    def _anchor(self, event_id, mac):
        pending = self.anchor_path.with_suffix(self.anchor_path.suffix + ".pending")
        with pending.open("w", encoding="utf-8") as target:
            json.dump({"id": event_id, "mac": mac}, target, sort_keys=True)
            target.flush()
            os.fsync(target.fileno())
        pending.replace(self.anchor_path)

    def _append(self, db, action, user_id=None, workspace_id=None, resource=None, outcome="ok"):
        previous = db.execute("SELECT id,mac FROM audit_events ORDER BY id DESC LIMIT 1").fetchone()
        event_id, previous_mac = (previous["id"] + 1, previous["mac"]) if previous else (1, "")
        event = json.dumps(
            {
                "id": event_id,
                "at": int(time.time()),
                "action": action,
                "user_id": user_id,
                "workspace_id": workspace_id,
                "resource": resource,
                "outcome": outcome,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        mac = hmac.new(self.key, (previous_mac + "\n" + event).encode(), hashlib.sha256).hexdigest()
        db.execute("INSERT INTO audit_events VALUES(?,?,?,?)", (event_id, event, previous_mac, mac))
        return event_id, mac

    def _write(self, operation, action, **event):
        with self.lock, self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                if not self._verify_tip(db):
                    raise RuntimeError("Audit checkpoint verification failed; writes are disabled.")
                result = operation(db)
                checkpoint = self._append(db, action, **event)
                db.commit()
            except BaseException:
                db.rollback()
                raise
            # Crash between commit and checkpoint fails closed on restart.
            self._anchor(*checkpoint)
            return result

    def _verify_tip(self, db):
        # ponytail: constant-time append guard; full verification catches older corruption at startup/backup.
        row = db.execute("SELECT * FROM audit_events ORDER BY id DESC LIMIT 1").fetchone()
        try:
            anchor = json.loads(self.anchor_path.read_text(encoding="utf-8"))
            if row is None:
                return anchor == {"id": 0, "mac": ""}
            expected = hmac.new(
                self.key, (row["previous"] + "\n" + row["event"]).encode(), hashlib.sha256
            ).hexdigest()
            return (
                anchor.get("id") == row["id"]
                and hmac.compare_digest(anchor.get("mac", ""), row["mac"])
                and hmac.compare_digest(row["mac"], expected)
            )
        except (OSError, ValueError, TypeError, AttributeError):
            return False

    @staticmethod
    def _password(password):
        if not isinstance(password, str) or not 12 <= len(password) <= 256:
            raise ValueError("Password must contain 12 to 256 characters.")
        salt = secrets.token_bytes(16)
        digest = hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1)
        return salt.hex() + ":" + digest.hex()

    @staticmethod
    def _matches(password, encoded):
        if not isinstance(password, str) or len(password) > 256:
            return False
        salt, digest = encoded.split(":")
        actual = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1)
        return hmac.compare_digest(actual.hex(), digest)

    @staticmethod
    def _username(username):
        if (
            not isinstance(username, str)
            or not 1 <= len(username.strip()) <= 80
            or any(ord(c) < 32 for c in username)
        ):
            raise ValueError("Invalid username.")
        return username.strip().casefold()

    @staticmethod
    def _public(row):
        return {key: row[key] for key in ("id", "username", "role", "workspace_id")}

    def bootstrap(self, username, password, workspace="Local"):
        username, encoded = self._username(username), self._password(password)
        if not isinstance(workspace, str) or not 1 <= len(workspace.strip()) <= 80:
            raise ValueError("Invalid workspace name.")
        user_id, workspace_id = secrets.token_hex(16), secrets.token_hex(16)

        def operation(db):
            if db.execute("SELECT 1 FROM users LIMIT 1").fetchone():
                raise ValueError("Administrator already initialized.")
            existing_workspace = db.execute(
                "SELECT id FROM workspaces WHERE name=?", (workspace.strip(),)
            ).fetchone()
            actual_workspace = existing_workspace[0] if existing_workspace else workspace_id
            if existing_workspace is None:
                db.execute(
                    "INSERT INTO workspaces VALUES(?,?)", (actual_workspace, workspace.strip())
                )
            db.execute(
                "INSERT INTO users(id,username,password,role,workspace_id) VALUES(?,?,?,?,?)",
                (user_id, username, encoded, "admin", actual_workspace),
            )
            return {
                "id": user_id,
                "username": username,
                "role": "admin",
                "workspace_id": actual_workspace,
            }

        return self._write(operation, "bootstrap", user_id=user_id, workspace_id=workspace_id)

    def create_user(self, username, password, role, workspace_id):
        if role not in ROLES:
            raise ValueError("Invalid role.")
        username, encoded, user_id = (
            self._username(username),
            self._password(password),
            secrets.token_hex(16),
        )

        def operation(db):
            if db.execute("SELECT 1 FROM users WHERE username=?", (username,)).fetchone():
                raise ValueError("Username already exists.")
            db.execute(
                "INSERT INTO users(id,username,password,role,workspace_id) VALUES(?,?,?,?,?)",
                (user_id, username, encoded, role, workspace_id),
            )
            return {"id": user_id, "username": username, "role": role, "workspace_id": workspace_id}

        return self._write(operation, "user.create", user_id=user_id, workspace_id=workspace_id)

    def create_workspace(self, name):
        if not isinstance(name, str) or not 1 <= len(name.strip()) <= 80:
            raise ValueError("Invalid workspace name.")
        workspace_id = secrets.token_hex(16)

        def operation(db):
            db.execute("INSERT INTO workspaces VALUES(?,?)", (workspace_id, name.strip()))
            return workspace_id

        return self._write(operation, "workspace.create", workspace_id=workspace_id)

    def authenticate(self, username, password, seconds=28800):
        try:
            username = self._username(username)
        except ValueError:
            self.audit("login", outcome="denied")
            return None
        if not 60 <= seconds <= 86400:
            raise ValueError("Invalid session lifetime.")
        with self.connection() as db:
            row = db.execute(
                "SELECT * FROM users WHERE username=? AND active=1", (username,)
            ).fetchone()
        # Unknown usernames still pay the password hashing cost.
        encoded = row["password"] if row else "00" * 16 + ":" + "00" * 64
        if not self._matches(password, encoded) or row is None:
            self.audit("login", outcome="denied")
            return None
        token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        digest, expires_at = hashlib.sha256(token.encode()).hexdigest(), int(time.time()) + seconds

        def operation(db):
            current = db.execute(
                "SELECT * FROM users WHERE id=? AND active=1", (row["id"],)
            ).fetchone()
            if current is None or current["password"] != encoded:
                return None
            db.execute("DELETE FROM sessions WHERE expires_at<=?", (int(time.time()),))
            db.execute(
                "INSERT INTO sessions VALUES(?,?,?,?)", (digest, row["id"], csrf, expires_at)
            )
            return {
                "token": token,
                "csrf": csrf,
                "user": {
                    **self._public(current),
                    "tenant_name": db.execute(
                        "SELECT name FROM workspaces WHERE id=?", (current["workspace_id"],)
                    ).fetchone()[0],
                },
                "expires_at": expires_at,
            }

        return self._write(operation, "login", user_id=row["id"], workspace_id=row["workspace_id"])

    def session(self, token):
        if not isinstance(token, str) or len(token) > 256:
            return None
        digest = hashlib.sha256(token.encode()).hexdigest()
        with self.connection() as db:
            row = db.execute(
                "SELECT u.*,s.csrf,s.expires_at,w.name AS workspace_name FROM sessions s JOIN users u ON u.id=s.user_id JOIN workspaces w ON w.id=u.workspace_id "
                "WHERE s.digest=? AND s.expires_at>? AND u.active=1",
                (digest, int(time.time())),
            ).fetchone()
        return (
            {
                **self._public(row),
                "csrf": row["csrf"],
                "expires_at": row["expires_at"],
                "workspace_name": row["workspace_name"],
                "tenant_name": row["workspace_name"],
            }
            if row
            else None
        )

    def revoke(self, token):
        digest = hashlib.sha256(token.encode()).hexdigest()
        self._write(
            lambda db: db.execute("DELETE FROM sessions WHERE digest=?", (digest,)).rowcount,
            "logout",
        )

    def change_password(self, user_id, password, keep_token=None):
        encoded = self._password(password)

        def operation(db):
            if not db.execute(
                "UPDATE users SET password=? WHERE id=?", (encoded, user_id)
            ).rowcount:
                raise ValueError("User not found.")
            digest = hashlib.sha256(keep_token.encode()).hexdigest() if keep_token else ""
            db.execute("DELETE FROM sessions WHERE user_id=? AND digest<>?", (user_id, digest))

        self._write(operation, "password.change", user_id=user_id)

    def workspace(self, workspace="Local"):
        with self.lock, self.connection() as db:
            row = db.execute("SELECT id FROM workspaces WHERE name=?", (workspace,)).fetchone()
            return row[0] if row else self.create_workspace(workspace)

    def get_user(self, user_id):
        with self.connection() as db:
            row = db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        return {**self._public(row), "active": bool(row["active"])} if row else None

    def list_users(self, workspace_id):
        with self.connection() as db:
            return [
                {**self._public(row), "active": bool(row["active"])}
                for row in db.execute(
                    "SELECT * FROM users WHERE workspace_id=? ORDER BY username", (workspace_id,)
                )
            ]

    def verify_password(self, user_id, password):
        with self.connection() as db:
            row = db.execute(
                "SELECT password FROM users WHERE id=? AND active=1", (user_id,)
            ).fetchone()
        return bool(row and self._matches(password, row[0]))

    def revoke_user(self, user_id, keep_token=None):
        digest = hashlib.sha256(keep_token.encode()).hexdigest() if keep_token else ""
        self._write(
            lambda db: (
                db.execute(
                    "DELETE FROM sessions WHERE user_id=? AND digest<>?", (user_id, digest)
                ).rowcount
            ),
            "sessions.revoke",
            user_id=user_id,
        )

    def register_resource(self, kind, resource_id, workspace_id, path):
        path = str(Path(path).resolve())

        def operation(db):
            existing = db.execute(
                "SELECT * FROM resources WHERE kind=? AND id=?", (kind, resource_id)
            ).fetchone()
            if existing:
                if existing["workspace_id"] != workspace_id or existing["path"] != path:
                    raise ValueError("Resource ownership cannot be reassigned.")
                return dict(existing)
            db.execute(
                "INSERT INTO resources VALUES(?,?,?,?)", (kind, resource_id, workspace_id, path)
            )
            return {"kind": kind, "id": resource_id, "workspace_id": workspace_id, "path": path}

        return self._write(
            operation, "resource.register", workspace_id=workspace_id, resource=resource_id
        )

    def require_resource(self, kind, resource_id, workspace_id):
        with self.connection() as db:
            row = db.execute(
                "SELECT * FROM resources WHERE kind=? AND id=? AND workspace_id=?",
                (kind, resource_id, workspace_id),
            ).fetchone()
        return dict(row) if row else None

    def list_resources(self, kind, workspace_id):
        with self.connection() as db:
            return [
                dict(row)
                for row in db.execute(
                    "SELECT * FROM resources WHERE kind=? AND workspace_id=? ORDER BY id",
                    (kind, workspace_id),
                )
            ]

    def get_document(self, path, default=None):
        with self.connection() as db:
            row = db.execute(
                "SELECT data FROM documents WHERE path=?", (str(Path(path).resolve()),)
            ).fetchone()
        return json.loads(row["data"]) if row else default

    def put_document(self, path, data, expected_revision=None):
        path, encoded = (
            str(Path(path).resolve()),
            json.dumps(data, ensure_ascii=False, allow_nan=False),
        )

        def operation(db):
            row = db.execute("SELECT revision FROM documents WHERE path=?", (path,)).fetchone()
            revision = row[0] if row else 0
            if expected_revision is not None and revision != expected_revision:
                raise ValueError("Document revision conflict.")
            db.execute(
                "INSERT INTO documents VALUES(?,?,?) ON CONFLICT(path) DO UPDATE SET data=excluded.data,revision=excluded.revision",
                (path, encoded, revision + 1),
            )
            return revision + 1

        return self._write(operation, "document.write", resource=path)

    def rate_limit(self, key, limit, seconds):
        if not isinstance(key, str) or len(key) > 256 or limit < 1 or seconds < 1:
            raise ValueError("Invalid rate limit.")
        now = int(time.time())
        with self.lock, self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM rate_counters WHERE key=?", (key,)).fetchone()
            if row and now - row["started"] < seconds:
                if row["count"] >= limit:
                    db.rollback()
                    return False
                db.execute("UPDATE rate_counters SET count=count+1 WHERE key=?", (key,))
            else:
                db.execute(
                    "INSERT INTO rate_counters VALUES(?,?,1) ON CONFLICT(key) DO UPDATE SET started=excluded.started,count=1",
                    (key, now),
                )
            db.commit()
            return True

    def audit(self, action, user_id=None, workspace_id=None, resource=None, outcome="ok"):
        return self._write(
            lambda db: None,
            action,
            user_id=user_id,
            workspace_id=workspace_id,
            resource=resource,
            outcome=outcome,
        )

    def verify_audit(self):
        with self.lock, self.connection() as db:
            previous, last_id = "", 0
            for row in db.execute("SELECT * FROM audit_events ORDER BY id"):
                expected = hmac.new(
                    self.key, (previous + "\n" + row["event"]).encode(), hashlib.sha256
                ).hexdigest()
                if (
                    row["id"] != last_id + 1
                    or row["previous"] != previous
                    or not hmac.compare_digest(row["mac"], expected)
                ):
                    return False
                previous, last_id = row["mac"], row["id"]
            try:
                anchor = json.loads(self.anchor_path.read_text(encoding="utf-8"))
                return anchor == {"id": last_id, "mac": previous}
            except (OSError, ValueError):
                return False

    def backup(self, target):
        target = Path(target).resolve()
        if target == self.path or target.exists():
            raise ValueError("Backup must use a new database path.")
        target.parent.mkdir(parents=True, exist_ok=True)
        with self.lock, self.connection() as source:
            if not self.verify_audit():
                raise RuntimeError("Cannot back up an invalid audit trail.")
            destination = sqlite3.connect(target)
            try:
                source.backup(destination)
            finally:
                destination.close()
            target.with_suffix(target.suffix + ".key").write_bytes(self.key)
            target.with_suffix(target.suffix + ".anchor").write_bytes(self.anchor_path.read_bytes())
        return target
