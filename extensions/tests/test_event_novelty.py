"""Synthetic ledger replay correctness; these fixtures do not establish detection quality."""

import copy
import json
import math
from collections import Counter

import pytest

from core.src.ngram import events
from extensions.experiments import event_novelty as novelty
from extensions.experiments import registry
from extensions.src.event_sequences import SYMBOLS
from extensions.src.models import CountBank, ExtensionLM


@pytest.fixture
def exported():
    rows = []
    for recording in range(12):
        for track in (1, 2):
            symbols = ["PERSON_ENTER_ZONE", "HELMET_UNKNOWN", "PERSON_EXIT_ZONE"]
            if (recording + track) % 3 == 0:
                symbols += ["PERSON_ENTER_ZONE", "HELMET_UNKNOWN"]
            for offset, symbol in enumerate(symbols):
                rows.append(
                    {
                        "id": f"event-{recording}-{track}-{offset}",
                        "workspace_id": "workspace-a",
                        "job_id": f"recording-{recording}",
                        "track_id": track,
                        "occurred_at": f"2026-10-10T08:00:{offset:02d}+07:00",
                        "symbol": symbol,
                        "status": "verified",
                        "category": "observation",
                        "payload": {"sensitive_subject": "never copied to artifacts"},
                    }
                )
    return {"events": rows}


@pytest.fixture
def runs(tmp_path, monkeypatch):
    monkeypatch.setattr(registry, "RUNS", tmp_path / "runs")
    return registry.RUNS


def read(directory, name):
    return json.loads((directory / name).read_text(encoding="utf-8"))


def test_recording_split_and_replay_are_deterministic(exported):
    sessions, split, _ = novelty.prepare(exported, "workspace-a")
    assert len(sessions) == 24
    assert list(map(len, split.values())) == [9, 1, 2]
    assert set(split["train"]).isdisjoint(split["dev"] + split["test"])
    assert set(split["dev"]).isdisjoint(split["test"])
    reversed_export = {"events": list(reversed(exported["events"]))}
    assert novelty.prepare(reversed_export, "workspace-a") == (sessions, split, {})
    assert all(set(row["symbols"]) <= SYMBOLS for row in sessions)
    assert all(len({event.split("-")[2] for event in row["event_ids"]}) == 1 for row in sessions)
    duplicate = {"events": exported["events"] + [exported["events"][0]]}
    assert novelty.prepare(duplicate, "workspace-a")[0] == sessions
    few = {
        "events": [
            row
            for row in exported["events"]
            if row["job_id"] in {"recording-0", "recording-1", "recording-2"}
        ]
    }
    assert list(map(len, novelty.prepare(few, "workspace-a")[1].values())) == [1, 1, 1]
    few["events"] = [row for row in few["events"] if row["job_id"] != "recording-2"]
    with pytest.raises(ValueError, match="three independent"):
        novelty.prepare(few, "workspace-a")


@pytest.mark.parametrize(
    "field,value",
    [
        ("workspace_id", "another-workspace"),
        ("symbol", "EMPLOYEE_ID"),
        ("symbol", []),
        ("track_id", True),
        ("track_id", -1),
        ("occurred_at", "2026-10-10T08:00:00"),
        ("occurred_at", "invalid"),
        ("id", ""),
        ("job_id", None),
    ],
)
def test_invalid_verified_events_fail_before_outputs(runs, exported, field, value):
    exported["events"][0][field] = value
    with pytest.raises(ValueError):
        novelty.run_novelty("invalid", exported, "workspace-a")
    assert not runs.exists()


def test_drafts_retractions_attendance_and_gaps(exported):
    baseline, _, _ = novelty.prepare(exported, "workspace-a")
    for status in ("draft", "stale", "retracted"):
        exported["events"].append(
            {
                "workspace_id": "workspace-a",
                "status": status,
                "category": "observation",
                "symbol": "unsupported-draft",
            }
        )
    exported["events"].append(
        {
            "workspace_id": "workspace-a",
            "status": "verified",
            "category": "attendance",
        }
    )
    assert novelty.prepare(exported, "workspace-a")[0] == baseline
    original = exported["events"][0]
    exported["events"].append(
        {
            **original,
            "id": "late-event",
            "occurred_at": "2026-10-10T08:02:00+07:00",
        }
    )
    sessions = novelty.prepare(exported, "workspace-a")[0]
    assert len(sessions) == len(baseline) + 1
    late = next(row for row in sessions if row["event_ids"] == ["late-event"])
    assert late["session_index"] == 1
    with pytest.raises(ValueError, match="workspace"):
        novelty.prepare(exported, "other")
    exported["events"].append({**original, "symbol": "PERSON_EXIT_ZONE"})
    with pytest.raises(ValueError, match="Conflicting"):
        novelty.prepare(exported, "workspace-a")


