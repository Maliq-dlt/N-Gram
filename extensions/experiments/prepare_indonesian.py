"""Bounded Indonesian Wikipedia introductions with attribution and raw API evidence."""

import argparse
import hashlib
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from core.src.data import ROOT
from core.src.preprocess import preprocess, tokenize
from extensions.src.datasets import digest, split_documents, validate_documents

API = "https://id.wikipedia.org/w/api.php"
LICENSE = "CC-BY-SA-4.0"
LICENSE_URL = "https://creativecommons.org/licenses/by-sa/4.0/"
TERMS = "https://foundation.wikimedia.org/wiki/Policy:Terms_of_Use#7._Licensing_of_Content"
POLICY = "idwiki-intro-punctuation-newline-wordpunct-alpha-lower-v1"
# Encyclopedic topic selection, not a representative Indonesian/news corpus.
TITLES = (
    "Teknologi",
    "Komputer",
    "Perangkat lunak",
    "Perangkat keras",
    "Internet",
    "Kecerdasan buatan",
    "Pembelajaran mesin",
    "Robot",
    "Otomatisasi",
    "Basis data",
    "Algoritma",
    "Pemrograman komputer",
    "Sistem operasi",
    "Jaringan komputer",
    "Keamanan komputer",
    "Kriptografi",
    "Telekomunikasi",
    "Serat optik",
    "Satelit",
    "Semikonduktor",
    "Transistor",
    "Elektronika",
    "Mikroprosesor",
    "Sensor",
    "Industri",
    "Manufaktur",
    "Revolusi Industri",
    "Logistik",
    "Rantai pasok",
    "Energi terbarukan",
    "Tenaga surya",
    "Tenaga angin",
    "Baterai",
    "Kendaraan listrik",
    "Pertanian",
    "Irigasi",
    "Hidroponik",
    "Pupuk",
    "Traktor",
    "Bioteknologi",
    "Nanoteknologi",
    "Pencetakan 3D",
    "Rekayasa",
    "Metalurgi",
    "Baja",
    "Semen",
    "Tekstil",
    "Industri otomotif",
    "Mesin uap",
    "Turbin",
    "Pompa",
    "Motor listrik",
    "Pengolahan air",
    "Daur ulang",
    "Pembangkit listrik",
    "Panel surya",
    "Penginderaan jauh",
    "Sistem informasi geografis",
    "Pertambangan",
    "Petroleum",
)


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def api_request(parameters, download=False):
    """Cache exact HTTPS JSON responses in-repo; network is explicitly opt-in."""
    url = (
        API
        + "?"
        + urlencode(
            {"action": "query", "format": "json", "formatversion": 2, "maxlag": 5, **parameters}
        )
    )
    key = hashlib.sha256(url.encode()).hexdigest()
    cache = ROOT / ".cache" / "idwiki"
    path = cache / (key + ".json")
    if path.exists():
        envelope = json.loads(path.read_text(encoding="utf-8"))
    else:
        if not download:
            raise ValueError("Missing API cache; pass --download to fetch public Wikipedia content")
        request = Request(
            url,
            headers={
                "User-Agent": "NgramResearchPilot/1.0 (local educational corpus; Python urllib)",
                "Accept": "application/json",
            },
        )
        with urlopen(request, timeout=30) as response:
            raw = response.read(32 * 2**20 + 1)
        if len(raw) > 32 * 2**20:
            raise ValueError("API response exceeds 32 MiB")
        data = json.loads(raw)
        if "error" in data:
            raise ValueError(f"MediaWiki API error: {data['error']}")
        envelope = {
            "url": url,
            "retrieved_at": timestamp(),
            "response_sha256": hashlib.sha256(raw).hexdigest(),
            "raw_json": raw.decode("utf-8"),
        }
        cache.mkdir(parents=True, exist_ok=True)
        with path.open("x", encoding="utf-8") as stream:
            json.dump(envelope, stream, ensure_ascii=False)
        time.sleep(1)
    raw = envelope["raw_json"].encode("utf-8")
    if envelope["url"] != url or hashlib.sha256(raw).hexdigest() != envelope["response_sha256"]:
        raise ValueError("API cache provenance/hash mismatch")
    data = json.loads(raw)
    if "error" in data:
        raise ValueError("Cached MediaWiki error")
    return data, {key: envelope[key] for key in ("url", "retrieved_at", "response_sha256")}


