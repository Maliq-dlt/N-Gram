from collections import Counter

from extensions.src.sparse import SparseCounts


def test_sparse_lookup_preserves_counts_and_missing_keys():
    source = Counter({(1, 2): 7, (0, 3): 2, (1, 3): 9})
    sparse = SparseCounts(source, 2)
    for key, count in source.items():
        assert sparse.get(key) == count
    assert sparse.get((3, 3)) == 0
    assert sparse.nbytes == 3 * (2 + 1) * 4
