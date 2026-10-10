"""Real synthetic document runs: provenance, selection order and frozen transfer."""

import json

import pytest

from extensions.experiments import registry, research
from extensions.src.cli import load_model


@pytest.fixture
def docs():
    return [
        {
            "id": f"doc{i}",
            "source": "synthetic-test",
            "license": "CC0",
            "genre": "mini",
            "sentences": [[f"unique{chr(97 + i)}", "shared", "term"]],
        }
        for i in range(12)
    ]


@pytest.fixture
def runs(tmp_path, monkeypatch):
    monkeypatch.setattr(registry, "RUNS", tmp_path / "research-runs")
    return registry.RUNS


def test_real_research_preregisters_selects_before_test_and_preserves_runs(runs, docs, monkeypatch):
    from extensions.src import analytics

    original = analytics.document_losses
    calls = []

    def observed(model, documents):
        directory = registry.run_directory("valid")
        assert (directory / "protocol.json").is_file()
        assert (directory / "selection.json").is_file()
        calls.append((model.n, model.method))
        return original(model, documents)

    monkeypatch.setattr(analytics, "document_losses", observed)
    directory = research.run_research(
        "valid",
        docs,
        orders=(1, 2),
        methods=("witten_bell", "modified_kneser_ney", "interpolation_em"),
        resamples=100,
    )
    manifest = registry.read_run("valid")
    assert manifest["status"] == "completed"
    assert len(calls) == 8 and len(set(calls)) == 8
    config = manifest["config"]
    assert config["methods"][-1] == "kneser_ney"
    assert config["budget"]["models"] == 8
    assert config["public_models"] is False
    autocomplete = json.loads((directory / "autocomplete.json").read_text())
    assert autocomplete["roles"]["unigram"] == "1-kneser_ney"
    assert len({row["queries"] for row in autocomplete["models"].values()}) == 1
    split = json.loads((directory / "splits.json").read_text())
    assert not set(split["ids"]["train"]) & set(split["ids"]["test"])
    selection = json.loads((directory / "selection.json").read_text())
    summary = json.loads((directory / "summary.json").read_text())
    assert selection["best"] == min(summary, key=lambda r: (r["dev_loss"], r["model"]))["model"]
    for path in (directory / "models").glob("*.json.gz"):
        model, metadata = load_model(path)
        assert metadata["selection"] == "dev-only"
        for i in split["ids"]["test"]:
            assert "unique" + chr(97 + int(i.removeprefix("doc"))) not in model.vocabulary
    assert len(list((directory / "receipts").glob("test-*.json"))) == 8
    assert (directory / "diagnostics.json").is_file()
    assert len(json.loads((directory / "generated.json").read_text())) == 100
    before = (directory / "manifest.json").read_bytes()
    with pytest.raises(FileExistsError):
        research.run_research("valid", docs, orders=(1,), methods=("witten_bell",), resamples=100)
    assert (directory / "manifest.json").read_bytes() == before


def test_frozen_cross_domain_records_distinct_data_without_target_training(runs, docs):
    target = [
        {
            "id": "target",
            "source": "target-test",
            "license": "CC0",
            "sentences": [["targetonly", "different"]],
        }
    ]
    directory = research.run_research(
        "transfer",
        docs,
        orders=(2,),
        methods=("witten_bell",),
        target_documents=target,
        resamples=100,
        public_models=True,
    )
    transfer = json.loads((directory / "domain_transfer.json").read_text())
    assert transfer["source_sha256"] != transfer["target_sha256"]
    assert transfer["target_training"] is False
    assert registry.read_run("transfer")["config"]["public_models"] is True
    assert (directory / "models" / "1-kneser_ney.json.gz").is_file()
    assert (directory / "target_bootstrap.json").is_file()
    for path in (directory / "models").glob("*.json.gz"):
        model, _ = load_model(path)
        assert "targetonly" not in model.vocabulary
    registry.read_run("transfer")


