"""Train/evaluate/generate CLI with YAML validation and JSON-gzip checkpoints."""

import argparse
import gzip
import hashlib
import json
import os
import sys
import uuid
from collections import Counter
from pathlib import Path

import yaml

from core.src.data import ROOT, load_corpus, set_seed
from core.src.preprocess import preprocess
from extensions.src.models import METHODS, CountBank, ExtensionLM, evaluate_counts
from extensions.src.pipeline import split_three, tune
from extensions.src.quality import Sampler


def read_config(path):
    config = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    allowed = {"corpus", "seed", "n", "method", "min_count"}
    if not isinstance(config, dict) or set(config) != allowed:
        raise ValueError(f"Config wajib tepat key {sorted(allowed)}")
    if config["corpus"] not in ("brown", "reuters") or config["method"] not in METHODS:
        raise ValueError("Corpus/metode config tidak valid")
    for key in ("n", "min_count", "seed"):
        if type(config[key]) is not int:
            raise ValueError(f"{key} harus integer")
    if not 1 <= config["n"] <= 4 or config["min_count"] < 1 or not 0 <= config["seed"] < 2**32:
        raise ValueError("n 1..4; min_count>=1; seed uint32")
    return config


def save_model(path, model, metadata):
    path = Path(path).resolve()
    if not path.is_relative_to(ROOT):
        raise ValueError("Output/cache harus berada di repository")
    if path.exists():
        raise FileExistsError(f"Checkpoint sudah ada: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".{uuid.uuid4().hex}.tmp")
    payload = {
        "format_version": 1,
        "metadata": metadata,
        "n": model.n,
        "method": model.method,
        "parameters": {
            "k": model.k,
            "discount": model.discount,
            "weights": model.weights,
            "backoff": model.backoff,
            "epsilon": model.epsilon,
        },
        "min_count": model.bank.min_count,
        "vocabulary": model.vocabulary,
        "counts": {
            str(n): [[g, c] for g, c in counts.items()] for n, counts in model.bank.raw.items()
        },
    }
    try:
        with gzip.open(temporary, "xt", encoding="utf-8") as stream:
            json.dump(payload, stream, ensure_ascii=False, allow_nan=False)
        os.link(temporary, path)  # Atomic commit fails if destination appeared concurrently.
    finally:
        temporary.unlink(missing_ok=True)


def load_model(path):
    # ponytail: in-memory JSON capped at 512 MiB; use streaming for larger corpora.
    with gzip.open(path, "rb") as stream:
        content = stream.read(512 * 2**20 + 1)
    if len(content) > 512 * 2**20:
        raise ValueError("Checkpoint melebihi 512 MiB setelah dekompresi")
    payload = json.loads(content)
    if not isinstance(payload, dict) or payload.get("format_version") != 1:
        raise ValueError("Format checkpoint tidak didukung")
    required = {
        "format_version",
        "metadata",
        "n",
        "method",
        "parameters",
        "min_count",
        "vocabulary",
        "counts",
    }
    if set(payload) != required or not isinstance(payload["counts"], dict):
        raise ValueError("Schema checkpoint tidak valid")
    raw = {}
    for order, entries in payload["counts"].items():
        if order not in ("1", "2", "3", "4") or not isinstance(entries, list):
            raise ValueError("Count order/entries tidak valid")
        counts = Counter()
        for entry in entries:
            if not isinstance(entry, list) or len(entry) != 2 or not isinstance(entry[0], list):
                raise ValueError("Count entry tidak valid")
            gram, count = entry
            if any(not isinstance(w, str) for w in gram) or tuple(gram) in counts:
                raise ValueError("Count key tidak valid/duplicate")
            counts[tuple(gram)] = count
        raw[int(order)] = counts
    if not isinstance(payload["metadata"], dict) or not isinstance(payload["parameters"], dict):
        raise ValueError("Metadata/parameters harus object")
    if type(payload["n"]) is not int:
        raise ValueError("n harus integer")
    bank = CountBank.from_counts(payload["vocabulary"], raw, payload["min_count"])
    model = ExtensionLM(bank, payload["n"], payload["method"], **payload["parameters"])
    return model, payload["metadata"]


def corpus_digest(sentences):
    return hashlib.sha256(
        json.dumps(sentences, ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    train = commands.add_parser("train", help="Fit train, tune dev, save model; test not evaluated")
    train.add_argument("--config", type=Path, default=ROOT / "extensions/config.yaml")
    train.add_argument("--model", type=Path, required=True)
    evaluate = commands.add_parser("evaluate", help="Evaluate recorded held-out split")
    evaluate.add_argument("--model", type=Path, required=True)
    generate = commands.add_parser("generate", help="Sample sentences")
    generate.add_argument("--model", type=Path, required=True)
    generate.add_argument("--seed", type=int, default=42)
    generate.add_argument("--count", type=int, default=5)
    generate.add_argument("--max-length", type=int, default=40)
    args = parser.parse_args(argv)
    try:
        if args.command == "train":
            config = read_config(args.config)
            set_seed(config["seed"])
            sentences, _ = preprocess(load_corpus(config["corpus"]))
            train_set, dev, _, _ = split_three(sentences, config["seed"])
            bank = CountBank(train_set, max_n=config["n"], min_count=config["min_count"])
            model, winner, _ = tune(
                bank, config["n"], config["method"], bank.event_counts(dev, config["n"])
            )
            metadata = {
                **config,
                "corpus_sha256": corpus_digest(sentences),
                "dev_loss": winner["dev_loss"],
                "selection": "dev-only; no test evaluation during train",
            }
            save_model(args.model, model, metadata)
            print(
                json.dumps(
                    {"model": str(args.model), "V": len(bank.vocabulary), **metadata},
                    ensure_ascii=False,
                )
            )
        else:
            model, metadata = load_model(args.model)
            if args.command == "evaluate":
                if not {"corpus", "seed", "corpus_sha256"} <= set(metadata):
                    raise ValueError("Checkpoint tidak punya metadata split/corpus")
                sentences, _ = preprocess(load_corpus(metadata["corpus"]))
                if corpus_digest(sentences) != metadata["corpus_sha256"]:
                    raise ValueError("Corpus berbeda dari training checkpoint")
                _, _, test, _ = split_three(sentences, metadata["seed"])
                result = evaluate_counts(model, model.bank.event_counts(test, model.n))
                print(json.dumps(result, ensure_ascii=False, allow_nan=False))
            else:
                if not 1 <= args.count <= 1000 or args.max_length < 1:
                    raise ValueError("count 1..1000; max-length>=1")
                sampler = Sampler(model, args.seed)
                for _ in range(args.count):
                    print(" ".join(sampler.generate(args.max_length)))
    except (ValueError, TypeError, KeyError, OSError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
