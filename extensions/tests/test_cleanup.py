import hashlib
import json
from pathlib import Path

from extensions.experiments import run


def test_core_manifest_available_without_cache(tmp_path, monkeypatch):
    root = tmp_path / "project"
    source = root / "core" / "model.py"
    source.parent.mkdir(parents=True)
    source.write_text("value = 42\n", encoding="utf-8")
    manifest = root / "verifikasi" / "core_manifest.json"
    manifest.parent.mkdir()
    manifest.write_text(
        json.dumps({"core/model.py": hashlib.sha256(source.read_bytes()).hexdigest()}),
        encoding="utf-8",
    )
    monkeypatch.setattr(run, "ROOT", root)
    run.assert_core_frozen()


def test_reorganized_results_are_complete():
    root = Path(__file__).resolve().parents[2]
    assert len(list((root / "extensions/results/tuning").glob("tuning_*.json"))) == 120
    assert len(list((root / "extensions/results/splits").glob("split_*.json"))) == 3
