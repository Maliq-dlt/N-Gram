"""Run .venv/Scripts/python tests/tracking_check.py (no test framework)."""

import json
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import runtime  # isort: skip  # Set workspace-local caches before library imports.

import cv2
import numpy as np
from fastapi.testclient import TestClient

import app
from prompt_tracking import PromptTracker

checks = []


def check(value, name):
    assert value, name
    checks.append(name)


with tempfile.TemporaryDirectory(dir=runtime.ROOT / ".tmp") as directory:
    root = Path(directory)
    job_id = str(uuid4())
    folder = root / job_id
    folder.mkdir()
    video = folder / "original.mp4"
    writer = cv2.VideoWriter(str(video), cv2.VideoWriter.fourcc(*"mp4v"), 10, (320, 180))
    rng = np.random.default_rng(6)
    texture = rng.integers(30, 240, (50, 40, 3), dtype=np.uint8)
    for index in range(15):
        frame = np.zeros((180, 320, 3), dtype=np.uint8)
        if index < 10:
            frame[60:110, 40 + index * 5 : 80 + index * 5] = texture
        writer.write(frame)
    writer.release()
    prompt = {
        "label": "karung",
        "name": "Benda uji",
        "color": "#336699",
        "bbox": [40 / 320, 60 / 180, 80 / 320, 110 / 180],
    }
    tracker = PromptTracker(
        video, 5, [{**prompt, "bbox": [65 / 320, 60 / 180, 105 / 320, 110 / 180]}]
    )
    check(tracker.index == 5, "starts at annotated frame, not frame zero")
    rows = tracker.advance(4)["frames"]
    check([r["frame_index"] for r in rows] == [6, 7, 8, 9], "incremental consecutive frames")
    check(len(rows[-1]["boxes"]) == 1, "textured object followed")
    check(
        abs(rows[-1]["boxes"][0]["bbox"][0] * 320 - 85) < 3,
        "movement matches controlled ground truth within 3px",
    )
    check(
        rows[-1]["boxes"][0]["name"] == "Benda uji" and rows[-1]["boxes"][0]["color"] == "#336699",
        "custom label, name and color survive",
    )
    lost = tracker.advance(2)["frames"][-1]
    check(
        not lost["boxes"] and len(lost["lost"]) == 1,
        "disappeared object stops instead of inventing a box",
    )
    check(tracker.advance(10)["ended"], "short clip reaches end without loop")
    check(tracker.advance(1)["frames"] == [], "ended session remains ended")
    tracker.close()
    tracker = PromptTracker(video, 0, [{"label": "helmet", "bbox": [0, 0, 0.05, 0.05]}])
    check(len(tracker.snapshot()["lost"]) == 1, "textureless box reports unavailable tracking")
    tracker.close()
    # Cached detector IDs anchor geometry without adopting a neighboring object's ID.
    overlays = [
        {
            "frame_index": i,
            "boxes": [
                {
                    **prompt,
                    "track_id": 7,
                    "bbox": [(40 + i * 5) / 320, 60 / 180, (80 + i * 5) / 320, 110 / 180],
                },
                {**prompt, "track_id": 99, "bbox": [0.6, 0.3, 0.8, 0.6]},
            ],
        }
        for i in range(10)
    ]
    tracker = PromptTracker(video, 0, [prompt], overlays)
    check(tracker.objects[0]["anchor"] == 7, "unambiguous initial detector ID matched")
    result = tracker.advance(9)["frames"][-1]
    check(
        abs(result["boxes"][0]["bbox"][0] * 320 - 85) < 1,
        "same cached ID guides geometry across consecutive frames",
    )
    tracker.close()
    jumped = [
        {"frame_index": 0, "boxes": overlays[0]["boxes"]},
        {
            "frame_index": 1,
            "boxes": [
                {**prompt, "track_id": 7, "bbox": [0.7, 0.3, 0.9, 0.6]},
                {**prompt, "track_id": 99},
            ],
        },
    ]
    tracker = PromptTracker(video, 0, [prompt], jumped)
    result = tracker.advance(1)["frames"][0]
    check(
        not result["boxes"] and len(result["lost"]) == 1,
        "detector jump stops target instead of swapping to nearby ID",
    )
    tracker.close()
    ambiguous = [
        {"frame_index": 0, "boxes": [{**prompt, "track_id": 7}, {**prompt, "track_id": 99}]}
    ]
    tracker = PromptTracker(video, 0, [prompt], ambiguous)
    check(tracker.objects[0]["anchor"] is None, "ambiguous initial overlap stays optical flow")
    tracker.close()
    tracker = PromptTracker(video, 0, [prompt])
    before_points = len(tracker.objects[0]["points"])
    tracker.advance(2)
    check(
        len(tracker.objects[0]["points"]) <= before_points,
        "unanchored points are retained, never replenished with neighbor features",
    )
    tracker.close()
    (folder / "state.json").write_text(json.dumps({"id": job_id, "status": "done"}))
    (folder / "summary.json").write_text(json.dumps({"frames": 15, "fps": 10, "duration": 1.5}))
    client = TestClient(app.app)
    with patch.object(runtime, "JOBS", root):
        base = f"/api/jobs/{job_id}"
        check(
            client.post(base + "/tracking", json={"frame_index": 15, "boxes": [prompt]}).status_code
            == 422,
            "out of bounds prompt rejected",
        )
        check(
            client.post(
                base + "/tracking",
                json={"frame_index": 0, "boxes": [{**prompt, "bbox": [0, 0, "NaN", 1]}]},
            ).status_code
            == 422,
            "non-finite box rejected",
        )
        check(
            client.post(
                base + "/tracking",
                json={"frame_index": 0, "boxes": [{**prompt, "bbox": [0.4, 0, 0.1, 1]}]},
            ).status_code
            == 422,
            "inverted box rejected",
        )
        check(
            client.post(
                base + "/tracking",
                json={"frame_index": 0, "boxes": [prompt]},
                headers={"origin": "http://external.invalid"},
            ).status_code
            == 403,
            "external origin rejected",
        )
        response = client.post(base + "/tracking", json={"frame_index": 0, "boxes": [prompt]})
        check(response.status_code == 200, "prompt API initializes native tracker")
        session = response.json()["id"]
        path = base + "/tracking/" + session
        check(
            client.post(path + "/step", json={"after_frame": 1}).status_code == 409,
            "stale cursor rejected",
        )
        check(
            client.post(path + "/step", json={"after_frame": 0, "count": 11}).status_code == 422,
            "unbounded batch rejected",
        )
        check(
            client.post(
                f"/api/jobs/{uuid4()}/tracking/{session}/step", json={"after_frame": 0}
            ).status_code
            == 404,
            "session belongs to its video",
        )
        result = client.post(path + "/step", json={"after_frame": 0, "count": 3}).json()
        check(
            result["next_frame"] == 3 and len(result["frames"]) == 3,
            "API advances only requested frames",
        )
        check(
            not (folder / "annotations.json").exists()
            and not list(folder.glob("annotation_*.jpg")),
            "generated tracks never become reviewed labels",
        )
        check(
            client.get(base + "/overlays").json() == {"frames": []},
            "legacy jobs work without an overlay file",
        )
        check(client.post(path + "/stop").json()["stopped"], "session resources released")
        check(
            client.post(path + "/step", json={"after_frame": 3}).status_code == 404,
            "closed session cannot update",
        )
        empty = client.post(base + "/tracking", json={"frame_index": 14, "boxes": []}).json()
        check(
            client.post(
                base + "/tracking/" + empty["id"] + "/step", json={"after_frame": 14}
            ).json()["ended"],
            "empty prompt and final frame supported",
        )
        client.post(base + "/tracking/" + empty["id"] + "/stop")

