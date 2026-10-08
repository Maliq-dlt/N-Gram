import math

import pytest

from extensions.src.models import CountBank, ExtensionLM, evaluate_counts
from extensions.src.pipeline import split_three


@pytest.mark.parametrize("n", [1, 2, 3, 4])
@pytest.mark.parametrize("method", ["laplace", "add_k", "interpolation", "kneser_ney"])
def test_normalized_smoothing(n, method):
    bank = CountBank([["a", "b"], ["a", "c"], ["d", "b"]], max_n=4, min_count=1)
    model = ExtensionLM(bank, n, method)
    for context in list(bank.totals[n]) + [("never",) * (n - 1)]:
        assert math.fsum(model.score(w, context) for w in bank.vocabulary) == pytest.approx(
            1, abs=1e-9
        )
    assert model.score("<s>", ()) == 0


def test_continuation_probability_manual():
    bank = CountBank([["a", "x"], ["b", "x"], ["a", "y"]], max_n=2, min_count=1)
    model = ExtensionLM(bank, 2, "kneser_ney", discount=0.5, epsilon=0)
    # Unique bigrams: s-a, a-x, x-e, s-b, b-x, a-y, y-e: seven.
    assert model.score("x", ("never",)) == pytest.approx(2 / 7)
    assert model.score("x", ("a",)) == pytest.approx(0.5 / 2 + (0.5 * 2 / 2) * (2 / 7))
    assert model.score("</s>", ("x",)) == pytest.approx(1.5 / 2 + (0.5 / 2) * (2 / 7))


def test_stupid_backoff_is_not_a_probability_distribution():
    bank = CountBank([["a", "b"], ["a", "c"]], max_n=2, min_count=1)
    model = ExtensionLM(bank, 2, "stupid_backoff")
    assert math.fsum(model.score(w, ("a",)) for w in bank.vocabulary) > 1
    result = evaluate_counts(model, {("a", "b"): 1})
    assert result["perplexity"] is None
    assert result["score_cross_entropy"] > 0


def test_split_no_leakage_and_bank_train_only():
    sentences = [[str(i)] for i in range(100)]
    train, dev, test, ids = split_three(sentences, seed=42)
    assert list(map(len, [train, dev, test])) == [80, 10, 10]
    assert not set(ids["train"]) & set(ids["dev"])
    assert not set(ids["train"]) & set(ids["test"])
    assert not set(ids["dev"]) & set(ids["test"])
    bank = CountBank(train, max_n=2, min_count=1)
    assert not set(w for s in test + dev for w in s) & bank.vocab_set


@pytest.mark.parametrize(
    "kwargs", [{"k": 0}, {"discount": 1}, {"weights": [1, 1]}, {"method": "unknown"}]
)
def test_invalid_hyperparameters(kwargs):
    bank = CountBank([["a"]], max_n=2, min_count=1)
    with pytest.raises(ValueError):
        ExtensionLM(bank, 2, **kwargs)
