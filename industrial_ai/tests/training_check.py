"""Real optimizer/checkpoint/reanalysis smoke on explicitly controlled test data."""

import hashlib
import json
import shutil
import sys
import time
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import runtime  # isort: skip

import cv2
import numpy as np
import torch
from access_fixture import authorize
from fastapi.testclient import TestClient
from ultralytics import YOLO

import app

root = runtime.ROOT / ".tmp" / f"training_check_{uuid4()}"
jobs, trainings = root / "jobs", root / "trainings"
jobs.mkdir(parents=True)
trainings.mkdir()
group = sys.argv[2] if len(sys.argv) > 2 else "objects"
assert group in {"objects", "helmets"}
base_name = "yolo26n.pt" if group == "objects" else "helmet.pt"
folders = []
checks = []


def check(value, label):
    assert value, label
    checks.append(label)


for n in range(2):
    folder = jobs / str(uuid4())
    folder.mkdir()
    folders.append(folder)
    writer = cv2.VideoWriter(
        str(folder / "original.mp4"), cv2.VideoWriter.fourcc(*"mp4v"), 10, (160, 96)
    )
    for i in range(6):
        frame = np.random.default_rng(n * 10 + i).integers(10, 35, (96, 160, 3), dtype=np.uint8)
        cv2.rectangle(
            frame, (25 + i + n * 15, 20), (60 + i + n * 15, 80), (180, 100 + n * 50, 80), -1
        )
        writer.write(frame)
    writer.release()
    shutil.copyfile(folder / "original.mp4", folder / "upload.bin")
    app.write_json(
        folder / "state.json",
        {
            "id": folder.name,
            "status": "done",
            "filename": "controlled-training.mp4",
            "created_at": "2026-10-09",
            "line": 0.5,
            "progress": 100,
            "bytes": (folder / "upload.bin").stat().st_size,
        },
    )
    app.write_json(
        folder / "summary.json",
        {
            "frames": 6,
            "fps": 10,
            "duration": 0.6,
            "tracks": [],
            "crossings": [],
            "occupancy": [{"seconds": i / 10, "person": 0} for i in range(6)],
        },
    )
    app.write_json(folder / "selection.json", {"groups": [group], "frames": [{"frame_index": 0}]})

base_hashes = {
    name: hashlib.sha256((runtime.MODELS / name).read_bytes()).hexdigest()
    for name in ["yolo26n.pt", "helmet.pt"]
}
with (
    patch.object(runtime, "JOBS", jobs),
    patch.object(app, "training_root", trainings),
    TestClient(app.app) as client,
):
    authorize(client)
    for folder in folders:
        response = client.post(
            "/api/jobs/" + folder.name + "/annotations",
            json={
                "frame_index": 0,
                "revision": 0,
                "complete": group == "objects",
                "helmets_complete": group == "helmets",
                "learn_group": group,
                "boxes": [
                    {
                        "label": "person" if group == "objects" else "Hardhat",
                        "bbox": [0.15, 0.2, 0.55, 0.9],
                    }
                ],
            },
        )
        check(response.status_code == 200, "controlled fixture approved for test only")
    state = app.start_detector_training(
        app.DetectorTrainingRequest(
            job_ids=[f.name for f in folders],
            epochs=1,
            group=group,
            device=sys.argv[1] if len(sys.argv) > 1 else "cpu",
        ),
        approved_only=True,
        followup_job_id=folders[0].name,
    )
    deadline = time.monotonic() + 300
    while time.monotonic() < deadline:
        state = client.get("/api/training/" + state["id"]).json()
        if state["status"] in {"error", "cancelled"}:
            raise AssertionError(state)
        if state.get("result_job_id"):
            analysis = client.get("/api/jobs/" + state["result_job_id"]).json()
            if analysis["status"] in {"error", "cancelled"}:
                raise AssertionError(analysis)
            if analysis["status"] == "done":
                break
        time.sleep(0.1)
    else:
        raise AssertionError("Real training/inference exceeded 300s")
    candidate = trainings / state["id"] / "weights/best.pt"
    check(
        state["checkpoint_sha256"] == hashlib.sha256(candidate.read_bytes()).hexdigest(),
        "actual trained checkpoint matches status SHA256",
    )
    before = dict(YOLO(str(runtime.MODELS / base_name)).model.named_parameters())
    after = dict(YOLO(str(candidate)).model.named_parameters())
    changed = [
        k
        for k, v in after.items()
        if k in before
        and v.shape == before[k].shape
        and v.is_floating_point()
        and not torch.equal(v.detach().half(), before[k].detach().half())
    ]
    check(bool(changed), "optimizer changed actual model parameters beyond checkpoint rounding")
    check(analysis["summary"]["model_id"] == state["id"], "real reanalysis uses trained candidate")
    check(
        analysis["summary"]["learning_evidence"]["checkpoint_sha256"] == state["checkpoint_sha256"],
        "new result carries genuine training evidence",
    )
    capture = cv2.VideoCapture(str(jobs / analysis["id"] / "tracked.mp4"))
    ok, image = capture.read()
    capture.release()
    check(ok and image.size > 0, "new model video decodes")
    provenance = json.loads((trainings / state["id"] / "dataset/provenance.json").read_text())
    train = {r["source_sha256"] for r in provenance["frames"] if r["split"] == "train"}
    val = {r["source_sha256"] for r in provenance["frames"] if r["split"] == "val"}
    check(train and val and train.isdisjoint(val), "training and validation sources separated")
check(
    all(
        hashlib.sha256((runtime.MODELS / n).read_bytes()).hexdigest() == h
        for n, h in base_hashes.items()
    ),
    "base model weights unchanged",
)
report = {
    "checks": checks,
    "passed": len(checks),
    "training": state,
    "result_job_id": analysis["id"],
    "changed_parameters": len(changed),
    "notice": "Controlled functional smoke only; no accuracy evaluation or approval of user/public drafts.",
}
(root / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(
    f"PASS: {len(checks)} real learning checks; {len(changed)} parameters changed. Evidence: {root}"
)
