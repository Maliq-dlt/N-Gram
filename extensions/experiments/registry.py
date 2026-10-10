"""Exclusive experiment runs and verified completion receipts; historical outputs are read-only."""

from __future__ import annotations

import hashlib
import json
import os
import re
from importlib.metadata import version
from pathlib import Path
from uuid import uuid4

from core.src.data import DATA_DIR, ROOT

RUNS = ROOT / "extensions" / "results" / "runs"


def fingerprint(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, allow_nan=False, separators=(",", ":")).encode()
    ).hexdigest()


def run_directory(run_id):
    if not isinstance(run_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", run_id):
        raise ValueError("Run ID must contain 1–80 letters, digits, underscores or hyphens.")
    directory = RUNS / run_id
    if not directory.resolve().is_relative_to(RUNS.resolve()) or directory.is_symlink():
        raise ValueError("Run directory escapes the registry.")
    return directory


def atomic_json(path, data):
    path = Path(path)
    encoded = json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_name(path.name + "." + uuid4().hex + ".pending")
    try:
        with pending.open("x", encoding="utf-8") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        pending.replace(path)
    finally:
        pending.unlink(missing_ok=True)


def create_run(run_id, config):
    directory = run_directory(run_id)
    digest = fingerprint(config)
    directory.parent.mkdir(parents=True, exist_ok=True)
    directory.mkdir()  # exclusive; partial directories are never silently reused
    atomic_json(
        directory / "manifest.json",
        {
            "schema": 1,
            "run_id": run_id,
            "config": config,
            "config_sha256": digest,
            "status": "created",
            "stages": {},
        },
    )
    return directory


def _files(directory):
    if any(path.is_symlink() for path in directory.rglob("*")):
        raise ValueError("Run outputs must not contain symlinks.")
    return {
        str(path.relative_to(directory).as_posix()): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(directory.rglob("*"))
        if path.is_file()
        and path.name != "manifest.json"
        and not path.name.endswith(".pending")
        and "derived" not in path.relative_to(directory).parts
    }


def read_run(run_id, require_completed=True):
    directory = run_directory(run_id)
    data = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    if (
        data.get("schema") != 1
        or data.get("run_id") != run_id
        or data.get("config_sha256") != fingerprint(data.get("config"))
    ):
        raise ValueError("Invalid run manifest or configuration fingerprint.")
    if require_completed:
        if data.get("status") != "completed" or data.get("files") != _files(directory):
            raise ValueError("Run is incomplete or output fingerprints differ.")
    return data


def start_stage(run_id, stage, config):
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,40}", stage):
        raise ValueError("Invalid stage name.")
    directory = run_directory(run_id)
    manifest = read_run(run_id, require_completed=False)
    if manifest["config_sha256"] != fingerprint(config):
        raise ValueError("Run configuration differs; create a new run ID.")
    if stage in manifest["stages"] or manifest["status"] not in {"created", "completed"}:
        raise ValueError("Stage already attempted or run interrupted; create a new run ID.")
    if manifest["status"] == "completed":
        read_run(run_id)
    with (directory / ("stage_" + stage + ".claim")).open("x", encoding="utf-8") as claim:
        claim.write(manifest["config_sha256"])
    manifest["baseline_files"] = _files(directory)
    manifest["status"] = "running"
    manifest["stages"][stage] = "running"
    atomic_json(directory / "manifest.json", manifest)
    return directory


def complete_stage(run_id, stage):
    manifest = read_run(run_id, require_completed=False)
    if manifest["status"] != "running" or manifest["stages"].get(stage) != "running":
        raise ValueError("Stage was not started.")
    files = _files(run_directory(run_id))
    if any(files.get(name) != expected for name, expected in manifest["baseline_files"].items()):
        raise ValueError("Previously completed outputs changed during this stage.")
    manifest["stages"][stage] = "completed"
    manifest["files"] = files
    manifest["status"] = "completed"
    atomic_json(run_directory(run_id) / "manifest.json", manifest)
    return manifest


def selected_run(run_id):
    config = read_run(run_id)["config"]
    for name, expected in config.get("code_sha256", {}).items():
        path = ROOT / name
        if (
            not path.resolve().is_relative_to(ROOT.resolve())
            or hashlib.sha256(path.read_bytes()).hexdigest() != expected
        ):
            raise ValueError("Code fingerprint differs from completed run.")
    for name, expected in config.get("versions", {}).items():
        if version(name) != expected:
            raise ValueError("Dependency fingerprint differs from completed run.")
    if config.get("corpus") == "brown" and "corpus_sha256" in config:
        actual = hashlib.sha256((DATA_DIR / "corpora/brown.zip").read_bytes()).hexdigest()
        if actual != config["corpus_sha256"]:
            raise ValueError("Corpus fingerprint differs from completed run.")
    return run_directory(run_id)


def legacy_analysis_source(run_id):
    directory = selected_run(run_id)
    manifest = read_run(run_id)
    expected = {
        "corpus": "brown",
        "seeds": [42, 43, 44],
        "thresholds": [2, 3],
        "orders": [1, 2, 3, 4],
        "train_ratio": 0.8,
        "dev_ratio": 0.1,
        "test_ratio": 0.1,
    }
    if manifest["stages"].get("22") != "completed" or any(
        manifest["config"].get(key) != value for key, value in expected.items()
    ):
        raise ValueError("Analysis requires completed stage 22 with the original Brown protocol.")
    return directory


def derived_directory(run_id, name):
    directory = selected_run(run_id)
    if not re.fullmatch(r"[a-z_]+", name):
        raise ValueError("Invalid analysis name.")
    target = directory / "derived" / name
    target.mkdir(parents=True)  # exclusive, preserve prior derived results
    source = read_run(run_id)
    atomic_json(
        target / "manifest.json",
        {
            "status": "running",
            "source_run": run_id,
            "source_config_sha256": source["config_sha256"],
            "source_files": source["files"],
        },
    )
    return target


def complete_derived(directory):
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    source = read_run(manifest["source_run"])
    if (
        source["config_sha256"] != manifest["source_config_sha256"]
        or source["files"] != manifest["source_files"]
    ):
        raise ValueError("Source run changed during analysis.")
    manifest["status"] = "completed"
    manifest["files"] = _files(directory)
    atomic_json(directory / "manifest.json", manifest)
