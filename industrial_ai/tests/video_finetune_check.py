"""Standalone checks for segmentation, selection and original-source split safety."""

import hashlib
import json
import sys
from itertools import pairwise
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import runtime  # isort: skip

import cv2
import numpy as np

import access
import app
from detector_training import build_dataset, collect_reviewed
from video_finetune import dedup_frames, probe, segment_video, select_frames

root = runtime.ROOT / ".tmp" / f"video_finetune_check_{uuid4()}"
root.mkdir()
source = root / "source.mp4"
writer = cv2.VideoWriter(str(source), cv2.VideoWriter.fourcc(*"mp4v"), 10, (320, 180))
for image in np.random.default_rng(42).integers(0, 255, (31, 180, 320, 3), dtype=np.uint8):
    writer.write(image)
writer.release()
before = hashlib.sha256(source.read_bytes()).hexdigest()
segments = segment_video(source, root / "segments", 2)
assert len(segments) == 2
assert all(probe(s["path"])["duration"] <= 2.1 for s in segments)
assert abs(sum(s["source"]["duration"] for s in segments) - 3.1) < 0.11
assert segments[0]["source"]["source_sha256"] == segments[1]["source"]["source_sha256"] == before
assert segments[1]["source"]["start_seconds"] == 2
selected = select_frames(segments[0]["path"], limit=5, stride=2)
assert 0 < len(selected) <= 5
assert all(b["frame_index"] - a["frame_index"] >= 4 for a, b in pairwise(selected))
assert dedup_frames([{"frame_index": 0, "phash": 0}, {"frame_index": 10, "phash": 1}], 2, []) == [
    {"frame_index": 0, "phash": 0}
]
assert (
    len(
        dedup_frames(
            [{"frame_index": 0, "phash": 0}, {"frame_index": 10, "phash": (1 << 12) - 1}], 2, []
        )
    )
    == 2
)
folders = []
for index, segment in enumerate(segments):
    folder = root / f"job_{index}"
    folder.mkdir()
    (folder / "upload.bin").write_bytes(segment["path"].read_bytes())
    (folder / "source.json").write_text(json.dumps(segment["source"]))
    row = {
        "frame_index": 0,
        "seconds": 0,
        "complete": True,
        "helmets_complete": False,
        "learn_groups": ["objects"],
        "boxes": [{"label": "person", "bbox": [0.1, 0.1, 0.3, 0.4]}],
    }
    (folder / "annotations.json").write_text(json.dumps({"revision": 1, "frames": [row]}))
    cv2.imwrite(str(folder / "annotation_0.jpg"), np.zeros((180, 320, 3), dtype=np.uint8))
    folders.append(folder)
try:
    collect_reviewed(folders, "objects", approved_only=True)
except ValueError as exc:
    assert "dua sumber" in str(exc)
else:
    raise AssertionError("Two segments from one video must not qualify as two sources")
other = root / "independent_source"
other.mkdir()
(other / "upload.bin").write_bytes(b"independent controlled fixture")
(other / "annotations.json").write_text(json.dumps({"revision": 1, "frames": [row]}))
cv2.imwrite(str(other / "annotation_0.jpg"), np.zeros((180, 320, 3), dtype=np.uint8))
rows = collect_reviewed([*folders, other], "objects", approved_only=True)
assert len(rows) == 3, "Same local frame in separate segments is not a duplicate global position"
dataset = root / "training_candidate"
dataset.mkdir()
provenance = build_dataset(dataset, rows, "objects", ["person"])
source_splits = {}
for frame in provenance["frames"]:
    source_splits.setdefault(frame["source_sha256"], set()).add(frame["split"])
assert len(source_splits) == 2 and all(len(s) == 1 for s in source_splits.values())
assert set.union(*source_splits.values()) == {"train", "val"}
app.write_json(
    folders[0] / "state.json",
    {
        "filename": "segment.mp4",
        "line": 0.5,
        "status": "done",
        "bytes": (folders[0] / "upload.bin").stat().st_size,
    },
)
with (
    patch.object(app, "job_folder", return_value=folders[0]),
    patch.object(runtime, "JOBS", root),
    patch.object(app.executor, "submit"),
):
    user = access.store().bootstrap("owner", "controlled-test-password-123")
    access.principal.set({**user, "tenant_name": "Local"})
    reanalysis = app.create_reanalysis("test_source", app.ReanalysisRequest())
    assert (
        json.loads((root / reanalysis["id"] / "source.json").read_text()) == segments[0]["source"]
    )
meta = segments[0]["source"].copy()
meta["segment_sha256"] = "0" * 64
(folders[0] / "source.json").write_text(json.dumps(meta))
try:
    collect_reviewed([*folders, other], "objects")
except ValueError as exc:
    assert "hash upload" in str(exc)
else:
    raise AssertionError("Changed provenance/upload must be rejected")
assert hashlib.sha256(source.read_bytes()).hexdigest() == before
(root / "report.json").write_text(
    json.dumps(
        {
            "status": "passed",
            "segments": len(segments),
            "selected": len(selected),
            "source_splits": {k: list(v) for k, v in source_splits.items()},
        },
        indent=2,
    )
)
print(
    "PASS: exact segments, pHash/temporal selection, original-source split, global frame positions, metadata integrity and legacy fallback."
)
