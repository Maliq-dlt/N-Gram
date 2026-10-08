"""Short-term box-prompt tracking on clean pixels; never training ground truth."""

import time

import cv2
import numpy as np


class PromptTracker:
    def __init__(self, video, frame_index, boxes, overlays=None):
        self.capture = cv2.VideoCapture(str(video))
        self.touched = time.monotonic()
        self.index = frame_index
        self.capture.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        ok, frame = self.capture.read()
        if not ok:
            self.close()
            raise ValueError("Frame awal tracker tidak dapat dibaca.")
        self.gray = self.image(frame)
        self.height, self.width = self.gray.shape
        self.overlays = {f["frame_index"]: f["boxes"] for f in (overlays or [])}
        self.objects: list[dict] = []
        claimed = set()
        for i, box in enumerate(boxes):
            bbox = np.array(box["bbox"], dtype=np.float32) * ([self.width, self.height] * 2)
            points = self.features(self.gray, bbox)
            matches = sorted(
                [
                    (self.overlap(box["bbox"], b["bbox"]), b["track_id"])
                    for b in self.overlays.get(frame_index, [])
                    if b.get("track_id") is not None
                    and b["label"] == box["label"]
                    and b["track_id"] not in claimed
                ],
                reverse=True,
            )
            anchor = None
            if (
                matches
                and matches[0][0] >= 0.5
                and (len(matches) == 1 or matches[0][0] - matches[1][0] >= 0.15)
            ):
                anchor = matches[0][1]
                claimed.add(anchor)
            self.objects.append(
                {
                    "box": box,
                    "id": i + 1,
                    "bbox": bbox,
                    "points": points,
                    "minimum": max(6, 0 if points is None else int(len(points) * 0.3)),
                    "anchor": anchor,
                    "lost": anchor is None and (points is None or len(points) < 6),
                }
            )
        self.ended = False

    @staticmethod
    def image(frame):
        # ponytail: 640px short-term preview; add ReID/segmentation for persistent identity after occlusion.
        scale = min(1, 640 / frame.shape[1])
        frame = cv2.resize(frame, None, fx=scale, fy=scale)
        return cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    @staticmethod
    def overlap(a, b):
        intersection = max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(
            0, min(a[3], b[3]) - max(a[1], b[1])
        )
        union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - intersection
        return intersection / union if union > 0 else 0

    @staticmethod
    def features(gray, bbox):
        mask = np.zeros_like(gray)
        x1, y1, x2, y2 = bbox.astype(int)
        dx, dy = int((x2 - x1) * 0.08), int((y2 - y1) * 0.08)
        mask[max(0, y1 + dy) : max(0, y2 - dy), max(0, x1 + dx) : max(0, x2 - dx)] = 255
        return cv2.goodFeaturesToTrack(gray, 50, 0.01, 3, mask=mask)

    def snapshot(self):
        boxes, lost = [], []
        for item in self.objects:
            box = {**item["box"], "track_id": item["id"], "source": "prompt_tracker"}
            box["bbox"] = (item["bbox"] / ([self.width, self.height] * 2)).tolist()
            if item["lost"]:
                lost.append({**box, "reason": "Titik objek hilang; jeda dan tandai ulang."})
            else:
                boxes.append(box)
        return {"frame_index": self.index, "boxes": boxes, "lost": lost}

    def advance(self, count):
        self.touched = time.monotonic()
        frames = []
        for _ in range(count):
            ok, frame = self.capture.read()
            if not ok:
                self.ended = True
                break
            gray = self.image(frame)
            for item in self.objects:
                if item["lost"]:
                    continue
                anchor = next(
                    (
                        b
                        for b in self.overlays.get(self.index + 1, [])
                        if b.get("track_id") == item["anchor"]
                        and item["anchor"] is not None
                        and b["label"] == item["box"]["label"]
                    ),
                    None,
                )
                if anchor is not None:
                    anchored = np.array(anchor["bbox"], dtype=np.float32) * (
                        [self.width, self.height] * 2
                    )
                    if self.overlap(item["bbox"], anchored) < 0.3:
                        item["lost"] = True
                        continue
                    # Reseeding is allowed only while the same cached detector ID guides the box.
                    item["bbox"] = anchored
                    item["points"] = self.features(gray, anchored)
                    item["minimum"] = max(
                        6, 0 if item["points"] is None else int(len(item["points"]) * 0.3)
                    )
                    continue
                points = item["points"]
                if points is None or len(points) < item["minimum"]:
                    item["lost"] = True
                    continue
                nxt, valid, error = cv2.calcOpticalFlowPyrLK(
                    self.gray, gray, points, np.empty_like(points)
                )
                if nxt is None or valid is None or error is None:
                    item["lost"] = True
                    continue
                back, back_valid, _ = cv2.calcOpticalFlowPyrLK(
                    gray, self.gray, nxt, np.empty_like(nxt)
                )
                if back is None or back_valid is None:
                    item["lost"] = True
                    continue
                good = (
                    (valid.ravel() > 0)
                    & (error.ravel() < 30)
                    & (back_valid.ravel() > 0)
                    & (np.linalg.norm(back - points, axis=2).ravel() < 1.5)
                )
                if good.sum() < item["minimum"]:
                    item["lost"] = True
                    continue
                shifts = (nxt - points)[good].reshape(-1, 2)
                delta = np.median(shifts, axis=0)
                coherent = np.linalg.norm(shifts - delta, axis=1) < 3
                if coherent.sum() < max(item["minimum"], len(shifts) * 0.5):
                    item["lost"] = True
                    continue
                bbox = item["bbox"] + np.tile(delta, 2)
                bbox = np.clip(bbox, 0, [self.width, self.height] * 2)
                x1, y1, x2, y2 = bbox
                if x2 - x1 < 3 or y2 - y1 < 3:
                    item["lost"] = True
                    continue
                # Keep the original feature cohort; reseeding a moving box can adopt a neighbor.
                item["points"] = nxt[good][coherent].reshape(-1, 1, 2)
                item["bbox"] = bbox
            self.gray = gray
            self.index += 1
            frames.append(self.snapshot())
        return {"frames": frames, "ended": self.ended, "next_frame": self.index}

    def close(self):
        self.capture.release()
