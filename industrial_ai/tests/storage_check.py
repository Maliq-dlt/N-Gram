"""Run: python industrial_ai/tests/storage_check.py"""

import json
import sqlite3
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from storage import Store


def rejected(call):
    try:
        call()
    except (ValueError, sqlite3.IntegrityError):
        return
    raise AssertionError("Operation should have been rejected")


def main():
    runtime = ROOT / "tests" / "runtime"
    runtime.mkdir(exist_ok=True)
    base = runtime / ("storage-" + uuid4().hex)
    base.mkdir()
    store = Store(base / "studio.sqlite3")
    admin = store.bootstrap("Admin", "correct horse battery staple")
    workspace = admin["workspace_id"]
    rejected(lambda: store.bootstrap("other", "different-password"))
    rejected(lambda: store.create_user("bad", "valid-password-here", "owner", workspace))
    rejected(lambda: store.create_user("foreign", "valid-password-here", "viewer", "missing"))
    try:
        store.create_user("Admin", "different-password", "viewer", workspace)
    except ValueError:
        pass
    else:
        raise AssertionError("Duplicate username must produce a domain error")
    second = store.create_workspace("Other")
    viewer = store.create_user("Reader", "reader-password-long", "viewer", second)
    assert store.workspace("Other") == second
    assert store.authenticate("Admin", "wrong-password") is None
    assert store.authenticate("   ", "wrong-password") is None
    login = store.authenticate("Admin", "correct horse battery staple")
    assert login and store.session(login["token"])["role"] == "admin"
    assert store.session(login["token"])["tenant_name"] == "Local"
    assert store.verify_password(admin["id"], "correct horse battery staple")
    with store.connection() as db:
        db.execute("UPDATE users SET role='reviewer' WHERE id=?", (admin["id"],))
        db.commit()
    assert store.session(login["token"])["role"] == "reviewer"
    with store.connection() as db:
        db.execute("UPDATE sessions SET expires_at=0")
        db.commit()
    assert store.session(login["token"]) is None
    with store.connection() as db:
        raw = db.execute("SELECT digest FROM sessions").fetchone()[0]
        assert raw != login["token"]
    store.revoke(login["token"])
    assert store.session(login["token"]) is None
    login = store.authenticate("Reader", "reader-password-long")
    store.change_password(viewer["id"], "changed-password-long")
    assert store.session(login["token"]) is None
    assert store.authenticate("Reader", "reader-password-long") is None
    login = store.authenticate("Reader", "changed-password-long")
    store.change_password(viewer["id"], "another-password-long", keep_token=login["token"])
    assert store.session(login["token"])
    store.revoke_user(viewer["id"])
    assert store.session(login["token"]) is None
    assert store.list_users(second)[0]["id"] == viewer["id"]
    store.register_resource("job", "a", workspace, base / "job-a")
    assert store.require_resource("job", "a", second) is None
    assert store.require_resource("job", "a", workspace)["id"] == "a"
    rejected(lambda: store.register_resource("job", "a", second, base / "job-a"))
    rejected(lambda: store.register_resource("job", "b", second, base / "job-a"))
    assert len(store.list_resources("job", workspace)) == 1
    doc = base / "state.json"
    assert store.get_document(doc) is None
    assert store.put_document(doc, {"status": "queued"}, expected_revision=0) == 1
    rejected(lambda: store.put_document(doc, {}, expected_revision=0))
    assert store.get_document(doc) == {"status": "queued"}
    with ThreadPoolExecutor(max_workers=6) as pool:
        writes = list(pool.map(lambda i: store.put_document(doc, {"value": i}), range(12)))
        allowed = list(pool.map(lambda _: store.rate_limit("login", 3, 60), range(12)))
    assert sorted(writes) == list(range(2, 14))
    assert sum(allowed) == 3
    assert store.verify_audit()
    backup = store.backup(base / "backup.sqlite3")
    restored = Store(backup)
    assert restored.verify_audit() and restored.get_document(doc) == store.get_document(doc)
    assert restored.require_resource("job", "a", workspace)
    with store.connection() as db:
        events = " ".join(row[0] for row in db.execute("SELECT event FROM audit_events"))
        assert login["token"] not in events and login["csrf"] not in events
        assert "another-password-long" not in events
        db.execute(
            "UPDATE audit_events SET event=? WHERE id=(SELECT MAX(id) FROM audit_events)",
            (json.dumps({"changed": True}),),
        )
        db.commit()
    assert not store.verify_audit()
    try:
        store.put_document(doc, {"unsafe": True})
    except RuntimeError:
        pass
    else:
        raise AssertionError("Tampered trail must block writes")
    try:
        Store(store.path)
    except RuntimeError:
        pass
    else:
        raise AssertionError("Tampered trail must fail closed")
    with restored.connection() as db:
        db.execute("DELETE FROM audit_events WHERE id=(SELECT MAX(id) FROM audit_events)")
        db.commit()
    assert not restored.verify_audit(), "Checkpoint must detect suffix deletion"
    try:
        restored.put_document(doc, {})
    except RuntimeError:
        pass
    else:
        raise AssertionError("Truncated tail must block append")
    future_path = base / "future.sqlite3"
    with sqlite3.connect(future_path) as db:
        db.execute("PRAGMA user_version=2")
    try:
        Store(future_path)
    except RuntimeError:
        pass
    else:
        raise AssertionError("Future schema must not be overwritten")
    with sqlite3.connect(future_path) as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 2
    performance = Store(base / "constant.sqlite3")
    performance.audit("first")
    performance.audit("second")
    with patch.object(
        performance, "verify_audit", side_effect=AssertionError("Append must not scan full history")
    ):
        performance.put_document(doc, {"progress": 1})
    with performance.connection() as db:
        db.execute("UPDATE audit_events SET event='changed' WHERE id=1")
        db.commit()
    performance.put_document(doc, {"progress": 2})
    assert not performance.verify_audit(), "Older corruption requires full verification"
    print("Storage checks passed: constraints, sessions, tenancy, concurrency, audit and restore")


if __name__ == "__main__":
    main()
