"""Run in studio environment; isolated real HTTP/math tests without detector or LLM loads."""

from __future__ import annotations

import csv
import json
import sys
from io import StringIO
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from access_fixture import AccessFixture
from extensions.experiments import registry, research
from extensions.src.cli import score_sentence
from fastapi.testclient import TestClient

import academic
import access
import app
import runtime

fixture = AccessFixture(runtime.ROOT / ".tmp" / ("academic_check_" + uuid4().hex))
runtime.JOBS = fixture.jobs
app.training_root = fixture.trainings
access._stores[access.database_path()] = fixture.store
registry.RUNS = fixture.root / "runs"
academic.PUBLISHED = fixture.root / "published.json"

with TestClient(app.app) as client:
    assert client.get("/api/ngram/catalog").status_code == 401
    assert client.get("/api/ngram/runs/shared/csv").status_code == 401
    fixture.login(client, "viewer")
    assert client.get("/api/ngram/catalog").json()["models"] == []
    assert client.get("/api/ngram/catalog").json()["validation"]["source"].startswith("historical")
    body = {
        "model_id": "demo",
        "method": "add_k",
        "n": 2,
        "text": "the cat sits",
        "seed": 42,
        "max_length": 12,
    }
    response = client.post("/api/ngram/explore", json=body)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["score"] == score_sentence(academic.demo_model(2, "add_k"), body["text"])
    assert data["top_k"] and data["generated"]
    assert "illustrative" in data["model"]["parameters"]["selection"]
    assert data["generated"] == client.post("/api/ngram/explore", json=body).json()["generated"]
    assert data["score"]["predicted_tokens"] == 4
    assert "C=(" not in data["formula_details"][0]
    assert any("raw C=" in row for row in data["formula_details"])
    assert "torch" not in sys.modules and "transformers" not in sys.modules
    assert client.post("/api/ngram/explore", json={**body, "n": 5}).status_code == 422
    assert (
        client.post("/api/ngram/explore", json={**body, "model_id": "../../secret"}).status_code
        == 422
    )
    assert client.post("/api/ngram/explore", json={**body, "text": "123!!!"}).status_code == 422
    assert client.post("/api/ngram/explore", json={**body, "prefix": "x" * 257}).status_code == 422
    assert client.post("/api/ngram/explore", json={**body, "unexpected": True}).status_code == 422
    assert (
        client.post("/api/ngram/explore", json={**body, "method": "stupid_backoff"}).json()[
            "score"
        ]["perplexity"]
        is None
    )
    assert (
        client.post("/api/ngram/explore", json=body, headers={"X-CSRF-Token": "wrong"}).status_code
        == 403
    )
    docs = [
        {
            "id": f"doc{i}",
            "source": "CC0-demo",
            "license": "CC0",
            "sentences": [["word" + chr(97 + i), "common", "token"]],
        }
        for i in range(12)
    ]
    research.run_research("private", docs, orders=(1,), methods=("witten_bell",), resamples=100)
    assert client.get("/api/ngram/runs").json()["runs"] == []
    directory = research.run_research(
        "shared", docs, orders=(1,), methods=("witten_bell",), resamples=100, public_models=True
    )
    assert len(client.get("/api/ngram/catalog").json()["models"]) == 2
    assert len(client.get("/api/ngram/runs").json()["runs"]) == 1
    download = client.get("/api/ngram/runs/shared/csv")
    assert (
        download.status_code == 200
        and 'filename="shared.csv"' in download.headers["content-disposition"]
    )
    exported = list(csv.DictReader(StringIO(download.text)))
    numeric = client.get("/api/ngram/runs").json()["runs"][0]["metrics"]
    for actual, expected in zip(exported, numeric, strict=True):
        assert int(actual["n"]) == expected["n"] and actual["method"] == expected["method"]
        assert float(actual["test_cross_entropy"]) == expected["test_cross_entropy"]
    assert client.get("/api/ngram/runs/private/csv").status_code == 404
    assert client.get("/api/ngram/runs/missing/csv").status_code == 404
    archived = {
        **client.get("/api/ngram/runs").json()["runs"][0],
        "run_id": "archive",
        "status": "published_summary",
    }
    academic.PUBLISHED.write_text(json.dumps({"schema_version": 1, "runs": [archived]}))
    assert client.get("/api/ngram/runs/archive/csv").status_code == 200
    assert all(
        "archive" not in row["id"] for row in client.get("/api/ngram/catalog").json()["models"]
    )
    requested = {**body, "model_id": "run:shared:1:witten_bell", "method": "witten_bell", "n": 1}
    selected = client.post("/api/ngram/explore", json=requested)
    assert selected.status_code == 200
    assert selected.json()["model"]["parameters"]["selection"] == "dev-only"
    assert selected.json()["model"]["parameters"]["tuning_trace"]
    assert len(academic._cache) == 1
    academic._compute.acquire()
    try:
        assert client.post("/api/ngram/explore", json=body).status_code == 429
    finally:
        academic._compute.release()
    assert client.get("/api/ledger/novelty/runs").json()["runs"] == []
    assert client.post("/api/ngram/explore", json={**requested, "n": 2}).status_code == 409
    summary = json.loads((directory / "summary.json").read_text())
    summary[0]["test_cross_entropy"] = 0
    (directory / "summary.json").write_text(json.dumps(summary))
    assert client.get("/api/ngram/runs").json()["errors"]
    assert client.get("/api/ngram/runs/shared/csv").status_code == 409
    assert client.post("/api/ngram/explore", json=requested).status_code == 409
print(
    "PASS: authenticated lab, CSRF, bounded input, exact math, seeded generation, shared run integrity and cache lifecycle"
)
