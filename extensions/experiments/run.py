"""Sequential 2.1/2.2 experiment; each tuned winner sees test exactly once."""

import argparse
import gc
import hashlib
import json
import platform
import time
from importlib.metadata import version

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from core.src.data import DATA_DIR, ROOT, load_corpus, set_seed
from core.src.preprocess import oov_rate, preprocess
from extensions.src.models import METHODS, CountBank, evaluate_counts
from extensions.src.pipeline import split_three, tune

OUT = ROOT / "extensions" / "results"


def assert_core_frozen():
    manifest = ROOT / ".cache/core_frozen.json"
    if not manifest.is_file():
        manifest = ROOT / "verifikasi/core_manifest.json"
    frozen = json.loads(manifest.read_text(encoding="utf-8"))
    for name, digest in frozen.items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name


def dump(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8"
    )


def final_row(bank, n, method, dev_counts, test_counts, seed, threshold):
    started = time.perf_counter()
    model, winner, trials = tune(bank, n, method, dev_counts)
    # Only the dev winner is evaluated against held-out test.
    final = evaluate_counts(model, test_counts)
    row = {
        "seed": seed,
        "min_count": threshold,
        "n": n,
        "method": method,
        "V": len(bank.vocabulary),
        "parameters": json.dumps(winner["parameters"]),
        "dev_loss": winner["dev_loss"],
        **final,
        "tune_and_eval_seconds": time.perf_counter() - started,
    }
    dump(OUT / "tuning" / f"tuning_{seed}_{threshold}_{n}_{method}.json", trials)
    print(f"seed={seed} min_count={threshold} n={n} {method}: PP={final['perplexity']}", flush=True)
    return row


def run21(sentences):
    train, dev, test, ids = split_three(sentences, seed=42)
    dump(OUT / "splits" / "split_42.json", ids)
    bank = CountBank(train, max_n=3, min_count=2)
    dev_counts, test_counts = bank.event_counts(dev, 3), bank.event_counts(test, 3)
    rows = [final_row(bank, 3, method, dev_counts, test_counts, 42, 2) for method in METHODS]
    pd.DataFrame(rows).to_csv(OUT / "phase21.csv", index=False)
    return rows


def run22(sentences, rows):
    for seed in (42, 43, 44):
        train, dev, test, ids = split_three(sentences, seed)
        dump(OUT / "splits" / f"split_{seed}.json", ids)
        for threshold in (2, 3):
            started = time.perf_counter()
            bank = CountBank(train, max_n=4, min_count=threshold)
            print(
                f"Count bank seed={seed} threshold={threshold}: "
                f"{time.perf_counter() - started:.2f}s",
                flush=True,
            )
            for n in (1, 2, 3, 4):
                if seed == 42 and threshold == 2 and n == 3:
                    continue  # reuse phase 2.1 final test scores
                dev_counts, test_counts = bank.event_counts(dev, n), bank.event_counts(test, n)
                for method in METHODS:
                    row = final_row(bank, n, method, dev_counts, test_counts, seed, threshold)
                    row["test_oov_rate"] = oov_rate(test, bank.vocab_set)
                    rows.append(row)
                    pd.DataFrame(rows).to_csv(OUT / "experiments.csv", index=False)
            del bank
            gc.collect()
    frame = pd.DataFrame(rows)
    assert len(frame) == 120
    assert not frame.duplicated(["seed", "min_count", "n", "method"]).any()
    frame.to_csv(OUT / "experiments.csv", index=False)
    summary = frame.groupby(["min_count", "n", "method"], as_index=False).agg(
        pp_mean=("perplexity", "mean"),
        pp_std=("perplexity", "std"),
        loss_mean=("score_cross_entropy", "mean"),
        loss_std=("score_cross_entropy", "std"),
        seeds=("seed", "count"),
    )
    summary.to_csv(OUT / "summary.csv", index=False)
    fig, axes = plt.subplots(1, 2, figsize=(12, 5), constrained_layout=True)
    normalized = [m for m in METHODS if m != "stupid_backoff"]
    for ax, threshold in zip(axes, (2, 3)):
        matrix = (
            summary[summary.min_count == threshold]
            .pivot(index="method", columns="n", values="pp_mean")
            .reindex(normalized)
        )
        values = matrix.to_numpy(dtype=float)
        heat = ax.imshow(np.log10(values), cmap="YlGnBu", aspect="auto")
        ax.set(
            xticks=range(4),
            xticklabels=(1, 2, 3, 4),
            yticks=range(4),
            yticklabels=normalized,
            xlabel="Orde n",
            title=f"min_count={threshold}; mean PP (3 seeds)",
        )
        for y in range(4):
            for x in range(4):
                ax.text(
                    x,
                    y,
                    f"{values[y, x]:.0f}",
                    ha="center",
                    va="center",
                    color="black",
                    bbox={"facecolor": "white", "alpha": 0.7, "edgecolor": "none"},
                )
        fig.colorbar(heat, ax=ax, label="log10 mean PP")
    fig.savefig(OUT / "heatmap.png", dpi=160)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=("21", "22"), required=True)
    args = parser.parse_args()
    assert_core_frozen()
    OUT.mkdir(parents=True, exist_ok=True)
    set_seed(42)
    sentences, dropped = preprocess(load_corpus("brown"))
    dump(
        OUT / "manifest.json",
        {
            "corpus": "brown",
            "sentences": len(sentences),
            "empty_dropped": dropped,
            "corpus_sha256": hashlib.sha256(
                (DATA_DIR / "corpora/brown.zip").read_bytes()
            ).hexdigest(),
            "python": platform.python_version(),
            "versions": {x: version(x) for x in ("nltk", "numpy", "pandas", "matplotlib")},
            "seeds": [42, 43, 44],
            "thresholds": [2, 3],
            "orders": [1, 2, 3, 4],
            "train_ratio": 0.8,
            "dev_ratio": 0.1,
            "test_ratio": 0.1,
            "test_policy": "One evaluation per dev-selected configuration; pilot rows reused.",
        },
    )
    if args.stage == "21":
        if (OUT / "phase21.csv").exists():
            raise FileExistsError("phase21.csv sudah ada; simpan run lama sebelum run baru")
        run21(sentences)
    else:
        if (OUT / "experiments.csv").exists():
            raise FileExistsError("experiments.csv sudah ada; simpan run lama sebelum run baru")
        pilot = pd.read_csv(OUT / "phase21.csv")
        rows = pilot.astype(object).where(pd.notna(pilot), None).to_dict("records")
        train, _, test, _ = split_three(sentences, 42)
        pilot_bank = CountBank(train, max_n=1, min_count=2)
        pilot_oov = oov_rate(test, pilot_bank.vocab_set)
        for row in rows:
            row["test_oov_rate"] = pilot_oov
        del pilot_bank
        run22(sentences, rows)
    assert_core_frozen()


if __name__ == "__main__":
    main()
