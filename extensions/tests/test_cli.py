import gzip
import json

import pytest

from extensions.src.cli import load_model, read_config, save_model
from extensions.src.models import ALL_METHODS, CountBank, ExtensionLM


def test_checkpoint_round_trip_and_no_overwrite(tmp_path):
    model = ExtensionLM(CountBank([["a", "b"], ["a", "c"]], max_n=3, min_count=1), 3, "kneser_ney")
    path = tmp_path / "model.json.gz"
    save_model(path, model, {"corpus": "brown", "seed": 42})
    restored, metadata = load_model(path)
    assert metadata["seed"] == 42
    for context in [("<s>", "a"), ("a", "b"), ("unknown", "context")]:
        for word in model.vocabulary:
            assert restored.score(word, context) == model.score(word, context)
    with pytest.raises(FileExistsError):
        save_model(path, model, {})


def test_rejects_corrupt_artifact_and_unknown_config_keys(tmp_path):
    artifact = tmp_path / "corrupt.json.gz"
    with gzip.open(artifact, "wt", encoding="utf-8") as stream:
        json.dump({"format_version": 999}, stream)
    with pytest.raises(ValueError):
        load_model(artifact)
    config = tmp_path / "bad.yaml"
    config.write_text("n: 3\nsecret: invalid\n", encoding="utf-8")
    with pytest.raises(ValueError):
        read_config(config)


@pytest.mark.parametrize("method", ALL_METHODS)
def test_v2_round_trip_all_methods_and_deterministic_artifacts(tmp_path, method):
    from extensions.src.cli import model_info

    model = ExtensionLM(CountBank([["a", "b"], ["a", "c"]], max_n=3, min_count=1), 3, method)
    first, second = tmp_path / "first.json.gz", tmp_path / "second.json.gz"
    save_model(first, model, {"source": "fixture"})
    # Count insertion order and gzip destination names must not affect artifact identity.
    model.bank.raw = {
        n: type(counts)(dict(reversed(list(counts.items()))))
        for n, counts in model.bank.raw.items()
    }
    save_model(second, model, {"source": "fixture"})
    assert first.read_bytes() == second.read_bytes()
    info = model_info(first)
    assert info["checkpoint"]["format_version"] == 2
    assert info["artifact_size"] == first.stat().st_size
    restored, _ = load_model(first)
    for context in [("<s>", "a"), ("unknown", "context")]:
        assert sum(restored.score(word, context) for word in restored.vocabulary) == pytest.approx(
            sum(model.score(word, context) for word in model.vocabulary)
        )
        for word in model.vocabulary:
            assert restored.score(word, context) == pytest.approx(model.score(word, context))


def test_legacy_v1_without_sidecar_is_readable_and_schema_remains_strict(tmp_path):
    from extensions.src.cli import _sidecar

    model = ExtensionLM(CountBank([["a", "b"]], max_n=2, min_count=1), 2, "add_k")
    path = tmp_path / "legacy.json.gz"
    save_model(path, model, {}, format_version=1)
    _sidecar(path).unlink()
    assert load_model(path)[0].score("a", ["<s>"]) == model.score("a", ["<s>"])
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        payload = json.load(stream)
    payload["algorithm_version"] = "must-not-enter-v1"
    with gzip.open(path, "wt", encoding="utf-8") as stream:
        json.dump(payload, stream)
    with pytest.raises(ValueError, match="Schema"):
        load_model(path)


def test_v2_needs_committed_pair_and_sidecar_hash_matches(tmp_path, monkeypatch):
    import extensions.src.cli as cli

    model = ExtensionLM(CountBank([["a"]], min_count=1), 2)
    path = tmp_path / "model.json.gz"
    save_model(path, model, {})
    monkeypatch.setattr(
        gzip, "open", lambda *a, **k: pytest.fail("info must not decompress counts")
    )
    assert cli.model_info(path)["checkpoint"]["method"] == "add_k"
    info = json.loads(cli._sidecar(path).read_text())
    info["artifact_size"] += 1
    cli._sidecar(path).write_text(json.dumps(info), encoding="utf-8")
    with pytest.raises(ValueError, match="Hash/ukuran"):
        cli.model_info(path)
    cli._sidecar(path).unlink()
    monkeypatch.undo()
    with pytest.raises(ValueError, match="committed"):
        load_model(path)


