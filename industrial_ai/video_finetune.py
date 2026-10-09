"""Prepare long videos as existing review jobs. Auto labels stay unapproved."""

from __future__ import annotations

import runtime  # isort: skip  # Workspace-local caches before importing native libraries.

import argparse
import hashlib
import http.client
import json
import math
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import cast
from urllib.parse import urlsplit
from uuid import uuid4


def command(args: list[str]) -> bytes:
    result = subprocess.run(args, capture_output=True, timeout=600, check=False)
    if result.returncode:
        raise ValueError("FFmpeg/FFprobe gagal: " + result.stderr.decode(errors="replace")[-800:])
    return result.stdout


def probe(video: Path) -> dict:
    tool = shutil.which("ffprobe")
    if not tool:
        raise ValueError("FFprobe tidak tersedia pada PATH.")
    metadata = json.loads(
        command(
            [
                tool,
                "-v",
                "error",
                "-protocol_whitelist",
                "file,pipe",
                "-format_whitelist",
                "mov,matroska,avi,m4v,ogg",
                "-show_format",
                "-show_streams",
                "-of",
                "json",
                str(video),
            ]
        )
    )
    duration = float(metadata["format"].get("duration", 0))
    videos = [s for s in metadata["streams"] if s["codec_type"] == "video"]
    if not videos or not math.isfinite(duration) or duration <= 0:
        raise ValueError("Sumber harus berupa video dengan durasi valid.")
    return {
        "duration": duration,
        "width": int(videos[0]["width"]),
        "height": int(videos[0]["height"]),
    }


def build_source_meta(
    source: Path, segment: Path, index: int, start: float, source_hash: str
) -> dict:
    with segment.open("rb") as stream:
        segment_hash = hashlib.file_digest(stream, "sha256").hexdigest()
    attribution = source.with_suffix(".source.json")
    credit = json.loads(attribution.read_text(encoding="utf-8")) if attribution.is_file() else {}
    return {
        "source_id": source_hash,
        "source_sha256": source_hash,
        "source_filename": source.name,
        "segment_sha256": segment_hash,
        "segment_index": index,
        "start_seconds": start,
        "duration": probe(segment)["duration"],
        "attribution": {
            key: credit[key]
            for key in ("source", "author", "license", "license_url")
            if key in credit
        },
    }


def segment_video(source: Path, output: Path, seconds: float = 110) -> list[dict]:
    if not source.is_file() or not 1 <= seconds <= 110:
        raise ValueError("Video harus ada; durasi segmen antara 1 dan 110 detik.")
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise ValueError("FFmpeg tidak tersedia pada PATH.")
    metadata = probe(source)
    with source.open("rb") as stream:
        source_hash = hashlib.file_digest(stream, "sha256").hexdigest()
    output = output.resolve()
    if not output.is_relative_to(runtime.ROOT):
        raise ValueError("Output harus berada di workspace industrial_ai.")
    output.mkdir(parents=True, exist_ok=False)
    rows = []
    # Exact time cuts need re-encoding: stream copy can cross the application's 120s cap.
    for index in range(math.ceil(metadata["duration"] / seconds)):
        start = round(index * seconds, 6)
        stem = re.sub(r"[^A-Za-z0-9_-]", "_", source.stem)[:80] or "video"
        target = output / f"{stem}_segment_{index:04}.mp4"
        command(
            [
                ffmpeg,
                "-hide_banner",
                "-loglevel",
                "error",
                "-n",
                "-ss",
                str(start),
                "-protocol_whitelist",
                "file,pipe",
                "-format_whitelist",
                "mov,matroska,avi,m4v,ogg",
                "-i",
                str(source),
                "-t",
                str(min(seconds, metadata["duration"] - start)),
                "-map",
                "0:v:0",
                "-map",
                "0:a?",
                "-vf",
                "scale=1280:720:force_original_aspect_ratio=decrease:force_divisible_by=2,fps=10",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "23",
                "-c:a",
                "aac",
                "-movflags",
                "+faststart",
                str(target),
            ]
        )
        meta = build_source_meta(source, target, index, start, source_hash)
        if not 0 < meta["duration"] <= 120 or target.stat().st_size > 250 * 1024 * 1024:
            raise ValueError("Segmen melampaui batas upload; source dan hasil tetap disimpan.")
        target.with_suffix(".source.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
        rows.append({"path": target, "source": meta})
    return rows


def dedup_frames(
    candidates: list[dict], minimum_gap: int, seen: list[int], distance: int = 5
) -> list[dict]:
    selected = []
    last = -minimum_gap
    for row in candidates:
        if row["frame_index"] - last < minimum_gap or any(
            (row["phash"] ^ h).bit_count() <= distance for h in seen
        ):
            continue
        selected.append(row)
        seen.append(row["phash"])
        last = row["frame_index"]
    return selected


def select_frames(
    video: Path, limit: int = 80, stride: int = 5, seen: list[int] | None = None
) -> list[dict]:
    import cv2
    import numpy as np

    if not 1 <= limit <= 80 or not 1 <= stride <= 100:
        raise ValueError("Batas frame 1–80; stride 1–100.")
    capture = cv2.VideoCapture(str(video))
    candidates = []
    try:
        total = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        if not capture.isOpened() or total <= 0:
            raise ValueError("Video seleksi frame tidak dapat dibaca.")
        # ponytail: bounded uniform samples + pHash; use embeddings when small moving objects are missed.
        interval = max(stride, math.ceil(total / (limit * 2)))
        for index in range(0, total, interval):
            capture.set(cv2.CAP_PROP_POS_FRAMES, index)
            ok, image = capture.read()
            if not ok:
                raise ValueError("Kandidat frame tidak dapat dibaca.")
            gray = cv2.resize(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY), (32, 32)).astype(np.float32)
            coefficients = cv2.dct(gray)[:8, :8].flatten()
            bits = coefficients > np.median(coefficients[1:])
            bits[0] = False
            candidates.append(
                {"frame_index": index, "phash": int("".join("1" if b else "0" for b in bits), 2)}
            )
        return dedup_frames(candidates, interval * 2, seen if seen is not None else [])[:limit]
    finally:
        capture.release()


