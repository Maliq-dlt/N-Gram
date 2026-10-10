"""Post-hoc paired n=3 minus n=4 analysis of the frozen 120-configuration CSV.

Uses only Python's standard library. Never loads a corpus, fits a model,
chooses hyperparameters, or evaluates test data. Positive deltas favor n=4.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import itertools
import json
import math
import platform
from datetime import datetime, timezone
from pathlib import Path
from statistics import fmean, stdev

SOURCE_COMMIT = "34e3df8e3298b6d73fb50d03a2a36d09bd9d79c3"
SOURCE_PATH = "extensions/results/experiments.csv"
SOURCE_BLOB = "86db4a6332ada15d1ffc314f4e1726f89f8a86e6"
SOURCE_SHA256 = "a38e17a988a58e8db06d01acf666e129308ec4a44d5b23ff7b62dc100f9719a8"
METHODS = ("add_k", "interpolation", "kneser_ney", "laplace")
SEEDS = (42, 43, 44)
THRESHOLDS = (2, 3)


def analyze(
    rows: list[dict[str, str]], method: str = "kneser_ney"
) -> tuple[list[dict], list[dict]]:
    """Validate the grid and return pairs and descriptive, unweighted summaries."""
    if method not in METHODS:
        raise ValueError("Select a normalized method; Stupid Backoff has no perplexity.")
    lookup = {}
    metadata = {}
    for row in rows:
        try:
            seed, threshold, order = (int(row[key]) for key in ("seed", "min_count", "n"))
            name = row["method"]
            key = (seed, threshold, order, name)
            if key in lookup:
                raise ValueError(f"Duplicate configuration: {key}")
            vocabulary, targets = (int(row[field]) for field in ("V", "predicted_tokens"))
            if vocabulary <= 0 or targets <= 0:
                raise ValueError("Nonpositive metadata")
            group = (seed, threshold)
            if group in metadata and metadata[group] != (vocabulary, targets):
                raise ValueError(f"Inconsistent paired metadata: {group}")
            metadata[group] = (vocabulary, targets)
            if name == "stupid_backoff":
                if row["perplexity"].strip():
                    raise ValueError("Stupid Backoff perplexity must be empty.")
                perplexity = None
            else:
                perplexity = float(row["perplexity"])
                if not math.isfinite(perplexity) or perplexity <= 0:
                    raise ValueError("Perplexity must be positive and finite.")
            lookup[key] = perplexity
        except (KeyError, TypeError, OverflowError) as exc:
            raise ValueError(f"Invalid or missing CSV field: {exc}") from exc
    expected = set(itertools.product(SEEDS, THRESHOLDS, (1, 2, 3, 4),
                                     (*METHODS, "stupid_backoff")))
    if set(lookup) != expected:
        raise ValueError("Input grid must contain all 120 unique original configurations.")
    pairs, summaries = [], []
    for threshold in THRESHOLDS:
        subset = []
        for seed in SEEDS:
            pp3, pp4 = (lookup[(seed, threshold, order, method)] for order in (3, 4))
            if pp3 is None or pp4 is None:
                raise ValueError("Expected normalized perplexities for both orders.")
            delta = pp3 - pp4
            relative = 100 * (delta / pp3)
            if not math.isfinite(delta) or not math.isfinite(relative):
                raise ValueError("Derived differences must be finite.")
            vocabulary, targets = metadata[(seed, threshold)]
            subset.append({"method": method, "min_count": threshold, "seed": seed,
                           "n_baseline": 3, "n_comparison": 4, "V": vocabulary,
                           "predicted_tokens": targets, "pp_n3": pp3, "pp_n4": pp4,
                           "delta_pp": delta, "relative_reduction_pct": relative})
        deltas = [row["delta_pp"] for row in subset]
        relative = [row["relative_reduction_pct"] for row in subset]
        summaries.append({"method": method, "min_count": threshold, "seeds": len(subset),
                          "pp_n3_mean": fmean(row["pp_n3"] for row in subset),
                          "pp_n4_mean": fmean(row["pp_n4"] for row in subset),
                          "delta_pp_mean": fmean(deltas), "delta_pp_std_ddof1": stdev(deltas),
                          "delta_pp_min": min(deltas), "delta_pp_max": max(deltas),
                          "relative_reduction_pct_mean": fmean(relative),
                          "relative_reduction_pct_min": min(relative),
                          "relative_reduction_pct_max": max(relative),
                          "improved_seeds": sum(delta > 0 for delta in deltas)})
        pairs.extend(subset)
    return pairs, summaries


def run_analysis(source: Path, output: Path, method: str = "kneser_ney") -> dict:
    """Write an exclusive derived-result directory, with input and output hashes."""
    raw = source.read_bytes()
    canonical = raw.replace(b"\r\n", b"\n")
    if hashlib.sha256(canonical).hexdigest() != SOURCE_SHA256:
        raise ValueError("Input does not match the frozen experiments.csv snapshot.")
    rows = list(csv.DictReader(io.StringIO(canonical.decode("utf-8"), newline="")))
    pairs, summaries = analyze(rows, method)
    output.mkdir(parents=True, exist_ok=False)
    manifest = {
        "schema": 1, "status": "running", "analysis": "post_hoc_paired_orders",
        "source_commit": SOURCE_COMMIT, "source_path": SOURCE_PATH,
        "source_git_blob": SOURCE_BLOB,
        "input_sha256": hashlib.sha256(raw).hexdigest(),
        "lf_normalized_input_sha256": hashlib.sha256(canonical).hexdigest(),
        "crlf_normalized_for_snapshot_check": raw != canonical,
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "python_version": platform.python_version(),
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "method": method, "orders": [3, 4], "input_rows": len(rows), "paired_rows": len(pairs),
        "delta_definition": "pp_n3 - pp_n4",
        "relative_definition": "100 * (pp_n3 - pp_n4) / pp_n3",
        "summary_definition": "Arithmetic means of paired differences; sample std ddof=1",
        "selection": "Fixed order contrast; no selection or fitting on test",
        "split_identity": (
            "Inherited from source protocol; metadata checks do not prove split identity"
        ),
        "inference": (
            "Descriptive only; shared corpus across seeds; no p-values or confidence intervals"
        ),
    }
    manifest_path = output / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, allow_nan=False) + "\n",
                             encoding="utf-8")
    hashes = {}
    for filename, table in (("paired_orders.csv", pairs), ("paired_summary.csv", summaries)):
        destination = output / filename
        with destination.open("x", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(table[0]), lineterminator="\n")
            writer.writeheader()
            writer.writerows(table)
        hashes[filename] = hashlib.sha256(destination.read_bytes()).hexdigest()
    if source.read_bytes() != raw:
        raise RuntimeError("Input changed during analysis; output is not marked completed.")
    manifest.update(status="completed", output_sha256=hashes, input_unchanged=True)
    pending = output / "manifest.json.pending"
    with pending.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(manifest, indent=2, allow_nan=False) + "\n")
    pending.replace(manifest_path)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path(SOURCE_PATH))
    parser.add_argument("--output", type=Path, required=True,
                        help="New directory; existing directories are never overwritten")
    parser.add_argument("--method", choices=METHODS, default="kneser_ney")
    args = parser.parse_args()
    try:
        result = run_analysis(args.input, args.output, args.method)
    except (OSError, ValueError, RuntimeError) as exc:
        parser.exit(2, f"Error: {exc}\n")
    print(json.dumps({"status": result["status"], "paired_rows": result["paired_rows"],
                      "output": str(args.output)}, sort_keys=True))


if __name__ == "__main__":
    main()