def test_real_run_freezes_selection_and_keeps_fixed_symbol_space(runs, exported, monkeypatch):
    sessions, split, _ = novelty.prepare(exported, "workspace-a")
    test_ids = set(split["test"])
    original = novelty.session_loss
    calls = []

    def observed(model, row):
        if row["recording_id"] in test_ids:
            assert (runs / "diagnostics" / "selection.json").is_file()
            calls.append((model.n, model.method, novelty.session_key(row)))
        return original(model, row)

    monkeypatch.setattr(novelty, "session_loss", observed)
    directory = novelty.run_novelty("diagnostics", exported, "workspace-a")
    manifest = registry.read_run("diagnostics")
    assert manifest["stages"]["event_novelty"] == "completed"
    assert manifest["config"]["tokenizer"] == novelty.TOKENIZER
    assert len(calls) == 6 * sum(row["recording_id"] in test_ids for row in sessions)
    counts = read(directory, "counts.json")
    assert set(counts["vocabulary"]) == SYMBOLS | {"</s>", "<UNK>"}
    raw = {
        int(n): Counter({tuple(gram): value for gram, value in entries})
        for n, entries in counts["raw"].items()
    }
    train = [row["symbols"] for row in sessions if row["recording_id"] in split["train"]]
    assert raw[2] == Counter(gram for sentence in train for gram in events(sentence, 2))
    bank = CountBank.from_counts(counts["vocabulary"], raw, 1)
    calibration = read(directory, "selection.json")
    predictions = read(directory, "predictions.json")
    pairs = Counter(pair for sentence in train for pair in zip(sentence, sentence[1:]))
    for row in predictions["pair_frequency_lt2"]:
        session = next(
            item for item in sessions if novelty.session_key(item) == novelty.session_key(row)
        )
        rare = sum(pairs[pair] < 2 for pair in zip(session["symbols"], session["symbols"][1:]))
        assert row["rare_pairs"] == rare and row["alert"] == (rare > 0)
    for name, settings in calibration["models"].items():
        model = ExtensionLM(bank, settings["n"], settings["method"], **settings["parameters"])
        assert settings["threshold"] == novelty.quantile95(settings["dev_session_ce"])
        for row in predictions[name]:
            session = next(
                item for item in sessions if novelty.session_key(item) == novelty.session_key(row)
            )
            assert row["session_ce"] == pytest.approx(original(model, session))
            assert row["alert"] == (row["session_ce"] > settings["threshold"])
    summary = read(directory, "summary.json")
    assert summary["mode"].startswith("novelty diagnostics only")
    assert len(summary["models"]) == 7
    assert all(
        row["precision"] is None and row["recall"] is None for row in summary["models"].values()
    )
    assert "sensitive_subject" not in (directory / "sessions.json").read_text()
    snapshot = (directory / "manifest.json").read_bytes()
    with pytest.raises(FileExistsError):
        novelty.run_novelty("diagnostics", exported, "workspace-a")
    assert (directory / "manifest.json").read_bytes() == snapshot


def test_labels_metrics_and_test_data_cannot_change_selection(runs, exported):
    sessions, split, _ = novelty.prepare(exported, "workspace-a")
    exported["labels"] = [
        {
            "recording_id": row["recording_id"],
            "track_id": row["track_id"],
            "session_index": row["session_index"],
            "novel": row["track_id"] == 1,
        }
        for row in sessions
    ]
    with pytest.raises(ValueError, match="independent source"):
        novelty.prepare(exported, "workspace-a")
    exported["label_provenance"] = {"source": "controlled synthetic test", "independent": True}
    first = novelty.run_novelty("labelled", exported, "workspace-a")
    summary = read(first, "summary.json")
    assert summary["mode"] == "labelled offline novelty evaluation"
    for metrics in summary["models"].values():
        assert metrics["labelled_test_sessions"] == metrics["test_sessions"] == 4
        assert metrics["false_alerts_per_hour"] is None
        assert metrics["detection_delay_seconds"] is None
    changed = copy.deepcopy(exported)
    for row in changed["events"]:
        if row["job_id"] in split["test"]:
            row["symbol"] = "HELMET_UNKNOWN"
    second = novelty.run_novelty("changed-test", changed, "workspace-a")
    assert read(first, "selection.json") == read(second, "selection.json")
    rows = [
        {"recording_id": "r", "track_id": 1, "session_index": i, "alert": flag}
        for i, flag in enumerate((True, True, False))
    ]
    metrics = novelty.label_metrics(
        rows, {("r", 1, i): label for i, label in enumerate((True, False, True))}
    )
    assert metrics["precision"] == metrics["recall"] == 0.5
    assert novelty.quantile95([1, 2, 3]) == pytest.approx(2.9)
    assert novelty.quantile95([4]) == 4
    with pytest.raises(ValueError):
        novelty.quantile95([math.inf])


