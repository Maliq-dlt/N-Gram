"""Disjoint sentence split and dev-only hyperparameter selection."""

import random

from .models import ExtensionLM, evaluate_counts


def split_three(sentences, seed=42):
    if len(sentences) < 10:
        raise ValueError("80/10/10 memerlukan >=10 kalimat")
    indices = list(range(len(sentences)))
    random.Random(seed).shuffle(indices)
    a, b = int(len(indices) * 0.8), int(len(indices) * 0.9)
    ids = {"train": indices[:a], "dev": indices[a:b], "test": indices[b:]}
    assert not set(ids["train"]) & set(ids["dev"])
    assert not set(ids["train"]) & set(ids["test"])
    assert not set(ids["dev"]) & set(ids["test"])
    return (*([sentences[i] for i in ids[key]] for key in ("train", "dev", "test")), ids)


def candidates(n, method):
    if method == "add_k":
        return [{"k": k} for k in (0.001, 0.01, 0.1, 0.5)]
    if method == "kneser_ney":
        return [{"discount": d} for d in (0.5, 0.75, 0.9)]
    if method == "interpolation" and n > 1:
        return [
            {"weights": weights}
            for weights in [
                [1 / n] * n,
                [0.3 / (n - 1)] * (n - 1) + [0.7],
                [0.7] + [0.3 / (n - 1)] * (n - 1),
            ]
        ]
    return [{}]


def tune(bank, n, method, dev_counts):
    trials = []
    for parameters in candidates(n, method):
        model = ExtensionLM(bank, n, method, **parameters)
        loss = evaluate_counts(model, dev_counts)["score_cross_entropy"]
        trials.append({"parameters": parameters, "dev_loss": loss})
    winner = min(trials, key=lambda trial: trial["dev_loss"])
    return ExtensionLM(bank, n, method, **winner["parameters"]), winner, trials
