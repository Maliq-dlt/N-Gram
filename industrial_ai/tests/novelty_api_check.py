"""Actual offline runner through authenticated HTTP; controlled events, no quality claim."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from access_fixture import AccessFixture
from extensions.experiments import event_novelty, registry
from fastapi import FastAPI
from fastapi.testclient import TestClient

import academic  # Initialize deployment registry before redirecting the test fixture.
import access
import event_ledger
import runtime

fixture = AccessFixture(runtime.ROOT / ".tmp" / ("novelty-api-" + uuid4().hex))
api = FastAPI()
access.install(api, 250 * 1024 * 1024)
event_ledger.install(api)
with (
    patch.object(access, "store", return_value=fixture.store),
    patch.object(runtime, "JOBS", fixture.jobs),
    patch.object(registry, "RUNS", fixture.root / "runs"),
    TestClient(api) as owner,
    TestClient(api) as foreign,
    TestClient(api) as anonymous,
):
    endpoint = "/api/ledger/novelty/runs"
    assert anonymous.get(endpoint).status_code == 401
    fixture.login(owner, "owner")
    fixture.login(foreign, "other")
    assert owner.get(endpoint).json()["runs"] == []
    for index in range(3):
        folder = fixture.resource("job", fixture.owner)
        state = fixture.store.get_document(folder / "state.json")
        fixture.store.put_document(folder / "state.json", {**state, "status": "done"})
        summary = {
            "duration": 10,
            "line": 0.5,
            "models": {"tracking": "controlled test evidence"},
            "tracks": [{"id": 1, "kind": "person"}],
            "crossings": [
                {"track_id": 1, "kind": "person", "direction": "down", "seconds": 1},
                {"track_id": 1, "kind": "person", "direction": "up", "seconds": 2},
            ],
        }
        fixture.store.put_document(folder / "summary.json", summary)
        response = owner.post(
            f"/api/ledger/jobs/{folder.name}/import",
            json={
                "recorded_at": f"2026-10-10T0{index + 1}:00:00+00:00",
                "crossing_indices": [0, 1],
            },
        )
        assert response.status_code == 200, response.text
    exported = owner.get("/api/ledger/events").json()
    directory = event_novelty.run_novelty("own-novelty", exported, fixture.owner["workspace_id"])
    result = owner.get(endpoint).json()
    assert directory.is_relative_to(fixture.root / "runs")
    assert (
        academic.read_json(directory / "summary.json")["selected_model"]
        == result["runs"][0]["summary"]["selected_model"]
    )
    assert len(result["runs"]) == 1 and not result["errors"]
    assert result["runs"][0]["summary"]["stale"] is False
    assert "diagnostics" in result["runs"][0]["summary"]["mode"]
    assert foreign.get(endpoint).json() == {"schema_version": 1, "runs": [], "errors": []}
    event = exported["events"][0]["id"]
    assert (
        owner.post(
            f"/api/ledger/events/{event}/retract", json={"reason": "withdrawn source"}
        ).status_code
        == 200
    )
    assert owner.get(endpoint).json()["runs"][0]["summary"]["stale"] is True
    (directory / "summary.json").write_text("{}")
    assert not owner.get(endpoint).json()["runs"] and owner.get(endpoint).json()["errors"]
    assert not foreign.get(endpoint).json()["errors"]
print(
    "PASS: real offline runner, HTTP auth/workspace isolation, no live claims, stale/retracted source and corrupt artifact"
)
