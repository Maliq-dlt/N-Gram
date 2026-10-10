"""Token-weighted diagnostics, paired document bootstrap and bounded ranking evaluation."""

import math
import time
from collections import Counter, defaultdict

import numpy as np

from core.src.ngram import events, ngrams
from core.src.preprocess import UNK


def top_k(model, context, k=5, prefix=""):
    if type(k) is not int or not 1 <= k <= 50:
        raise ValueError("k must be 1..50")
    if not isinstance(prefix, str) or len(prefix) > 256:
        raise ValueError("Invalid prefix")
    # ponytail: exact vocabulary scan; add a prefix index only after latency measurement.
    scored = (
        (word, model.score(word, context)) for word in model.vocabulary if word.startswith(prefix)
    )
    return [
        {"word": word, "probability": probability}
        for word, probability in sorted(scored, key=lambda item: (-item[1], item[0]))[:k]
    ]


def document_losses(model, documents):
    rows = []
    for doc in documents:
        nll, count, unknown, tokens = 0.0, 0, 0, 0
        for sentence in doc["sentences"]:
            mapped = model.map_sentence(sentence)
            unknown += sum(a != b for a, b in zip(sentence, mapped))
            tokens += len(sentence)
            for gram in events(mapped, model.n):
                probability = model.score_mapped(gram[-1], gram[:-1])
                nll += -math.log(probability) if probability > 0 else math.inf
                count += 1
        rows.append(
            {
                "id": doc["id"],
                "group_id": doc.get("split_group", doc.get("group", doc["id"])),
                "nll": nll,
                "predicted_tokens": count,
                "oov_rate": unknown / tokens if tokens else 0,
                "genre": doc.get("genre", "unknown"),
            }
        )
    return rows


def aggregate(rows, probabilistic=True):
    count = sum(row["predicted_tokens"] for row in rows)
    if not count:
        raise ValueError("Empty evaluation")
    nll = math.fsum(row["nll"] for row in rows)
    ce = nll / count
    return {
        "predicted_tokens": count,
        "nll": nll if math.isfinite(nll) else None,
        "cross_entropy": ce if math.isfinite(ce) else None,
        "perplexity": math.exp(ce) if probabilistic and ce < 709 else None,
        "zero_probability": not math.isfinite(nll),
        "probabilistic": probabilistic,
    }


def paired_bootstrap(rows_a, rows_b, seed=42, resamples=1000):
    if type(resamples) is not int or not 100 <= resamples <= 100000:
        raise ValueError("resamples must be 100..100000")
    left, right = {r["id"]: r for r in rows_a}, {r["id"]: r for r in rows_b}
    if (
        not left
        or len(left) != len(rows_a)
        or len(right) != len(rows_b)
        or left.keys() != right.keys()
    ):
        raise ValueError("Paired unique document IDs required")
    keys = sorted(left)
    for key in keys:
        if (
            left[key]["predicted_tokens"] != right[key]["predicted_tokens"]
            or left[key]["predicted_tokens"] <= 0
        ):
            raise ValueError("Paired target tokens must match")
    groups = defaultdict(lambda: [0.0, 0])
    for key in keys:
        group = left[key].get("group_id", key)
        if group != right[key].get("group_id", key):
            raise ValueError("Paired independent groups must match")
        groups[group][0] += left[key]["nll"] - right[key]["nll"]
        groups[group][1] += left[key]["predicted_tokens"]
    differences = np.array([groups[g][0] for g in sorted(groups)], dtype=float)
    counts = np.array([groups[g][1] for g in sorted(groups)], dtype=float)
    if not np.isfinite(differences).all():
        raise ValueError("Finite paired losses required")
    rng = np.random.default_rng(seed)
    samples = []
    for _ in range(resamples):
        indices = rng.integers(0, len(groups), len(groups))
        samples.append(float(differences[indices].sum() / counts[indices].sum()))
    low, high = np.quantile(samples, [0.025, 0.975])
    return {
        "metric": "paired token-weighted CE difference (A minus B)",
        "difference": float(differences.sum() / counts.sum()),
        "ci95": [float(low), float(high)],
        "documents": len(keys),
        "independent_groups": len(groups),
        "resamples": resamples,
        "seed": seed,
        "unit": "duplicate/source group; paired resampling",
    }


