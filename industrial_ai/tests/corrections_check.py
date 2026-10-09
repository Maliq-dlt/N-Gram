"""Run .venv/Scripts/python tests/corrections_check.py; requires FFmpeg/FFprobe."""

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import runtime  # isort: skip  # Workspace-local caches before native libraries.

import cv2
import numpy as np
from fastapi.testclient import TestClient

import app

checks = []


def check(value, name):
    assert value, name
    checks.append(name)


def run(args):
    return subprocess.run(args, capture_output=True, check=True, timeout=60).stdout


root = runtime.ROOT / ".tmp" / f"corrections_check_{uuid4()}"
folder = root / str(uuid4())
folder.mkdir(parents=True)
source = folder / "silent.mp4"
writer = cv2.VideoWriter(str(source), cv2.VideoWriter.fourcc(*"mp4v"), 10, (320, 180))
texture = np.random.default_rng(6).integers(30, 240, (50, 40, 3), dtype=np.uint8)
for i in range(15):
    frame = np.zeros((180, 320, 3), dtype=np.uint8)
    frame[60:110, 40 + i * 5 : 80 + i * 5] = texture
    writer.write(frame)
writer.release()
ffmpeg, ffprobe = shutil.which("ffmpeg"), shutil.which("ffprobe")
assert ffmpeg and ffprobe, "FFmpeg and FFprobe must be on PATH"
run(
    [
        ffmpeg,
        "-v",
        "error",
        "-y",
        "-i",
        str(source),
        "-f",
        "lavfi",
        "-i",
        "sine=frequency=440:duration=1.5",
        "-c:v",
        "libx264",
        "-c:a",
        "aac",
        "-shortest",
        str(folder / "original.mp4"),
    ]
)
shutil.copyfile(folder / "original.mp4", folder / "tracked.mp4")
shutil.copyfile(folder / "original.mp4", folder / "upload.bin")
summary = {
    "frames": 15,
    "fps": 10,
    "duration": 1.5,
    "line": 0.5,
    "tracks": [],
    "crossings": [],
    "object_classes": ["person", "car"],
    "occupancy": [{"seconds": i / 10, "person": 1, "car": 1} for i in range(15)],
}
app.write_json(folder / "summary.json", summary)
app.write_json(
    folder / "state.json",
    {
        "id": folder.name,
        "status": "done",
        "filename": "Controlled motion.mp4",
        "created_at": "2026-10-09",
    },
)
person = {
    "label": "person",
    "color": "#0f766e",
    "track_id": 7,
    "source": "detector",
    "bbox": [40 / 320, 60 / 180, 80 / 320, 110 / 180],
}
car = {
    "label": "car",
    "color": "#2563eb",
    "track_id": 8,
    "source": "detector",
    "bbox": [0.7, 0.2, 0.9, 0.4],
}
app.write_json(
    folder / "overlays.json",
    {
        "frames": [
            {
                "frame_index": i,
                "boxes": [
                    {
                        **person,
                        "bbox": [(40 + i * 5) / 320, 60 / 180, (80 + i * 5) / 320, 110 / 180],
                    },
                    car,
                ],
            }
            for i in range(15)
        ]
    },
)
original_hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.iterdir()}
prompt = {"label": "karung", "name": "Benda uji", "color": "#336699", "bbox": person["bbox"]}
base = f"/api/jobs/{folder.name}"
with patch.object(runtime, "JOBS", root), TestClient(app.app) as client:
    check(
        client.get(base + "/corrections").json() == {"revision": 0, "frames": []},
        "legacy empty corrections",
    )
    check(client.post(base + "/corrected-video").status_code == 409, "empty export rejected")
    started = client.post(
        base + "/tracking",
        json={"frame_index": 0, "boxes": [prompt], "revision": 0, "suppressed_ids": [7]},
    )
    check(started.status_code == 200, "tracking starts and persists initial row")
    session = base + "/tracking/" + started.json()["id"]
    stepped = client.post(session + "/step", json={"after_frame": 0, "count": 10}).json()
    check(
        stepped["revision"] == 2 and len(stepped["frames"]) == 10,
        "batched persistence has revision",
    )
    check(
        [b["label"] for b in stepped["frames"][-1]["boxes"]] == ["karung", "car"],
        "removed detector stays suppressed; other objects retained",
    )
    check(
        stepped["frames"][-1]["boxes"][0]["bbox"][0] > prompt["bbox"][0] + 0.1,
        "moving correction follows texture",
    )
    check(stepped["frames"][-1]["boxes"][0]["color"] == "#336699", "custom color preserved")
    saved = client.get(base + "/corrections").json()
    check(
        client.post(
            base + "/tracking", json={"frame_index": 0, "boxes": [], "revision": 0}
        ).status_code
        == 409,
        "stale tab cannot overwrite",
    )
    check(
        client.get(base + "/annotations").json()["frames"] == [],
        "propagated boxes never become reviewed annotations",
    )
    check(
        client.get(base).json()["summary"]["reviewed_occupancy"] == summary["occupancy"],
        "propagation never inflates chat counts",
    )
    check(
        client.get(base + "/dataset").status_code == 409,
        "unreviewed propagation never enters dataset",
    )
    # A second tab advances the revision; the first must fail before advancing pixels.
    second = client.post(
        base + "/tracking", json={"frame_index": 14, "boxes": [], "revision": 2}
    ).json()
    check(
        client.post(session + "/step", json={"after_frame": 10}).status_code == 409,
        "stale active session rejected",
    )
    client.post(session + "/stop")
    client.post(base + "/tracking/" + second["id"] + "/stop")
    saved = client.get(base + "/corrections").json()
