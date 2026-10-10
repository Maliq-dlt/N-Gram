"""Document provenance and duplicate-aware splits; frozen preprocessing stays unchanged."""

import hashlib
import json
import random
from collections import defaultdict
from pathlib import Path

from core.src.data import DATA_DIR
from core.src.preprocess import preprocess

POLICY = "document-exact-sentence-and-5gram-jaccard-0.9-v1"


def digest(value):
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def validate_documents(documents):
    if not isinstance(documents, list) or not documents:
        raise ValueError("Documents must be a nonempty list")
    seen = set()
    for doc in documents:
        if not isinstance(doc, dict) or not {"id", "source", "license", "sentences"} <= doc.keys():
            raise ValueError("Document requires id/source/license/sentences")
        for key in ("id", "source", "license"):
            if not isinstance(doc[key], str) or not doc[key].strip() or len(doc[key]) > 1000:
                raise ValueError(f"Invalid document {key}")
        if doc["id"] in seen:
            raise ValueError("Duplicate document id")
        seen.add(doc["id"])
        if not isinstance(doc["sentences"], list) or not doc["sentences"]:
            raise ValueError("Empty document")
        for sentence in doc["sentences"]:
            if (
                not isinstance(sentence, list)
                or not sentence
                or any(not isinstance(w, str) or not w or len(w) > 256 for w in sentence)
            ):
                raise ValueError("Sentences must contain bounded nonempty token strings")
        if "group" in doc and (not isinstance(doc["group"], str) or not doc["group"]):
            raise ValueError("Invalid source group")
    return documents


def read_documents(path):
    path = Path(path)
    if path.stat().st_size > 128 * 2**20:
        raise ValueError("Dataset exceeds 128 MiB")
    with path.open(encoding="utf-8") as stream:
        docs = []
        for line in stream:
            if len(line) > 2**20:
                raise ValueError("Document line exceeds 1 MiB")
            if line.strip():
                docs.append(json.loads(line))
    return validate_documents(docs)


def nltk_documents(name, limit=None, download=False):
    if name not in ("brown", "reuters") or (
        limit is not None and (type(limit) is not int or limit < 3)
    ):
        raise ValueError("Corpus brown/reuters; limit >=3")
    import nltk

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if str(DATA_DIR) not in nltk.data.path:
        nltk.data.path.insert(0, str(DATA_DIR))
    resources = [name] + (["punkt_tab"] if name == "reuters" else [])
    for resource in resources:
        location = f"tokenizers/{resource}" if resource == "punkt_tab" else f"corpora/{resource}"
        try:
            try:
                nltk.data.find(location)
            except LookupError:
                nltk.data.find(location + ".zip")
        except LookupError:
            if not download or not nltk.download(resource, download_dir=str(DATA_DIR), quiet=True):
                raise ValueError(
                    f"Missing {resource}; use --download to prepare local corpus"
                ) from None
    from nltk.corpus import brown, reuters

    reader = brown if name == "brown" else reuters
    ids = sorted(reader.fileids())
    if limit:
        ids = ids[:limit]
    docs = []
    for fileid in ids:
        sentences, _ = preprocess(reader.sents(fileid))
        if sentences:
            docs.append(
                {
                    "id": f"{name}/{fileid}",
                    "source": f"nltk:{name}",
                    "license": f"NLTK corpus {name}: see packaged README",
                    "genre": ",".join(reader.categories(fileid)),
                    "sentences": sentences,
                }
            )
    return validate_documents(docs)


def split_documents(documents, seed=42):
    """Union exact documents/sentences, shared source groups, and near-duplicate documents."""
    validate_documents(documents)
    if type(seed) is not int or not 0 <= seed < 2**32:
        raise ValueError("Seed must be uint32")
    ordered = sorted(documents, key=lambda d: d["id"])
    parent = list(range(len(ordered)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def join(i, j):
        parent[find(i)] = find(j)

    exact, groups, sentence_owner, inverted, shingles = {}, {}, {}, defaultdict(set), []
    for i, doc in enumerate(ordered):
        fingerprint = digest(doc["sentences"])
        if fingerprint in exact:
            join(i, exact[fingerprint])
        exact[fingerprint] = i
        if "group" in doc:
            if doc["group"] in groups:
                join(i, groups[doc["group"]])
            groups[doc["group"]] = i
        current = set()
        for sentence in doc["sentences"]:
            key = tuple(sentence)
            if key in sentence_owner:
                join(i, sentence_owner[key])
            sentence_owner[key] = i
            current.update(tuple(sentence[k : k + 5]) for k in range(max(0, len(sentence) - 4)))
        candidates = set().union(*(inverted[g] for g in current)) if current else set()
        for j in candidates:
            other = shingles[j]
            if len(current & other) / len(current | other) >= 0.9:
                join(i, j)
        shingles.append(current)
        for gram in current:
            inverted[gram].add(i)
    members = defaultdict(list)
    for i, doc in enumerate(ordered):
        members[find(i)].append(doc)
    grouped = sorted(members.values(), key=lambda ds: ds[0]["id"])
    if len(grouped) < 3:
        raise ValueError("Need >=3 independent groups after duplicate/source grouping")
    random.Random(seed).shuffle(grouped)
    cut1 = max(1, min(len(grouped) - 2, int(len(grouped) * 0.8)))
    cut2 = max(cut1 + 1, min(len(grouped) - 1, int(len(grouped) * 0.9)))
    # Copies retain independent resampling units without mutating source provenance.
    grouped = [
        [dict(d, split_group=digest(sorted(x["id"] for x in group))) for d in group]
        for group in grouped
    ]
    split = {
        name: [d for group in chunk for d in group]
        for name, chunk in zip(
            ("train", "dev", "test"), (grouped[:cut1], grouped[cut1:cut2], grouped[cut2:])
        )
    }
    manifest = {
        "policy": POLICY,
        "seed": seed,
        "corpus_sha256": digest(ordered),
        "groups": [[d["id"] for d in group] for group in grouped],
        "ids": {name: [d["id"] for d in docs] for name, docs in split.items()},
    }
    return split, manifest


def sentences(documents):
    return [sentence for doc in documents for sentence in doc["sentences"]]
