"""Review positions are navigation hints, never automatic label approval."""

from pathlib import Path

from access import has_document, read_document


def review_queue(
    folder: Path, annotations: dict, corrections: dict, summary: dict, group: str
) -> dict:
    positions = {}
    flag = "complete" if group == "objects" else "helmets_complete"

    def add(index, reason):
        if isinstance(index, int) and 0 <= index < summary["frames"]:
            positions.setdefault(index, set()).add(reason)

    selection = folder / "selection.json"
    if has_document(selection):
        data = read_document(selection)
        if group in data.get("groups", ["objects", "helmets"]):
            for row in data["frames"]:
                add(row["frame_index"], "Sampel untuk review")
                if any(
                    (f["label"] in {"Hardhat", "NO-Hardhat"}) == (group == "helmets")
                    for f in row.get("review_flags", [])
                ):
                    add(row["frame_index"], "Deteksi meragukan")
    for row in annotations["frames"]:
        add(row["frame_index"], "Koreksi disahkan" if row.get(flag) else "Draft manual")
    previous_lost = set()
    for row in sorted(corrections["frames"], key=lambda r: r["frame_index"]):
        lost = {
            b["track_id"]
            for b in row.get("lost", [])
            if (b["label"] in {"Hardhat", "NO-Hardhat"}) == (group == "helmets")
        }
        if lost - previous_lost:
            add(row["frame_index"], "Target hilang; periksa ulang")
        previous_lost = lost
    saved = {row["frame_index"]: row for row in annotations["frames"]}
    rows = []
    for index, reasons in sorted(positions.items()):
        row = saved.get(index, {})
        rows.append(
            {
                "frame_index": index,
                "seconds": round(index / summary["fps"], 3),
                "reviewed": bool(row.get(flag) and group in row.get("learn_groups", [])),
                "reasons": sorted(reasons),
            }
        )
    reviewed = sum(1 for row in rows if row["reviewed"])
    return {
        "group": group,
        "positions": rows,
        "total": len(rows),
        "reviewed": reviewed,
        "pending": len(rows) - reviewed,
    }
