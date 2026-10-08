"""Run All in a fresh local kernel; no global kernel registration."""

import argparse
import hashlib
import json
import sys
from pathlib import Path

import nbformat
from jupyter_client import KernelManager
from jupyter_client.kernelspec import KernelSpecManager
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description="Run All notebook dengan kernel lokal baru")
parser.add_argument("notebook", nargs="?", default="core/ngram_lm.ipynb")
args = parser.parse_args()
path = (ROOT / args.notebook).resolve()
if not path.is_relative_to(ROOT) or path.suffix.lower() != ".ipynb" or not path.is_file():
    parser.error("Notebook harus file .ipynb yang tersedia di dalam repository")
kernel_dir = ROOT / ".cache" / "jupyter" / "kernels"
local = kernel_dir / "ngram-local"
local.mkdir(parents=True, exist_ok=True)
(local / "kernel.json").write_text(
    json.dumps(
        {
            "argv": [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"],
            "display_name": "Python (ngram local)",
            "language": "python",
        }
    ),
    encoding="utf-8",
)
manager = KernelManager(
    kernel_name="ngram-local", kernel_spec_manager=KernelSpecManager(kernel_dirs=[str(kernel_dir)])
)
notebook = nbformat.read(path, as_version=4)
client = NotebookClient(
    notebook, timeout=900, km=manager, resources={"metadata": {"path": str(ROOT)}}
)
client.execute()
nbformat.write(notebook, path)
assert all(
    o.output_type != "error" for c in notebook.cells if c.cell_type == "code" for o in c.outputs
)
print(f"Run All OK: {sum(c.cell_type == 'code' for c in notebook.cells)} code cells")

hashes = {
    str(p.relative_to(ROOT)).replace("\\", "/"): hashlib.sha256(p.read_bytes()).hexdigest()
    for p in (ROOT / "core").rglob("*")
    if p.is_file() and "__pycache__" not in p.parts
}
(ROOT / ".cache/core_frozen.json").write_text(json.dumps(hashes, indent=2), encoding="utf-8")
