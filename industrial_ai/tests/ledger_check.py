"""Run .venv/Scripts/python tests/ledger_check.py; no models or biometric data."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent))
import runtime  # isort: skip

from access_fixture import AccessFixture
from extensions.src.event_sequences import event_sequences
from fastapi import FastAPI
from fastapi.testclient import TestClient

import access
import event_ledger


def main():
    root = ROOT / ".tmp" / ("ledger-check-" + uuid4().hex)
    fixture = AccessFixture(root)
    own = fixture.resource("job", fixture.owner)
    foreign = fixture.resource("job", fixture.other)
    state = fixture.store.get_document(own / "state.json")
    fixture.store.put_document(own / "state.json", {**state, "status": "done"})
    summary = {
        "duration": 120,
        "line": 0.5,
        "models": {"tracking": "test controlled evidence"},
        "tracks": [
            {"id": 1, "kind": "person", "evidence": "evidence_1.jpg"},
            {"id": 2, "kind": "person"},
        ],
        "crossings": [
            {"track_id": 1, "kind": "person", "direction": "down", "seconds": 1},
            {"track_id": 2, "kind": "person", "direction": "down", "seconds": 2},
            {"track_id": 1, "kind": "person", "direction": "up", "seconds": 3},
            {"track_id": 1, "kind": "person", "direction": "down", "seconds": 100},
        ],
    }
    (own / "evidence_1.jpg").write_bytes(b"controlled evidence bytes")
    fixture.store.put_document(own / "summary.json", summary)
    api = FastAPI()
    access.install(api, 250 * 1024 * 1024)
    event_ledger.install(api)
    payload = {"recorded_at": "2026-10-10T08:00:00+07:00", "crossing_indices": [0, 1, 2, 3]}
    with (
        patch.object(access, "store", return_value=fixture.store),
        patch.object(runtime, "JOBS", fixture.jobs),
        TestClient(api) as anonymous,
        TestClient(api) as reviewer,
        TestClient(api) as viewer,
        TestClient(api) as owner,
        TestClient(api) as other,
    ):
        assert anonymous.get("/api/ledger/facts").status_code == 401
        fixture.login(reviewer, "reviewer")
        fixture.login(viewer, "viewer")
        fixture.login(owner, "owner")
        fixture.login(other, "other")
        endpoint = f"/api/ledger/jobs/{own.name}/import"
        assert viewer.post(endpoint, json=payload).status_code == 403
        assert (
            reviewer.post(f"/api/ledger/jobs/{foreign.name}/import", json=payload).status_code
            == 404
        )
        assert (
            reviewer.post(
                endpoint, json={**payload, "recorded_at": "2026-10-10T08:00:00"}
            ).status_code
            == 422
        )
        assert (
            reviewer.post(endpoint, json={**payload, "crossing_indices": [-1]}).status_code == 422
        )
        first = reviewer.post(endpoint, json=payload)
        assert first.status_code == 200, first.text
        events = reviewer.get("/api/ledger/events").json()["events"]
        assert len(events) == 8 and all(row["status"] == "verified" for row in events)
        assert min(row["occurred_at"] for row in events) == "2026-10-10T01:00:01+00:00"
        again = reviewer.post(endpoint, json=payload)
        assert (
            again.status_code == 200
            and len(reviewer.get("/api/ledger/events").json()["events"]) == 8
        )
        assert (
            reviewer.post(
                endpoint, json={**payload, "recorded_at": "2026-10-10T09:00:00+07:00"}
            ).status_code
            == 409
        )
        sequences = event_sequences(list(reversed(events)), max_gap_seconds=30)
        assert len(sequences) == 3
        assert all(
            len(set(sequence["event_ids"])) == len(sequence["event_ids"]) for sequence in sequences
        )
        assert sequences[0]["symbols"] == [
            "PERSON_ENTER_ZONE",
            "HELMET_UNKNOWN",
            "PERSON_EXIT_ZONE",
            "HELMET_UNKNOWN",
        ]
        fact = viewer.get("/api/ledger/facts").json()
        assert fact["observed_track_count"] == 2 and fact["crossing_event_count"] == 4
        assert fact["unique_person_count"] is None and fact["identity_status"] == "unknown"
        assert fact["unknown_helmet_observation_count"] == 4
        assert not other.get("/api/ledger/events").json()["events"]
        attendance = {
            "subject_id": "worker-1",
            "source_kind": "badge",
            "source_id": "manual-check-1",
            "occurred_at": "2026-10-10T08:00:01+07:00",
            "action": "arrived",
            "job_id": own.name,
            "track_id": 1,
        }
        assert reviewer.post("/api/ledger/attendance", json=attendance).status_code == 403
        attendance_response = owner.post("/api/ledger/attendance", json=attendance)
        assert attendance_response.status_code == 201
        attendance_id = attendance_response.json()["records"][0]["id"]
        assert (
            reviewer.post(
                f"/api/ledger/events/{attendance_id}/retract", json={"reason": "unauthorized"}
            ).status_code
            == 403
        )
        assert owner.post("/api/ledger/attendance", json=attendance).status_code == 201
        for reader in (reviewer, viewer):
            assert all(
                row["category"] == "observation"
                for row in reader.get("/api/ledger/events").json()["events"]
            )
            redacted = reader.get("/api/ledger/facts").json()
            assert redacted["attendance_record_count"] == 1
            assert "subject_id" not in str(redacted["proof"])
        assert all(
            "verifier_id" not in row for row in viewer.get("/api/ledger/events").json()["events"]
        )
        assert all(
            "verifier_id" not in row for row in viewer.get("/api/ledger/facts").json()["proof"]
        )
        assert any(
            row["category"] == "attendance"
            for row in owner.get("/api/ledger/events").json()["events"]
        )
        assert (
            owner.post(
                "/api/ledger/attendance", json={**attendance, "subject_id": "worker-2"}
            ).status_code
            == 409
        )
        assert (
            owner.post(
                "/api/ledger/attendance",
                json={**attendance, "subject_id": "worker-2", "source_id": "manual-check-2"},
            ).status_code
            == 201
        )
        assert (
            owner.get("/api/ledger/facts").json()["ambiguous_track_links"][0]["identity"]
            == "unknown"
        )
        event_id = events[0]["id"]
        assert (
            other.post(
                f"/api/ledger/events/{event_id}/retract", json={"reason": "foreign"}
            ).status_code
            == 404
        )
        assert (
            reviewer.post(
                f"/api/ledger/events/{event_id}/retract", json={"reason": "source withdrawn"}
            ).status_code
            == 200
        )
        assert reviewer.get("/api/ledger/facts").json()["retracted_count"] == 1
        assert reviewer.post(endpoint, json=payload).status_code == 200
        assert reviewer.get("/api/ledger/facts").json()["retracted_count"] == 1, (
            "Duplicate import must not resurrect withdrawn events"
        )
        empty = {**summary, "crossings": []}
        fixture.store.put_document(own / "summary.json", empty)
        assert reviewer.post(endpoint, json=payload).status_code == 422, (
            "Detected frames cannot fabricate crossings"
        )
        fixture.store.put_document(own / "summary.json", summary)
        (own / "evidence_1.jpg").write_bytes(b"altered evidence bytes")
        assert reviewer.get("/api/ledger/facts").json()["stale_count"] == 9
        (own / "evidence_1.jpg").write_bytes(b"controlled evidence bytes")
        assert reviewer.get("/api/ledger/facts").json()["stale_count"] == 0
        (own / "evidence_1.jpg").unlink()
        assert reviewer.get("/api/ledger/facts").json()["stale_count"] == 9
        assert reviewer.post(endpoint, json=payload).status_code == 409
        (own / "evidence_1.jpg").write_bytes(b"controlled evidence bytes")
        fixture.store.put_document(own / "annotations.json", {"revision": 1, "frames": []})
        stale = reviewer.get("/api/ledger/facts").json()
        assert (
            stale["stale_count"] == 9
            and stale["observed_track_count"] == 0
            and stale["attendance_record_count"] == 0
        )
        assert fixture.store.verify_audit()
        # Batch insertion is all-or-nothing, including a conflict after a fresh first row.
        token = access.principal.set(fixture.owner)
        try:
            ledger = event_ledger.Ledger(fixture.store)
            row = {
                "source_key": "rollback-new",
                "source_fingerprint": "manual",
                "occurred_at": "2026-10-10T00:00:00+00:00",
                "symbol": "ATTENDANCE_ARRIVED",
                "payload": {"subject_id": "rollback"},
            }
            conflicting = {**row, "source_key": "badge:manual-check-1"}
            before = len(ledger.rows())
            try:
                ledger.append("attendance", [row, conflicting])
            except ValueError:
                pass
            else:
                raise AssertionError("Conflicting batch should fail")
            assert len(ledger.rows()) == before
        finally:
            access.principal.reset(token)
    print(
        "Ledger checks passed: authorization, provenance, duplicates, rollback, retraction, staleness, timezone, interleaving and unknown identity"
    )


if __name__ == "__main__":
    main()
