"""Group verified observations by recording/track; camera gaps end a sequence."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime

SYMBOLS = {"PERSON_ENTER_ZONE", "PERSON_EXIT_ZONE", "HELMET_UNKNOWN"}


def event_sequences(rows, max_gap_seconds=30):
    if type(max_gap_seconds) not in (int, float) or not 0 < max_gap_seconds <= 86400:
        raise ValueError("Gap must be positive and at most one day.")
    grouped = defaultdict(list)
    seen = set()
    for row in rows:
        if row.get("status") != "verified" or row.get("category") != "observation":
            continue
        if row["symbol"] not in SYMBOLS or row.get("track_id") is None or not row.get("job_id"):
            raise ValueError("Verified observation lacks a supported symbol/recording/track.")
        when = datetime.fromisoformat(row["occurred_at"].replace("Z", "+00:00"))
        if when.tzinfo is None:
            raise ValueError("Observation time must include a timezone.")
        unique = (
            row["workspace_id"],
            row["job_id"],
            row["track_id"],
            when.timestamp(),
            row["symbol"],
        )
        if unique in seen:
            continue
        seen.add(unique)
        grouped[unique[:3]].append((when.timestamp(), row))
    result = []
    for key, observations in sorted(grouped.items()):
        chunk = []
        previous = None
        session_index = 0
        start_reason = "track_start"

        def finish():
            nonlocal session_index
            if chunk:
                result.append(
                    {
                        "workspace_id": key[0],
                        "recording_id": key[1],
                        "track_id": key[2],
                        "session_index": session_index,
                        "start_reason": start_reason,
                        "symbols": [item["symbol"] for item in chunk],
                        "event_ids": [item["id"] for item in chunk],
                        "times": [item["occurred_at"] for item in chunk],
                    }
                )
                session_index += 1

        for when, row in sorted(
            observations,
            key=lambda item: (
                item[0],
                item[1]["symbol"] == "HELMET_UNKNOWN",
                item[1]["symbol"],
                item[1]["id"],
            ),
        ):
            if previous is not None and when - previous > max_gap_seconds:
                finish()
                chunk = []
                start_reason = "camera_gap"
            chunk.append(row)
            previous = when
        finish()
    return result
