import gzip
import json

import pytest

from extensions.src.cli import load_model, read_config, save_model
from extensions.src.models import CountBank, ExtensionLM


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
