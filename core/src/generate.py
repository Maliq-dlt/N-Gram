"""Sampling from the exact add-alpha mixture, including EOS."""

import random

from .preprocess import BOS, EOS


def generate(model, seed=42, max_length=40):
    if max_length < 1:
        raise ValueError("max_length harus >=1")
    if not model.vocabulary:
        raise ValueError("Model belum dilatih")
    rng = random.Random(seed)
    output = []
    context = [BOS] * (model.n - 1)
    for _ in range(max_length):
        ctx = model.context(context)
        followers = model.followers.get(ctx, {})
        observed = sum(followers.values())
        mass = observed + model.alpha * len(model.vocabulary)
        if not mass:
            break
        if rng.random() * mass < observed:
            word = rng.choices(list(followers), weights=list(followers.values()), k=1)[0]
        else:
            word = rng.choice(model.vocabulary)
        if word == EOS:
            break
        output.append(word)
        context.append(word)
    return output
