"""Phase 2.3: dev-selected model; test inspection never feeds tuning."""

import argparse
import gc
import json
import math
from collections import Counter, defaultdict

import matplotlib.pyplot as plt
import pandas as pd

from core.src.data import load_corpus
from core.src.ngram import events
from core.src.preprocess import preprocess
from extensions.experiments.registry import (
    complete_derived,
    derived_directory,
    legacy_analysis_source,
)
from extensions.experiments.run import assert_core_frozen, dump
from extensions.src.models import CountBank, ExtensionLM
from extensions.src.pipeline import split_three
from extensions.src.quality import Sampler, generation_metrics


def model_from_row(bank, row):
    return ExtensionLM(bank, int(row.n), row.method, **json.loads(row.parameters))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    source = legacy_analysis_source(args.run_id)
    OUT = derived_directory(args.run_id, "analyze")
    assert_core_frozen()
    frame = pd.read_csv(source / "experiments.csv")
    assert len(frame) == 120
    candidates = frame[
        (frame.seed == 42) & (frame.min_count == 2) & (frame.method != "stupid_backoff")
    ]
    winner = candidates.sort_values(["dev_loss", "n", "method"]).iloc[0]
    print("Dev-selected:", winner[["n", "method", "parameters", "dev_loss"]].to_dict(), flush=True)
    sentences, _ = preprocess(load_corpus("brown"))
    train, _, test, _ = split_three(sentences, 42)
    bank = CountBank(train, max_n=4, min_count=2)
    model = model_from_row(bank, winner)
    words, grams = defaultdict(lambda: [0, 0.0]), defaultdict(lambda: [0, 0.0])
    lengths = defaultdict(lambda: [0, 0.0, 0])
    sentence_rows = []
    for sentence in test:
        loss = 0.0
        for gram in events(model.map_sentence(sentence), model.n):
            nll = -math.log(model.score_mapped(gram[-1], gram[:-1]))
            for table, key in ((words, gram[-1]), (grams, gram)):
                table[key][0] += 1
                table[key][1] += nll
            loss += nll
        length = len(sentence)
        bucket = (
            "1-10"
            if length <= 10
            else "11-20"
            if length <= 20
            else "21-40"
            if length <= 40
            else "41+"
        )
        lengths[bucket][0] += length + 1
        lengths[bucket][1] += loss
        lengths[bucket][2] += 1
        sentence_rows.append(
            {
                "length": length,
                "target_tokens": length + 1,
                "nll": loss,
                "perplexity": math.exp(loss / (length + 1)),
            }
        )
    for label, table in (("token", words), ("ngram", grams)):
        rows = [
            {label: str(key), "occurrences": v[0], "total_nll": v[1], "mean_nll": v[1] / v[0]}
            for key, v in table.items()
        ]
        pd.DataFrame(rows).sort_values("total_nll", ascending=False).to_csv(
            OUT / f"error_{label}.csv", index=False
        )
    pd.DataFrame(sentence_rows).to_csv(OUT / "sentence_perplexity.csv", index=False)
    length_rows = [
        {
            "length_bin": key,
            "sentences": v[2],
            "predicted_tokens": v[0],
            "perplexity": math.exp(v[1] / v[0]),
        }
        for key, v in lengths.items()
    ]
    length_frame = (
        pd.DataFrame(length_rows)
        .set_index("length_bin")
        .reindex(["1-10", "11-20", "21-40", "41+"])
        .reset_index()
    )
    length_frame.to_csv(OUT / "length_perplexity.csv", index=False)
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(length_frame.length_bin, length_frame.perplexity, color="#245f7a")
    ax.set(
        xlabel="Panjang kalimat (tanpa EOS)",
        ylabel="Token-weighted PP",
        title=f"Dev-selected {model.method}, n={model.n}",
    )
    fig.tight_layout()
    fig.savefig(OUT / "length_perplexity.png", dpi=150)
    plt.close(fig)
    generation_rows, generated = [], {}
    comparison = [candidates[(candidates.n == 1) & (candidates.method == "add_k")].iloc[0]]
    comparison += [
        candidates[(candidates.n == n) & (candidates.method == "kneser_ney")].iloc[0]
        for n in (2, 3, 4)
    ]
    for row in comparison:
        lm = model_from_row(bank, row)
        sampler = Sampler(lm, seed=42)
        texts = [sampler.generate(max_length=40) for _ in range(200)]
        key = f"{row.method}_n{int(row.n)}"
        generated[key] = texts
        generation_rows.append({"model": key, **generation_metrics(texts)})
        print(key, generation_rows[-1], flush=True)
        del sampler
        gc.collect()
    generation_frame = pd.DataFrame(generation_rows)
    generation_frame.to_csv(OUT / "generation_metrics.csv", index=False)
    dump(OUT / "generated.json", generated)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4), constrained_layout=True)
    for ax, metric in zip(axes, ("distinct_2", "repeated_bigram_rate")):
        ax.bar(generation_frame.model, generation_frame[metric], color="#489c86")
        ax.set(ylabel=metric)
        ax.tick_params(axis="x", rotation=20)
    fig.savefig(OUT / "generation.png", dpi=150)
    plt.close(fig)
    dump(
        OUT / "analysis_model.json",
        {
            "selection": "minimum dev_loss, seed=42/min_count=2, normalized methods only",
            "n": int(winner.n),
            "method": winner.method,
            "parameters": json.loads(winner.parameters),
            "dev_loss": float(winner.dev_loss),
            "test_pp_from_final_table": float(winner.perplexity),
        },
    )
    # Lexical exploration supplement; these counts never enter any model.
    top_words = Counter(w for s in sentences for w in s).most_common(20)
    pd.DataFrame(top_words, columns=["word", "count"]).to_csv(
        OUT / "top20_clean_words.csv", index=False
    )
    assert_core_frozen()

    complete_derived(OUT)


if __name__ == "__main__":
    main()