def auto_label_batch(
    video: Path, frames: list[dict], group: str = "both", device: str = "auto"
) -> dict:
    import gc

    import cv2
    import torch
    from ultralytics import YOLO
    from ultralytics.engine.results import Results

    from vision import OBJECT_NAMES

    if group not in {"objects", "helmets", "both"} or len(frames) > 80:
        raise ValueError("Kelompok/batas frame auto-label tidak valid.")
    selected, reason = runtime.select_device(device, 2)
    groups = ["objects", "helmets"] if group == "both" else [group]
    rows: list[dict] = [
        {"frame_index": f["frame_index"], "boxes": [], "review_flags": []} for f in frames
    ]
    capture = cv2.VideoCapture(str(video))
    try:
        for kind in groups:
            model = YOLO(str(runtime.MODELS / ("yolo26n.pt" if kind == "objects" else "helmet.pt")))
            labels = set(OBJECT_NAMES) if kind == "objects" else {"Hardhat", "NO-Hardhat"}
            classes = [i for i, name in model.names.items() if name in labels]
            for offset in range(0, len(rows), 4):
                batch = rows[offset : offset + 4]
                images = []
                for row in batch:
                    capture.set(cv2.CAP_PROP_POS_FRAMES, row["frame_index"])
                    ok, image = capture.read()
                    if not ok:
                        raise ValueError("Frame auto-label tidak dapat dibaca.")
                    images.append(image)
                try:
                    results = model.predict(
                        images,
                        conf=0.15,
                        classes=classes,
                        imgsz=640,
                        device=selected,
                        verbose=False,
                    )
                except torch.cuda.OutOfMemoryError:
                    if selected == "cpu":
                        raise
                    gc.collect()
                    torch.cuda.empty_cache()
                    selected, reason = "cpu", "VRAM habis; auto-label dilanjutkan pada CPU."
                    results = model.predict(
                        images, conf=0.15, classes=classes, imgsz=640, device="cpu", verbose=False
                    )
                # One low-threshold pass: >=0.5 becomes draft; lower confidence only flags review.
                for row, result, image in zip(batch, cast(list[Results], results), images):
                    height, width = image.shape[:2]
                    if result.boxes is None:
                        continue
                    for xyxy, cls, confidence in zip(
                        result.boxes.xyxy.tolist(),
                        result.boxes.cls.tolist(),
                        result.boxes.conf.tolist(),
                    ):
                        label = model.names[int(cls)]
                        if confidence < 0.5:
                            row["review_flags"].append(
                                {"label": label, "confidence": round(confidence, 3)}
                            )
                            continue
                        bbox = [
                            max(0, min(1, v / dim))
                            for v, dim in zip(xyxy, (width, height, width, height))
                        ]
                        if bbox[0] < bbox[2] and bbox[1] < bbox[3]:
                            row["boxes"].append(
                                {"label": label, "name": None, "color": None, "bbox": bbox}
                            )
            del model
        for row in rows:
            if len(row["boxes"]) > 100:
                raise ValueError("Lebih dari 100 kotak; tinjau frame padat secara manual.")
        return {
            "frames": rows,
            "groups": groups,
            "device": selected,
            "device_reason": reason,
            "source": "AI suggestions; human review required; no model training",
        }
    finally:
        capture.release()


