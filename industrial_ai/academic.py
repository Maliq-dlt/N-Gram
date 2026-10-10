"""Read-only academic lab: bounded demonstration and explicitly shared research models."""

from __future__ import annotations

import csv
import json
import random
import re
from functools import lru_cache
from io import StringIO
from pathlib import Path
from threading import Lock, RLock

import extensions
from core.src.preprocess import BOS, EOS
from extensions.experiments import registry
from extensions.src.analytics import top_k
from extensions.src.cli import load_model, score_sentence
from extensions.src.models import ALL_METHODS, CountBank, ExtensionLM
from fastapi import HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field

import runtime

# Deployment-owned registry; clients cannot supply a file path.
registry.RUNS = runtime.ROOT.parent / "extensions" / "results" / "runs"
BOUNDARY = "Implementasi sendiri tanpa library N-gram eksternal. Demo kecil menjelaskan matematika; metrik riset hanya berasal dari run selesai. N-gram tidak mendeteksi piksel atau identitas."
DEMO = [
    "the cat sits",
    "the cat sleeps",
    "the dog sits",
    "a dog sleeps",
    "a cat walks",
    "the dog walks",
]
_lock = RLock()
_compute = Lock()
_PACKAGE = Path(extensions.__file__).parent
PUBLISHED = _PACKAGE / "reports" / "pilot_metrics.json"
VALIDATION = _PACKAGE / "results" / "nltk_comparison.json"
_cache: dict[tuple[str, str], tuple[ExtensionLM, dict]] = {}


class Explore(BaseModel):
    model_config = ConfigDict(extra="forbid")
    model_id: str = Field(default="demo", max_length=180)
    method: str = Field(default="add_k", max_length=40)
    n: int = Field(default=2, ge=1, le=4, strict=True)
    text: str = Field(default="the cat sits", min_length=1, max_length=6000)
    prefix: str = Field(default="", max_length=256)
    seed: int = Field(default=42, ge=0, le=2**32 - 1, strict=True)
    max_length: int = Field(default=12, ge=1, le=40, strict=True)


def read_json(path: Path, limit=2**20):
    if path.is_symlink() or path.stat().st_size > limit:
        raise ValueError("Academic metadata exceeds its limit or contains a symlink")
    return json.loads(path.read_text(encoding="utf-8"))


def shared_runs():
    runs, errors = [], []
    folders = sorted(registry.RUNS.iterdir())[:100] if registry.RUNS.is_dir() else []
    for folder in folders:
        shared = False
        if not folder.is_dir():
            continue
        try:
            preliminary = read_json(folder / "manifest.json")
            config = preliminary.get("config", {})
            if (
                config.get("experiment") != "document-research-v1"
                or config.get("public_models") is not True
            ):
                continue
            shared = True
            manifest = registry.read_run(folder.name)
            summary = read_json(folder / "summary.json")
            if not isinstance(summary, list) or len(summary) > 64:
                raise ValueError("Invalid research summary")
            runs.append(
                {
                    "run_id": folder.name,
                    "status": manifest["status"],
                    "source_name": config["source"],
                    "metrics": [
                        {
                            "n": row["n"],
                            "method": row["method"],
                            "dev_cross_entropy": row["dev_loss"],
                            "test_cross_entropy": row["test_cross_entropy"]
                            if isinstance(row["test_cross_entropy"], (int, float))
                            else None,
                            "test_perplexity": row["perplexity"]
                            if isinstance(row["perplexity"], (int, float))
                            else None,
                        }
                        for row in summary
                    ],
                    "comparison": [read_json(folder / "bootstrap.json")],
                    "test_policy": config["test_policy"],
                }
            )
        except (OSError, ValueError, KeyError, TypeError):
            # Failed shared runs are visible as errors; never serve partially verified models.
            if not shared:
                continue
            errors.append(
                {
                    "run_id": folder.name,
                    "detail": "Run belum selesai atau integritas artefaknya gagal.",
                }
            )
    if PUBLISHED.is_file():
        try:
            archived = read_json(PUBLISHED)
            if archived.get("schema_version") != 1 or not isinstance(archived.get("runs"), list):
                raise ValueError("Invalid published summaries")
            seen = {r["run_id"] for r in runs} | {r["run_id"] for r in errors}
            for row in archived["runs"]:
                if row["run_id"] not in seen:
                    runs.append(
                        {
                            key: row[key]
                            for key in (
                                "run_id",
                                "status",
                                "source_name",
                                "metrics",
                                "comparison",
                                "test_policy",
                            )
                        }
                    )
        except (OSError, ValueError, KeyError, TypeError):
            errors.append({"run_id": "published", "detail": "Ringkasan publik tidak dapat dibaca."})
    return runs, errors


