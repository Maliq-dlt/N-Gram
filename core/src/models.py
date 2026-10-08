"""Maximum likelihood and add-alpha language models, built from Counter."""

import math
from collections import Counter, defaultdict

from .ngram import events
from .preprocess import BOS, EOS, UNK, fit_vocabulary, replace_unknown


class NGramLM:
    def __init__(self, n, alpha=0.0, min_count=2):
        if n < 1 or min_count < 1 or not math.isfinite(alpha) or alpha < 0:
            raise ValueError("n/min_count >=1; alpha finite dan >=0")
        self.n, self.alpha, self.min_count = n, float(alpha), min_count
        self.vocabulary = ()
        self.vocab_set = set()
        self.counts = Counter()
        self.context_counts = Counter()
        self.followers = defaultdict(Counter)
        self.raw_counts = Counter()

    def fit(self, train, vocabulary=None):
        if not train or not any(train):
            raise ValueError("Training corpus kosong")
        fitted, self.raw_counts = fit_vocabulary(train, self.min_count)
        self.vocab_set = set(fitted if vocabulary is None else vocabulary) | {UNK, EOS}
        self.vocab_set.discard(BOS)
        self.vocabulary = tuple(sorted(self.vocab_set))
        self.counts.clear()
        self.context_counts.clear()
        self.followers.clear()
        for sentence in replace_unknown(train, self.vocab_set):
            for gram in events(sentence, self.n):
                self.counts[gram] += 1
                self.context_counts[gram[:-1]] += 1
                self.followers[gram[:-1]][gram[-1]] += 1
        return self

    def map_sentence(self, sentence):
        return [w if w in self.vocab_set else UNK for w in sentence]

    def context(self, context):
        tokens = context.split() if isinstance(context, str) else list(context)
        if self.n == 1:
            return ()
        tokens = [w if w in self.vocab_set or w == BOS else UNK for w in tokens]
        return tuple(([BOS] * (self.n - 1) + tokens)[-(self.n - 1) :])

    def score(self, word, context=()):
        if not self.vocabulary:
            raise ValueError("Model belum dilatih")
        if word == BOS:
            return 0.0
        word = word if word in self.vocab_set else UNK
        ctx = self.context(context)
        denominator = self.context_counts[ctx] + self.alpha * len(self.vocabulary)
        return (self.counts[ctx + (word,)] + self.alpha) / denominator if denominator else 0.0

    def predict_next(self, context, k=5):
        if k < 1:
            raise ValueError("k harus >=1")
        return sorted(
            ((w, self.score(w, context)) for w in self.vocabulary),
            key=lambda pair: (-pair[1], pair[0]),
        )[:k]

    def assert_laplace_normalized(self, tolerance=1e-9):
        if self.alpha <= 0:
            raise ValueError("Pemeriksaan memerlukan alpha >0")
        size = len(self.vocabulary)
        for context, count in self.context_counts.items():
            seen = self.followers[context]
            denominator = count + self.alpha * size
            # Group equal unseen probabilities instead of enumerating V for every context.
            total = math.fsum((c + self.alpha) / denominator for c in seen.values())
            total += (size - len(seen)) * self.alpha / denominator
            assert abs(total - 1.0) <= tolerance, (context, total)
        assert abs(size * (1.0 / size) - 1) <= tolerance  # all unseen contexts
        return len(self.context_counts)
