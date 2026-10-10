"""Independent grouping and token-weighted inference checks."""

import copy
import math

import pytest

from extensions.src.analytics import (
    aggregate,
    autocomplete_metrics,
    diagnostics,
    document_losses,
    paired_bootstrap,
    top_k,
)
from extensions.src.datasets import digest, split_documents
from extensions.src.models import CountBank, ExtensionLM


def documents():
    return [
        {
            "id": str(i),
            "source": "CC0-fixture",
            "license": "CC0",
            "sentences": [["word" + chr(97 + i), "shared", "term", "unique" + chr(97 + i), "tail"]],
        }
        for i in range(12)
    ]


def test_source_duplicates_stay_in_one_split_without_mutation():
    docs = documents()
    docs.extend(
        [
            {**copy.deepcopy(docs[0]), "id": "duplicate"},
            {
                **copy.deepcopy(docs[1]),
                "id": "sharedsentence",
                "sentences": docs[1]["sentences"] + [["other"]],
            },
        ]
    )
    docs[2]["group"] = docs[3]["group"] = "one-source"
    before = digest(docs)
    split, manifest = split_documents(docs)
    assert digest(docs) == before
    assert split == split_documents(list(reversed(docs)))[0]
    placement = {
        doc["id"]: (name, doc["split_group"]) for name, group in split.items() for doc in group
    }
    assert placement["0"] == placement["duplicate"]
    assert placement["1"] == placement["sharedsentence"]
    assert placement["2"] == placement["3"]
    assert (
        len(
            {doc["split_group"] for doc in split["train"]}
            & {doc["split_group"] for doc in split["test"]}
        )
        == 0
    )
    assert manifest["corpus_sha256"] == digest(sorted(docs, key=lambda d: d["id"]))


def test_near_duplicate_shingles_are_grouped():
    docs = documents()
    long = ["word" + chr(97 + i // 26) + chr(97 + i % 26) for i in range(100)]
    docs[0]["sentences"] = [long]
    docs.append({**docs[0], "id": "almost", "sentences": [long[:-1] + ["changed"]]})
    split, _ = split_documents(docs)
    groups = {d["id"]: d["split_group"] for ds in split.values() for d in ds}
    assert groups["0"] == groups["almost"]


def test_group_bootstrap_uses_clusters_and_token_weighting():
    a = [
        {"id": "a", "group_id": "same", "nll": 2.0, "predicted_tokens": 1},
        {"id": "b", "group_id": "same", "nll": 18.0, "predicted_tokens": 9},
        {"id": "c", "group_id": "other", "nll": 0.0, "predicted_tokens": 2},
    ]
    b = [{**r, "nll": 0.0} for r in a]
    result = paired_bootstrap(a, b, resamples=100, seed=7)
    assert result["independent_groups"] == 2 and result["documents"] == 3
    assert result["difference"] == pytest.approx(20 / 12)
    assert result["ci95"] == [0.0, 2.0]
    assert paired_bootstrap(a, a, resamples=100)["ci95"] == [0.0, 0.0]
    assert aggregate(a)["cross_entropy"] == pytest.approx(20 / 12)
    with pytest.raises(ValueError, match="groups"):
        paired_bootstrap(a, [{**r, "group_id": "wrong"} for r in b], resamples=100)


def test_ranking_oov_boundaries_and_diagnostics():
    bank = CountBank([["cat", "sits"], ["cat", "sleeps"], ["dog", "sits"]], min_count=1)
    model = ExtensionLM(bank, 2, "witten_bell")
    result = top_k(model, ["cat"], 5, prefix="s")
    assert [r["word"] for r in result] == ["sits", "sleeps"]
    assert top_k(model, [], prefix="nomatch") == []
    docs = [{"id": "test", "sentences": [["cat", "sits", "unseen"]]}]
    metrics = autocomplete_metrics(model, docs)
    assert metrics["oov_rate"] == pytest.approx(1 / 3)
    rows = document_losses(model, docs)
    assert rows[0]["predicted_tokens"] == 4 and rows[0]["group_id"] == "test"
    assert math.isfinite(rows[0]["nll"])
    diag = diagnostics(model, docs, [["cat", "cat", "cat", "cat"]])
    assert diag["generation"]["distinct_3"] == 0.5
    assert diag["generation"]["repeated_trigram_rate"] == 0.5
    assert diag["generation"]["reference_unigram_entropy_nats"] == pytest.approx(math.log(3))
