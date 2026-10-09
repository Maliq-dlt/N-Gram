"""Queue, approval, recovery and real media export. Run with the studio Python."""

import json
import shutil
import sys
import threading
import time
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import runtime  # isort: skip

import cv2
import numpy as np
from access_fixture import authorize
from fastapi.testclient import TestClient

import access
import app
from operations import WorkCancelled, check_cancel, run_command

root = runtime.ROOT / ".tmp" / f"workflow_check_{uuid4()}"
jobs, trainings = root / "jobs", root / "trainings"
jobs.mkdir(parents=True)
trainings.mkdir()
checks = []


def check(value, label):
    assert value, label
    checks.append(label)


def fixture(offset=0, status="done"):
    folder = jobs / str(uuid4())
    folder.mkdir()
    writer = cv2.VideoWriter(
        str(folder / "original.mp4"), cv2.VideoWriter.fourcc(*"mp4v"), 10, (160, 96)
    )
    for i in range(12):
        image = np.zeros((96, 160, 3), np.uint8)
        cv2.rectangle(image, (20 + i + offset, 20), (50 + i + offset, 70), (60, 140, 220), -1)
        writer.write(image)
    writer.release()
    shutil.copyfile(folder / "original.mp4", folder / "upload.bin")
    shutil.copyfile(folder / "original.mp4", folder / "tracked.mp4")
    app.write_json(
        folder / "state.json",
        {
            "id": folder.name,
            "status": status,
            "filename": "controlled.mp4",
            "created_at": "2026-10-09",
            "line": 0.5,
            "progress": 100,
            "bytes": (folder / "upload.bin").stat().st_size,
        },
    )
    app.write_json(
        folder / "summary.json",
        {
            "frames": 12,
            "fps": 10,
            "duration": 1.2,
            "tracks": [],
            "crossings": [],
            "occupancy": [{"seconds": i / 10, "person": 0} for i in range(12)],
        },
    )
    app.write_json(
        folder / "selection.json",
        {
            "groups": ["objects", "helmets"],
            "frames": [
                {"frame_index": 0, "review_flags": [{"label": "person"}]},
                {"frame_index": 5},
            ],
        },
    )
    if runtime.JOBS == jobs and access.principal.get() is not None:
        access.register("job", folder)
    return folder


source, second = fixture(), fixture(15)
interrupted = fixture(status="processing")
box = {"label": "person", "bbox": [0.1, 0.1, 0.5, 0.8]}
helmet = {"label": "Hardhat", "bbox": [0.2, 0.1, 0.3, 0.2]}
base = "/api/jobs/" + source.name


def save(client, index, group, boxes):
    data = client.get(base + "/annotations").json()
    return client.post(
        base + "/annotations",
        json={
            "frame_index": index,
            "revision": data["revision"],
            "complete": group == "objects",
            "helmets_complete": group == "helmets",
            "learn_group": group,
            "boxes": boxes,
        },
    )


def wait(client, url):
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        data = client.get(url).json()
        if data["status"] not in {"queued", "processing", "cancelling"}:
            return data
        time.sleep(0.02)
    raise AssertionError("Worker did not finish: " + url)


