"""Shared raw counts and normalized interpolated absolute-discount Kneser-Ney."""

import math
from collections import Counter, defaultdict

from core.src.ngram import events
from core.src.preprocess import BOS, UNK, fit_vocabulary, replace_unknown

METHODS = ("laplace", "add_k", "interpolation", "stupid_backoff", "kneser_ney")
ALL_METHODS = METHODS + ("witten_bell", "modified_kneser_ney", "interpolation_em")


def context_stats(counts):
    totals, types = Counter(), Counter()
    for gram, count in counts.items():
        totals[gram[:-1]] += count
        types[gram[:-1]] += 1
    return totals, types


class CountBank:
    def __init__(self, train, max_n=4, min_count=2):
        if not train or not any(train) or not 1 <= max_n <= 4:
            raise ValueError("Corpus tidak kosong; max_n antara 1 dan 4")
        self.max_n, self.min_count = max_n, min_count
        self.vocab_set, self.raw_word_counts = fit_vocabulary(train, min_count)
        self.vocab_set.discard(BOS)
        self.vocabulary = tuple(sorted(self.vocab_set))
        mapped = replace_unknown(train, self.vocab_set)
        self.raw = {
            n: Counter(g for s in mapped for g in events(s, n)) for n in range(1, max_n + 1)
        }
        self._index_counts()

    def _index_counts(self):
        stats = {n: context_stats(counts) for n, counts in self.raw.items()}
        self.totals = {n: v[0] for n, v in stats.items()}
        self.types = {n: v[1] for n, v in stats.items()}
        # C_cont(g) = number of distinct left extensions, not token frequency.
        self.continuation = {
            n: Counter(g[1:] for g in self.raw[n + 1]) for n in range(1, self.max_n)
        }
        cont_stats = {n: context_stats(counts) for n, counts in self.continuation.items()}
        self.cont_totals = {n: v[0] for n, v in cont_stats.items()}
        self.cont_types = {n: v[1] for n, v in cont_stats.items()}

    @classmethod
    def from_counts(cls, vocabulary, raw, min_count):
        if not isinstance(vocabulary, list) or any(not isinstance(w, str) for w in vocabulary):
            raise ValueError("Vocabulary harus list string")
        if len(set(vocabulary)) != len(vocabulary) or BOS in vocabulary:
            raise ValueError("Vocabulary duplicate/BOS tidak valid")
        if not {UNK, "</s>"} <= set(vocabulary) or not raw or len(raw) > 4:
            raise ValueError("Vocabulary/order artifact tidak valid")
        if set(raw) != set(range(1, len(raw) + 1)):
            raise ValueError("Counts harus memuat semua orde 1..n")
        if type(min_count) is not int or min_count < 1:
            raise ValueError("min_count tidak valid")
        allowed = set(vocabulary) | {BOS}
        for n, counts in raw.items():
            if not counts:
                raise ValueError("Counts kosong")
            for gram, count in counts.items():
                if (
                    len(gram) != n
                    or gram[-1] not in allowed
                    or gram[-1] == BOS
                    or any(w not in allowed for w in gram)
                ):
                    raise ValueError("N-gram artifact tidak valid")
                if type(count) is not int or count <= 0:
                    raise ValueError("Count harus positive integer")
        if len({sum(c.values()) for c in raw.values()}) != 1:
            raise ValueError("Total event antar orde tidak konsisten")
        bank = object.__new__(cls)
        bank.max_n, bank.min_count = len(raw), min_count
        bank.vocabulary, bank.vocab_set = tuple(sorted(vocabulary)), set(vocabulary)
        bank.raw, bank.raw_word_counts = raw, Counter()
        bank._index_counts()
        return bank

    def map_sentence(self, sentence):
        return [w if w in self.vocab_set else UNK for w in sentence]

    def event_counts(self, sentences, n):
        return Counter(g for s in sentences for g in events(self.map_sentence(s), n))


