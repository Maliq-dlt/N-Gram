"""Importer trust boundaries and deterministic plaintext conversion; no network in tests."""

import hashlib
import json
from urllib.parse import urlencode

import pytest

from extensions.experiments import prepare_indonesian as importer


def page():
    return {
        "ns": 0,
        "pageid": 123,
        "title": "Teknologi",
        "pagelanguage": "id",
        "extract": (
            "Teknologi membantu masyarakat mengolah informasi dan membangun perangkat "
            "yang bermanfaat. Komputer digunakan untuk penelitian industri pendidikan "
            "komunikasi serta produksi barang dalam kehidupan sehari hari."
        ),
        "revisions": [{"revid": 456, "timestamp": "2026-10-10T00:00:00Z"}],
    }


def test_plaintext_conversion_and_article_attribution():
    document, evidence = importer.parse_page(page())
    assert document["id"] == document["group"] == "idwiki/123"
    assert len(document["sentences"]) == 2
    assert all(
        word.isalpha() and word == word.lower()
        for sentence in document["sentences"]
        for word in sentence
    )
    assert document["license"] == "CC-BY-SA-4.0"
    assert evidence["revision_url"].endswith("oldid=456")
    assert evidence["authors_history_url"].endswith("action=history")
    assert evidence["extract_sha256"] == hashlib.sha256(page()["extract"].encode()).hexdigest()
    assert evidence["tokens_sha256"] == importer.digest(document["sentences"])


@pytest.mark.parametrize(
    "change",
    [
        {"ns": 1},
        {"missing": True},
        {"extract": ""},
        {"pagelanguage": "en"},
        {"revisions": []},
        {"extract": "Singkat."},
    ],
)
def test_nonarticle_missing_and_tiny_extracts_skipped(change):
    assert importer.parse_page({**page(), **change}) is None


def test_html_and_invalid_identifiers_rejected():
    with pytest.raises(ValueError, match="plain-text"):
        importer.parse_page({**page(), "extract": "<div>Article</div>"})
    with pytest.raises(ValueError, match="identifier"):
        importer.parse_page({**page(), "pageid": -1})


def test_network_requires_opt_in_and_cache_hash_is_verified(tmp_path, monkeypatch):
    monkeypatch.setattr(importer, "ROOT", tmp_path)
    parameters = {"meta": "siteinfo", "siprop": "rightsinfo"}
    with pytest.raises(ValueError, match="--download"):
        importer.api_request(parameters)
    url = (
        importer.API
        + "?"
        + urlencode(
            {
                "action": "query",
                "format": "json",
                "formatversion": 2,
                "maxlag": 5,
                **parameters,
            }
        )
    )
    key = hashlib.sha256(url.encode()).hexdigest()
    cache = tmp_path / ".cache" / "idwiki"
    cache.mkdir(parents=True)
    raw = json.dumps({"query": {"rightsinfo": {"url": importer.LICENSE_URL}}})
    envelope = {
        "url": url,
        "raw_json": raw,
        "retrieved_at": "2026-10-10T00:00:00Z",
        "response_sha256": hashlib.sha256(raw.encode()).hexdigest(),
    }
    path = cache / (key + ".json")
    path.write_text(json.dumps(envelope), encoding="utf-8")
    data, evidence = importer.api_request(parameters)
    assert data["query"]["rightsinfo"]["url"] == importer.LICENSE_URL
    assert evidence["url"] == url
    envelope["raw_json"] += " "
    path.write_text(json.dumps(envelope), encoding="utf-8")
    with pytest.raises(ValueError, match="hash mismatch"):
        importer.api_request(parameters)


def test_output_and_budget_boundaries(tmp_path, monkeypatch):
    monkeypatch.setattr(importer, "ROOT", tmp_path)
    with pytest.raises(ValueError, match="inside"):
        importer.prepare(tmp_path / "outside")
    with pytest.raises(ValueError, match="30"):
        importer.prepare(tmp_path / "data" / "pilot", limit=29)
    existing = tmp_path / "data" / "existing"
    existing.mkdir(parents=True)
    with pytest.raises(FileExistsError):
        importer.prepare(existing)
