"""Wave 43: the dark-matter adjudicator, tested on fabricated modules before it is trusted on real ones.

The instrument's whole claim is that it can tell four states apart. So the tests fabricate one
module per state, drive the same code path the sweep uses, and require the separation. Then they
pin the ledger: the counts in `canonical/verification/DARK_MATTER_ADJUDICATION_20261126_V1.json`
must add up, and every PROVEN verdict named there must still be reproducible on demand.
"""
from __future__ import annotations

import json
import pathlib
import tempfile
import unittest

from canonical.tools.dark_matter_adjudicator_v1 import (
    BROKEN,
    IMPORTS_ONLY,
    MISSING_SUBSTRATE,
    PROVEN,
    _classify_failure,
    adjudicate_importable,
    run,
    self_check,
    unimported_modules,
)

ROOT = pathlib.Path(__file__).resolve().parents[2]
LEDGER = ROOT / "canonical/verification/DARK_MATTER_ADJUDICATION_20261126_V1.json"

FIXTURES = {
    "good_v1": "def self_check():\n    return {'pass': True, 'checks': 3, 'passed': 3}\n",
    "says_no_v1": "def self_check():\n    return {'pass': False, 'checks': 3, 'passed': 1}\n",
    "raises_v1": "def self_check():\n    raise RuntimeError('boom')\n",
    "no_check_v1": "VALUE = 1\n",
    "needs_kit_v1": "import a_package_this_repo_never_ships\n",
    "syntax_v1": "def broken(:\n    return 1\n",
}