class ExtensionLM:
    def __init__(
        self,
        bank,
        n,
        method="add_k",
        k=0.01,
        discount=0.75,
        weights=None,
        backoff=0.4,
        epsilon=1e-8,
    ):
        if not 1 <= n <= bank.max_n or method not in ALL_METHODS:
            raise ValueError("Orde/metode tidak valid")
        if not math.isfinite(k) or k <= 0 or not 0 < discount < 1:
            raise ValueError("k >0 finite; discount antara 0 dan 1")
        if not 0 < backoff < 1 or not math.isfinite(epsilon) or epsilon < 0:
            raise ValueError("backoff antara 0 dan 1; epsilon finite >=0")
        weights = tuple(weights) if weights is not None else (1 / n,) * n
        if len(weights) != n or any(not math.isfinite(x) or x < 0 for x in weights):
            raise ValueError("Weights finite, nonnegative, satu per orde")
        if not math.isclose(sum(weights), 1, abs_tol=1e-9):
            raise ValueError("Jumlah weights harus 1")
        self.bank, self.n, self.method = bank, n, method
        self.k, self.discount, self.weights = k, discount, weights
        self.backoff, self.epsilon = backoff, epsilon
        self.vocabulary, self.vocab_set = bank.vocabulary, bank.vocab_set
        self.mkn_discounts, self.mkn_mass = {}, {}
        if method == "modified_kneser_ney":
            for order in range(2, n + 1):
                counts = bank.raw[order] if order == n else bank.continuation[order]
                frequencies = Counter(counts.values())
                fallback = None
                if all(frequencies[c] for c in (1, 2, 3, 4)):
                    y = frequencies[1] / (frequencies[1] + 2 * frequencies[2])
                    discounts = tuple(
                        c - (c + 1) * y * frequencies[c + 1] / frequencies[c] for c in (1, 2, 3)
                    )
                    if any(
                        not math.isfinite(d) or not 0 < d < c for c, d in enumerate(discounts, 1)
                    ):
                        fallback = "invalid count-of-counts estimate"
                else:
                    fallback = "sparse count-of-counts (requires N1..N4)"
                if fallback:
                    discounts = (0.75, 0.75, 0.75)
                self.mkn_discounts[order] = {
                    "discounts": discounts,
                    "count_of_counts": {c: frequencies[c] for c in (1, 2, 3, 4)},
                    "fallback": fallback,
                }
                mass = defaultdict(float)
                for gram, count in counts.items():
                    mass[gram[:-1]] += discounts[min(count, 3) - 1]
                self.mkn_mass[order] = mass

    def map_sentence(self, sentence):
        return self.bank.map_sentence(sentence)

    def score(self, word, context=()):
        if word == BOS:
            return 0.0
        word = word if word in self.vocab_set else UNK
        ctx = context.split() if isinstance(context, str) else list(context)
        ctx = [w if w in self.vocab_set or w == BOS else UNK for w in ctx]
        ctx = tuple(([BOS] * (self.n - 1) + ctx)[-(self.n - 1) :]) if self.n > 1 else ()
        return self.score_mapped(word, ctx)

    def _add(self, word, context, order, k):
        ctx = context[-(order - 1) :] if order > 1 else ()
        return (self.bank.raw[order][ctx + (word,)] + k) / (
            self.bank.totals[order][ctx] + k * len(self.vocabulary)
        )

    def score_mapped(self, word, context):
        if self.method not in METHODS and word == BOS:
            return 0.0
        if self.method in ("laplace", "add_k"):
            return self._add(word, context, self.n, 1 if self.method == "laplace" else self.k)
        if self.method in ("interpolation", "interpolation_em"):
            return math.fsum(
                weight * self._add(word, context, order, self.k)
                for order, weight in enumerate(self.weights, 1)
            )
        if self.method == "stupid_backoff":
            factor = 1.0
            for order in range(self.n, 1, -1):
                ctx = context[-(order - 1) :]
                count = self.bank.raw[order][ctx + (word,)]
                if count:
                    return factor * count / self.bank.totals[order][ctx]
                factor *= self.backoff
            return factor * self._add(word, (), 1, self.epsilon or 1e-8)
        if self.method == "witten_bell":
            return 0.0 if word == BOS else self._wb(word, context, self.n)
        return self._kn(word, context, self.n)

    def _wb(self, word, context, order):
        if order == 1:
            return self._add(word, (), 1, self.epsilon)
        ctx = context[-(order - 1) :]
        total, types = self.bank.totals[order][ctx], self.bank.types[order][ctx]
        lower = self._wb(word, context, order - 1)
        if not total:
            return lower
        return (self.bank.raw[order][ctx + (word,)] + types * lower) / (total + types)

    def _kn(self, word, context, order):
        if order == 1:
            # KN unigram baseline = raw unigram; higher-order KN = continuation base.
            counts = self.bank.continuation[1] if self.n > 1 else self.bank.raw[1]
            totals = self.bank.cont_totals[1] if self.n > 1 else self.bank.totals[1]
            denominator = totals[()] + self.epsilon * len(self.vocabulary)
            return (counts[(word,)] + self.epsilon) / denominator
        top = order == self.n
        counts = self.bank.raw[order] if top else self.bank.continuation[order]
        totals = self.bank.totals[order] if top else self.bank.cont_totals[order]
        types = self.bank.types[order] if top else self.bank.cont_types[order]
        ctx = context[-(order - 1) :]
        lower = self._kn(word, context, order - 1)
        total = totals[ctx]
        if not total:
            return lower
        if self.method == "modified_kneser_ney":
            count = counts[ctx + (word,)]
            discounts = self.mkn_discounts[order]["discounts"]
            direct = max(count - discounts[min(count, 3) - 1], 0) / total if count else 0.0
            return direct + self.mkn_mass[order][ctx] / total * lower
        direct = max(counts[ctx + (word,)] - self.discount, 0) / total
        return direct + self.discount * types[ctx] / total * lower


def evaluate_counts(model, event_counts):
    count = sum(event_counts.values())
    if not count:
        raise ValueError("Evaluation corpus kosong")
    terms = []
    for gram, frequency in event_counts.items():
        probability = model.score_mapped(gram[-1], gram[:-1])
        terms.append(-frequency * math.log(probability) if probability else math.inf)
    cross_entropy = math.fsum(terms) / count
    pp = math.exp(cross_entropy) if cross_entropy < 709 else math.inf
    return {
        "perplexity": None if model.method == "stupid_backoff" else pp,
        "score_cross_entropy": cross_entropy,
        "predicted_tokens": count,
    }
