"""N-grams never cross sentence boundaries."""

from .preprocess import BOS, EOS


def ngrams(tokens, n):
    if n < 1:
        raise ValueError("n harus >=1")
    for i in range(len(tokens) - n + 1):
        yield tuple(tokens[i : i + n])


def add_boundaries(tokens, n=2):
    if n < 1:
        raise ValueError("n harus >=1")
    return [BOS] * (n - 1) + list(tokens) + [EOS]


def events(tokens, n):
    yield from ngrams(add_boundaries(tokens, n), n)
