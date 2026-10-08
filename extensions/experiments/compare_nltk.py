"""Phase 2.5: NLTK sanity check on 1,000 training sentences, identical event counts."""

import math
import random

from nltk.lm import KneserNeyInterpolated, Vocabulary

from core.src.data import load_corpus
from core.src.ngram import events
from core.src.preprocess import BOS, preprocess
from extensions.experiments.run import OUT, assert_core_frozen, dump
from extensions.src.models import CountBank, ExtensionLM
from extensions.src.pipeline import split_three


def compare(train):
    bank = CountBank(train, max_n=3, min_count=2)
    mapped = [bank.map_sentence(s) for s in train]
    rows = []
    for n in (2, 3):
        text = [[g for order in range(1, n + 1) for g in events(s, order)] for s in mapped]
        external = KneserNeyInterpolated(
            n, discount=0.75, vocabulary=Vocabulary(list(bank.vocabulary) + [BOS], unk_cutoff=1)
        )
        external.fit(text)
        ours = ExtensionLM(bank, n, "kneser_ney", discount=0.75, epsilon=0)
        floored = ExtensionLM(bank, n, "kneser_ney", discount=0.75, epsilon=1e-8)
        queries = list(bank.raw[n])[:1000]
        rng = random.Random(42)
        contexts = list(bank.totals[n])
        queries += [rng.choice(contexts) + (rng.choice(bank.vocabulary),) for _ in range(1000)]
        differences = [
            abs(ours.score_mapped(g[-1], g[:-1]) - external.score(g[-1], g[:-1])) for g in queries
        ]
        floor_diff = [
            abs(floored.score_mapped(g[-1], g[:-1]) - ours.score_mapped(g[-1], g[:-1]))
            for g in queries
        ]
        max_diff = max(differences)
        assert max_diff < 1e-12, (n, max_diff)
        rows.append(
            {
                "n": n,
                "queries": len(queries),
                "max_absolute_difference": max_diff,
                "mean_absolute_difference": math.fsum(differences) / len(differences),
                "default_epsilon_max_difference": max(floor_diff),
                "V_targets": len(bank.vocabulary),
            }
        )
    return rows


def main():
    assert_core_frozen()
    sentences, _ = preprocess(load_corpus("brown"))
    train, _, _, _ = split_three(sentences, 42)
    rows = compare(train[:1000])
    dump(
        OUT / "nltk_comparison.json",
        {
            "training_sentences": 1000,
            "discount": 0.75,
            "padding": "independent events for each order; no BOS target counts",
            "epsilon": "0 for exact comparison; 1e-8 measured separately",
            "rows": rows,
        },
    )
    print(rows)
    assert_core_frozen()


if __name__ == "__main__":
    main()
