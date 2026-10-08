"""Sorted observed n-gram arrays, without a dense V**n tensor."""

import sys

import numpy as np


class SparseCounts:
    def __init__(self, counts, n):
        if not counts or n < 1 or any(len(g) != n for g in counts):
            raise ValueError("Counts nonempty; panjang key harus n")
        if any(not isinstance(c, int) or not 0 < c < 2**32 for c in counts.values()):
            raise ValueError("Counts harus positive uint32")
        if any(not isinstance(w, int) or not 0 <= w < 2**32 for g in counts for w in g):
            raise ValueError("Token ID harus uint32")
        keys = np.array(list(counts), dtype=np.uint32)
        values = np.array(list(counts.values()), dtype=np.uint32)
        order = np.lexsort(keys[:, ::-1].T)
        self.keys, self.values = keys[order], values[order]
        self.dtype = np.dtype([(f"w{i}", np.uint32) for i in range(n)])
        self.records = self.keys.view(self.dtype).reshape(-1)
        self.n = n

    @property
    def nbytes(self):
        return self.keys.nbytes + self.values.nbytes

    def get(self, gram):
        if len(gram) != self.n:
            raise ValueError("Panjang query harus n")
        query = np.array(tuple(gram), dtype=self.dtype)
        index = int(np.searchsorted(self.records, query))
        return (
            int(self.values[index])
            if index < len(self.records) and self.records[index] == query
            else 0
        )


def deep_size(obj, seen=None) -> int:
    seen = set() if seen is None else seen
    if id(obj) in seen:
        return 0
    seen.add(id(obj))
    size = sys.getsizeof(obj)
    if isinstance(obj, dict):
        size += sum(deep_size(k, seen) + deep_size(v, seen) for k, v in obj.items())
    elif isinstance(obj, (tuple, list, set)):
        size += sum(deep_size(v, seen) for v in obj)
    return size
