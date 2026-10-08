"""Real detector fine-tuning from reviewed frames; separate candidate and source split."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from runtime import MODELS


def collect_reviewed(folders: list[Path], group: str, *, approved_only: bool = False) -> list[dict]:
    flag = "complete" if group == "objects" else "helmets_complete"
    rows = []
    for folder in folders:
        with (folder / "upload.bin").open("rb") as source:
            source_hash = hashlib.file_digest(source, "sha256").hexdigest()
        annotations = folder / "annotations.json"
        if not annotations.is_file():
            continue
        data = json.loads(annotations.read_text(encoding="utf-8"))
        for frame in data["frames"]:
            if not frame.get(flag, False) or (
                approved_only and group not in frame.get("learn_groups", [])
            ):
                continue
            boxes = [
                b
                for b in frame["boxes"]
                if (b["label"] in {"Hardhat", "NO-Hardhat"}) == (group == "helmets")
            ]
            image = folder / f"annotation_{frame['frame_index']}.jpg"
            if not image.is_file():
                raise ValueError("Foto anotasi hilang; simpan koreksi kembali.")
            rows.append(
                {
                    "job_id": folder.name,
                    "source_sha256": source_hash,
                    "revision": data["revision"],
                    "updated_at": frame.get("updated_at", ""),
                    "frame_index": frame["frame_index"],
                    "image": image,
                    "boxes": boxes,
                }
            )
    if approved_only:
        rows = list(
            {
                (r["source_sha256"], r["frame_index"]): r
                for r in sorted(rows, key=lambda r: r["updated_at"])
            }.values()
        )
    if len({r["source_sha256"] for r in rows}) < 2:
        raise ValueError(
            "Tambahkan koreksi lengkap dari video sumber berbeda. Minimal dua sumber diperlukan agar latihan dan evaluasi terpisah."
        )
    if not any(r["boxes"] for r in rows):
        raise ValueError("Belum ada kotak pada kelompok yang dipilih.")
    return rows


def build_dataset(folder: Path, rows: list[dict], group: str, base_names: list[str]) -> dict:
    observed = {b["label"] for r in rows for b in r["boxes"]}
    names = base_names + sorted(observed - set(base_names))
    sources = sorted({r["source_sha256"] for r in rows})
    val_sources = set(sources[-max(1, len(sources) // 5) :])
    if not any(r["boxes"] for r in rows if r["source_sha256"] not in val_sources):
        positive = next(r["source_sha256"] for r in rows if r["boxes"])
        val_sources.remove(positive)
        val_sources.add(next(s for s in sources if s != positive))
    counts = {"train": 0, "val": 0}
    manifest = []
    for row in rows:
        split = "val" if row["source_sha256"] in val_sources else "train"
        stem = f"{row['job_id']}_{row['frame_index']}"
        image_dir = folder / "dataset/images" / split
        label_dir = folder / "dataset/labels" / split
        image_dir.mkdir(parents=True, exist_ok=True)
        label_dir.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(row["image"], image_dir / (stem + ".jpg"))
        labels = []
        for b in row["boxes"]:
            x1, y1, x2, y2 = b["bbox"]
            if not (0 <= x1 < x2 <= 1 and 0 <= y1 < y2 <= 1):
                raise ValueError("Koordinat dataset tidak valid.")
            labels.append(
                f"{names.index(b['label'])} {(x1 + x2) / 2:.6f} {(y1 + y2) / 2:.6f} {x2 - x1:.6f} {y2 - y1:.6f}"
            )
        (label_dir / (stem + ".txt")).write_text("\n".join(labels) + "\n", encoding="utf-8")
        counts[split] += 1
        manifest.append(
            {
                **{k: v for k, v in row.items() if k != "image"},
                "split": split,
                "image_sha256": hashlib.sha256(row["image"].read_bytes()).hexdigest(),
            }
        )
    config = {
        "path": (folder / "dataset").resolve().as_posix(),
        "train": "images/train",
        "val": "images/val",
        "names": dict(enumerate(names)),
    }
    # JSON is valid YAML; no extra YAML dependency or generated shell commands.
    (folder / "dataset/data.yaml").write_text(json.dumps(config, indent=2), encoding="utf-8")
    provenance = {
        "group": group,
        "names": names,
        "learned_classes": sorted(observed),
        "frames": manifest,
        "counts": counts,
        "split_unit": "source upload SHA256",
        "notice": "Small local pilot. User-complete labels are not independently validated; no factory accuracy claim.",
    }
    (folder / "dataset/provenance.json").write_text(
        json.dumps(provenance, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return provenance


def train_once(folder: Path, state: dict, device: str, progress) -> dict:
    import time

    import torch
    from ultralytics import YOLO

    folder = folder.resolve()
    torch.set_num_threads(8)
    base = MODELS / ("yolo26n.pt" if state["group"] == "objects" else "helmet.pt")
    model = YOLO(str(base))
    attempt = "gpu_attempt" if device.startswith("cuda") else "cpu_attempt"

    def epoch_done(trainer):
        progress(
            5 + int(90 * (trainer.epoch + 1) / state["epochs"]),
            f"Training epoch {trainer.epoch + 1}/{state['epochs']}",
        )

    model.add_callback("on_fit_epoch_end", epoch_done)
    started = time.monotonic()
    result = model.train(
        data=str(folder / "dataset/data.yaml"),
        epochs=state["epochs"],
        imgsz=640,
        batch=2,
        device=int(device.split(":")[1]) if device.startswith("cuda") else "cpu",
        workers=0,
        project=str(folder),
        name=attempt,
        exist_ok=False,
        plots=False,
        cache=False,
        amp=False,
        freeze=10,
        seed=42,
        deterministic=True,
        optimizer="AdamW",
        lr0=0.001,
        warmup_epochs=0,
        mosaic=0,
        close_mosaic=0,
        patience=state["epochs"],
        verbose=False,
    )
    checkpoint = folder / attempt / "weights/best.pt"
    if not checkpoint.is_file():
        raise RuntimeError("Training tidak menghasilkan checkpoint.")
    (folder / "weights").mkdir(exist_ok=True)
    shutil.copyfile(checkpoint, folder / "weights/best.pt")
    metrics = {k: float(v) for k, v in result.results_dict.items()}
    return {
        "device": device,
        "training_seconds": round(time.monotonic() - started, 2),
        "metrics": metrics,
        "checkpoint_sha256": hashlib.sha256(checkpoint.read_bytes()).hexdigest(),
        "base_sha256": hashlib.sha256(base.read_bytes()).hexdigest(),
    }


def train_candidate(folder: Path, state: dict, progress) -> dict:
    import gc

    import torch
    from ultralytics import YOLO

    import chat
    from runtime import select_device

    chat.release_model()
    base = MODELS / ("yolo26n.pt" if state["group"] == "objects" else "helmet.pt")
    names = [n.replace(" ", "_") for n in YOLO(str(base)).names.values()]
    rows = [{**r, "image": Path(r["image"])} for r in state["review_snapshot"]]
    provenance = build_dataset(folder, rows, state["group"], names)
    device, reason = select_device(state["device_preference"], 2)
    fallback = False
    try:
        result = train_once(folder, state, device, progress)
    except torch.cuda.OutOfMemoryError:
        if device == "cpu":
            raise
        fallback = True
    if fallback:
        gc.collect()
        torch.cuda.empty_cache()
        device, reason = "cpu", "VRAM habis; training diulang dengan CPU."
        result = train_once(folder, state, device, progress)
    return {
        **result,
        "device_reason": reason,
        "learned_classes": provenance["learned_classes"],
        "dataset_counts": provenance["counts"],
        "validation_notice": provenance["notice"],
    }