def autocomplete_metrics(model, documents, limit=100):
    if type(limit) is not int or not 1 <= limit <= 10000:
        raise ValueError("limit must be 1..10000")
    matched, ranks, truncated_ranks, latencies, oov, queried = Counter(), [], [], [], 0, 0
    for doc in sorted(documents, key=lambda d: d["id"]):
        for sentence in doc["sentences"]:
            for pos, target in enumerate(sentence):
                if queried >= limit:
                    break
                queried += 1
                if target not in model.vocab_set:
                    oov += 1
                start = time.perf_counter()
                ranking = sorted(
                    ((word, model.score(word, sentence[:pos])) for word in model.vocabulary),
                    key=lambda row: (-row[1], row[0]),
                )
                latencies.append((time.perf_counter() - start) * 1000)
                words = [row[0] for row in ranking]
                rank = words.index(target) + 1 if target in words else None
                ranks.append(1 / rank if rank else 0)
                truncated_ranks.append(1 / rank if rank and rank <= 50 else 0)
                for k in (1, 3, 5):
                    matched[k] += int(rank is not None and rank <= k)
            if queried >= limit:
                break
        if queried >= limit:
            break
    if not queried:
        raise ValueError("No autocomplete targets")
    return {
        "queries": queried,
        "sampling": "first fixed targets by sorted document ID; includes OOV",
        "top1": matched[1] / queried,
        "top3": matched[3] / queried,
        "top5": matched[5] / queried,
        "mrr": math.fsum(ranks) / queried,
        "mrr_at_50": math.fsum(truncated_ranks) / queried,
        "oov_rate": oov / queried,
        "coverage": 1 - oov / queried,
        "latency_ms_p50": float(np.quantile(latencies, 0.5)),
        "latency_ms_p95": float(np.quantile(latencies, 0.95)),
        "latency_kind": "exact CPU vocabulary scan; end-to-end ranking; no warmup",
    }


def diagnostics(model, documents, generated):
    buckets = defaultdict(lambda: [0, 0.0])
    words = defaultdict(lambda: [0, 0.0])
    for doc in documents:
        for sentence in doc["sentences"]:
            length = "1-10" if len(sentence) <= 10 else "11-20" if len(sentence) <= 20 else "21+"
            for gram in events(model.map_sentence(sentence), model.n):
                word = gram[-1]
                p = model.score_mapped(word, gram[:-1])
                loss = -math.log(p) if p > 0 else math.inf
                frequency = model.bank.raw_word_counts[word]
                frequency_bucket = "unseen" if frequency == 0 else "1-5" if frequency <= 5 else "6+"
                for name in (
                    f"length:{length}",
                    f"frequency:{frequency_bucket}",
                    f"genre:{doc.get('genre', 'unknown')}",
                ):
                    buckets[name][0] += 1
                    buckets[name][1] += loss
                words[word][0] += 1
                words[word][1] += loss
    reference_counts = Counter(
        word for doc in documents for sentence in doc["sentences"] for word in sentence
    )
    reference_total = sum(reference_counts.values())
    reference_entropy = (
        -math.fsum(
            c / reference_total * math.log(c / reference_total) for c in reference_counts.values()
        )
        if reference_total
        else 0.0
    )
    generated_counts = Counter(word for sentence in generated for word in sentence)
    total = sum(generated_counts.values())
    entropy = (
        -math.fsum(c / total * math.log(c / total) for c in generated_counts.values())
        if total
        else 0.0
    )
    triples = Counter(g for sentence in generated for g in ngrams(sentence, 3))
    repeat = sum(
        sum(c - 1 for c in Counter(ngrams(sentence, 3)).values()) for sentence in generated
    )
    triples_total = sum(triples.values())
    contexts = list(model.bank.totals[model.n])[:20]
    context_entropy = []
    if model.method != "stupid_backoff":
        for context in contexts:
            probabilities = [model.score_mapped(w, context) for w in model.vocabulary]
            context_entropy.append(
                {
                    "context": list(context),
                    "entropy_nats": -math.fsum(p * math.log(p) for p in probabilities if p > 0),
                }
            )
    return {
        "buckets": [
            {
                "bucket": name,
                "predicted_tokens": count,
                "nll": loss if math.isfinite(loss) else None,
                "cross_entropy": loss / count if math.isfinite(loss) else None,
            }
            for name, (count, loss) in sorted(buckets.items())
        ],
        "largest_nll_tokens": [
            {"word": word, "count": count, "nll": loss if math.isfinite(loss) else None}
            for word, (count, loss) in sorted(words.items(), key=lambda item: -item[1][1])[:20]
        ],
        "generation": {
            "distinct_3": len(triples) / triples_total if triples_total else 0,
            "repeated_trigram_rate": repeat / triples_total if triples_total else 0,
            "unigram_entropy_nats": entropy,
            "reference_unigram_entropy_nats": reference_entropy,
            "tokens": total,
            "unk_rate": generated_counts[UNK] / total if total else 0,
        },
        "context_entropy": context_entropy,
        "entropy_sampling": "first 20 observed contexts; diagnostic only",
        "frequency_source": "original training lexical counts"
        if model.bank.raw_word_counts
        else "unavailable after checkpoint load; do not interpret frequency buckets",
        "boundaries": "lexical diversity is not coherence",
    }