with (
    patch.object(runtime, "JOBS", jobs),
    patch.object(app, "training_root", trainings),
    TestClient(app.app) as client,
):
    authorize(client)
    check(
        client.get("/api/jobs/" + interrupted.name).json()["status"] == "error",
        "restart marks interrupted work retryable",
    )
    queue = client.get(base + "/review-queue").json()
    check(
        queue["pending"] == 2 and "Deteksi meragukan" in queue["positions"][0]["reasons"],
        "queue includes samples and uncertainty",
    )
    check(
        save(client, 0, "objects", [box, helmet]).status_code == 200, "objects explicitly approved"
    )
    check(
        save(client, 0, "helmets", [box, helmet]).json()["frames"][0]["learn_groups"]
        == ["objects", "helmets"],
        "approval of both groups survives sequential save",
    )
    check(
        client.post(base + "/learn", json={}).json()["status"] == "waiting",
        "pending queue blocks training",
    )
    revised = {**box, "bbox": [0.2, 0.1, 0.6, 0.8]}
    row = save(client, 0, "helmets", [revised, helmet]).json()["frames"][0]
    check(
        row["learn_groups"] == ["helmets"] and not row["complete"],
        "changed other-group geometry invalidates approval and count",
    )
    save(client, 0, "objects", [revised, helmet])
    save(client, 5, "objects", [revised])
    check(
        client.get(base + "/review-queue").json()["pending"] == 0, "all selected positions approved"
    )
    check(
        client.post(base + "/learn", json={}).json()["status"] == "waiting"
        and not list(trainings.iterdir()),
        "one source never trains or creates fake model",
    )
    app.write_json(
        source / "tracking_corrections.json",
        {
            "revision": 1,
            "frames": [
                {"frame_index": 7, "boxes": [], "lost": [{**box, "track_id": 2}]},
                {"frame_index": 8, "boxes": [], "lost": [{**box, "track_id": 2}]},
            ],
        },
    )
    queue = client.get(base + "/review-queue").json()
    check(
        [r["frame_index"] for r in queue["positions"]] == [0, 5, 7],
        "lost onset produces one review target and accepts dict metadata",
    )
    check(
        client.get(base + "/review-queue?group=helmets").json()["total"] == 2,
        "object lost target excluded from helmet queue",
    )
    app.compute_lock.acquire()
    try:
        state = client.post(base + "/exports").json()
        result = wait(client, base + "/exports/" + state["id"])
        check(result["status"] == "done", "real async export runs independently of GPU lock")
    finally:
        app.compute_lock.release()
    output = source / result["filename"]
    capture = cv2.VideoCapture(str(output))
    ok, image = capture.read()
    capture.release()
    check(ok and image.shape[:2] == (96, 160), "corrected MP4 decodes")
    check(
        client.get(result["media_url"]).status_code == 200,
        "corrected media allowlist serves result",
    )
    check(client.post(base + "/exports").json()["id"] == state["id"], "same revision export reused")
    check(
        client.get(base + "/exports/../../state").status_code == 404,
        "export path boundary validated",
    )
    event = threading.Event()
    event.set()
    try:
        run_command([sys.executable, "-c", "print(1)"], cancel=event)
        raise AssertionError("Expected cancellation")
    except WorkCancelled:
        check(True, "native process checks pre-cancel")
    event.clear()
    timer = threading.Timer(0.1, event.set)
    timer.start()
    try:
        run_command([sys.executable, "-c", "import time;time.sleep(20)"], cancel=event)
        raise AssertionError("Expected cancellation")
    except WorkCancelled:
        check(True, "running child killed and reaped on cancel")
    finally:
        timer.join()

    def controlled_analysis(folder, line, progress, **options):
        while True:
            check_cancel(options["cancel"])
            time.sleep(0.01)

    with patch.object(app, "process_video", controlled_analysis):
        retried = client.post("/api/jobs/" + interrupted.name + "/retry", json={})
        check(retried.status_code == 202, "complete interrupted upload retried without reupload")
        new = retried.json()["id"]
        newbase = "/api/jobs/" + new
        check(
            (jobs / new / "upload.bin").read_bytes() == (interrupted / "upload.bin").read_bytes(),
            "retry preserves source and copies complete upload",
        )
        client.post(newbase + "/cancel")
        check(
            wait(client, newbase)["status"] == "cancelled" and not app.compute_lock.locked(),
            "analysis cancellation stops worker and releases lock",
        )
    app.update_state(interrupted, bytes=1)
    check(
        client.post("/api/jobs/" + interrupted.name + "/retry", json={}).status_code == 409
        and not app.compute_lock.locked(),
        "partial upload refused and lock released",
    )
    with (
        patch.object(app, "run_export", wraps=app.run_export),
        patch.object(app, "render_video", side_effect=ValueError("controlled export failure")),
    ):
        save(client, 5, "objects", [box])
        state = client.post(base + "/exports").json()
        check(
            wait(client, base + "/exports/" + state["id"])["status"] == "error"
            and not app.export_lock.locked(),
            "export failure visible and lock released",
        )
    check(output.is_file(), "failed revision preserves older export")
    app.active_work[source] = threading.Event()
    check(
        client.post(base + "/cancel").json()["status"] == "done",
        "late cancellation cannot change completed status",
    )
    app.finish_work(source)

    def controlled_training(folder, state, progress, cancel):
        while True:
            check_cancel(cancel)
            time.sleep(0.01)

    save(client, 7, "objects", [box])
    second_base = "/api/jobs/" + second.name
    for index in [0, 5]:
        data = client.get(second_base + "/annotations").json()
        client.post(
            second_base + "/annotations",
            json={
                "frame_index": index,
                "revision": data["revision"],
                "complete": True,
                "learn_group": "objects",
                "boxes": [box],
            },
        )
    with patch("detector_training.train_candidate", controlled_training):
        state = app.start_detector_training(
            app.DetectorTrainingRequest(job_ids=[source.name, second.name]), approved_only=True
        )
        client.post("/api/training/" + state["id"] + "/cancel")
        check(
            wait(client, "/api/training/" + state["id"])["status"] == "cancelled"
            and not app.compute_lock.locked(),
            "training cancellation releases AI and keeps candidate unavailable",
        )
    check(
        app.read_state(trainings / state["id"])["status"] == "cancelled",
        "cancelled model remains unavailable",
    )

    # Routing regression only; real parameter updates are tested in training_check.py.
    with patch.object(app, "start_detector_training", return_value={"status": "queued"}) as start:
        client.post(base + "/learn", json={})
        fingerprint = start.call_args.kwargs["fingerprint"]
        check(
            bool(start.call_args.kwargs["review_snapshot"]),
            "training receives the exact reviewed snapshot used for its fingerprint",
        )
    candidate = trainings / state["id"]
    app.update_state(candidate, status="done", fingerprint=fingerprint)
    failed = fixture(status="error")
    app.update_state(failed, source_job_id=source.name, model_id=candidate.name)
    replacement_id = str(uuid4())
    with patch.object(app, "reanalyze", return_value={"id": replacement_id}) as reanalyze:
        reused = client.post(base + "/learn", json={}).json()
        check(
            reanalyze.call_count == 1 and reused["result_job_id"] == replacement_id,
            "completed candidate retries a failed followup without retraining",
        )
    app.update_state(failed, status="done")
    with patch.object(
        app, "reanalyze", side_effect=AssertionError("Unexpected duplicate analysis")
    ):
        check(
            client.post(base + "/learn", json={}).json()["result_job_id"] == failed.name,
            "completed candidate reuses a successful analysis",
        )


(root / "report.json").write_text(json.dumps({"checks": checks, "passed": len(checks)}, indent=2))
print(f"PASS: {len(checks)} workflow checks. Evidence: {root}")
