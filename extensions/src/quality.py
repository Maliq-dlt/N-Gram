"""Exact mixture sampling and transparent lexical generation metrics."""

import itertools
import random
from collections import Counter, defaultdict

from core.src.ngram import ngrams
from core.src.preprocess import BOS, EOS


class Sampler:
    def __init__(self, model, seed=42):
        self.model = model
        self.rng = random.Random(seed)
        self.raw = (
            {n: self._tables(model.bank.raw[n]) for n in range(1, model.n + 1)}
            if model.method != "kneser_ney" or model.n == 1
            else {}
        )
        self.cont = (
            {
                n: self._tables(model.bank.continuation[n], model.discount if n > 1 else 0)
                for n in range(1, model.n)
            }
            if model.method == "kneser_ney"
            else {}
        )
        self.discounted = (
            self._tables(model.bank.raw[model.n], model.discount)
            if model.method == "kneser_ney" and model.n > 1
            else {}
        )
        self.backoff_cache = {}

    @staticmethod
    def _tables(counts, discount=0):
        grouped = defaultdict(list)
        for gram, count in counts.items():
            grouped[gram[:-1]].append((gram[-1], count - discount))
        return {
            ctx: (tuple(w for w, _ in pairs), tuple(itertools.accumulate(c for _, c in pairs)))
            for ctx, pairs in grouped.items()
        }

    def _draw(self, table):
        words, cumulative = table
        return self.rng.choices(words, cum_weights=cumulative, k=1)[0]

    def _add(self, context, order, k, tables):
        ctx = context[-(order - 1) :] if order > 1 else ()
        table = tables[order].get(ctx)
        count = table[1][-1] if table else 0
        if self.rng.random() * (count + k * len(self.model.vocabulary)) < count:
            return self._draw(table)
        return self.rng.choice(self.model.vocabulary)

    def _kn(self, context, order):
        if order == 1:
            tables = self.cont if self.model.n > 1 else self.raw
            return self._add((), 1, self.model.epsilon, tables)
        ctx = context[-(order - 1) :]
        top = order == self.model.n
        totals = self.model.bank.totals[order] if top else self.model.bank.cont_totals[order]
        table = (self.discounted if top else self.cont[order]).get(ctx)
        if table and self.rng.random() * totals[ctx] < table[1][-1]:
            return self._draw(table)
        return self._kn(context, order - 1)

    def next_word(self, context):
        model = self.model
        if model.method in ("add_k", "laplace"):
            return self._add(
                context, model.n, 1 if model.method == "laplace" else model.k, self.raw
            )
        if model.method == "interpolation":
            order = self.rng.choices(range(1, model.n + 1), weights=model.weights, k=1)[0]
            return self._add(context, order, model.k, self.raw)
        if model.method == "kneser_ney":
            return self._kn(context, model.n)
        # Raw Stupid Backoff scores normalized only for sampling, not PP evaluation.
        if context not in self.backoff_cache:
            probabilities = [model.score_mapped(w, context) for w in model.vocabulary]
            self.backoff_cache[context] = (
                model.vocabulary,
                tuple(itertools.accumulate(probabilities)),
            )
        return self._draw(self.backoff_cache[context])

    def generate(self, max_length=40):
        if max_length < 1:
            raise ValueError("max_length harus >=1")
        output = []
        for _ in range(max_length):
            context = (
                tuple(([BOS] * (self.model.n - 1) + output)[-(self.model.n - 1) :])
                if self.model.n > 1
                else ()
            )
            word = self.next_word(context)
            if word == EOS:
                return output
            output.append(word)
        return output


def generation_metrics(sentences, max_length=40):
    unigram = Counter(g for s in sentences for g in ngrams(s, 1))
    bigram = Counter(g for s in sentences for g in ngrams(s, 2))
    total1, total2 = sum(unigram.values()), sum(bigram.values())
    repetitions = sum(sum(c - 1 for c in Counter(ngrams(s, 2)).values()) for s in sentences)
    return {
        "sentences": len(sentences),
        "tokens": total1,
        "distinct_1": len(unigram) / total1 if total1 else 0,
        "distinct_2": len(bigram) / total2 if total2 else 0,
        "repeated_bigram_rate": repetitions / total2 if total2 else 0,
        "UNK_rate": sum(s.count("<UNK>") for s in sentences) / total1 if total1 else 0,
        "mean_length": total1 / len(sentences) if sentences else 0,
        "max_length_rate": sum(len(s) == max_length for s in sentences) / len(sentences)
        if sentences
        else 0,
    }
