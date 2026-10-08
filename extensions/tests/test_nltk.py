from extensions.experiments.compare_nltk import compare


def test_external_kneser_ney_matches_same_event_counts():
    rows = compare([["a", "x"], ["b", "x"], ["a", "y"], ["a", "z"]])
    assert all(row["max_absolute_difference"] < 1e-12 for row in rows)