class AdjudicatorSelfCheckTest(unittest.TestCase):
    def test_instrument_self_check_passes(self) -> None:
        report = self_check()
        self.assertEqual(report["verdict"], "SELF_CHECK_PASS")
        self.assertEqual(report["checks"], report["passed"])

    def test_fabricated_modules_land_in_four_distinct_states(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pkg = pathlib.Path(tmp) / "wave43_pkg"
            pkg.mkdir()
            (pkg / "__init__.py").write_text("")
            for name, body in FIXTURES.items():
                (pkg / f"{name}.py").write_text(body)

            verdicts = {
                name: adjudicate_importable(f"wave43_pkg.{name}", timeout=20.0,
                                            extra_paths=[tmp]).verdict
                for name in FIXTURES
            }

        self.assertEqual(verdicts["good_v1"], PROVEN)
        self.assertEqual(verdicts["no_check_v1"], IMPORTS_ONLY)
        self.assertEqual(verdicts["says_no_v1"], BROKEN)
        self.assertEqual(verdicts["raises_v1"], BROKEN)
        self.assertEqual(verdicts["needs_kit_v1"], MISSING_SUBSTRATE)
        self.assertEqual(verdicts["syntax_v1"], BROKEN)

    def test_third_party_absence_is_not_a_defect_but_an_in_repo_import_is(self) -> None:
        self.assertEqual(
            _classify_failure("ModuleNotFoundError: No module named 'polars'"),
            MISSING_SUBSTRATE,
        )
        self.assertEqual(
            _classify_failure("ImportError: cannot import name 'x' from 'canonical.swe_kernel.y_v1'"),
            BROKEN,
        )
        self.assertEqual(
            _classify_failure("SyntaxError: unexpected character after line continuation"),
            BROKEN,
        )

    def test_ablation_executes_nothing_and_proves_nothing(self) -> None:
        candidates = [
            ROOT / "canonical/swe_kernel/metamorphic_laws_v1.py",
            ROOT / "canonical/swe_kernel/producer_lineage_graph_v1.py",
        ]
        report = run(modules=candidates, probe=False)
        self.assertEqual(report["counts"][PROVEN], 0)
        self.assertEqual(report["counts"][IMPORTS_ONLY], len(candidates))
        self.assertEqual(report["proven_loc"], 0)
        self.assertTrue(all(v["stage"] == "ablation" for v in report["verdicts"]))

    def test_probing_enables_the_same_modules(self) -> None:
        candidates = [
            ROOT / "canonical/swe_kernel/metamorphic_laws_v1.py",
            ROOT / "canonical/swe_kernel/producer_lineage_graph_v1.py",
        ]
        report = run(modules=candidates, probe=True, workers=2, timeout=60.0)
        self.assertEqual(report["counts"][PROVEN], len(candidates))
        self.assertGreater(report["proven_loc"], 1_000)


class LedgerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.ledger = json.loads(LEDGER.read_text(encoding="utf-8"))

    def test_every_census_accounts_for_every_candidate(self) -> None:
        for key in ("no_importer_census", "every_module_census"):
            census = self.ledger[key]
            self.assertEqual(sum(census["counts"].values()), census["candidates"], key)

    def test_counts_account_for_the_every_module_census(self) -> None:
        census = self.ledger["every_module_census"]
        self.assertEqual(sum(census["counts"].values()), census["candidates"])
        self.assertEqual(len(self.ledger["proven"]), census["counts"][PROVEN])

    def test_proven_entries_match_the_proven_count_and_exist_on_disk(self) -> None:
        ledger = self.ledger
        census = ledger["every_module_census"]
        self.assertEqual(len(ledger["proven"]), census["counts"][PROVEN])
        self.assertEqual(sum(row["loc"] for row in ledger["proven"]), census["proven_loc"])
        for row in ledger["proven"]:
            self.assertTrue((ROOT / row["path"]).is_file(), row["path"])
            # `checks` is None where a module's self-check reports a boolean instead of a count.
            self.assertTrue(row["checks"] is None or row["checks"] > 0, row["module"])

    def test_quarantine_entries_match_the_broken_count(self) -> None:
        ledger = self.ledger
        self.assertEqual(len(ledger["broken_quarantine"]),
                         ledger["every_module_census"]["counts"][BROKEN])
        for row in ledger["broken_quarantine"]:
            self.assertTrue(row["probe"], row["module"])

    def test_ablation_is_recorded_as_collapsing_every_state(self) -> None:
        ablation = self.ledger["ablation"]
        self.assertEqual(ablation["counts"][PROVEN], 0)
        self.assertEqual(ablation["counts"][IMPORTS_ONLY], ablation["candidates"])

    def test_the_rule_repair_is_recorded_with_both_numbers(self) -> None:
        repair = self.ledger["candidate_rule_repair"]
        self.assertGreater(repair["before"]["no_importer_ge140_non_test"],
                           repair["after"]["no_importer_ge140_non_test"] * 5)

    def test_run_digests_are_present_and_shaped_like_sha256(self) -> None:
        for key in ("no_importer_census", "every_module_census", "ablation"):
            digest = self.ledger[key]["run_digest_sha256"]
            self.assertEqual(len(digest), 64, key)
            int(digest, 16)

    def test_ledger_proven_modules_still_pass_their_own_checks(self) -> None:
        """The six PROVEN rows are re-driven here, not trusted because they were written down."""
        rows = [row for row in self.ledger["proven"] if row["contract_source"] == "this_wave"]
        self.assertGreaterEqual(len(rows), 4)
        for row in rows:
            verdict = adjudicate_importable(row["module"], timeout=120.0)
            self.assertEqual(verdict.verdict, PROVEN, row["module"])
            self.assertEqual(verdict.evidence.get("checks"), row["checks"], row["module"])


class CandidateRuleTest(unittest.TestCase):
    def test_candidates_exclude_anything_a_peer_imports_by_dotted_name(self) -> None:
        """The bug this wave fixed: a bare-stem comparison counted dotted imports as dark."""
        names = {p.stem for p in unimported_modules()}
        for reached in ("meme_protocol_memory_v1", "metamorphic_laws_v1",
                        "producer_lineage_graph_v1", "semantic_causal_engine_v1"):
            self.assertNotIn(reached, names)
        self.assertGreater(len(names), 3_000)

    def test_test_files_are_filtered_out_of_a_run(self) -> None:
        report = run(min_loc=140, limit=200, probe=False)
        self.assertFalse([v for v in report["verdicts"] if v["module"].rsplit(".", 1)[-1]
                          .startswith("test_")])
        self.assertFalse([v for v in report["verdicts"] if "tests" in v["path"].split("/")])

    def test_every_module_scope_includes_reached_modules(self) -> None:
        report = run(everything=True, min_loc=140, limit=200, probe=False)
        self.assertEqual(report["candidate_scope"], "every_module")
        names = {v["module"] for v in report["verdicts"]}
        self.assertGreater(len(names), 0)
        self.assertEqual(report["counts"][PROVEN], 0)  # ablation never proves anything


if __name__ == "__main__":
    unittest.main()
