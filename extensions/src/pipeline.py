"""Disjoint sentence split and dev-only hyperparameter selection."""

import math
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


def fit_interpolation_em(bank, n, dev_counts, max_iterations=200, tolerance=1e-10):
    """Fit global add-k component weights on dev event frequencies only."""
    if (
        type(max_iterations) is not int
        or max_iterations < 1
        or not math.isfinite(tolerance)
        or tolerance < 0
    ):
        raise ValueError("EM requires positive iteration cap and finite nonnegative tolerance")
    if not dev_counts or any(type(f) is not int or f <= 0 for f in dev_counts.values()):
        raise ValueError("Dev event frequencies must be positive integers")
    model = ExtensionLM(bank, n, "interpolation_em")
    rows = []
    for gram, frequency in dev_counts.items():
        if (
            not isinstance(gram, tuple)
            or len(gram) != n
            or gram[-1] not in bank.vocab_set
            or any(w not in bank.vocab_set and w != "<s>" for w in gram[:-1])
        ):
            raise ValueError("Dev events must use the model order and mapped vocabulary")
        rows.append(
            (
                frequency,
                tuple(model._add(gram[-1], gram[:-1], order, model.k) for order in range(1, n + 1)),
            )
        )
    total = sum(dev_counts.values())
    weights = model.weights

    def loss(values):
        return (
            -math.fsum(
                f * math.log(math.fsum(w * p for w, p in zip(values, probabilities)))
                for f, probabilities in rows
            )
            / total
        )

    previous = loss(weights)
    trace = [{"iteration": 0, "weights": weights, "dev_loss": previous}]
    for iteration in range(1, max_iterations + 1):
        expected = [0.0] * n
        for frequency, probabilities in rows:
            mixture = math.fsum(w * p for w, p in zip(weights, probabilities))
            for j, probability in enumerate(probabilities):
                expected[j] += frequency * weights[j] * probability / mixture
        denominator = math.fsum(expected)
        weights = tuple(value / denominator for value in expected)
        current = loss(weights)
        if current > previous + 1e-12:
            raise ArithmeticError("EM dev loss increased")
        trace.append({"iteration": iteration, "weights": weights, "dev_loss": current})
        if previous - current <= tolerance:
            break
        previous = current
    return ExtensionLM(bank, n, "interpolation_em", weights=weights), trace


def tune(bank, n, method, dev_counts):
    if method == "interpolation_em":
        model, trace = fit_interpolation_em(bank, n, dev_counts)
        winner = {
            "parameters": {"weights": model.weights},
            "dev_loss": trace[-1]["dev_loss"],
            "em_trace": trace,
        }
        return model, winner, [winner]
    trials = []
    for parameters in candidates(n, method):
        model = ExtensionLM(bank, n, method, **parameters)
        loss = evaluate_counts(model, dev_counts)["score_cross_entropy"]
        trials.append({"parameters": parameters, "dev_loss": loss})
    winner = min(trials, key=lambda trial: trial["dev_loss"])
    return ExtensionLM(bank, n, method, **winner["parameters"]), winner, trials
