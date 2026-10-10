"""Run in studio environment; verified facts never invoke Qwen or invent identity."""

from __future__ import annotations

import sys
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from access_fixture import AccessFixture
from fastapi.testclient import TestClient

import access
import app
import runtime
from fact_query import answer_ledger


def row(event, category, symbol, subject=None, job=None, track=None, status="verified"):
    return {
        "id": event,
        "category": category,
        "symbol": symbol,
        "status": status,
        "job_id": job,
        "track_id": track,
        "occurred_at": "2026-10-10T01:00:00+00:00",
        "verified_at": "2026-10-10T02:00:00+00:00",
        "verifier_id": "admin",
        "payload": {"subject_id": subject, "source_kind": "manual", "source_id": event},
    }


rows = [
    row("a", "attendance", "ATTENDANCE_ARRIVED", "staff1", "video", 1),
    row("b", "attendance", "ATTENDANCE_ARRIVED", "staff2", "video", 1),
    row("c", "attendance", "ATTENDANCE_ARRIVED", "staff3"),
    row("d", "attendance", "ATTENDANCE_DEPARTED", "staff3", status="retracted"),
    row("e", "observation", "PERSON_ENTER_ZONE", job="video", track=1),
    row("f", "observation", "HELMET_UNKNOWN", job="video", track=1),
    row("g", "observation", "PERSON_EXIT_ZONE", job="video", track=1, status="stale"),
]
answer = answer_ledger("siapa datang?", rows, "admin")
assert (
    "staff3" in answer["answer"]
    and "staff1" not in answer["answer"]
    and "staff2" not in answer["answer"]
)
assert answer["ledger_proof"][0]["event_id"] == "c"
assert "staff" not in answer_ledger("siapa datang?", rows, "viewer")["answer"]
assert "Ada 3 catatan" in answer_ledger("berapa catatan absensi?", rows, "admin")["answer"]
assert "Ada 2 catatan" in answer_ledger("berapa catatan absensi?", rows, "admin", "video")["answer"]
assert (
    "Ada 1 kejadian" in answer_ledger("berapa crossing terverifikasi?", rows, "reviewer")["answer"]
)
assert "unknown" in answer_ledger("helm terverifikasi?", rows, "reviewer")["answer"]
assert "Filter waktu" in answer_ledger("siapa hadir pukul 08:00?", rows, "admin")["answer"]
for temporal in ("hari ini", "tadi", "pagi", "minggu lalu"):
    assert "Filter waktu" in answer_ledger("siapa hadir " + temporal, rows, "admin")["answer"]
assert answer_ledger("berapa mobil di video?", rows, "admin") is None
assert "belum diketahui" in answer_ledger("berapa orang unik di ledger?", rows, "admin")["answer"]
for question in (
    "berapa catatan absensi untuk staff1?",
    "siapa datang selain staff3?",
    "siapa yang tidak hadir?",
    "berapa orang tidak hadir?",
    "siapa datang dan pulang?",
    "berapa orang unik dalam absensi?",
    "berapa crossing terverifikasi keluar?",
    "berapa crossing terverifikasi untuk track 1?",
    "berapa crossing terverifikasi mobil?",
    "berapa track terverifikasi dan lintasan terverifikasi?",
):
    rejected = answer_ledger(question, rows, "admin")
    assert rejected is not None and "belum didukung" in rejected["answer"], question
    assert rejected["ledger_proof"] == [] and "Ada " not in rejected["answer"], question
    assert "staff" not in rejected["answer"], question
assert "staff3" in answer_ledger("  SIAPA   DATANG?!  ", rows, "admin")["answer"]
assert "Ada 3 catatan" in answer_ledger("jumlah absensi di ledger", rows, "admin")["answer"]
fixture = AccessFixture(runtime.ROOT / ".tmp" / ("fact_check_" + uuid4().hex))
runtime.JOBS = fixture.jobs
access._stores[access.database_path()] = fixture.store
app.training_root = fixture.trainings
with TestClient(app.app) as client:
    fixture.login(client, "owner")
    created = client.post(
        "/api/ledger/attendance",
        json={
            "subject_id": "staff42",
            "source_kind": "manual",
            "source_id": "verified42",
            "occurred_at": "2026-10-10T08:00:00+07:00",
            "action": "arrived",
        },
    )
    assert created.status_code == 201, created.text
    response = client.post("/api/chat", json={"message": "siapa datang?"})
    assert response.status_code == 200, response.text
    assert response.json()["mode"] == "facts" and "staff42" in response.json()["answer"]
    assert response.json()["ledger_proof"][0]["source"]["source_id"] == "verified42"
    unsupported = client.post(
        "/api/chat", json={"message": "berapa catatan absensi untuk staff42?"}
    )
    assert unsupported.status_code == 200, unsupported.text
    assert "belum didukung" in unsupported.json()["answer"]
    assert unsupported.json()["ledger_proof"] == []
    fixture.login(client, "other")
    assert (
        "staff42"
        not in client.post("/api/chat", json={"message": "siapa datang?"}).json()["answer"]
    )
    fixture.login(client, "viewer")
    assert (
        "staff42"
        not in client.post("/api/chat", json={"message": "siapa datang?"}).json()["answer"]
    )
    assert "transformers" not in sys.modules
print(
    "PASS: deterministic counts/identity, ambiguity, recording scope, unknown/time/stale/retraction, HTTP role/workspace and no Qwen"
)
