"""Real HTTP/video/model check. Run after starting the localhost server."""

from __future__ import annotations

import hashlib
import io
import json
import subprocess
import sys
import time
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import httpx

from runtime import ROOT


def main():
    clip = ROOT / ".tmp/real_smoke/upload.bin"
    if not clip.is_file():
        raise SystemExit("Create a real smoke clip first; see README. No fake detections are used.")
    results = []
    with httpx.Client(base_url="http://127.0.0.1:8765", timeout=120) as client:

        def require(condition, label):
            assert condition, label
            results.append(label)
            print("PASS:", label, flush=True)

        require(client.get("/").status_code == 200, "page served")
        health = client.get("/api/health").json()
        require(health["chat_ready"], "real base chat model is available")
        chat_mode = "lora" if health["adapter_ready"] else "base"
        require(client.get("/api/jobs/not-a-uuid").status_code == 404, "invalid job rejected")
        require(
            client.get("/api/jobs", headers={"Host": "evil.example"}).status_code == 400,
            "untrusted Host rejected",
        )
        require(
            client.post(
                "/api/chat", json={"message": "hi"}, headers={"Origin": "https://evil.example"}
            ).status_code
            == 403,
            "cross-origin writes rejected",
        )
        require(
            client.post("/api/chat", json={"message": " "}).status_code == 422,
            "blank chat rejected",
        )
        require(
            client.post("/api/chat", json={"message": "x" * 601}).status_code == 422,
            "chat length bounded",
        )
        require(
            client.post("/api/jobs", files={"file": ("bad.txt", b"invalid")}).status_code == 415,
            "invalid extension rejected",
        )
        require(
            client.post("/api/jobs", files={"file": ("empty.mp4", b"")}).status_code == 422,
            "empty upload rejected",
        )
        require(
            client.post(
                "/api/jobs", files={"file": ("video.mp4", b"invalid")}, data={"line": "0.95"}
            ).status_code
            == 422,
            "counting line range validated",
        )
        with clip.open("rb") as file:
            response = client.post(
                "/api/jobs",
                files={"file": ("../real-demo.mp4", file, "video/mp4")},
                data={"line": "0.5", "device": "cpu"},
            )
        require(response.status_code == 202, "real video accepted")
        job_id = response.json()["id"]
        require(response.json()["filename"] == "real-demo.mp4", "upload name normalized")
        require(
            client.post("/api/jobs", files={"file": ("second.mp4", b"data")}).status_code == 409,
            "concurrent vision bounded",
        )
        require(
            client.post("/api/chat", json={"message": "hasil video", "job_id": job_id}).status_code
            == 409,
            "unfinished analysis is explicit",
        )
        deadline = time.monotonic() + 180
        while time.monotonic() < deadline:
            job = client.get(f"/api/jobs/{job_id}").json()
            if job["status"] in {"done", "error"}:
                break
            time.sleep(0.5)
        require(job["status"] == "done", "real detector and tracker completed")
        summary = job["summary"]
        require(
            job["device"] == summary["device"] == "cpu", "explicit CPU analysis executes on CPU"
        )
        require(
            summary["frames"] == 120 and len(summary["occupancy"]) == 120,
            "all real clip frames analyzed",
        )
        require(
            any(t["kind"] == "person" for t in summary["tracks"]), "real person detections exist"
        )
        require(
            len({t["id"] for t in summary["tracks"]}) == len(summary["tracks"]),
            "tracks not duplicated",
        )
        prefix = f"/api/jobs/{job_id}/media/"
        require(client.get(prefix + "state.json").status_code == 404, "media allowlist enforced")
        require(
            client.get(prefix + "original.mp4", headers={"Range": "bytes=0-127"}).status_code
            == 206,
            "browser range requests supported",
        )
        require(
            client.get(prefix + "summary.json").json()["occupancy"] == summary["occupancy"]
            and client.get(f"/api/jobs/{job_id}/summary").json() == summary,
            "original AI occupancy preserved and reviewed download matches API",
        )
        saved = ROOT / "data/jobs" / job_id
        original_hashes = {
            name: hashlib.sha256((saved / name).read_bytes()).hexdigest()
            for name in ["upload.bin", "original.mp4", "tracked.mp4", "summary.json"]
        }
        people = [t for t in summary["tracks"] if t["kind"] == "person"]
        require(
            all("evidence_bbox" in t and "evidence" in t for t in people),
            "every tracked person has target bbox and proof",
        )
        require(
            all(client.get(prefix + t["evidence"]).status_code == 200 for t in people),
            "real person JPEG proofs are served",
        )
        reply = client.post(
            "/api/chat", json={"job_id": job_id, "message": "Ada berapa orang di video?"}
        ).json()
        require(
            "mobil" not in reply["answer"]
            and reply["evidence"]
            and all(e["kind"] == "person" for e in reply["evidence"]),
            "people-only question has people-only answer and proofs",
        )
        for preference in ["invalid", "gpu"]:
            require(
                client.post("/api/chat", json={"message": "Halo", "device": preference}).status_code
                == 422,
                f"invalid device {preference} rejected",
            )
        base = f"/api/jobs/{job_id}"
        require(
            client.get(base + "/frame/30").headers["content-type"] == "image/jpeg",
            "real manual-review frame is served",
        )
        require(
            client.get(base + "/frame/120").status_code == 422
            and client.get(base + "/frame/-1").status_code == 422,
            "manual frame bounds enforced",
        )
        require(
            client.get(base + "/dataset").status_code == 409, "empty annotation export rejected"
        )
        require(
            client.get(base + "/annotations").json() == {"revision": 0, "frames": []},
            "new job starts without manual labels",
        )
        # These are API validation fixtures, not human ground-truth labels.
        payload = {
            "frame_index": 30,
            "revision": 0,
            "complete": False,
            "boxes": [
                {
                    "label": "person",
                    "name": "Fixture API",
                    "color": "#123456",
                    "bbox": [0.1, 0.2, 0.3, 0.6],
                },
                {"label": "Hardhat", "bbox": [0.1, 0.2, 0.2, 0.3]},
            ],
        }
        for bad in [
            {"label": "invalid label", "bbox": [0, 0, 1, 1]},
            {"label": "person", "bbox": [0.6, 0, 0.2, 1]},
            {"label": "person", "bbox": [-1, 0, 1, 1]},
        ]:
            require(
                client.post(base + "/annotations", json={**payload, "boxes": [bad]}).status_code
                == 422,
                "invalid annotation rejected: " + str(bad),
            )
        require(
            client.post(
                base + "/annotations", json={**payload, "boxes": payload["boxes"] * 51}
            ).status_code
            == 422,
            "annotation count bounded",
        )
        draft = client.post(base + "/annotations", json=payload)
        require(
            draft.status_code == 200 and draft.json()["revision"] == 1,
            "manual draft saved atomically",
        )
        require(
            client.post(base + "/annotations", json=payload).status_code == 409,
            "stale revision cannot overwrite review",
        )
        require(
            client.get(base + "/dataset").status_code == 409,
            "draft frames excluded from training export",
        )
        draft_reply = client.post(
            "/api/chat", json={"job_id": job_id, "message": "Berapa orang pada detik 3?"}
        ).json()
        require(draft_reply["mode"] == "facts", "draft does not override AI frame counts")
        done = client.post(
            base + "/annotations", json={**payload, "revision": 1, "complete": True}
        ).json()
        require(
            done["revision"] == 2 and client.get(base + "/annotations").json() == done,
            "completed review persists via API",
        )
        manual = client.post(
            "/api/chat", json={"job_id": job_id, "message": "Berapa orang pada detik 3?"}
        ).json()
        require(
            manual["mode"] == "manual"
            and "1 orang" in manual["answer"]
            and "mobil" not in manual["answer"],
            "reviewed frame gives clearly labeled manual people count",
        )
        require(
            client.post(
                "/api/chat", json={"job_id": job_id, "message": "Berapa orang pada detik 3.2?"}
            ).json()["mode"]
            == "facts",
            "review only overrides exact selected frame",
        )
        export = client.get(base + "/dataset")
        require(export.status_code == 200, "reviewed objects export as real YOLO ZIP")
        with zipfile.ZipFile(io.BytesIO(export.content)) as archive:
            stem = f"{job_id}_0030"
            names = archive.namelist()
            require(
                not any(n.startswith("helmets/") for n in names),
                "unreviewed heads excluded from export",
            )
            row = archive.read(f"objects/labels/{stem}.txt").decode().split()
            require(
                row == ["0", "0.200000", "0.400000", "0.200000", "0.400000"],
                "YOLO xyxy converted to normalized center/size",
            )
            require(
                archive.read("objects/classes.txt").decode()
                == "person\ncar\nbus\ntruck\nmotorcycle\nbicycle\n",
                "object class mapping matches detector",
            )
            require(
                archive.read(f"objects/images/{stem}.jpg").startswith(b"\xff\xd8"),
                "dataset contains real source frame JPEG",
            )
            meta = json.loads(archive.read("annotations.json"))
            require(
                meta["source_upload_sha256"] == original_hashes["upload.bin"]
                and meta["split"] == "unassigned",
                "dataset provenance and split status recorded",
            )
        require(
            client.get(base + "/dataset").content == export.content, "export cached by revision"
        )
        done = client.post(
            base + "/annotations",
            json={**payload, "revision": 2, "complete": True, "helmets_complete": True},
        ).json()
        with zipfile.ZipFile(io.BytesIO(client.get(base + "/dataset").content)) as archive:
            require(
                archive.read("helmets/classes.txt").decode() == "Hardhat\nNO-Hardhat\n"
                and len(archive.read(f"helmets/labels/{stem}.txt").decode().splitlines()) == 1,
                "reviewed heads export separately with helmet detector classes",
            )
        require((saved / "annotations_v2_r2.zip").is_file(), "older annotation export retained")
        require(
            all(
                hashlib.sha256((saved / name).read_bytes()).hexdigest() == digest
                for name, digest in original_hashes.items()
            ),
            "manual review leaves original AI results and uploads unchanged",
        )
        require(
            hashlib.sha256((saved / "upload.bin").read_bytes()).digest()
            == hashlib.sha256(clip.read_bytes()).digest(),
            "original upload bytes preserved",
        )
        durations = []
        for name in ["original.mp4", "tracked.mp4"]:
            probe = subprocess.run(
                ["ffprobe", "-v", "error", "-show_streams", "-of", "json", str(saved / name)],
                capture_output=True,
                text=True,
                check=True,
            )
            stream = next(
                s for s in json.loads(probe.stdout)["streams"] if s["codec_type"] == "video"
            )
            require(stream["codec_name"] == "h264", name + " is browser-ready H264")
            durations.append(float(stream["duration"]))
        require(abs(durations[0] - durations[1]) < 0.11, "comparison durations aligned")
        fact = client.post(
            "/api/chat", json={"job_id": job_id, "message": "Berapa orang AI pada detik 3?"}
        ).json()
        frame = min(summary["occupancy"], key=lambda f: abs(f["seconds"] - 3))
        require(
            f"{frame['person']} orang" in fact["answer"] and fact["mode"] == "facts",
            "chat frame count matches stored analysis",
        )
        crossings = sum(c["kind"] == "person" for c in summary["crossings"])
        fact = client.post(
            "/api/chat", json={"job_id": job_id, "message": "Berapa orang melintas?"}
        ).json()
        require(f"{crossings} lintasan" in fact["answer"], "chat crossings match actual tracks")
        local = client.post(
            "/api/chat",
            json={"message": "Apa hasil 2 ditambah 3? Jawab satu angka saja.", "device": "cpu"},
        ).json()
        require(
            local["mode"] == chat_mode and "5" in local["answer"],
            "real local chat model generated a reply",
        )
        require(local["device"] == "cpu", "explicit CPU chat executes real model on CPU")
        gpu = client.post(
            "/api/chat",
            json={"message": "Apa hasil 2 ditambah 3? Jawab satu angka saja.", "device": "auto"},
        ).json()
        require(
            gpu["mode"] == chat_mode and "5" in gpu["answer"],
            "Auto chat generates with the real local model",
        )
        if client.get("/api/health").json()["device"].startswith("cuda"):
            require(gpu["device"].startswith("cuda"), "Auto chat uses available RTX CUDA")
        corrupt = client.post(
            "/api/jobs", files={"file": ("corrupt.mp4", b"this is not video")}
        ).json()
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            failed = client.get(f"/api/jobs/{corrupt['id']}").json()
            if failed["status"] == "error":
                break
            time.sleep(0.2)
        require(failed["status"] == "error", "corrupt video produces error, never fake results")
        # Additional API fixtures only; these boxes are not ground truth.
        extra = client.post(
            base + "/annotations",
            json={
                **payload,
                "revision": 3,
                "complete": True,
                "boxes": [
                    *payload["boxes"],
                    {
                        "label": "forklift",
                        "name": "Custom fixture",
                        "color": "#abcdef",
                        "bbox": [0.4, 0.2, 0.6, 0.6],
                    },
                ],
            },
        ).json()
        require(
            extra["revision"] == 4 and extra["frames"][0]["boxes"][0]["color"] == "#123456",
            "name/color metadata survives persistence",
        )
        with zipfile.ZipFile(io.BytesIO(client.get(base + "/dataset").content)) as archive:
            require(
                archive.read("objects/classes.txt").decode().endswith("bicycle\nforklift\n"),
                "custom class is appended to stable base mapping",
            )
            meta = json.loads(archive.read("annotations.json"))
            require(
                meta["schema_version"] == 2
                and meta["frames"][0]["boxes"][0]["name"] == "Fixture API",
                "v2 export preserves display metadata",
            )
        for bad in [{"color": "#xyzxyz"}, {"name": " "}, {"name": "bad\nname"}]:
            require(
                client.post(
                    base + "/annotations",
                    json={**payload, "revision": 4, "boxes": [{**payload["boxes"][0], **bad}]},
                ).status_code
                == 422,
                "invalid metadata rejected: " + str(bad),
            )
        require(
            client.get("/assets/dashboard.css").status_code == 200
            and client.get("/assets/dashboard.js").status_code == 200,
            "local dashboard assets served",
        )
        require(client.get("/assets/app.py").status_code == 404, "asset allowlist enforced")
        report = {
            "status": "passed",
            "checks": results,
            "job_id": job_id,
            "summary": {k: summary[k] for k in ["duration", "frames", "processing_seconds"]},
            "counts": {
                "peak_people": max(f["person"] for f in summary["occupancy"]),
                "tracks": len(summary["tracks"]),
                "person_crossings": crossings,
            },
            "real_chat": local,
            "real_chat_auto": gpu,
            "annotation_fixture_notice": "Test boxes exercise API/ZIP transformations; not human ground truth.",
            "source": "OpenCV vtest.avi, first 12 seconds; real inference, no ground-truth accuracy claim.",
        }
        (ROOT / "reports/e2e_publication.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"{len(results)} checks passed. Job {job_id}", flush=True)


if __name__ == "__main__":
    main()