def validation():
    try:
        return {
            **read_json(VALIDATION),
            "source": "historical ordinary KN validation; not MKN or current pilots",
        }
    except (OSError, ValueError, TypeError):
        return None


@lru_cache(maxsize=32)
def demo_model(n, method):
    bank = CountBank([text.split() for text in DEMO], max_n=4, min_count=1)
    # EM demo displays uniform fixed weights; fitting occurs only in registered research.
    return ExtensionLM(bank, n, method)


def selected_model(request):
    if request.method not in ALL_METHODS:
        raise HTTPException(422, "Metode N-gram tidak tersedia.")
    if request.model_id == "demo":
        return (
            demo_model(request.n, request.method),
            "Corpus mini pendidikan",
            "six authored English sentences; no evaluation claim",
            {"selection": "illustrative fixed parameters; no dev tuning", "tuning_trace": []},
        )
    match = re.fullmatch(
        r"run:([A-Za-z0-9][A-Za-z0-9_-]{0,79}):([1-4]):([a-z_]+)", request.model_id
    )
    if not match:
        raise HTTPException(422, "ID model tidak valid.")
    run_id, n, method = match.groups()
    folder = registry.run_directory(run_id)
    try:
        config = read_json(folder / "manifest.json")["config"]
        if (
            config.get("public_models") is not True
            or config.get("experiment") != "document-research-v1"
        ):
            raise ValueError("Model is not explicitly shared")
        manifest = registry.read_run(run_id)
        relative = f"models/{n}-{method}.json.gz"
        sha = manifest["files"][relative]
        path = folder / relative
        if path.stat().st_size > 64 * 2**20:
            raise ValueError("Model exceeds the interactive lab budget")
        with _lock:
            key = (str(path), sha)
            if key not in _cache:
                model, metadata = load_model(path)
                if len(_cache) >= 2:
                    _cache.pop(next(iter(_cache)))
                _cache[key] = (model, metadata)
            model, metadata = _cache[key]
        if (model.n, model.method) != (request.n, request.method):
            raise ValueError("Requested settings differ from the selected checkpoint")
        return model, run_id, config["source"], metadata
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise HTTPException(409, "Model riset belum tersedia atau integritasnya gagal.") from error


def formula_details(model, scores):
    formulas = {
        "laplace": "P=(C(h,w)+1)/(C(h)+V)",
        "add_k": "P=(C(h,w)+k)/(C(h)+kV)",
        "interpolation": "P=Σ λ_j (C_j+k)/(N_j+kV)",
        "interpolation_em": "P=Σ λ_j (C_j+k)/(N_j+kV); λ dipilih dari dev dengan EM (demo: bobot seragam tetap)",
        "witten_bell": "P=C/(N+T) + T/(N+T)·P_lower; empty history backs off; unigram=(C+ε)/(N+εV)",
        "kneser_ney": "P=max(C-D,0)/N + D·T/N·P_lower; lower orders use distinct left-extension counts",
        "modified_kneser_ney": "P=max(C-D_bucket,0)/N + Σ D_bucket·T_bucket/N·P_lower; lower counts are continuation counts",
        "stupid_backoff": "score=C/N if observed, else α·score_lower; not a normalized probability",
    }
    result = [
        formulas[model.method],
        f"V={len(model.vocabulary)}; k={model.k}; ε={model.epsilon}; λ={list(model.weights)}",
    ]
    for row in scores["events"][:40]:
        context = tuple(row["context"])
        count = model.bank.raw[model.n][(*context, row["word"])]
        total = model.bank.totals[model.n][context]
        result.append(
            f"h={list(context)}, w={row['word']}: raw C={count}, N={total}, P/score={row['probability']:.10g}, −ln(P/score)={row['nll']}"
        )
    if model.mkn_discounts:
        result.append("D1/D2/D3+ per order: " + json.dumps(model.mkn_discounts))
    return result


