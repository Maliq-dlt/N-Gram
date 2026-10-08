import math

import pytest

from core.src.evaluate import perplexity, sentence_log_probability, sentence_probability
from core.src.generate import generate
from core.src.models import NGramLM
from core.src.ngram import events, ngrams
from core.src.preprocess import preprocess, split_sentences


@pytest.mark.parametrize("n", [1, 2, 3])
def test_laplace_normalizes_seen_and_unseen_contexts(n):
    model = NGramLM(n, alpha=1, min_count=1).fit([["a", "b"], ["a", "c"]])
    contexts = list(model.context_counts) + [("never",) * (n - 1)]
    for context in contexts:
        assert sum(model.score(w, context) for w in model.vocabulary) == pytest.approx(1, abs=1e-9)
    assert model.score("<s>", ()) == 0


def test_manual_mle_and_boundaries():
    model = NGramLM(2, min_count=1).fit([["a", "b"], ["a", "c"]])
    assert model.score("a", ("<s>",)) == 1
    assert model.score("b", ("a",)) == 0.5
    assert model.score("</s>", ("b",)) == 1
    assert model.score("c", ("never",)) == 0
    assert model.context_counts[("a",)] == 2
    assert model.counts[("b", "</s>")] == 1
    assert sentence_probability(model, ["a", "b"]) == 0.5
    assert sentence_probability(model, ["b", "a"]) == 0
    assert sentence_log_probability(model, ["b", "a"]) == -math.inf
    trigram = NGramLM(3, min_count=1).fit([["a", "b"], ["a", "c"]])
    assert trigram.score("a", ("<s>", "<s>")) == 1
    assert trigram.score("b", ("<s>", "a")) == 0.5
    assert list(events(["a"], 3)) == [("<s>", "<s>", "a"), ("<s>", "a", "</s>")]


def test_train_only_vocabulary_and_unknown_mapping():
    train = [["common", "rare"], ["common"]]
    test = [["common", "testonly"]]
    model = NGramLM(2, alpha=1, min_count=2).fit(train)
    assert "testonly" not in model.raw_counts
    assert "testonly" not in model.vocabulary
    assert "rare" not in model.vocabulary
    assert model.map_sentence(test[0]) == ["common", "<UNK>"]
    assert model.counts[("common", "<UNK>")] == 1
    assert train == [["common", "rare"], ["common"]]
    assert test == [["common", "testonly"]]


def test_split_indices_disjoint_and_reproducible():
    sentences = [[str(i)] for i in range(50)]
    train, test, train_ids, test_ids = split_sentences(sentences)
    assert len(train) == 40 and len(test) == 10
    assert set(train_ids).isdisjoint(test_ids)
    assert set(train_ids) | set(test_ids) == set(range(50))
    assert split_sentences(sentences) == (train, test, train_ids, test_ids)


@pytest.mark.parametrize("n", [1, 2, 3])
def test_uniform_perplexity_equals_vocabulary_size(n):
    model = NGramLM(n, alpha=1, min_count=1).fit([["a", "b"]])
    model.counts.clear()
    model.context_counts.clear()
    assert perplexity(model, [["a", "b"], ["unknown"]])["perplexity"] == pytest.approx(
        len(model.vocabulary)
    )
    assert perplexity(model, [["a", "b"]])["predicted_tokens"] == 3


def test_product_underflows_log_remains_finite():
    model = NGramLM(2, alpha=1, min_count=1).fit([["a", "b"]])
    sentence = ["a", "b"] * 1000
    assert sentence_probability(model, sentence) == 0
    assert math.isfinite(sentence_log_probability(model, sentence))


def test_preprocessing_and_generic_ngrams():
    processed, dropped = preprocess([["Hello", ",", "WORLD", "123"], ["!"]])
    assert processed == [["hello", "world"]] and dropped == 1
    assert list(ngrams(["a", "b", "c"], 2)) == [("a", "b"), ("b", "c")]
    with pytest.raises(ValueError):
        list(ngrams(["a"], 0))


def test_prediction_and_generation_reproducible():
    model = NGramLM(2, min_count=1).fit([["a", "b"], ["a", "c"]])
    assert model.predict_next("a", 2) == [("b", 0.5), ("c", 0.5)]
    assert generate(model, seed=42) == generate(model, seed=42)
    assert "<s>" not in generate(model, seed=42)


@pytest.mark.parametrize("kwargs", [{"n": 0}, {"n": 2, "alpha": -1}, {"n": 2, "min_count": 0}])
def test_invalid_parameters(kwargs):
    with pytest.raises(ValueError):
        NGramLM(**kwargs)