# Lifespan shutdown and new client: no tracker or memory retained.
with patch.object(runtime, "JOBS", root), TestClient(app.app) as client:
    check(
        not app.tracking_sessions and client.get(base + "/corrections").json() == saved,
        "restart restores disk rows without live sessions",
    )
    first = client.post(base + "/corrected-video")
    check(
        first.status_code == 200 and first.headers["content-type"] == "video/mp4",
        "H264 corrected MP4 downloadable",
    )
    exported = next(folder.glob("corrected_*.mp4"))
    metadata = json.loads(
        run([ffprobe, "-v", "error", "-show_streams", "-of", "json", str(exported)])
    )
    streams = metadata["streams"]
    check(
        any(s["codec_name"] == "h264" and int(s["nb_frames"]) == 15 for s in streams),
        "frame count and H264 retained",
    )
    check(any(s["codec_type"] == "audio" for s in streams), "source audio retained")
    check(
        abs(float(next(s for s in streams if s["codec_type"] == "video")["duration"]) - 1.5) < 0.02,
        "duration remains synchronized",
    )
    cap = cv2.VideoCapture(str(exported))
    cap.set(cv2.CAP_PROP_POS_FRAMES, 10)
    ok, rendered = cap.read()
    cap.release()
    check(ok and rendered[60:111, 88:94].mean() > 20, "visible moving border exported")
    with patch.object(
        app, "render_video", side_effect=AssertionError("cached export must not rerender")
    ):
        check(
            client.post(base + "/corrected-video").content == first.content,
            "same revision reuses immutable export",
        )
    annotation = client.post(
        base + "/annotations",
        json={
            "frame_index": 10,
            "revision": 0,
            "complete": True,
            "boxes": [{"label": "bus", "bbox": [0.1, 0.1, 0.3, 0.3]}],
        },
    )
    check(annotation.status_code == 200, "reviewed exact-frame annotation saved independently")
    app.export_lock.acquire()
    try:
        check(
            client.post(base + "/corrected-video").status_code == 409,
            "busy export gives recoverable error",
        )
    finally:
        app.export_lock.release()
    with patch.object(app, "render_video", side_effect=ValueError("controlled failure")):
        check(client.post(base + "/corrected-video").status_code == 500, "export failure explicit")
    check(
        not app.compute_lock.locked() and len(list(folder.glob("corrected_*.mp4"))) == 1,
        "failure releases lock and keeps previous export",
    )
    check(
        client.post(base + "/corrected-video").status_code == 200,
        "new annotation revision creates second export",
    )
    latest = folder / f"corrected_c{saved['revision']}_a1.mp4"
    cap = cv2.VideoCapture(str(latest))
    cap.set(cv2.CAP_PROP_POS_FRAMES, 10)
    ok, rendered = cap.read()
    cap.release()
    check(
        ok and rendered[17:20, 32:97, 0].mean() > 50,
        "exact-frame manual boxes override propagated boxes",
    )
    check(
        hashlib.sha256(exported.read_bytes()).digest() == hashlib.sha256(first.content).digest(),
        "older corrected export untouched",
    )
check(
    all(
        hashlib.sha256((folder / n).read_bytes()).hexdigest() == h
        for n, h in original_hashes.items()
    ),
    "original AI, video, upload and summary unchanged",
)
(root / "report.json").write_text(
    json.dumps({"passed": len(checks), "checks": checks, "fixture": str(folder)}, indent=2),
    encoding="utf-8",
)
print(f"PASS: {len(checks)} correction persistence/export checks. Fixture: {folder}")