def test_sidecar_metadata_tampering_and_exact_keys_fail(tmp_path):
    import extensions.src.cli as cli

    path = tmp_path / "model.json.gz"
    save_model(path, ExtensionLM(CountBank([["a"]], min_count=1), 2), {})
    sidecar = cli._sidecar(path)
    info = json.loads(sidecar.read_text())
    info["checkpoint"]["metadata"]["tampered"] = True
    sidecar.write_text(json.dumps(info), encoding="utf-8")
    with pytest.raises(ValueError, match="Fingerprint"):
        cli.model_info(path)
    info["extra"] = "not allowed"
    sidecar.write_text(json.dumps(info), encoding="utf-8")
    with pytest.raises(ValueError, match="Schema sidecar"):
        cli.model_info(path)


def test_checkpoint_pair_rollback_and_preexisting_sidecar_exclusive(tmp_path, monkeypatch):
    import extensions.src.cli as cli

    model = ExtensionLM(CountBank([["a"]], min_count=1), 2)
    path = tmp_path / "failure.json.gz"
    monkeypatch.setattr(cli, "_commit_json", lambda *a: (_ for _ in ()).throw(OSError("injected")))
    with pytest.raises(OSError, match="injected"):
        save_model(path, model, {})
    assert not path.exists() and not cli._sidecar(path).exists()
    assert not list(tmp_path.glob("*.tmp")) and not list(tmp_path.glob("*.lock"))
    cli._sidecar(path).write_text("preserve", encoding="utf-8")
    with pytest.raises(FileExistsError):
        save_model(path, model, {})
    assert cli._sidecar(path).read_text() == "preserve"


def test_score_sentence_matches_count_evaluation_and_backoff_pp_is_na():
    import math

    from extensions.src.cli import score_sentence
    from extensions.src.models import evaluate_counts

    model = ExtensionLM(CountBank([["hello", "world"], ["hello", "other"]], min_count=1), 2)
    scored = score_sentence(model, "Hello, world! 123")
    expected = evaluate_counts(model, model.bank.event_counts([["hello", "world"]], 2))
    assert scored["tokens"] == ["hello", "world"]
    assert scored["events"][-1]["word"] == "</s>"
    assert scored["predicted_tokens"] == 3
    assert scored["cross_entropy"] == pytest.approx(expected["score_cross_entropy"])
    assert scored["nll"] == pytest.approx(math.fsum(row["nll"] for row in scored["events"]))
    assert scored["perplexity"] == pytest.approx(expected["perplexity"])
    backoff = ExtensionLM(model.bank, 2, "stupid_backoff")
    assert score_sentence(backoff, "hello world")["perplexity"] is None
    for invalid in ("", "123 !!!", "a\x00b", "a " * 4097):
        with pytest.raises(ValueError):
            score_sentence(model, invalid)


