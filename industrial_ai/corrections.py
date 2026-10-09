"""Durable preview overlays and immutable MP4 exports; never training labels."""

import json
import shutil
import tempfile
from pathlib import Path

from operations import check_cancel, run_command
from prompt_tracking import PromptTracker


def read_corrections(folder: Path) -> dict:
    path = folder / "tracking_corrections.json"
    return (
        json.loads(path.read_text(encoding="utf-8"))
        if path.is_file()
        else {"revision": 0, "frames": []}
    )


def merge_overlay(row: dict, detected: list, suppressed: set) -> dict:
    prompts = row["boxes"]
    remaining = [
        b
        for b in detected
        if b.get("track_id") not in suppressed
        and not any(
            p["label"] == b["label"] and PromptTracker.overlap(p["bbox"], b["bbox"]) > 0.3
            for p in prompts
        )
    ]
    return {**row, "boxes": [*prompts, *remaining], "merged": True}


COLORS = {
    "person": "#0f766e",
    "car": "#2563eb",
    "bus": "#7c3aed",
    "truck": "#c2410c",
    "motorcycle": "#0369a1",
    "bicycle": "#a16207",
    "Hardhat": "#15803d",
    "NO-Hardhat": "#dc2626",
}


def render_video(
    folder: Path,
    target: Path,
    summary: dict,
    corrections: dict,
    annotations: dict,
    progress=None,
    cancel=None,
):
    import cv2

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise ValueError("FFmpeg belum tersedia pada PATH server.")
    source = folder / "original.mp4"
    overlays = folder / "overlays.json"
    ai = json.loads(overlays.read_text(encoding="utf-8")) if overlays.is_file() else {"frames": []}
    rows = {f["frame_index"]: f for f in ai["frames"]}
    rows.update({f["frame_index"]: f for f in corrections["frames"]})
    rows.update({f["frame_index"]: f for f in annotations["frames"]})
    # ponytail: export saved spans only; following beyond them requires playing that span first.
    with tempfile.TemporaryDirectory(prefix="correction_", dir=folder) as directory:
        temporary = Path(directory)
        capture = cv2.VideoCapture(str(source))
        width, height = int(capture.get(3)), int(capture.get(4))
        writer = cv2.VideoWriter(
            str(temporary / "overlay.avi"),
            cv2.VideoWriter.fourcc(*"MJPG"),
            summary["fps"],
            (width, height),
        )
        try:
            if not capture.isOpened() or not writer.isOpened():
                raise ValueError("Video koreksi tidak dapat dibaca/ditulis.")
            for index in range(summary["frames"]):
                check_cancel(cancel)
                if progress and index % 10 == 0:
                    progress(
                        5 + int(85 * index / summary["frames"]),
                        f"Merender koreksi {index}/{summary['frames']} frame",
                    )
                ok, frame = capture.read()
                if not ok:
                    raise ValueError("Video berhenti sebelum semua frame koreksi terbaca.")
                row = rows.get(index, {})
                for box in row.get("boxes", []):
                    x1, y1, x2, y2 = [
                        round(v * dimension)
                        for v, dimension in zip(box["bbox"], (width, height, width, height))
                    ]
                    hex_color = box.get("color") or COLORS.get(box["label"], "#9333ea")
                    color = tuple(int(hex_color[i : i + 2], 16) for i in (5, 3, 1))
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                    text = box.get("name") or box["label"]
                    if box.get("track_id") is not None:
                        prefix = "T" if box.get("source") == "prompt_tracker" else "AI"
                        text += f" {prefix}{box['track_id']}"
                    cv2.putText(
                        frame,
                        text,
                        (x1, max(16, y1 - 6)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.45,
                        color,
                        1,
                        cv2.LINE_AA,
                    )
                cv2.putText(
                    frame,
                    "CORRECTION PREVIEW - REVIEW TRACKS",
                    (8, height - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.4,
                    (255, 255, 255),
                    1,
                    cv2.LINE_AA,
                )
                if row.get("lost"):
                    cv2.putText(
                        frame,
                        f"LOST: {len(row['lost'])} - MARK AGAIN",
                        (8, 18),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.45,
                        (0, 180, 255),
                        1,
                        cv2.LINE_AA,
                    )
                writer.write(frame)
        finally:
            capture.release()
            writer.release()
        if progress:
            progress(92, "Encoding MP4 H264 dan audio")
        result = run_command(
            [
                ffmpeg,
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-i",
                str(temporary / "overlay.avi"),
                "-i",
                str(source),
                "-map",
                "0:v:0",
                "-map",
                "1:a?",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "23",
                "-c:a",
                "aac",
                "-t",
                str(summary["frames"] / summary["fps"]),
                "-movflags",
                "+faststart",
                str(temporary / "result.mp4"),
            ],
            timeout=300,
            cancel=cancel,
        )
        if result.returncode:
            raise ValueError("FFmpeg gagal mengekspor video koreksi; hasil awal tetap tersimpan.")
        check_cancel(cancel)
        (temporary / "result.mp4").replace(target)