def _explore(request: Explore):
    model, name, source, metadata = selected_model(request)
    try:
        score = score_sentence(model, request.text)
        if not score["tokens"]:
            raise ValueError("Input contains no alphabetic tokens")
        context = (
            tuple(([BOS] * (model.n - 1) + score["mapped_tokens"])[-(model.n - 1) :])
            if model.n > 1
            else ()
        )
        ranking = top_k(model, context, 5, request.prefix.lower())
        generated, rng, stop = [], random.Random(request.seed), "length cap"
        for _ in range(request.max_length):
            probabilities = [model.score_mapped(word, context) for word in model.vocabulary]
            word = rng.choices(model.vocabulary, weights=probabilities, k=1)[0]
            probability = model.score_mapped(word, context)
            generated.append({"word": word, "context": list(context), "probability": probability})
            if word == EOS:
                stop = "EOS"
                break
            context = (*context, word)[-(model.n - 1) :] if model.n > 1 else ()
        return {
            "schema_version": 1,
            "model": {
                "name": name,
                "method": model.method,
                "n": model.n,
                "vocabulary_size": len(model.vocabulary),
                "parameters": {
                    "k": model.k,
                    "epsilon": model.epsilon,
                    "discount": model.discount,
                    "weights": model.weights,
                    "selection": metadata.get("selection"),
                    "tuning_trace": metadata.get("tuning_trace", []),
                },
                "source": source,
            },
            "score": score,
            "top_k": ranking,
            "generated": generated,
            "stop_reason": stop,
            "context_window_size": model.n - 1,
            "formula_details": formula_details(model, score),
            "boundary": BOUNDARY,
            "validation": validation(),
        }
    except ValueError as error:
        raise HTTPException(422, str(error)) from error


def explore(request: Explore):
    if not _compute.acquire(blocking=False):
        raise HTTPException(429, "Lab sedang menghitung. Coba kembali sebentar.")
    try:
        return _explore(request)
    finally:
        _compute.release()


def install(app):
    @app.get("/api/ngram/catalog")
    def catalog():
        runs, errors = shared_runs()
        models = [
            {
                "id": f"run:{run['run_id']}:{row['n']}:{row['method']}",
                "name": run["run_id"],
                "n": row["n"],
                "method": row["method"],
                "corpus": run["source_name"],
            }
            for run in runs
            if run["status"] == "completed"
            for row in run["metrics"]
        ]
        return {
            "schema_version": 1,
            "methods": ALL_METHODS,
            "models": models,
            "runs": [
                {
                    "run_id": run["run_id"],
                    "summary": {"source": run["source_name"], "test_policy": run["test_policy"]},
                }
                for run in runs
            ],
            "errors": errors,
            "boundary": BOUNDARY,
            "validation": validation(),
        }

    @app.get("/api/ngram/runs")
    def runs():
        rows, errors = shared_runs()
        return {"schema_version": 1, "runs": rows, "errors": errors}

    @app.get("/api/ngram/runs/{run_id}/csv")
    def run_csv(run_id: str):
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", run_id):
            raise HTTPException(404, "Run tidak tersedia.")
        rows, errors = shared_runs()
        selected = next((row for row in rows if row["run_id"] == run_id), None)
        if selected is None:
            status = 409 if any(row["run_id"] == run_id for row in errors) else 404
            raise HTTPException(status, "Run tidak tersedia atau integritasnya gagal.")
        stream = StringIO(newline="")
        fields = ("n", "method", "dev_cross_entropy", "test_cross_entropy", "test_perplexity")
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows({key: row[key] for key in fields} for row in selected["metrics"])
        return Response(
            stream.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{run_id}.csv"'},
        )

    app.post("/api/ngram/explore")(explore)