def test_partial_failure_cannot_be_reused_or_claimed_complete(runs, docs, monkeypatch):
    from extensions.src import analytics

    def failure(model, documents):
        raise RuntimeError("Interrupted test")

    monkeypatch.setattr(analytics, "document_losses", failure)
    with pytest.raises(RuntimeError):
        research.run_research("partial", docs, orders=(1,), methods=("witten_bell",), resamples=100)
    assert registry.read_run("partial", False)["status"] == "running"
    with pytest.raises(ValueError):
        registry.read_run("partial")
    with pytest.raises(FileExistsError):
        research.run_research("partial", docs, orders=(1,), methods=("witten_bell",), resamples=100)


def test_cli_input_and_nonfinite_json(runs, docs, tmp_path):
    path = tmp_path / "documents.jsonl"
    path.write_text("\n".join(json.dumps(doc) for doc in docs), encoding="utf-8")
    assert (
        research.main(
            [
                "--input",
                str(path),
                "--run-id",
                "cli",
                "--orders",
                "1",
                "--methods",
                "witten_bell",
                "--resamples",
                "100",
            ]
        )
        == 0
    )
    registry.read_run("cli")
    assert research.finite_json({"loss": float("inf"), "nan": float("nan")}) == {
        "loss": {"nonfinite": "Infinity"},
        "nan": {"nonfinite": "NaN"},
    }


@pytest.mark.parametrize(
    "orders,methods,threshold",
    [((0,), ("witten_bell",), 2), ((1,), ("bad",), 2), ((1,), ("witten_bell",), 0)],
)
def test_grid_rejected_before_run_creation(runs, docs, orders, methods, threshold):
    with pytest.raises(ValueError):
        research.run_research("invalid", docs, orders, methods, threshold)
    assert not runs.exists()


@pytest.mark.parametrize("overlap", ["renamed", "sentence", "near", "group"])
def test_cross_domain_overlap_rejected_before_run_creation(runs, docs, overlap):
    target = [
        {**doc, "id": "target-" + doc["id"], "source": "renamed-source"} for doc in reversed(docs)
    ]
    if overlap == "sentence":
        target = [{**target[0], "sentences": [docs[0]["sentences"][0], ["different"]]}]
    elif overlap == "near":
        words = ["word" + chr(97 + index // 26) + chr(97 + index % 26) for index in range(100)]
        docs[0] = {**docs[0], "sentences": [words]}
        target = [{**target[0], "sentences": [words[:-1] + ["different"]]}]
    elif overlap == "group":
        docs[0]["group"] = "same-source-group"
        target = [
            {**target[0], "sentences": [["distinct", "target"]], "group": "same-source-group"}
        ]
    with pytest.raises(ValueError, match="overlap"):
        research.run_research(
            "overlap",
            docs,
            orders=(1,),
            methods=("witten_bell",),
            target_documents=target,
            resamples=100,
        )
    assert not runs.exists()


def test_jsonl_source_is_exploratory_even_when_protocol_is_written_first(runs, docs):
    directory = research.run_research(
        "exploratory", docs, orders=(1,), methods=("witten_bell",), resamples=100
    )
    config = json.loads((directory / "protocol.json").read_text())
    assert config["test_policy"].startswith("exploratory")


def test_duplicate_target_rows_use_joint_source_policy_group_without_mutating_input(runs, docs):
    target = [
        {
            "id": identifier,
            "source": "target",
            "license": "CC0",
            "sentences": [["separate", "target", "content"]],
        }
        for identifier in ("targeta", "targetb")
    ]
    before = json.dumps(target, sort_keys=True)
    directory = research.run_research(
        "targetgroups",
        docs,
        orders=(2,),
        methods=("witten_bell",),
        target_documents=target,
        resamples=100,
    )
    assert json.dumps(target, sort_keys=True) == before
    assert json.loads((directory / "target_documents.json").read_text()) == target
    config = registry.read_run("targetgroups")["config"]
    assert config["target_sha256"] == research.digest(target)
    assert len(set(config["target_group_ids"].values())) == 1
    bootstrap = json.loads((directory / "target_bootstrap.json").read_text())
    assert bootstrap["documents"] == 2
    assert bootstrap["independent_groups"] == 1
    selection = json.loads((directory / "selection.json").read_text())
    rows = json.loads(
        (directory / "metrics" / ("target-" + selection["best"] + ".json")).read_text()
    )
    assert len({row["group_id"] for row in rows}) == 1
    assert rows[0]["group_id"] == config["target_group_ids"][rows[0]["id"]]
