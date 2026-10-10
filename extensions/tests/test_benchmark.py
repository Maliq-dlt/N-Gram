"""Real native-memory/subprocess benchmark verification on a small synthetic source run."""

import json

import pytest

from extensions.experiments import benchmark, registry, research


def test_native_process_peak_and_quantiles():
    assert benchmark.peak_rss_bytes() > 0
    result = benchmark.distribution([1.0, 2.0, 3.0, 4.0, 5.0])
    assert result["p50_ms"] == 3.0
    assert result["p95_ms"] == pytest.approx(4.8)


@pytest.mark.parametrize(
    "parameters",
    [
        {"warmup": 0},
        {"repeats": 1},
        {"targets": 0},
        {"targets": 1001},
    ],
)
def test_invalid_budget_rejected_before_source_access(parameters):
    with pytest.raises(ValueError):
        benchmark.benchmark("missing", **parameters)


@pytest.fixture
def source(tmp_path, monkeypatch):
    monkeypatch.setattr(registry, "RUNS", tmp_path / "runs")
    docs = [
        {
            "id": f"doc{i}",
            "source": "test",
            "license": "CC0",
            "sentences": [["term" + chr(97 + i), "common", "text"]],
        }
        for i in range(12)
    ]
    return research.run_research(
        "benchmark", docs, orders=(1,), methods=("witten_bell", "interpolation_em"), resamples=100
    )


def test_real_subprocesses_preserve_completed_source_and_use_same_dev_targets(source):
    before = (source / "manifest.json").read_bytes()
    derived = benchmark.benchmark("benchmark", warmup=1, repeats=2, targets=3)
    assert before == (source / "manifest.json").read_bytes()
    registry.read_run("benchmark")
    manifest = json.loads((derived / "manifest.json").read_text())
    assert manifest["status"] == "completed"
    summary = json.loads((derived / "summary.json").read_text())
    rows = list(summary["models"].values())
    assert len(rows) == 3
    assert len({row["fixed_targets_sha256"] for row in rows}) == 1
    for row in rows:
        assert row["cpu"] >= 0 and row["peak_rss_bytes"] > 0
        assert row["targets"] == 3
        assert len(row["build_countbank_and_dev_tune"]["samples_ms"]) == 2
        assert len(row["score_single_target"]["samples_ms"]) == 6
        assert len(row["top_k_five_single_context"]["samples_ms"]) == 6
    with pytest.raises(FileExistsError):
        benchmark.benchmark("benchmark", warmup=1, repeats=2, targets=3)


@pytest.mark.parametrize(
    "case", ["bad-path", "completed", "source-hash", "receipt-hash", "existing", "claim"]
)
def test_worker_rejects_unsafe_output_before_pin_or_work(source, monkeypatch, case):
    derived = registry.derived_directory("benchmark", "benchmark")
    output = derived / "1-witten_bell.json"
    expected_error = ValueError
    if case == "bad-path":
        output = source / "summary.json"
    elif case in {"completed", "receipt-hash"}:
        receipt = json.loads((derived / "manifest.json").read_text())
        receipt["status" if case == "completed" else "source_config_sha256"] = (
            "completed" if case == "completed" else "0" * 64
        )
        registry.atomic_json(derived / "manifest.json", receipt)
    elif case == "source-hash":
        (source / "source_documents.json").write_text("[]", encoding="utf-8")
    elif case == "existing":
        output.write_text("preserved existing output", encoding="utf-8")
        expected_error = FileExistsError
    else:
        output.with_suffix(".claim").write_text("previous attempt", encoding="utf-8")
        expected_error = FileExistsError
    before = output.read_bytes() if output.exists() else None
    monkeypatch.setattr(benchmark, "pin_cpu", lambda: pytest.fail("Must reject before pin/work"))
    with pytest.raises(expected_error):
        benchmark.worker(source, "1-witten_bell", output, warmup=1, repeats=2, targets=1)
    assert (output.read_bytes() if output.exists() else None) == before


def test_worker_exclusive_output_survives_a_competing_writer(source, monkeypatch):
    derived = registry.derived_directory("benchmark", "benchmark")
    output = derived / "1-witten_bell.json"

    def concurrent_output():
        output.write_text("competing output preserved", encoding="utf-8")
        return 0

    monkeypatch.setattr(benchmark, "pin_cpu", concurrent_output)
    with pytest.raises(FileExistsError):
        benchmark.worker(source, "1-witten_bell", output, warmup=1, repeats=2, targets=1)
    assert output.read_text() == "competing output preserved"
    assert output.with_suffix(".claim").is_file()
    assert json.loads((derived / "manifest.json").read_text())["status"] == "running"