def test_score_info_list_cli_jsonl_limits_and_errors(tmp_path, capsys, monkeypatch):
    import extensions.src.cli as cli

    path = tmp_path / "model.json.gz"
    save_model(path, ExtensionLM(CountBank([["hello", "world"]], min_count=1), 2), {})
    text = tmp_path / "sentences.txt"
    text.write_text("Hello world\nUnknown words\n", encoding="utf-8")
    assert cli.main(["score", "--model", str(path), "--input", str(text)]) == 0
    rows = [json.loads(row) for row in capsys.readouterr().out.splitlines()]
    assert [row["line"] for row in rows] == [1, 2]
    assert all(row["predicted_tokens"] == 3 for row in rows)
    assert cli.main(["info", "--model", str(path)]) == 0
    assert json.loads(capsys.readouterr().out)["artifact_size"] == path.stat().st_size
    assert cli.main(["list", "--dir", str(tmp_path)]) == 0
    assert len(capsys.readouterr().out.splitlines()) == 1
    monkeypatch.setattr(cli, "MAX_LINE", 8)
    assert cli.main(["score", "--model", str(path), "--input", str(text)]) == 2
    assert "Input melebihi" in capsys.readouterr().err
    monkeypatch.undo()
    text.write_bytes(b"\xff\n")
    assert cli.main(["score", "--model", str(path), "--input", str(text)]) == 2
    assert "Error:" in capsys.readouterr().err
    with pytest.raises(SystemExit) as help_exit:
        cli.main(["--help"])
    assert help_exit.value.code == 0
    help_text = capsys.readouterr().out
    assert all(command in help_text for command in ("score", "info", "list"))


@pytest.mark.parametrize("method", ALL_METHODS)
def test_train_records_provenance_and_evaluate_reuses_receipt(
    tmp_path, monkeypatch, capsys, method
):
    import extensions.src.cli as cli

    corpus = [["hello", "world"], ["hello", "other"]] * 10
    monkeypatch.setattr(cli, "load_corpus", lambda name: corpus)
    config, path = tmp_path / "config.yaml", tmp_path / "trained.json.gz"
    config.write_text(
        f"corpus: brown\nseed: 42\nn: 2\nmethod: {method}\nmin_count: 1\n", encoding="utf-8"
    )
    evaluated, original = [], cli.evaluate_counts
    monkeypatch.setattr(
        cli, "evaluate_counts", lambda *args: (evaluated.append(True), original(*args))[1]
    )
    assert cli.main(["train", "--config", str(config), "--model", str(path)]) == 0
    capsys.readouterr()
    assert not evaluated, "train must never evaluate held-out test"
    _, metadata = load_model(path)
    assert metadata["tuning_trace"] and set(metadata["split"]["ids"]) == {"train", "dev", "test"}
    assert cli.main(["evaluate", "--model", str(path)]) == 0
    assert json.loads(capsys.readouterr().out)["cached"] is False
    assert cli.main(["evaluate", "--model", str(path)]) == 0
    assert json.loads(capsys.readouterr().out)["cached"] is True
    assert len(evaluated) == 1
    receipt = path.with_name(path.name + ".evaluation.json")
    data = json.loads(receipt.read_text())
    data["result"]["predicted_tokens"] += 1
    receipt.write_text(json.dumps(data), encoding="utf-8")
    assert cli.main(["evaluate", "--model", str(path)]) == 2
    assert len(evaluated) == 1, "corrupt receipt must not trigger repeat test evaluation"
    assert "Receipt" in capsys.readouterr().err


def test_reject_duplicate_json_boolean_versions_and_input_output_boundaries(tmp_path):
    import extensions.src.cli as cli

    assert cli.main(["info", "--model", str(tmp_path / "missing.json.gz")]) == 2
    with pytest.raises(ValueError, match="Duplicate"):
        cli._json(b'{"format_version":1,"format_version":2}')
    with pytest.raises(ValueError, match="finite"):
        cli._json(b'{"value":NaN}')
    outside = cli.ROOT.parent / "must-not-create-cli.json.gz"
    with pytest.raises(ValueError, match="repository"):
        save_model(outside, ExtensionLM(CountBank([["a"]], min_count=1), 2), {})
    assert not outside.exists()
    invalid = tmp_path / "bool.json.gz"
    with gzip.open(invalid, "wt", encoding="utf-8") as stream:
        json.dump({"format_version": True}, stream)
    with pytest.raises(ValueError, match="Format"):
        load_model(invalid)


