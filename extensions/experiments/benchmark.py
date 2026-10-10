"""Derived CPU benchmarks: isolated process/model; train/dev workloads, no test evaluation."""

import argparse
import ctypes
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
import time
from pathlib import Path
from statistics import quantiles


def pin_cpu():
    """Pin to the first already-allowed CPU; fail rather than claim an unlocked benchmark."""
    if os.name == "nt":
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.GetCurrentProcess.restype = ctypes.c_void_p
        handle = kernel.GetCurrentProcess()
        current, system = ctypes.c_size_t(), ctypes.c_size_t()
        kernel.GetProcessAffinityMask.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_size_t),
            ctypes.POINTER(ctypes.c_size_t),
        ]
        kernel.SetProcessAffinityMask.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
        if not kernel.GetProcessAffinityMask(handle, ctypes.byref(current), ctypes.byref(system)):
            raise ctypes.WinError(ctypes.get_last_error())
        mask = current.value & -current.value
        if not mask or not kernel.SetProcessAffinityMask(handle, mask):
            raise ctypes.WinError(ctypes.get_last_error())
        return mask.bit_length() - 1
    allowed = os.sched_getaffinity(0)
    cpu = min(allowed)
    os.sched_setaffinity(0, {cpu})
    return cpu


def peak_rss_bytes():
    """Peak working set/RSS of this whole process, including imports, caches and warmup."""
    if os.name == "nt":
        from ctypes import wintypes

        class Counters(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD)] + [
                (name, ctypes.c_size_t)
                for name in (
                    "PeakWorkingSetSize",
                    "WorkingSetSize",
                    "QuotaPeakPagedPoolUsage",
                    "QuotaPagedPoolUsage",
                    "QuotaPeakNonPagedPoolUsage",
                    "QuotaNonPagedPoolUsage",
                    "PagefileUsage",
                    "PeakPagefileUsage",
                )
            ]

        counters = Counters()
        counters.cb = ctypes.sizeof(counters)
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.GetCurrentProcess.restype = ctypes.c_void_p
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
        psapi.GetProcessMemoryInfo.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(Counters),
            wintypes.DWORD,
        ]
        if not psapi.GetProcessMemoryInfo(
            kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb
        ):
            raise ctypes.WinError(ctypes.get_last_error())
        return counters.PeakWorkingSetSize
    import resource

    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(value if sys.platform == "darwin" else value * 1024)


def distribution(samples):
    cuts = quantiles(samples, n=100, method="inclusive")
    return {"p50_ms": cuts[49], "p95_ms": cuts[94], "samples_ms": samples}


def worker(source, name, output, warmup=1, repeats=5, targets=100):
    from core.src.data import ROOT
    from extensions.experiments import registry
    from extensions.src.analytics import top_k
    from extensions.src.datasets import digest, sentences
    from extensions.src.models import CountBank
    from extensions.src.pipeline import tune

    source, output = Path(source).resolve(), Path(output).resolve()
    if not source.is_relative_to(ROOT.resolve()) or not output.is_relative_to(ROOT.resolve()):
        raise ValueError("Benchmark inputs/outputs must remain in repository")
    if (
        type(warmup) is not int
        or not 1 <= warmup <= 10
        or type(repeats) is not int
        or not 2 <= repeats <= 30
    ):
        raise ValueError("warmup1..10 and repeats2..30 required")
    if type(targets) is not int or not 1 <= targets <= 1000:
        raise ValueError("targets1..1000 required")
    if not isinstance(name, str) or not re.fullmatch(r"[1-4]-[a-z_]+", name):
        raise ValueError("Invalid benchmark model name")
    if output != source / "derived" / "benchmark" / (name + ".json"):
        raise ValueError("Worker output must be its model file in the source benchmark directory")
    manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
    config = manifest["config"]
    if (
        manifest.get("status") != "completed"
        or manifest.get("run_id") != source.name
        or manifest.get("config_sha256") != registry.fingerprint(config)
        or manifest.get("files") != registry._files(source)
        or config.get("experiment") != "document-research-v1"
        or name not in config.get("grid", {})
    ):
        raise ValueError("Worker requires a verified completed source and registered model")
    receipt_path = output.parent / "manifest.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if (
        receipt.get("status") != "running"
        or receipt.get("source_run") != source.name
        or receipt.get("source_config_sha256") != manifest["config_sha256"]
        or receipt.get("source_files") != manifest["files"]
    ):
        raise ValueError("Worker requires a running benchmark receipt bound to its source")
    if output.exists():
        raise FileExistsError("Benchmark output already exists")
    with output.with_suffix(".claim").open("x", encoding="utf-8") as claim:
        claim.write(manifest["config_sha256"])
    cpu = pin_cpu()
    documents = json.loads((source / "source_documents.json").read_text(encoding="utf-8"))
    split = json.loads((source / "splits.json").read_text(encoding="utf-8"))
    by_id = {doc["id"]: doc for doc in documents}
    train = sentences([by_id[key] for key in split["ids"]["train"]])
    dev = sentences([by_id[key] for key in split["ids"]["dev"]])
    fixed_dev = sentences([by_id[key] for key in sorted(split["ids"]["dev"])])
    fixed = [
        (sentence[:pos], target) for sentence in fixed_dev for pos, target in enumerate(sentence)
    ][:targets]
    if not fixed:
        raise ValueError("No fixed dev targets for benchmark")
    n_text, method = name.split("-", 1)
    n = int(n_text)
    model, winner = None, None
    builds, scores, rankings = [], [], []
    score_check, ranking_check = None, None
    for repeat in range(warmup + repeats):
        start = time.perf_counter()
        # Release prior bank/model before rebuilding to avoid two full models resident.
        model = None
        bank = counts = None
        bank = CountBank(train, max_n=max(config["orders"]), min_count=config["min_count"])
        counts = bank.event_counts(dev, n)
        model, winner, _ = tune(bank, n, method, counts)
        elapsed = (time.perf_counter() - start) * 1000
        if repeat >= warmup:
            builds.append(elapsed)
        score_times, ranking_times, score_values, rank_values = [], [], [], []
        for context, target in fixed:
            start = time.perf_counter()
            value = model.score(target, context)
            score_times.append((time.perf_counter() - start) * 1000)
            score_values.append(value)
            start = time.perf_counter()
            rows = top_k(model, context, 5)
            ranking_times.append((time.perf_counter() - start) * 1000)
            rank_values.append(rows)
        if repeat >= warmup:
            scores.extend(score_times)
            rankings.extend(ranking_times)
        current_score, current_rank = digest(score_values), digest(rank_values)
        if score_check is not None and (
            score_check != current_score or ranking_check != current_rank
        ):
            raise ValueError("Repeated benchmark produced different predictions")
        score_check, ranking_check = current_score, current_rank
    expected = json.loads((source / "tuning" / (name + ".json")).read_text())["winner"]
    if digest(winner) != digest(expected):
        raise ValueError("Rebuilt train/dev model differs from source tuning receipt")
    assert model is not None
    result = {
        "model": name,
        "cpu": cpu,
        "platform": platform.platform(),
        "python": sys.version,
        "warmup": warmup,
        "repeats": repeats,
        "targets": len(fixed),
        "target_domain": "source dev",
        "fixed_targets_sha256": digest(fixed),
        "vocabulary_sha256": digest(model.vocabulary),
        "build_countbank_and_dev_tune": distribution(builds),
        "score_single_target": distribution(scores),
        "top_k_five_single_context": distribution(rankings),
        "peak_rss_bytes": peak_rss_bytes(),
        "memory_scope": (
            "Whole isolated worker peak RSS/working set including provenance validation, "
            "imports, warmup and all repeats; not object size or incremental model memory"
        ),
        "timing_scope": (
            "CPU pinned; single BLAS thread; build train CountBank + dev counts + "
            "dev-only tuning; scores include token/context mapping; "
            "top-k exact vocabulary scan"
        ),
        "score_sha256": score_check,
        "top_k_sha256": ranking_check,
        "source_checkpoint_sha256": hashlib.sha256(
            (source / "models" / (name + ".json.gz")).read_bytes()
        ).hexdigest(),
    }
    if json.loads(receipt_path.read_text(encoding="utf-8")) != receipt:
        raise ValueError("Benchmark receipt changed during worker execution")
    with output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
    return result


