"""Tests for post-hoc paired analysis; no corpus or model is loaded."""

import csv
import hashlib
import importlib
import json
import subprocess
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "extensions/experiments/paired_orders.py"
SOURCE = ROOT / "extensions/results/experiments.csv"
sys.path.insert(0, str(ROOT))


class PairedOrdersTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(SCRIPT.is_file(), "Paired analysis has not been implemented")
        self.module = importlib.import_module("extensions.experiments.paired_orders")
        with SOURCE.open(encoding="utf-8", newline="") as stream:
            self.rows = list(csv.DictReader(stream))

    def target(self, order=4):
        return next(row for row in self.rows if row["method"] == "kneser_ney"
                    and row["seed"] == "42" and row["min_count"] == "2"
                    and row["n"] == str(order))

    def test_each_pair_agrees_with_independent_decimal_arithmetic(self):
        pairs, summaries = self.module.analyze(self.rows)
        self.assertEqual((len(pairs), len(summaries)), (6, 2))
        for pair in pairs:
            lookup = {int(row["n"]): row for row in self.rows
                      if row["method"] == "kneser_ney"
                      and int(row["seed"]) == pair["seed"]
                      and int(row["min_count"]) == pair["min_count"]}
            a, b = Decimal(lookup[3]["perplexity"]), Decimal(lookup[4]["perplexity"])
            self.assertAlmostEqual(pair["delta_pp"], float(a - b), places=10)
            self.assertAlmostEqual(pair["relative_reduction_pct"],
                                   float(100 * (a - b) / a), places=10)
            self.assertGreater(pair["delta_pp"], 0)

    def test_summary_uses_paired_sample_standard_deviation(self):
        for seed, delta in ((42, 1), (43, 2), (44, 3)):
            for row in self.rows:
                if row["method"] == "kneser_ney" and row["min_count"] == "2":
                    if row["seed"] == str(seed) and row["n"] in ("3", "4"):
                        row["perplexity"] = str(100 if row["n"] == "3" else 100 - delta)
        _, summaries = self.module.analyze(self.rows)
        self.assertEqual(summaries[0]["delta_pp_mean"], 2)
        self.assertEqual(summaries[0]["delta_pp_std_ddof1"], 1)
        self.assertEqual(summaries[0]["relative_reduction_pct_mean"], 2)

    def test_input_order_does_not_change_results(self):
        self.assertEqual(self.module.analyze(self.rows), self.module.analyze(self.rows[::-1]))

    def test_reports_regressions_and_ties_without_changing_the_sign(self):
        self.target(4)["perplexity"] = self.target(3)["perplexity"]
        pairs, summaries = self.module.analyze(self.rows)
        self.assertEqual(pairs[0]["delta_pp"], 0)
        self.assertEqual(summaries[0]["improved_seeds"], 2)
        self.target(4)["perplexity"] = "500"
        pairs, summaries = self.module.analyze(self.rows)
        self.assertLess(pairs[0]["delta_pp"], 0)
        self.assertEqual(summaries[0]["improved_seeds"], 2)

    def test_missing_row_is_rejected(self):
        self.rows.remove(self.target())
        with self.assertRaisesRegex(ValueError, "grid"):
            self.module.analyze(self.rows)

    def test_duplicate_row_is_rejected(self):
        self.rows[-1] = dict(self.rows[0])
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            self.module.analyze(self.rows)

    def test_unexpected_seed_is_rejected(self):
        self.target()["seed"] = "45"
        with self.assertRaisesRegex(ValueError, "grid"):
            self.module.analyze(self.rows)

    def test_vocabulary_mismatch_is_rejected(self):
        self.target()["V"] = "1"
        with self.assertRaisesRegex(ValueError, "metadata"):
            self.module.analyze(self.rows)

    def test_target_count_mismatch_is_rejected(self):
        self.target()["predicted_tokens"] = "1"
        with self.assertRaisesRegex(ValueError, "metadata"):
            self.module.analyze(self.rows)

    def test_nonpositive_metadata_is_rejected(self):
        self.target()["V"] = "0"
        with self.assertRaises(ValueError):
            self.module.analyze(self.rows)

    def test_invalid_perplexity_is_rejected(self):
        for value in ("", "nan", "inf", "-inf", "0", "-1", "not-a-number"):
            with self.subTest(value=value):
                self.target()["perplexity"] = value
                with self.assertRaises(ValueError):
                    self.module.analyze(self.rows)

    def test_missing_column_is_rejected(self):
        del self.target()["perplexity"]
        with self.assertRaises(ValueError):
            self.module.analyze(self.rows)

    def test_unnormalized_backoff_is_excluded(self):
        with self.assertRaisesRegex(ValueError, "normalized"):
            self.module.analyze(self.rows, method="stupid_backoff")
        pairs, _ = self.module.analyze(self.rows, method="laplace")
        self.assertEqual(len(pairs), 6)
        self.assertTrue(all(pair["delta_pp"] < 0 for pair in pairs))

    def test_cli_preserves_input_and_records_output_hashes(self):
        before = SOURCE.read_bytes()
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "result"
            command = [sys.executable, str(SCRIPT), "--input", str(SOURCE),
                       "--output", str(output)]
            result = subprocess.run(command, capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
            manifest = json.loads((output / "manifest.json").read_text())
            self.assertEqual(manifest["status"], "completed")
            self.assertEqual(manifest["input_sha256"], hashlib.sha256(before).hexdigest())
            self.assertEqual(manifest["script_sha256"],
                             hashlib.sha256(SCRIPT.read_bytes()).hexdigest())
            for filename, expected in manifest["output_sha256"].items():
                self.assertEqual(hashlib.sha256((output / filename).read_bytes()).hexdigest(),
                                 expected)
            saved = {p.name: p.read_bytes() for p in output.iterdir()}
            retry = subprocess.run(command, capture_output=True, text=True, check=False)
            self.assertNotEqual(retry.returncode, 0)
            self.assertEqual(saved, {p.name: p.read_bytes() for p in output.iterdir()})
        self.assertEqual(SOURCE.read_bytes(), before)

    def test_altered_input_is_rejected_without_creating_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "changed.csv"
            source.write_bytes(SOURCE.read_bytes().replace(b"327.772930919238", b"300.0"))
            output = Path(temporary) / "result"
            with self.assertRaisesRegex(ValueError, "snapshot"):
                self.module.run_analysis(source, output)
            self.assertFalse(output.exists())

    def test_crlf_checkout_is_explicitly_normalized_and_raw_hash_recorded(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "windows.csv"
            source.write_bytes(SOURCE.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))
            output = Path(temporary) / "result"
            self.module.run_analysis(source, output)
            manifest = json.loads((output / "manifest.json").read_text())
            self.assertEqual(manifest["input_sha256"],
                             hashlib.sha256(source.read_bytes()).hexdigest())
            self.assertTrue(manifest["crlf_normalized_for_snapshot_check"])

    def test_repeated_runs_have_identical_numeric_outputs(self):
        with tempfile.TemporaryDirectory() as temporary:
            a, b = Path(temporary) / "a", Path(temporary) / "b"
            self.module.run_analysis(SOURCE, a)
            self.module.run_analysis(SOURCE, b)
            for name in ("paired_orders.csv", "paired_summary.csv"):
                self.assertEqual((a / name).read_bytes(), (b / name).read_bytes())

    def test_extreme_finite_values_do_not_emit_infinite_derived_values(self):
        self.target(3)["perplexity"] = "1e-300"
        self.target(4)["perplexity"] = "1e300"
        with self.assertRaisesRegex(ValueError, "finite"):
            self.module.analyze(self.rows)


if __name__ == "__main__":
    unittest.main()