def test_cli_runs_real_fixture_and_rejects_oversize(runs, exported, tmp_path, monkeypatch):
    path = tmp_path / "ledger.json"
    path.write_text(json.dumps(exported), encoding="utf-8")
    argv = ["--input", str(path), "--workspace-id", "workspace-a", "--run-id", "cli"]
    assert novelty.main(argv) == 0
    registry.read_run("cli")
    monkeypatch.setattr(novelty, "MAX_BYTES", 10)
    with pytest.raises(SystemExit) as raised:
        novelty.main(argv)
    assert raised.value.code == 2


def test_single_symbol_label_is_excluded_from_pair_baseline_metrics(runs, exported):
    _, split, _ = novelty.prepare(exported, "workspace-a")
    recording = split["test"][0]
    exported["events"] = [
        row
        for row in exported["events"]
        if row["job_id"] != recording or row["track_id"] != 1 or row["id"].endswith("-0")
    ]
    exported["labels"] = [
        {
            "recording_id": recording,
            "track_id": 1,
            "session_index": 0,
            "novel": True,
        }
    ]
    exported["label_provenance"] = {"source": "independent synthetic label", "independent": True}
    directory = novelty.run_novelty("single-symbol", exported, "workspace-a")
    predictions = read(directory, "predictions.json")["pair_frequency_lt2"]
    single = next(
        row for row in predictions if row["recording_id"] == recording and row["track_id"] == 1
    )
    assert single["supported"] is False and single["alert"] is False
    models = read(directory, "summary.json")["models"]
    baseline = models["pair_frequency_lt2"]
    assert baseline["test_sessions"] == 4 and baseline["supported_test_sessions"] == 3
    assert baseline["available_labelled_test_sessions"] == 1
    assert baseline["labelled_test_sessions"] == 0
    assert baseline["false_negatives"] is None
    assert baseline["precision"] is None and baseline["recall"] is None
    for name, metrics in models.items():
        if name != "pair_frequency_lt2":
            assert metrics["supported_test_sessions"] == 4
            assert metrics["labelled_test_sessions"] == 1


def test_reserved_symbols_keep_support_without_fabricated_training_counts(runs, exported):
    for row in exported["events"]:
        row["symbol"] = "PERSON_ENTER_ZONE"
    directory = novelty.run_novelty("sparse-alphabet", exported, "workspace-a")
    counts = read(directory, "counts.json")
    raw = {
        int(n): Counter({tuple(gram): value for gram, value in entries})
        for n, entries in counts["raw"].items()
    }
    bank = CountBank.from_counts(counts["vocabulary"], raw, 1)
    assert raw[1][("PERSON_EXIT_ZONE",)] == 0
    for method in ("kneser_ney", "witten_bell"):
        model = ExtensionLM(bank, 3, method)
        assert model.score("PERSON_EXIT_ZONE", ["PERSON_ENTER_ZONE"]) > 0
        assert sum(
            model.score(symbol, ["PERSON_ENTER_ZONE"]) for symbol in model.vocabulary
        ) == pytest.approx(1)


def test_interruption_preserves_partial_run_and_rejects_reuse(runs, exported, monkeypatch):
    def interrupted(*args):
        raise RuntimeError("Controlled calibration interruption")

    monkeypatch.setattr(novelty, "tune", interrupted)
    with pytest.raises(RuntimeError, match="interruption"):
        novelty.run_novelty("interrupted", exported, "workspace-a")
    assert registry.read_run("interrupted", require_completed=False)["status"] == "running"
    with pytest.raises(ValueError, match="incomplete"):
        registry.read_run("interrupted")
    with pytest.raises(FileExistsError):
        novelty.run_novelty("interrupted", exported, "workspace-a")