def benchmark(run_id, warmup=1, repeats=5, targets=100):
    from core.src.data import ROOT
    from extensions.experiments import registry

    if (
        type(warmup) is not int
        or not 1 <= warmup <= 10
        or type(repeats) is not int
        or not 2 <= repeats <= 30
    ):
        raise ValueError("warmup1..10 and repeats2..30 required")
    if type(targets) is not int or not 1 <= targets <= 1000:
        raise ValueError("targets1..1000 required")
    source = registry.selected_run(run_id)
    config = registry.read_run(run_id)["config"]
    if config.get("experiment") != "document-research-v1":
        raise ValueError("Benchmark requires a completed document research run")
    output = registry.derived_directory(run_id, "benchmark")
    env = {
        **os.environ,
        **{
            name: "1"
            for name in (
                "OMP_NUM_THREADS",
                "OPENBLAS_NUM_THREADS",
                "MKL_NUM_THREADS",
                "NUMEXPR_NUM_THREADS",
            )
        },
        "PYTHONUTF8": "1",
        "PYTHONPYCACHEPREFIX": str(ROOT / ".cache" / "benchmark_pycache"),
    }
    temporary = ROOT / ".tmp" / "benchmark"
    temporary.mkdir(parents=True, exist_ok=True)
    env.update({key: str(temporary) for key in ("TEMP", "TMP", "TMPDIR")})
    results = {}
    for name in sorted(config["grid"]):
        path = output / (name + ".json")
        subprocess.run(
            [
                sys.executable,
                "-m",
                "extensions.experiments.benchmark",
                "--worker",
                "--source",
                str(source),
                "--model",
                name,
                "--output",
                str(path),
                "--warmup",
                str(warmup),
                "--repeats",
                str(repeats),
                "--targets",
                str(targets),
            ],
            check=True,
            cwd=ROOT,
            env=env,
        )
        results[name] = json.loads(path.read_text(encoding="utf-8"))
    registry.atomic_json(
        output / "summary.json",
        {
            "source_run": run_id,
            "benchmark_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "models": results,
            "warmup": warmup,
            "repeats": repeats,
            "targets": targets,
            "execution": (
                "One new serial subprocess per model; same fixed source-dev targets; "
                "no held-out test scoring"
            ),
        },
    )
    registry.complete_derived(output)
    return output


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id")
    parser.add_argument("--warmup", type=int, default=1)
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--targets", type=int, default=100)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--source", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--model", help=argparse.SUPPRESS)
    parser.add_argument("--output", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.worker:
        if not args.source or not args.model or not args.output:
            parser.error("Worker source/model/output required")
        worker(args.source, args.model, args.output, args.warmup, args.repeats, args.targets)
    else:
        if not args.run_id:
            parser.error("--run-id required")
        print(benchmark(args.run_id, args.warmup, args.repeats, args.targets))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