# Existing moving pedestrian footage is read-only; its annotations are not ground truth.
source = runtime.JOBS / "a553e7be-e25f-4920-bf49-674477923f3e"
real = None
if source.is_dir():
    summary = json.loads((source / "summary.json").read_text())
    capture = cv2.VideoCapture(str(source / "original.mp4"))
    width = capture.get(3)
    height = capture.get(4)
    capture.release()
    box = summary["tracks"][0]["evidence_bbox"]
    prompt = {
        "label": "person",
        "name": None,
        "color": None,
        "bbox": [box[0] / width, box[1] / height, box[2] / width, box[3] / height],
    }
    tracker = PromptTracker(source / "original.mp4", 0, [prompt])
    started = time.perf_counter()
    rows = tracker.advance(10)["frames"] + tracker.advance(10)["frames"]
    elapsed = time.perf_counter() - started
    check(len(rows) == 20, "real moving footage: twenty subsequent frames")
    check(bool(rows[-1]["boxes"]), "real moving footage: target still followed at two seconds")
    check(
        rows[-1]["boxes"][0]["bbox"][0] < prompt["bbox"][0] - 0.15,
        "real moving footage: trajectory follows leftward motion",
    )
    real = {
        "job": source.name,
        "frames": len(rows),
        "elapsed_seconds": elapsed,
        "seconds_per_frame": elapsed / len(rows),
        "last": rows[-1],
    }
    tracker.close()
report = {
    "checks": checks,
    "passed": len(checks),
    "real_clip": real,
    "limits": "Controlled motion checks and one real target; no factory accuracy claim.",
}
(runtime.ROOT / ".tmp/tracking_check.json").write_text(
    json.dumps(report, indent=2), encoding="utf-8"
)
print(
    f"PASS: {len(checks)} tracking checks; real clip {real['seconds_per_frame']:.4f} seconds/frame."
    if real
    else f"PASS: {len(checks)} tracking checks."
)
