import json
from pathlib import Path
from unittest.mock import patch

import pytest

from extensions.experiments import registry


@pytest.fixture
def runs(tmp_path, monkeypatch):
    monkeypatch.setattr(registry, "RUNS", tmp_path / "runs")
    return tmp_path / "runs"


def test_fresh_collision_traversal_and_partial(runs):
    for name in ("../outside", "a/b", "a\\b", "", ".", "a" * 81):
        with pytest.raises(ValueError):
            registry.run_directory(name)
    directory = registry.create_run("fresh", {"seed": 42})
    with pytest.raises(FileExistsError):
        registry.create_run("fresh", {"seed": 43})
    registry.start_stage("fresh", "21", {"seed": 42})
    registry.atomic_json(directory / "trial.json", {"loss": 1.2})
    with pytest.raises(ValueError):
        registry.read_run("fresh")
    with pytest.raises(ValueError):
        registry.start_stage("fresh", "21", {"seed": 42})
    assert registry.read_run("fresh", False)["status"] == "running"


def test_completion_mismatch_and_continuation(runs):
    config = {"seed": 42}
    directory = registry.create_run("receipt", config)
    registry.start_stage("receipt", "21", config)
    registry.atomic_json(directory / "split.json", {"train": [0], "dev": [1], "test": [2]})
    registry.atomic_json(directory / "final.json", {"dev_winner": "laplace", "test_loss": 2})
    registry.complete_stage("receipt", "21")
    assert registry.selected_run("receipt") == directory
    with pytest.raises(ValueError):
        registry.start_stage("receipt", "22", {"seed": 43})
    registry.start_stage("receipt", "22", config)
    registry.atomic_json(directory / "final22.json", {"test_loss": 3})
    registry.complete_stage("receipt", "22")
    analysis = registry.derived_directory("receipt", "analysis")
    registry.atomic_json(analysis / "result.json", {"nll": 2})
    assert registry.read_run("receipt")["status"] == "completed"
    with pytest.raises(FileExistsError):
        registry.derived_directory("receipt", "analysis")
    registry.atomic_json(directory / "final22.json", {"test_loss": 0})
    with pytest.raises(ValueError):
        registry.read_run("receipt")


def test_atomic_failure_preserves_prior(runs):
    directory = registry.create_run("atomic", {})
    target = directory / "value.json"
    registry.atomic_json(target, {"before": True})
    with patch.object(Path, "replace", side_effect=OSError("interrupted")):
        with pytest.raises(OSError):
            registry.atomic_json(target, {"after": True})
    assert json.loads(target.read_text()) == {"before": True}
    assert not list(directory.glob("*.pending"))


def test_selected_code_mismatch(runs):
    registry.create_run("code", {"code_sha256": {"extensions/experiments/registry.py": "wrong"}})
    config = registry.read_run("code", False)["config"]
    registry.start_stage("code", "synthetic", config)
    registry.complete_stage("code", "synthetic")
    with pytest.raises(ValueError):
        registry.selected_run("code")


def test_historical_writers_refuse(runs):
    from extensions.experiments.run import OUT, dump, run21

    with pytest.raises(ValueError):
        dump(OUT / "must-not-exist.json", {})
    with pytest.raises(ValueError):
        run21([["tiny"]])


def test_tiny_real_pilot_receipt(runs, monkeypatch):
    import pandas as pd

    from extensions.experiments import run

    config = {"corpus": "synthetic", "seed": 42}
    directory = registry.create_run("tiny", config)
    registry.start_stage("tiny", "21", config)
    monkeypatch.setattr(run, "OUT", directory)
    rows = run.run21([["a", "small", "test"] for _ in range(20)])
    assert len(rows) == len(run.METHODS)
    assert len(pd.read_csv(directory / "phase21.csv")) == len(rows)
    registry.complete_stage("tiny", "21")
    manifest = registry.read_run("tiny")
    assert "phase21.csv" in manifest["files"]
    assert len([name for name in manifest["files"] if name.startswith("tuning/")]) == len(rows)
    with pytest.raises(ValueError):
        registry.start_stage("tiny", "21", config)


def test_interrupted_create_refuses_reuse(runs):
    with patch.object(Path, "replace", side_effect=OSError("interrupted")):
        with pytest.raises(OSError):
            registry.create_run("broken", {})
    with pytest.raises(FileExistsError):
        registry.create_run("broken", {})


def test_analysis_rejects_protocol_mismatch(runs):
    config = {"corpus": "brown", "thresholds": [99]}
    registry.create_run("protocol", config)
    registry.start_stage("protocol", "22", config)
    registry.complete_stage("protocol", "22")
    with pytest.raises(ValueError):
        registry.legacy_analysis_source("protocol")


def test_later_stage_cannot_approve_changed_previous_outputs(runs):
    config = {"seed": 42}
    directory = registry.create_run("immutable", config)
    registry.start_stage("immutable", "21", config)
    registry.atomic_json(directory / "final21.json", {"score": 2})
    registry.complete_stage("immutable", "21")
    registry.start_stage("immutable", "22", config)
    registry.atomic_json(directory / "final21.json", {"score": 0})
    registry.atomic_json(directory / "final22.json", {"score": 3})
    with pytest.raises(ValueError):
        registry.complete_stage("immutable", "22")
    assert registry.read_run("immutable", False)["status"] == "running"
    with pytest.raises(ValueError):
        registry.read_run("immutable")