def api_request(
    server: str, path: str, payload=None, upload: Path | None = None, device: str = "auto"
) -> dict:
    location = urlsplit(server)
    if (
        location.scheme != "http"
        or location.hostname != "127.0.0.1"
        or location.path not in {"", "/"}
        or location.query
        or location.username
    ):
        raise ValueError("Server harus http://127.0.0.1:<port> tanpa credential/path/query.")
    connection = http.client.HTTPConnection(location.hostname, location.port or 8765, timeout=600)
    try:
        if upload:
            boundary = uuid4().hex
            header = f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{upload.name}"\r\nContent-Type: video/mp4\r\n\r\n'.encode()
            footer = f'\r\n--{boundary}\r\nContent-Disposition: form-data; name="device"\r\n\r\n{device}\r\n--{boundary}--\r\n'.encode()
            connection.putrequest("POST", path)
            connection.putheader("Content-Type", f"multipart/form-data; boundary={boundary}")
            connection.putheader(
                "Content-Length", str(len(header) + upload.stat().st_size + len(footer))
            )
            connection.endheaders(header)
            with upload.open("rb") as stream:
                while block := stream.read(1024 * 1024):
                    connection.send(block)
            connection.send(footer)
        else:
            data = json.dumps(payload).encode() if payload is not None else None
            connection.request(
                "POST" if payload is not None else "GET",
                path,
                body=data,
                headers={"Content-Type": "application/json"},
            )
        response = connection.getresponse()
        result = json.loads(response.read())
        if response.status >= 400:
            raise ValueError(f"API {response.status}: {result.get('detail', result)}")
        return result
    finally:
        connection.close()


def prepare(source: Path, server: str, group: str, device: str, limit: int) -> Path:
    if not 1 <= limit <= 80:
        raise ValueError("Pilih 1–80 frame per sumber.")
    # Metadata is written locally: only the standard local server using this workspace is supported.
    health = api_request(server, "/api/health")
    if not health.get("vision_ready"):
        raise ValueError("Model vision server belum tersedia.")
    output = runtime.ROOT / "data/video-prep" / str(uuid4())
    segments = segment_video(source, output)
    seen: list[int] = []
    remaining = limit
    manifest = []
    for segment in segments:
        state = api_request(server, "/api/jobs", upload=segment["path"], device=device)
        folder = runtime.JOBS / state["id"]
        if not (folder / "state.json").is_file():
            raise ValueError("Server memakai workspace berbeda; metadata sumber belum ditulis.")
        (folder / "source.json").write_text(
            json.dumps(segment["source"], indent=2), encoding="utf-8"
        )
        deadline = time.monotonic() + 600
        while (
            state["status"] in {"queued", "processing", "uploading"} and time.monotonic() < deadline
        ):
            time.sleep(0.5)
            state = api_request(server, f"/api/jobs/{state['id']}")
        if state["status"] != "done":
            raise ValueError("Analisis segmen gagal/belum selesai; semua output tetap tersimpan.")
        budget = min(
            remaining,
            max(
                1,
                math.ceil(
                    limit
                    * segment["source"]["duration"]
                    / sum(s["source"]["duration"] for s in segments)
                ),
            ),
        )
        selected_frames = (
            select_frames(folder / "original.mp4", budget, seen=seen) if budget else []
        )
        remaining -= len(selected_frames)
        labelled = auto_label_batch(folder / "original.mp4", selected_frames, group, device)
        data = api_request(server, f"/api/jobs/{state['id']}/annotations")
        if data["frames"]:
            raise ValueError("Job sudah memiliki koreksi pengguna; auto-label tidak menimpanya.")
        for row in labelled["frames"]:
            data = api_request(
                server,
                f"/api/jobs/{state['id']}/annotations",
                {
                    "frame_index": row["frame_index"],
                    "revision": data["revision"],
                    "complete": False,
                    "helmets_complete": False,
                    "boxes": row["boxes"],
                },
            )
        (folder / "selection.json").write_text(json.dumps(labelled, indent=2), encoding="utf-8")
        manifest.append({"job_id": state["id"], "source": segment["source"], "selection": labelled})
        (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        print(
            f"Job {state['id']}: {len(labelled['frames'])} draft frame; {labelled['device']}",
            flush=True,
        )
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("videos", type=Path, nargs="+")
    parser.add_argument("--server", default="http://127.0.0.1:8765")
    parser.add_argument("--group", choices=["objects", "helmets", "both"], default="both")
    parser.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto")
    parser.add_argument("--frames", type=int, default=60)
    args = parser.parse_args()
    try:
        for video in args.videos:
            print(
                "Prepared:",
                prepare(video.resolve(), args.server, args.group, args.device, args.frames),
            )
    except (ValueError, OSError, subprocess.TimeoutExpired) as exc:
        parser.exit(1, f"Gagal: {exc}\n")


if __name__ == "__main__":
    main()