def parse_page(page):
    """Only API plaintext article introductions; no HTML, menus or sidebar scraping."""
    if (
        page.get("ns") != 0
        or "missing" in page
        or not page.get("extract")
        or not page.get("revisions")
        or page.get("pagelanguage") != "id"
    ):
        return None
    extract = page["extract"]
    if not isinstance(extract, str) or "<" in extract or ">" in extract:
        raise ValueError("Expected plain-text article extract")
    chunks = re.split(r"(?<=[.!?])\s+|\n+", extract.strip())
    sentences, _ = preprocess([tokenize(chunk) for chunk in chunks if chunk.strip()])
    if sum(map(len, sentences)) < 20:
        return None
    revision = page["revisions"][0]
    pageid, revid = page["pageid"], revision["revid"]
    if type(pageid) is not int or pageid < 1 or type(revid) is not int or revid < 1:
        raise ValueError("Invalid Wikipedia article/revision identifier")
    url = f"https://id.wikipedia.org/?curid={pageid}"
    doc = {
        "id": f"idwiki/{pageid}",
        "source": url,
        "license": LICENSE,
        "genre": "encyclopedia-technology-industry",
        "group": f"idwiki/{pageid}",
        "sentences": sentences,
    }
    evidence = {
        "id": doc["id"],
        "title": page["title"],
        "source_url": url,
        "observed_revision_id": revid,
        "revision_timestamp": revision["timestamp"],
        "revision_url": f"https://id.wikipedia.org/w/index.php?oldid={revid}",
        "authors_history_url": f"https://id.wikipedia.org/w/index.php?curid={pageid}&action=history",
        "extract_sha256": hashlib.sha256(extract.encode()).hexdigest(),
        "tokens_sha256": digest(sentences),
        "license": LICENSE,
        "license_url": LICENSE_URL,
        "changes": "Introduction only; sentence segmentation and lowercase alphabetic tokens",
    }
    return doc, evidence


def prepare(output, limit=40, download=False):
    output = Path(output).resolve()
    if not output.is_relative_to((ROOT / "data").resolve()):
        raise ValueError("Corpus output must remain inside repository data/")
    if type(limit) is not int or not 30 <= limit <= len(TITLES):
        raise ValueError(f"Pilot document limit must be 30..{len(TITLES)}")
    if output.exists():
        raise FileExistsError(output)
    rights, rights_request = api_request({"meta": "siteinfo", "siprop": "rightsinfo"}, download)
    rightsinfo = rights["query"]["rightsinfo"]
    if rightsinfo.get("url", "").rstrip("/") not in (
        LICENSE_URL.rstrip("/"),
        LICENSE_URL + "deed.id",
    ):
        raise ValueError("Wikipedia site license differs from configured CC-BY-SA-4.0")
    documents, articles, requests, skipped = [], [], [rights_request], []
    seen = set()
    for offset in range(0, len(TITLES), 10):
        data, request = api_request(
            {
                "prop": "extracts|info|revisions",
                "titles": "|".join(TITLES[offset : offset + 10]),
                "redirects": 1,
                "explaintext": 1,
                "exintro": 1,
                "exlimit": 10,
                "rvprop": "ids|timestamp",
                "inprop": "url",
            },
            download,
        )
        requests.append(request)
        for page in sorted(data["query"]["pages"], key=lambda item: item["title"]):
            parsed = parse_page(page)
            if parsed is None:
                skipped.append(page["title"])
                continue
            doc, article = parsed
            if doc["id"] in seen:
                continue
            seen.add(doc["id"])
            documents.append(doc)
            articles.append(article)
            if len(documents) == limit:
                break
        if len(documents) == limit:
            break
    if len(documents) < limit:
        raise ValueError(f"Only {len(documents)} usable articles; requested {limit}")
    validate_documents(documents)
    split, split_manifest = split_documents(documents, seed=42)
    if len(split_manifest["groups"]) < 30:
        raise ValueError("Pilot needs at least 30 independent duplicate-aware document groups")
    output.mkdir(parents=True)
    corpus = output / "documents.jsonl"
    with corpus.open("x", encoding="utf-8") as stream:
        for doc in documents:
            stream.write(json.dumps(doc, ensure_ascii=False) + "\n")
    manifest = {
        "format": "indonesian-wikipedia-pilot-v1",
        "created_at": timestamp(),
        "policy": POLICY,
        "language": "id",
        "license": LICENSE,
        "license_url": LICENSE_URL,
        "license_evidence": rightsinfo,
        "terms_url": TERMS,
        "api": API,
        "requests": requests,
        "selection": {"titles": TITLES, "limit": limit, "exintro": True, "seed": 42},
        "source_kind": "encyclopedic introductions; not news or representative language data",
        "preprocessing": (
            "Regex punctuation/newline segmentation (abbreviations may split); "
            "core wordpunct + alpha lowercase"
        ),
        "snapshot": (
            "Exact API response/extract hashes; revision IDs observed in same response, "
            "not revision-pinned extracts"
        ),
        "documents": len(documents),
        "sentences": sum(len(d["sentences"]) for d in documents),
        "tokens": sum(len(s) for d in documents for s in d["sentences"]),
        "independent_groups": len(split_manifest["groups"]),
        "split_sizes": {key: len(value) for key, value in split.items()},
        "documents_sha256": digest(documents),
        "jsonl_sha256": hashlib.sha256(corpus.read_bytes()).hexdigest(),
        "importer_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "articles": articles,
        "skipped": skipped,
        "attribution": (
            "Wikipedia contributors; each article source/history URL identifies authors. "
            "Derived tokens retain CC-BY-SA-4.0."
        ),
    }
    with (output / "manifest.json").open("x", encoding="utf-8") as stream:
        json.dump(manifest, stream, ensure_ascii=False, indent=2)
    return corpus, manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=40)
    parser.add_argument("--download", action="store_true")
    args = parser.parse_args(argv)
    corpus, manifest = prepare(args.output, args.limit, args.download)
    print(
        json.dumps(
            {
                "path": str(corpus),
                "documents": manifest["documents"],
                "independent_groups": manifest["independent_groups"],
                "split_sizes": manifest["split_sizes"],
                "license": manifest["license"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
