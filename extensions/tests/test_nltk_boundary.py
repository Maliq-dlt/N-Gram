"""Exercise the allowed NLTK boundary with vulnerable model APIs intercepted."""

import ast
import tempfile
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

import nltk
from nltk.classify import maxent
from nltk.corpus.reader import CategorizedTaggedCorpusReader
from nltk.parse.transitionparser import TransitionParser
from nltk.tag.perceptron import AveragedPerceptron, PerceptronTagger

ROOT = Path(__file__).resolve().parents[2]


def test_nltk_boundary():
    allowed = {
        "nltk.corpus": {"brown", "reuters"},
        "nltk.lm": {"KneserNeyInterpolated", "Vocabulary"},
        "nltk.tokenize": {"wordpunct_tokenize"},
    }
    sources = [
        *ROOT.glob("core/src/*.py"),
        *ROOT.glob("extensions/src/*.py"),
        *ROOT.glob("extensions/experiments/*.py"),
        *ROOT.glob("industrial_ai/*.py"),
    ]
    for source in sources:
        for node in ast.walk(ast.parse(source.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                for name in node.names:
                    if name.name.startswith("nltk"):
                        assert name.name == "nltk" and name.asname is None, source
            elif isinstance(node, ast.ImportFrom) and (node.module or "").startswith("nltk"):
                assert node.module in allowed, source
                assert {name.name for name in node.names} <= allowed[node.module], source
            elif isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
                if node.value.id == "nltk":
                    assert node.attr in {"data", "download"}, (source, node.attr)

    affected = [
        (TransitionParser, "train"),
        (TransitionParser, "parse"),
        (AveragedPerceptron, "save"),
        (AveragedPerceptron, "load"),
        (PerceptronTagger, "save_to_json"),
        (maxent, "save_maxent_params"),
    ]
    (ROOT / ".tmp").mkdir(exist_ok=True)
    with ExitStack() as stack:
        intercepted = [
            stack.enter_context(
                patch.object(owner, method, side_effect=AssertionError("Affected NLTK API reached"))
            )
            for owner, method in affected
        ]
        directory = Path(stack.enter_context(tempfile.TemporaryDirectory(dir=ROOT / ".tmp")))
        corpus = directory / "corpora/brown"
        corpus.mkdir(parents=True)
        for name, sentence in {
            "ca01": "The/at cat/nn sleeps/vbz ./.",
            "ca02": "The/at dog/nn sleeps/vbz ./.",
            "ca03": "A/at cat/nn walks/vbz ./.",
        }.items():
            (corpus / name).write_text(sentence + "\n", encoding="utf-8")
        stack.enter_context(patch.object(nltk.data, "path", [str(directory)]))
        reader = CategorizedTaggedCorpusReader(str(corpus), r"ca\d+", cat_pattern=r"(ca)\d+")
        stack.enter_context(patch.object(nltk.corpus, "brown", reader))
        from core.src import data
        from core.src.preprocess import tokenize
        from extensions.experiments.compare_nltk import compare
        from extensions.src import datasets
        from extensions.src.cli import load_model, save_model
        from extensions.src.models import CountBank, ExtensionLM

        stack.enter_context(patch.object(data, "DATA_DIR", directory))
        stack.enter_context(patch.object(datasets, "DATA_DIR", directory))
        # Frozen corpus loader asks for a zip pointer; a real corpus is read from the directory.
        import zipfile

        with zipfile.ZipFile(directory / "corpora/brown.zip", "w") as archive:
            for path in corpus.iterdir():
                archive.write(path, "brown/" + path.name)
        assert len(data.load_corpus("brown")) == 3
        documents = datasets.nltk_documents("brown", limit=3, download=False)
        train = [sentence for doc in documents for sentence in doc["sentences"]]
        assert tokenize("The cat, sleeps.") == ["The", "cat", ",", "sleeps", "."]
        assert all(row["max_absolute_difference"] < 1e-12 for row in compare(train))
        model = ExtensionLM(CountBank(train, max_n=3, min_count=1), 3, "kneser_ney")
        checkpoint = directory / "custom.json.gz"
        save_model(checkpoint, model, {"boundary": "controlled test"})
        restored, _ = load_model(checkpoint)
        assert restored.score("cat", ["the"]) == model.score("cat", ["the"])
        for intercepted_api in intercepted:
            intercepted_api.assert_not_called()


if __name__ == "__main__":
    test_nltk_boundary()
    print("PASS: NLTK corpus/tokenizer/KN/custom checkpoint; affected APIs unused")
