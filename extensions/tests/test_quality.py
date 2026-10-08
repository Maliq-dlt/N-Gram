from collections import Counter

import pytest

from extensions.src.models import CountBank, ExtensionLM
from extensions.src.quality import Sampler, generation_metrics


def test_distinct_and_repetition_manual():
    result = generation_metrics([["a", "b", "a", "b"], ["a", "c"]])
    assert result["distinct_1"] == 3 / 6
    assert result["distinct_2"] == 3 / 4
    assert result["repeated_bigram_rate"] == 1 / 4


@pytest.mark.parametrize("method", ["add_k", "interpolation", "kneser_ney"])
def test_sampling_matches_distribution_and_is_reproducible(method):
    bank = CountBank([["a", "b"], ["a", "c"]], max_n=2, min_count=1)
    model = ExtensionLM(bank, 2, method, k=0.1)
    sampler = Sampler(model, seed=42)
    observations = Counter(sampler.next_word(("a",)) for _ in range(20000))
    for word in bank.vocabulary:
        assert observations[word] / 20000 == pytest.approx(model.score(word, ("a",)), abs=0.015)
    assert Sampler(model, 42).generate() == Sampler(model, 42).generate()
