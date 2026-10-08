"""Workspace-local paths, set before ML and upload libraries are imported."""

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
for variable, relative in {
    "TEMP": ".tmp",
    "TMP": ".tmp",
    "HF_HOME": ".cache/huggingface",
    "TORCH_HOME": ".cache/torch",
    "YOLO_CONFIG_DIR": ".cache/ultralytics",
    "MPLCONFIGDIR": ".cache/matplotlib",
}.items():
    path = ROOT / relative
    path.mkdir(parents=True, exist_ok=True)
    os.environ[variable] = str(path)
tempfile.tempdir = str(ROOT / ".tmp")
MODELS = ROOT / "models"
JOBS = ROOT / "data" / "jobs"
for path in (MODELS, JOBS):
    path.mkdir(parents=True, exist_ok=True)

CHAT_BASE = MODELS / "chat-base-qwen3-17b"
CHAT_ADAPTER = MODELS / "chat-adapter-qwen3-17b"

INDEX = ROOT / "index.html"
if not INDEX.is_file():
    INDEX = Path(sys.prefix) / "share/industrial-video-workspace/index.html"


def select_device(preference: str = "auto", required_gb: float = 0.5) -> tuple[str, str]:
    """Prefer RTX 4060, checking free VRAM; CUDA wheels also execute CPU workloads."""
    import torch

    if preference not in {"auto", "cpu", "cuda"}:
        raise ValueError("Pilih auto, cpu, atau cuda.")
    if preference == "cpu":
        return "cpu", "CPU dipilih pengguna"
    try:
        if not torch.cuda.is_available():
            return "cpu", "CUDA tidak tersedia; menggunakan CPU"
        devices = list(range(torch.cuda.device_count()))
        index = next((i for i in devices if "4060" in torch.cuda.get_device_name(i)), devices[0])
        free, _ = torch.cuda.mem_get_info(index)
        if free < required_gb * 2**30:
            return "cpu", f"VRAM bebas kurang dari {required_gb:g} GiB; menggunakan CPU"
        return f"cuda:{index}", torch.cuda.get_device_name(index)
    except (RuntimeError, AssertionError):
        return "cpu", "CUDA tidak dapat digunakan; menggunakan CPU"
