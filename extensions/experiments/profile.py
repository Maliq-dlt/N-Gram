"""Phase 2.4: full-train count index memory/time, ID keys shared by both forms."""

import gc
import statistics
import time
from collections import Counter

import matplotlib.pyplot as plt
import pandas as pd

from core.src.data import load_corpus
from core.src.ngram import ngrams
from core.src.preprocess import BOS, EOS, fit_vocabulary, preprocess, replace_unknown
from extensions.experiments.run import OUT, assert_core_frozen
from extensions.src.pipeline import split_three
from extensions.src.sparse import SparseCounts, deep_size


def timed_lookup(function, queries):
    durations = []
    for _ in range(3):
        started = time.perf_counter()
        checksum = sum(function(q) for q in queries)
        durations.append(time.perf_counter() - started)
    return statistics.median(durations), checksum


def main():
    assert_core_frozen()
    sentences, _ = preprocess(load_corpus("brown"))
    train, _, _, _ = split_three(sentences, 42)
    vocabulary, _ = fit_vocabulary(train, 2)
    symbol_to_id = {w: i for i, w in enumerate(sorted(vocabulary | {BOS}))}
    mapped = [[symbol_to_id[w] for w in s] for s in replace_unknown(train, vocabulary)]
    bos, eos = symbol_to_id[BOS], symbol_to_id[EOS]
    rows = []
    for n in (1, 2, 3, 4):
        started = time.perf_counter()
        counts = Counter(g for s in mapped for g in ngrams([bos] * (n - 1) + s + [eos], n))
        build = time.perf_counter() - started
        dictionary_bytes = deep_size(counts)
        started = time.perf_counter()
        sparse = SparseCounts(counts, n)
        convert = time.perf_counter() - started
        queries = list(counts)[:10000]
        dict_time, dict_checksum = timed_lookup(counts.__getitem__, queries)
        sparse_time, sparse_checksum = timed_lookup(sparse.get, queries)
        assert dict_checksum == sparse_checksum
        row = {
            "n": n,
            "distinct_ngrams": len(counts),
            "dict_bytes": dictionary_bytes,
            "array_bytes": sparse.nbytes,
            "shared_symbol_table_bytes": deep_size(symbol_to_id),
            "dict_build_seconds": build,
            "array_conversion_seconds": convert,
            "queries": len(queries),
            "dict_lookup_seconds_median3": dict_time,
            "array_lookup_seconds_median3": sparse_time,
        }
        rows.append(row)
        print(row, flush=True)
        del counts, sparse
        gc.collect()
    table = pd.DataFrame(rows)
    table.to_csv(OUT / "profile.csv", index=False)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4), constrained_layout=True)
    axes[0].plot(table.n, table.dict_bytes / 2**20, "o-", label="Counter (token ID)")
    axes[0].plot(table.n, table.array_bytes / 2**20, "o-", label="Sorted uint32 arrays")
    axes[0].set(xlabel="n", ylabel="Count index MiB", xticks=[1, 2, 3, 4])
    axes[0].legend()
    axes[1].plot(table.n, table.dict_lookup_seconds_median3, "o-", label="Counter")
    axes[1].plot(table.n, table.array_lookup_seconds_median3, "o-", label="Array binary search")
    axes[1].set(xlabel="n", ylabel="10,000 scalar queries (seconds)", xticks=[1, 2, 3, 4])
    axes[1].legend()
    fig.savefig(OUT / "profile.png", dpi=150)
    plt.close(fig)
    assert_core_frozen()


if __name__ == "__main__":
    main()