@pytest.mark.parametrize("mutation", ["boolean_version", "invalid_result"])
def test_receipt_rejects_rehashed_invalid_schema(tmp_path, monkeypatch, mutation):
    import extensions.src.cli as cli

    corpus = [["hello", "world"]] * 10
    monkeypatch.setattr(cli, "load_corpus", lambda name: corpus)
    path = tmp_path / "receipt.json.gz"
    model = ExtensionLM(CountBank(corpus, max_n=2, min_count=1), 2, "add_k")
    metadata = {"corpus": "brown", "seed": 42, "corpus_sha256": cli.corpus_digest(corpus)}
    save_model(path, model, metadata)
    cli._evaluate(path, model, metadata)
    receipt = path.with_name(path.name + ".evaluation.json")
    saved = json.loads(receipt.read_text(encoding="utf-8"))
    if mutation == "boolean_version":
        saved["schema_version"] = True
    else:
        saved["result"]["predicted_tokens"] = True
        saved["sha256"] = cli._digest({"identity": saved["identity"], "result": saved["result"]})
    receipt.write_text(json.dumps(saved), encoding="utf-8")
    monkeypatch.setattr(cli, "evaluate_counts", lambda *args: pytest.fail("must not reevaluate"))
    with pytest.raises(ValueError, match="Receipt"):
        cli._evaluate(path, model, metadata)


def test_document_split_checkpoint_fingerprint_and_group_validation(tmp_path):
    import extensions.src.cli as cli

    split = {
        "policy": "document-exact-sentence-and-5gram-jaccard-0.9-v1",
        "seed": 42,
        "corpus_sha256": "a" * 64,
        "groups": [["doc1", "doc2"], ["doc3"], ["doc4"]],
        "ids": {"train": ["doc1", "doc2"], "dev": ["doc3"], "test": ["doc4"]},
    }
    metadata = {"seed": 42, "corpus_sha256": "a" * 64, "document_split": split}
    model = ExtensionLM(CountBank([["a", "b"]], max_n=2, min_count=1), 2, "add_k")
    path = tmp_path / "document.json.gz"
    save_model(path, model, metadata)
    assert load_model(path)[1] == metadata
    assert cli.model_info(path)["checkpoint"]["provenance"]["split_sha256"] == cli._digest(split)
    split["groups"] = [["doc1", "doc3"], ["doc2"], ["doc4"]]
    with pytest.raises(ValueError, match="leakage"):
        save_model(tmp_path / "leak.json.gz", model, metadata)


def test_v1_preserves_arbitrary_metadata(tmp_path):
    model = ExtensionLM(CountBank([["a"]], min_count=1), 2, "add_k")
    metadata = {"corpus": "custom", "seed": "external", "split": {"custom": True}}
    path = tmp_path / "old.json.gz"
    save_model(path, model, metadata, format_version=1)
    assert load_model(path)[1] == metadata


@pytest.mark.parametrize("method", ["kneser_ney", "stupid_backoff"])
def test_evaluate_zero_probability_serializes_and_reuses_receipt(
    tmp_path, monkeypatch, capsys, method
):
    import extensions.src.cli as cli

    corpus = [["unseen"]] * 10
    monkeypatch.setattr(cli, "load_corpus", lambda name: corpus)
    path = tmp_path / "zero.json.gz"
    model = ExtensionLM(CountBank([["known"]], max_n=2, min_count=1), 2, method, epsilon=0)
    metadata = {"corpus": "brown", "seed": 42, "corpus_sha256": cli.corpus_digest(corpus)}
    save_model(path, model, metadata)
    assert cli.main(["evaluate", "--model", str(path)]) == 0
    first = json.loads(capsys.readouterr().out)
    assert first["perplexity"] is None
    if method == "kneser_ney":
        assert first["score_cross_entropy"] is None
        assert model.score("unseen", ["<s>"]) == 0
    monkeypatch.setattr(cli, "evaluate_counts", lambda *args: pytest.fail("must reuse receipt"))
    assert cli.main(["evaluate", "--model", str(path)]) == 0
    second = json.loads(capsys.readouterr().out)
    assert second == {**first, "cached": True}
    receipt = path.with_name(path.name + ".evaluation.json").read_text(encoding="utf-8")
    assert "Infinity" not in receipt and "NaN" not in receipt
