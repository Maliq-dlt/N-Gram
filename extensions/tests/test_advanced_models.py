"""Independent count examples, normalization and dev-only EM guarantees."""

import math
from collections import Counter

import pytest

from core.src.preprocess import BOS, UNK
from extensions.src.models import ALL_METHODS, METHODS, CountBank, ExtensionLM
from extensions.src.pipeline import fit_interpolation_em, tune

NEW = ("witten_bell", "modified_kneser_ney", "interpolation_em")


def test_baseline_method_registry_unchanged():
    assert METHODS == ("laplace", "add_k", "interpolation", "stupid_backoff", "kneser_ney")
    assert ALL_METHODS == METHODS + NEW


@pytest.mark.parametrize("n", [1, 2, 3, 4])
@pytest.mark.parametrize("method", NEW)
def test_new_models_normalized_boundaries_unknowns(n, method):
    bank = CountBank([["a", "x"], ["a", "y"], ["b", "x"], ["rare"]], max_n=4)
    model = ExtensionLM(bank, n, method)
    for context in ([], [BOS] * (n - 1), ["a"], ["never", "seen"], ["</s>"]):
        scores = [model.score(word, context) for word in bank.vocabulary]
        assert all(math.isfinite(p) and p >= 0 for p in scores)
        assert sum(scores) == pytest.approx(1, abs=1e-12)
        assert model.score(BOS, context) == 0
        assert model.score_mapped(BOS, tuple(context)) == 0
        assert model.score("outside", context) == model.score(UNK, context)
    assert model.score(UNK, []) > 0


def test_witten_bell_manual_interpolation_and_base():
    bank = CountBank([["a", "x"], ["a", "y"]], max_n=2, min_count=1)
    model = ExtensionLM(bank, 2, "witten_bell", epsilon=0)
    # Raw unigram P(x)=1/6. Context a has N=2,T=2; (1 + 2/6)/(2+2)=1/3.
    assert model.score("x", ["a"]) == pytest.approx(1 / 3)
    assert model.score("x", ["unseen"]) == pytest.approx(1 / 6)
    assert ExtensionLM(bank, 1, "witten_bell", epsilon=0).score("</s>") == pytest.approx(2 / 6)


def test_mkn_manual_three_discounts_and_context_mass():
    train = []
    for frequency, number in [(1, 8), (2, 4), (3, 2), (4, 1)]:
        for index in range(number):
            train.extend([["c", f"w{frequency}_{index}"]] * frequency)
    bank = CountBank(train, max_n=2, min_count=1)
    model = ExtensionLM(bank, 2, "modified_kneser_ney", epsilon=0)
    # Bigram N1=16,N2=8,N3=4,N4=2; Y=1/2 => D1=.5,D2=1.25,D3+=2.
    assert model.mkn_discounts[2]["discounts"] == pytest.approx((0.5, 1.25, 2))
    assert model.mkn_discounts[2]["fallback"] is None
    # Context c: total26; buckets(8,4,3), mass=.5*8+1.25*4+2*3=15.
    # 31 distinct bigrams; continuation P(w1_0)=1/31.
    assert model.mkn_mass[2][("c",)] == 15
    assert model.score("w1_0", ["c"]) == pytest.approx(0.5 / 26 + 15 / 26 / 31)
    assert sum(model.score(w, ["c"]) for w in bank.vocabulary) == pytest.approx(1)


def test_mkn_fallback_recorded_and_reconstructed():
    bank = CountBank([["a", "x"], ["a", "y"]], max_n=3, min_count=1)
    model = ExtensionLM(bank, 3, "modified_kneser_ney")
    assert all(record["fallback"] for record in model.mkn_discounts.values())
    assert all(record["discounts"] == (0.75, 0.75, 0.75) for record in model.mkn_discounts.values())
    restored_bank = CountBank.from_counts(list(bank.vocabulary), bank.raw, bank.min_count)
    restored = ExtensionLM(restored_bank, 3, "modified_kneser_ney")
    assert restored.mkn_discounts == model.mkn_discounts
    for word in bank.vocabulary:
        assert restored.score(word, ["a"]) == model.score(word, ["a"])


def test_em_dev_frequency_monotonicity_cap_and_serializable_weights():
    bank = CountBank([["a", "x"], ["b", "y"], ["a", "y"]], max_n=2, min_count=1)
    before = {n: counts.copy() for n, counts in bank.raw.items()}
    dev = Counter({("a", "x"): 100, ("b", "x"): 1})
    model, trace = fit_interpolation_em(bank, 2, dev, max_iterations=7, tolerance=0)
    assert 2 <= len(trace) <= 8
    assert all(b["dev_loss"] <= a["dev_loss"] + 1e-12 for a, b in zip(trace, trace[1:]))
    assert model.weights != (0.5, 0.5)
    assert all(w >= 0 for w in model.weights) and sum(model.weights) == pytest.approx(1)
    assert bank.raw == before
    assert trace[-1]["weights"] == model.weights
    restored = ExtensionLM(bank, 2, "interpolation_em", weights=model.weights)
    assert restored.score("x", ["a"]) == model.score("x", ["a"])
    tuned, winner, trials = tune(bank, 2, "interpolation_em", dev)
    assert winner["parameters"]["weights"] == tuned.weights
    assert winner["em_trace"] == trials[0]["em_trace"]
    reverse, _ = fit_interpolation_em(bank, 2, Counter({("b", "x"): 100}))
    assert reverse.weights != tuned.weights


@pytest.mark.parametrize(
    "counts,cap,tol",
    [
        ({}, 1, 0),
        ({("a", "x"): 0}, 1, 0),
        ({("a", "x"): 1}, 0, 0),
        ({("a", "x"): 1}, 1, float("nan")),
        ({("a", "unknown"): 1}, 1, 0),
    ],
)
def test_em_rejects_invalid_dev_events(counts, cap, tol):
    bank = CountBank([["a", "x"]], max_n=2, min_count=1)
    with pytest.raises(ValueError):
        fit_interpolation_em(bank, 2, counts, max_iterations=cap, tolerance=tol)


def test_mkn_invalid_estimate_fallback_and_lower_continuation_statistics():
    train = [["c", "one"], ["c", "two"], ["c", "two"]]
    train += [["c", "three"]] * 3
    for i in range(100):
        train += [["c", f"four{i}"]] * 4
    bank = CountBank(train, max_n=3, min_count=1)
    bigram = ExtensionLM(bank, 2, "modified_kneser_ney")
    assert bigram.mkn_discounts[2]["fallback"] == "invalid count-of-counts estimate"
    assert bigram.mkn_discounts[2]["discounts"] == (0.75, 0.75, 0.75)
    trigram = ExtensionLM(bank, 3, "modified_kneser_ney")
    frequencies = Counter(bank.continuation[2].values())
    assert trigram.mkn_discounts[2]["count_of_counts"] == {
        count: frequencies[count] for count in (1, 2, 3, 4)
    }
