"""Corpus readers; downloads and caches stay inside this project."""

import random
from pathlib import Path

import nltk

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "nltk_data"


def load_corpus(name="brown"):
    readers = {"brown": "brown", "reuters": "reuters"}
    if name not in readers:
        raise ValueError(f"Corpus harus salah satu {tuple(readers)}")
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if str(DATA_DIR) not in nltk.data.path:
        nltk.data.path.insert(0, str(DATA_DIR))
    resource = readers[name]
    try:
        nltk.data.find(f"corpora/{resource}.zip")
    except LookupError:
        if not nltk.download(resource, download_dir=str(DATA_DIR), quiet=True):
            raise RuntimeError(f"Download {resource} gagal; periksa koneksi")
    if name != "brown":
        if not nltk.download("punkt_tab", download_dir=str(DATA_DIR), quiet=True):
            raise RuntimeError("Download tokenizer punkt_tab gagal")
    from nltk.corpus import brown, reuters

    sentences = {
        "brown": lambda: brown.sents(),
        "reuters": lambda: reuters.sents(),
    }[name]()
    return [list(sentence) for sentence in sentences]


def set_seed(seed=42):
    random.seed(seed)
    import numpy as np

    np.random.seed(seed)
