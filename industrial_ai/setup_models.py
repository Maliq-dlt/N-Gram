"""Download public, pinned checkpoints inside this project, then smoke-load them."""

import hashlib
import json
import shutil

from runtime import MODELS


def main():
    from urllib.request import urlretrieve

    import torch
    from huggingface_hub import hf_hub_download, snapshot_download
    from ultralytics import YOLO

    torch.set_num_threads(8)
    manifest = {}
    detector = MODELS / "yolo26n.pt"
    if not detector.is_file():
        urlretrieve(
            "https://github.com/ultralytics/assets/releases/download/v8.4.0/yolo26n.pt", detector
        )
    assert (
        hashlib.sha256(detector.read_bytes()).hexdigest()
        == "9b09cc8bf347f0fc8a5f7657480587f25db09b34bf33b0652110fb03a8ad4fef"
    )
    model = YOLO(str(detector))
    manifest["detector"] = {
        "path": detector.name,
        "classes": model.names,
        "sha256": hashlib.sha256(detector.read_bytes()).hexdigest(),
    }
    ppe_repo = "keremberke/yolov8n-hard-hat-detection"
    revision = "287bafa2feb311ee45d21f9e9b33315ff6ff955d"
    source = hf_hub_download(ppe_repo, "best.pt", revision=revision)
    ppe = MODELS / "helmet.pt"
    shutil.copy2(source, ppe)
    assert (
        hashlib.sha256(ppe.read_bytes()).hexdigest()
        == "05ed3a517485292d42d6eb6c9be3987ea51cd162e04807d2741eadcac8a19e6c"
    )
    model = YOLO(str(ppe))
    assert set(model.names.values()) == {"Hardhat", "NO-Hardhat"}
    manifest["helmet"] = {
        "repo": ppe_repo,
        "revision": revision,
        "classes": model.names,
        "sha256": hashlib.sha256(ppe.read_bytes()).hexdigest(),
    }
    repo = "Qwen/Qwen3-1.7B"
    revision = "70d244cc86ccca08cf5af4e1e306ecf908b1ad5e"
    snapshot_download(
        repo,
        revision=revision,
        local_dir=MODELS / "chat-base-qwen3-17b",
        allow_patterns=["*.json", "*.safetensors", "*.txt"],
    )
    manifest["chat"] = {
        "repo": repo,
        "revision": revision,
        "device": "cpu",
        "fine_tuned": (MODELS / "chat-adapter-qwen3-17b/adapter_model.safetensors").is_file(),
    }
    (MODELS / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
