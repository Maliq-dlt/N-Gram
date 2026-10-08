"""Natural-log likelihood; EOS counted, BOS never predicted."""

import math

from .ngram import events


def sentence_probability(model, sentence):
    return math.prod(
        model.score(g[-1], g[:-1]) for g in events(model.map_sentence(sentence), model.n)
    )


def sentence_log_probability(model, sentence):
    probabilities = [
        model.score(g[-1], g[:-1]) for g in events(model.map_sentence(sentence), model.n)
    ]
    return math.fsum(math.log(p) for p in probabilities) if all(probabilities) else -math.inf


def perplexity(model, sentences):
    total_log = 0.0
    count = 0
    for sentence in sentences:
        total_log += sentence_log_probability(model, sentence)
        count += len(sentence) + 1
    if not count:
        raise ValueError("Test corpus kosong")
    cross_entropy = -total_log / count
    value = math.exp(cross_entropy) if cross_entropy < 709 else math.inf
    return {"perplexity": value, "predicted_tokens": count, "log_likelihood": total_log}
