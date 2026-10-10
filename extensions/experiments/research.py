"""Preregistered document experiments with exclusive outputs and frozen domain transfer."""

import argparse
import hashlib
import json
import math
from importlib.metadata import version
from pathlib import Path

from core.src.data import ROOT
from extensions.experiments import registry
from extensions.src.cli import ALGORITHM_VERSION, PREPROCESS_VERSION, save_model
from extensions.src.datasets import (
    POLICY,
    digest,
    nltk_documents,
    read_documents,
    sentences,
    split_documents,
    validate_documents,
)
from extensions.src.models import ALL_METHODS, CountBank
from extensions.src.pipeline import candidates, tune


def finite_json(value):
    """Represent nonfinite scientific metrics explicitly, without invalid JSON numbers."""
    if isinstance(value, float) and not math.isfinite(value):
        return {
            "nonfinite": "NaN" if math.isnan(value) else "Infinity" if value > 0 else "-Infinity"
        }
    if isinstance(value, dict):
        return {str(key): finite_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [finite_json(item) for item in value]
    return value


def run_research(
    run_id,
    documents,
    orders=(1, 2, 3, 4),
    methods=ALL_METHODS,
    min_count=2,
    seed=42,
    target_documents=None,
    source_name="jsonl",
    resamples=1000,
    public_models=False,
):
    from extensions.src.analytics import (
        autocomplete_metrics,
        diagnostics,
        document_losses,
        paired_bootstrap,
    )
    from extensions.src.quality import Sampler

    orders, methods = tuple(orders), tuple(methods)
    if (
        type(public_models) is not bool
        or not orders
        or len(set(orders)) != len(orders)
        or any(type(n) is not int or not 1 <= n <= 4 for n in orders)
        or not methods
        or len(set(methods)) != len(methods)
        or any(method not in ALL_METHODS for method in methods)
        or type(min_count) is not int
        or min_count < 1
        or type(resamples) is not int
        or not 100 <= resamples <= 10000
    ):
        raise ValueError("Invalid research grid, vocabulary threshold or bootstrap budget")
    if "kneser_ney" not in methods:
        methods += ("kneser_ney",)
    validate_documents(documents)
    if any(
        not token.isalpha() or token != token.lower()
        for doc in documents
        for sentence in doc["sentences"]
        for token in sentence
    ):
        raise ValueError("Research tokens must follow alphabetic-lower preprocessing")
    split, split_manifest = split_documents(documents, seed)
    target_group_ids = {}
    if target_documents is not None:
        # Validate grouping/IDs without using target statistics in the source model.
        validate_documents(target_documents)
        if any(
            not token.isalpha() or token != token.lower()
            for doc in target_documents
            for sentence in doc["sentences"]
            for token in sentence
        ):
            raise ValueError("Target must follow the same alphabetic-lower token policy")
        # Reuse the exact grouping policy with namespaced IDs: renamed/reordered content
        # and source-group aliases cannot masquerade as independent target data.
        combined = [
            {**doc, "id": domain + "/" + doc["id"]}
            for domain, corpus in (("source", documents), ("target", target_documents))
            for doc in corpus
        ]
        _, combined_manifest = split_documents(combined, seed)
        if any(
            any(identifier.startswith("source/") for identifier in group)
            and any(identifier.startswith("target/") for identifier in group)
            for group in combined_manifest["groups"]
        ):
            raise ValueError("Source and target overlap under the duplicate/source-group policy")
        target_group_ids = {
            identifier.removeprefix("target/"): digest(sorted(group))
            for group in combined_manifest["groups"]
            for identifier in group
            if identifier.startswith("target/")
        }
    model_specs = [(n, method) for n in orders for method in methods]
    if 1 not in orders:
        model_specs.append((1, "kneser_ney"))
    code_names = [
        "extensions/src/" + name + ".py"
        for name in ("models", "pipeline", "datasets", "analytics", "cli")
    ]
    code_names += [
        "extensions/experiments/research.py",
        "extensions/experiments/registry.py",
        "extensions/src/quality.py",
    ]
    config = {
        "experiment": "document-research-v1",
        "source": source_name,
        "public_models": public_models,
        "source_sha256": split_manifest["corpus_sha256"],
        "target_sha256": digest(target_documents) if target_documents is not None else None,
        "target_group_ids": target_group_ids,
        "seed": seed,
        "orders": orders,
        "methods": methods,
        "min_count": min_count,
        "tokenizer": PREPROCESS_VERSION,
        "input_policy": "pretokenized alphabetic-lower words; reject incompatible tokens",
        "em": {
            "initial": "uniform",
            "components": "add-k(k=.01)",
            "max_iterations": 200,
            "tolerance": 1e-10,
        },
        "algorithm": ALGORITHM_VERSION,
        "vocabulary_policy": "train-only; fixed min_count and UNK mapping across all models",
        "grouping": POLICY,
        "split": split_manifest,
        "grid": {f"{n}-{method}": candidates(n, method) for n, method in model_specs},
        "budget": {
            "models": len(model_specs),
            "em_iterations": 200,
            "bootstrap_resamples": resamples,
            "autocomplete_events": 100,
            "documents": len(documents),
        },
        "test_policy": "exploratory Brown"
        if source_name == "brown"
        else "exploratory; parameters recorded before fitting; prior corpus exposure unknown",
        "code_sha256": {
            name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in code_names
        },
        "versions": {name: version(name) for name in ("numpy", "nltk")},
    }
    directory = registry.create_run(run_id, config)
    registry.start_stage(run_id, "research", config)

    def write(name, value):
        registry.atomic_json(directory / name, finite_json(value))

    write("protocol.json", config)
    write("splits.json", split_manifest)
    write("source_documents.json", documents)
    if target_documents is not None:
        write("target_documents.json", target_documents)
    bank = CountBank(sentences(split["train"]), max_n=max(orders), min_count=min_count)
    trained, summary = {}, []
    for n, method in model_specs:
        dev_counts = bank.event_counts(sentences(split["dev"]), n)
        name = f"{n}-{method}"
        model, winner, trials = tune(bank, n, method, dev_counts)
        if not math.isfinite(winner["dev_loss"]):
            raise ValueError("Nonfinite dev selection loss; do not inspect test")
        metadata = {
            "seed": seed,
            "source": source_name,
            "corpus_sha256": config["source_sha256"],
            "document_split": split_manifest,
            "tuning_trace": trials,
            "selection": "dev-only",
            "run_id": run_id,
        }
        save_model(directory / "models" / (name + ".json.gz"), model, metadata)
        write(
            "tuning/" + name + ".json",
            {"winner": winner, "trials": trials, "mkn_discounts": model.mkn_discounts},
        )
        trained[name] = model
        summary.append(
            {
                "model": name,
                "n": n,
                "method": method,
                "dev_loss": winner["dev_loss"],
                "normalized": method != "stupid_backoff",
            }
        )
    best = min(
        (row for row in summary if row["normalized"]),
        key=lambda row: (row["dev_loss"], row["model"]),
    )
    baseline = f"{best['n']}-kneser_ney"
    write(
        "selection.json",
        {
            "best": best["model"],
            "baseline": baseline,
            "rule": "minimum normalized dev_loss; lexical tie-break",
        },
    )
    losses = {}

    def evaluate(name, docs, domain, fingerprint):
        # Claim before computing: interrupted evaluations cannot be quietly repeated in this run.
        receipt = directory / "receipts" / (domain + "-" + name + ".json")
        receipt.parent.mkdir(exist_ok=True)
        with receipt.open("x", encoding="utf-8") as stream:
            json.dump(
                {
                    "model": name,
                    "domain": domain,
                    "source_sha256": fingerprint,
                    "model_sha256": hashlib.sha256(
                        (directory / "models" / (name + ".json.gz")).read_bytes()
                    ).hexdigest(),
                    "vocabulary_sha256": digest(bank.vocabulary),
                },
                stream,
                allow_nan=False,
            )
        rows = document_losses(trained[name], docs)
        write("metrics/" + domain + "-" + name + ".json", rows)
        return rows

    for row in summary:
        name = row["model"]
        rows = evaluate(name, split["test"], "test", digest(split["test"]))
        losses[name] = rows
        count = sum(item["predicted_tokens"] for item in rows)
        loss = math.fsum(item["nll"] for item in rows) / count
        row.update(
            test_cross_entropy=loss,
            perplexity=(math.exp(loss) if loss < 709 else math.inf) if row["normalized"] else None,
        )
    write(
        "bootstrap.json",
        paired_bootstrap(losses[best["model"]], losses[baseline], seed=seed, resamples=resamples),
    )
    write(
        "autocomplete.json",
        {
            "roles": {
                "unigram": "1-kneser_ney",
                "kneser_ney": baseline,
                "dev_winner": best["model"],
            },
            "models": {
                name: autocomplete_metrics(trained[name], split["test"], limit=100)
                for name in dict.fromkeys(("1-kneser_ney", baseline, best["model"]))
            },
        },
    )
    sampler = Sampler(trained[best["model"]], seed)
    generated = [sampler.generate() for _ in range(100)]
    write("diagnostics.json", diagnostics(trained[best["model"]], split["test"], generated))
    write("generated.json", generated)
    if target_documents is not None:
        target_losses = {
            name: evaluate(
                name,
                [dict(doc, split_group=target_group_ids[doc["id"]]) for doc in target_documents],
                "target",
                config["target_sha256"],
            )
            for name in dict.fromkeys((best["model"], baseline))
        }
        write(
            "target_bootstrap.json",
            paired_bootstrap(
                target_losses[best["model"]],
                target_losses[baseline],
                seed=seed,
                resamples=resamples,
            ),
        )
        write(
            "domain_transfer.json",
            {
                "source_sha256": config["source_sha256"],
                "target_sha256": config["target_sha256"],
                "vocabulary_sha256": digest(bank.vocabulary),
                "target_training": False,
                "selection": "source dev winner frozen before target evaluation",
            },
        )
    write("summary.json", summary)
    registry.complete_stage(run_id, "research")
    return directory


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--corpus", choices=("brown", "reuters"))
    source.add_argument("--input", type=Path)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--orders", nargs="+", type=int, default=[1, 2, 3, 4])
    parser.add_argument("--methods", nargs="+", choices=ALL_METHODS, default=list(ALL_METHODS))
    parser.add_argument("--min-count", type=int, default=2)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--limit-documents", type=int)
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--target-corpus", choices=("brown", "reuters"))
    parser.add_argument("--resamples", type=int, default=1000)
    parser.add_argument(
        "--public-models",
        action="store_true",
        help="Opt in to read-only browser access to model checkpoints",
    )
    args = parser.parse_args(argv)
    if args.limit_documents is not None and args.limit_documents < 3:
        parser.error("--limit-documents must be at least 3")
    if args.target_corpus and args.target_corpus == args.corpus:
        parser.error("Source and target corpus must differ")
    docs = (
        read_documents(args.input)
        if args.input
        else nltk_documents(args.corpus, args.limit_documents, args.download)
    )
    if args.input and args.limit_documents:
        docs = docs[: args.limit_documents]
    target = (
        nltk_documents(args.target_corpus, args.limit_documents, args.download)
        if args.target_corpus
        else None
    )
    path = run_research(
        args.run_id,
        docs,
        args.orders,
        args.methods,
        args.min_count,
        args.seed,
        target,
        args.corpus or "jsonl",
        args.resamples,
        args.public_models,
    )
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
