"""Run with .venv/Scripts/python tests/self_check.py; no test framework."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from vision import Counter, helmet_status

counter = Counter(0.5)
for time, position in enumerate([0.3, 0.49, 0.51, 0.55, 0.6]):
    counter.update(1, "person", position, time)
assert len(counter.crossings) == 1
assert counter.crossings[0]["direction"] == "down"
counter.update(1, "person", 0.3, 8)
assert len(counter.crossings) == 2
assert Counter(0.5).crossings == []
assert helmet_status([0, 0, 100, 200], []) == "unknown"
assert helmet_status([0, 0, 100, 200], [([20, 10, 50, 35], "Hardhat")]) == "helmet"
assert helmet_status([0, 0, 100, 200], [([20, 10, 50, 35], "NO-Hardhat")]) == "no_helmet"
assert helmet_status([0, 0, 100, 200], [([20, 120, 50, 150], "Hardhat")]) == "unknown"
assert (
    helmet_status(
        [0, 0, 100, 200], [([20, 10, 50, 35], "Hardhat"), ([20, 10, 50, 35], "NO-Hardhat")]
    )
    == "unknown"
)
print("PASS: counting hysteresis, direction, independent runs, and helmet uncertainty.")

from chat import answer_facts

sample = {
    "duration": 2,
    "occupancy": [{"seconds": 0, "person": 2, "car": 0}, {"seconds": 1, "person": 1, "car": 1}],
    "crossings": [{"kind": "person", "direction": "up"}],
    "tracks": [
        {
            "id": 1,
            "kind": "person",
            "helmet_candidate": True,
            "evidence": "evidence_1.jpg",
            "evidence_seconds": 1.0,
        }
    ],
}


def facts(question, data=sample):
    result = answer_facts(question, data)
    assert result is not None
    return result


assert "1 orang" in facts("Berapa orang pada detik 1?")["answer"]
assert "di luar video" in facts("Berapa orang detik 5?")["answer"]
assert "1 lintasan" in facts("Berapa orang lewat?")["answer"]
assert facts("Siapa tanpa helm?")["evidence"][0]["track_id"] == 1
assert "belum tersedia" in facts("Siapa dari wajahnya?")["answer"]
assert "belum mempunyai data" in facts("Berapa orang?", None)["answer"]
assert answer_facts("Selamat pagi", sample) is None
print("PASS: grounded answers, frame times, counting units, evidence and feature limits.")

assert "belum mendukung filter" in facts("Berapa orang antara detik 1 sampai 2?")["answer"]
assert facts("Jelaskan proyek ini")["mode"] == "guide"

assert answer_facts("Apa hasil 2 ditambah 3?", sample) is None
assert answer_facts("Berapa harga buku?", sample) is None

assert answer_facts("Kamu siapa?", None) is None
assert "1 orang dan 1 mobil" in facts("Berapa orang dan mobil pada detik 1?")["answer"]
assert "belum disimpan" in facts("Berapa orang yang pakai helm?")["answer"]
assert "Nama orang belum tersedia" in facts("Siapa yang ada di video ini?")["answer"]
print("PASS: ordinary chat routing and unsupported helmet/identity assumptions.")

# Regression: questions and evidence must stay scoped to the requested object.
mixed = {
    **sample,
    "tracks": [
        *sample["tracks"],
        {
            "id": 2,
            "kind": "car",
            "helmet_candidate": False,
            "evidence": "evidence_2.jpg",
            "evidence_seconds": 1.0,
        },
    ],
}
reply = facts("Ada berapa orang di video?", mixed)
assert "mobil" not in reply["answer"]
assert all(e["kind"] == "person" for e in reply["evidence"])
assert all(e["kind"] == "person" for e in facts("Bukti orang", mixed)["evidence"])
assert all(e["kind"] == "car" for e in facts("Bukti mobil", mixed)["evidence"])
assert "orang" not in facts("Ada berapa mobil?", mixed)["answer"]
assert len(facts("Ringkasan", mixed)["evidence"]) == 2
print("PASS: scoped counts and person/car evidence, including older saved summaries.")

from pydantic import ValidationError

from app import ManualBox, ManualFrame

for invalid in [[0.5, 0.2, 0.1, 0.3], [-0.1, 0, 1, 1], [0, 0, float("nan"), 1]]:
    try:
        ManualBox(label="person", bbox=invalid)
        raise AssertionError("Invalid bbox accepted")
    except ValidationError:
        pass
assert ManualBox(label="person", bbox=[0, 0, 1, 1]).label == "person"
try:
    ManualFrame(frame_index=0, revision=0, boxes=[{"label": "car", "bbox": [0, 0, 1, 1]}] * 101)
    raise AssertionError("Unbounded annotations accepted")
except ValidationError:
    pass
reviewed = {
    **sample,
    "manual_frames": [
        {"complete": True, "seconds": 1.0, "boxes": [{"label": "person", "bbox": [0, 0, 1, 1]}] * 3}
    ],
}
assert "3 orang" in facts("Berapa orang pada detik 1?", reviewed)["answer"]
assert facts("Berapa orang pada detik 1?", reviewed)["mode"] == "manual"
assert "1 orang" in facts("Berapa orang AI pada detik 1?", reviewed)["answer"]
reviewed["manual_frames"][0]["complete"] = False
assert facts("Berapa orang pada detik 1?", reviewed)["mode"] == "facts"
print("PASS: manual bbox validation, size limits, completed review, draft/AI separation.")


# Guard-path tests simulate resource failures; no detector outputs are fabricated.
from unittest.mock import patch

import torch

from runtime import select_device

assert select_device("cpu")[0] == "cpu"
with patch("torch.cuda.is_available", return_value=False):
    assert select_device("auto")[0] == "cpu"
    assert select_device("cuda")[0] == "cpu"
with (
    patch("torch.cuda.is_available", return_value=True),
    patch("torch.cuda.device_count", return_value=2),
    patch("torch.cuda.get_device_name", side_effect=lambda i: ["Other GPU", "RTX 4060"][i]),
    patch("torch.cuda.mem_get_info", return_value=(7 * 2**30, 8 * 2**30)),
):
    assert select_device("auto", 6)[0] == "cuda:1"
with (
    patch("torch.cuda.is_available", return_value=True),
    patch("torch.cuda.device_count", return_value=1),
    patch("torch.cuda.get_device_name", return_value="RTX 4060"),
    patch("torch.cuda.mem_get_info", return_value=(100, 8 * 2**30)),
):
    assert select_device("auto", 6)[0] == "cpu"
with patch("torch.cuda.is_available", side_effect=RuntimeError("CUDA init failed")):
    assert select_device("cuda")[0] == "cpu"

import chat

with (
    patch("chat.select_device", return_value=("cuda:0", "guard test")),
    patch(
        "chat._generate_once",
        side_effect=[torch.cuda.OutOfMemoryError("guard test"), {"answer": "guard test"}],
    ) as generate,
    patch("torch.cuda.empty_cache"),
):
    result = chat.generate_reply("guard test", [], None)
    assert result["device"] == "cpu"
    assert [call.args[3] for call in generate.call_args_list] == ["cuda:0", "cpu"]
print("PASS: RTX preference, CPU selection, VRAM/CUDA unavailability, chat OOM fallback guards.")

# Dashboard v3: real class schema, word boundaries, names and color validation.
from vision import OBJECT_NAMES

vehicles = {
    **mixed,
    "object_classes": list(OBJECT_NAMES),
    "occupancy": [
        {"seconds": 0, "person": 2, "car": 1, "bus": 2, "truck": 1, "motorcycle": 1, "bicycle": 3}
    ],
    "tracks": [
        *mixed["tracks"],
        {
            "id": 7,
            "kind": "bus",
            "helmet_candidate": False,
            "evidence": "bus.jpg",
            "evidence_seconds": 0,
        },
    ],
}
assert answer_facts("Bisakah kamu membantu?", vehicles) is None
assert "2 bus" in facts("Berapa bus?", vehicles)["answer"]
assert "mobil" not in facts("Berapa bis?", vehicles)["answer"]
assert all(e["kind"] == "bus" for e in facts("Bukti bus", vehicles)["evidence"])
assert "unggah ulang" in facts("Berapa bus?", mixed)["answer"].lower()
assert "sepeda" not in facts("Berapa sepeda motor?", vehicles)["answer"]
assert "orang" not in facts("Berapa kendaraan?", vehicles)["answer"]
assert (
    ManualBox(label="forklift", bbox=[0, 0, 1, 1], name="  Unit A  ", color="#aAbBcC").name
    == "Unit A"
)
assert ManualBox(label="person", bbox=[0, 0, 1, 1]).color is None
for bad in [
    {"label": "invalid label"},
    {"label": "<script>"},
    {"color": "red"},
    {"color": "#abc"},
    {"name": " "},
    {"name": "bad\nname"},
    {"name": "bad\x7fname"},
]:
    try:
        ManualBox.model_validate({"label": "person", "bbox": [0, 0, 1, 1], **bad})
        raise AssertionError(f"Invalid metadata accepted: {bad}")
    except ValidationError:
        pass
print("PASS: bus/vehicle queries, old summaries, boundaries, custom classes, names/colors.")

# Detector training: no source leakage, complete-only reviews and immutable labels.
import json

from detector_training import build_dataset, collect_reviewed, train_candidate
from operations import working_directory

with working_directory(dir=Path(".tmp")) as directory:
    root = Path(directory)
    folders = []
    for i in range(2):
        folder = root / str(i)
        folder.mkdir()
        (folder / "upload.bin").write_bytes(bytes([i]))
        (folder / "annotation_0.jpg").write_bytes(b"unit dataset fixture; not model evidence")
        frames = [
            {
                "frame_index": 0,
                "complete": True,
                "boxes": [{"label": "karung", "bbox": [0.1, 0.2, 0.5, 0.8]}],
            },
            {"frame_index": 1, "complete": False, "boxes": []},
        ]
        (folder / "annotations.json").write_text(json.dumps({"revision": 3, "frames": frames}))
        folders.append(folder)
    rows = collect_reviewed(folders, "objects")
    assert len(rows) == 2 and all(r["revision"] == 3 for r in rows)
    candidate = root / "candidate"
    candidate.mkdir()
    provenance = build_dataset(candidate, rows, "objects", ["person", "car"])
    assert provenance["names"] == ["person", "car", "karung"]
    assert provenance["counts"] == {"train": 1, "val": 1}
    assert len({f["source_sha256"] for f in provenance["frames"]}) == 2
    assert {f["split"] for f in provenance["frames"]} == {"train", "val"}
    assert all(
        "2 0.300000 0.500000 0.400000 0.600000" in f.read_text()
        for f in (candidate / "dataset/labels").rglob("*.txt")
    )
    assert rows[0]["boxes"][0]["label"] == "karung"
    (folders[1] / "upload.bin").write_bytes(bytes([0]))
    try:
        collect_reviewed(folders, "objects")
        raise AssertionError("Duplicate source allowed")
    except ValueError:
        pass
    with (
        patch("chat.release_model"),
        patch("runtime.select_device", return_value=("cuda:0", "guard test")),
        patch("detector_training.build_dataset", return_value=provenance),
        patch(
            "detector_training.train_once",
            side_effect=[torch.cuda.OutOfMemoryError("guard test"), {"device": "cpu"}],
        ) as train,
        patch("torch.cuda.empty_cache"),
    ):
        result = train_candidate(
            candidate,
            {"group": "objects", "device_preference": "auto", "review_snapshot": []},
            lambda *_: None,
        )
        assert result["device"] == "cpu"
        assert [c.args[2] for c in train.call_args_list] == ["cuda:0", "cpu"]
custom = {
    **sample,
    "object_names": {"person": "orang", "karung": "karung"},
    "object_classes": ["person", "karung"],
    "occupancy": [{"seconds": 1.0, "person": 1, "karung": 2}],
}
assert "2 karung" in facts("Berapa karung pada detik 1?", custom)["answer"]
custom["manual_frames"] = [
    {"complete": True, "seconds": 1.0, "boxes": [{"label": "forklift", "bbox": [0, 0, 1, 1]}]}
]
assert "1 forklift" in facts("Berapa forklift pada detik 1?", custom)["answer"]
assert "belum" in facts("Berapa forklift AI pada detik 1?", custom)["answer"].lower()
print(
    "PASS: complete-only detector data, source split, custom labels/queries and training OOM fallback."
)

custom["object_names"]["Tool_Box"] = "Tool_Box"
custom["object_classes"].append("Tool_Box")
custom["occupancy"][0]["Tool_Box"] = 2
assert "2 Tool_Box" in facts("Berapa Tool_Box AI pada detik 1?", custom)["answer"]
print("PASS: mixed-case custom class queries remain grounded.")

# Automatic learning accepts only explicit Simpan & pelajari records, never legacy fixtures.
with working_directory(dir=Path(".tmp")) as tmp:
    root = Path(tmp)
    folders = []
    for i in range(2):
        folder = root / str(i)
        folder.mkdir()
        (folder / "upload.bin").write_bytes(bytes([i]))
        (folder / "annotation_0.jpg").write_bytes(b"dataset selection test; not model evidence")
        frame = {
            "frame_index": 0,
            "complete": True,
            "boxes": [{"label": "person", "bbox": [0, 0, 1, 1]}],
        }
        (folder / "annotations.json").write_text(json.dumps({"revision": 1, "frames": [frame]}))
        folders.append(folder)
    try:
        collect_reviewed(folders, "objects", approved_only=True)
        raise AssertionError("Unapproved legacy labels entered automatic training")
    except ValueError:
        pass
    for folder in folders:
        data = json.loads((folder / "annotations.json").read_text())
        data["frames"][0]["learn_groups"] = ["objects"]
        (folder / "annotations.json").write_text(json.dumps(data))
    assert len(collect_reviewed(folders, "objects", approved_only=True)) == 2
    # Copied analyses of one upload do not duplicate a frame or cross train/validation boundaries.
    import shutil

    alias = root / "alias"
    shutil.copytree(folders[0], alias)
    data = json.loads((alias / "annotations.json").read_text())
    data["frames"][0]["updated_at"] = "2026-10-08"
    data["frames"][0]["boxes"][0]["label"] = "car"
    (alias / "annotations.json").write_text(json.dumps(data))
    rows = collect_reviewed([alias, *folders], "objects", approved_only=True)
    assert len(rows) == 2
    assert next(r for r in rows if r["job_id"] == "alias")["boxes"][0]["label"] == "car"
print(
    "PASS: automatic learning approval, legacy fixture exclusion and newest-source deduplication."
)
