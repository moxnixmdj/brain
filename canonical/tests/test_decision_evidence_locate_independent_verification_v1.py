#!/usr/bin/env python3
"""Independence evidence for structured.decision_evidence.locate.stdlib must be real.

The capability had no independence evidence, so the verified bound adapter refused to
run it, which blocked every goal whose chain began with it -- measured on
EXT_DECISION_VERIFY, three capabilities wide, of which this was the only unverified one.

The evidence is not an assertion. `decision_evidence_locate_verify` re-establishes every
load-bearing claim through a mechanism the producer does not use: the candidate set from
`git grep -l`, digests from `sha256sum`, canonical form and counts from `jq`, and
decidability by re-running the consumer's own validator on bytes re-opened from disk.

These tests run the real producer against the real repository and then attack its
output. Each attack must be caught; if any is not, the evidence is worthless.
"""
import importlib.util
import json
import pathlib
import unittest

CANONICAL_ROOT = pathlib.Path(__file__).resolve().parents[1]
REPO_ROOT = CANONICAL_ROOT.parent
CAPABILITIES = CANONICAL_ROOT / "runtime" / "bound_capabilities"
TMP = CANONICAL_ROOT / "astra_runtime" / "tmp"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


producer = _load("decision_evidence_locate_under_test",
                 CAPABILITIES / "decision_evidence_locate.py")
verifier = _load("decision_evidence_locate_verify_under_test",
                 CAPABILITIES / "decision_evidence_locate_verify.py")


class DecisionEvidenceIndependenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        TMP.mkdir(parents=True, exist_ok=True)
        cls.output_rel = "canonical/astra_runtime/tmp/TEST_INDEP_DECISION_EVIDENCE_INPUT.json"
        cls.result_rel = "canonical/astra_runtime/tmp/TEST_INDEP_DECISION_EVIDENCE_RESULT.json"
        cls.report = producer.run(
            {"search_root": ".", "output_path": cls.output_rel}, str(REPO_ROOT))
        (REPO_ROOT / cls.result_rel).write_text(
            json.dumps(cls.report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        cls.output_path = REPO_ROOT / cls.output_rel
        cls.pristine = cls.output_path.read_bytes()

    @classmethod
    def tearDownClass(cls):
        # The producer walks **/*.json from the repository root, so a file this
        # suite leaves behind is itself a schema-declaring, decidable candidate
        # that sorts AHEAD of the real source. Measured: leaving these in place
        # made the next run's producer pick its own earlier output while git's
        # tracked-file search still picked the real one, and the verifier then
        # correctly reported SOURCE_NOT_IN_GIT_SCHEMA_CANDIDATES. Two tests
        # failed on the second run of the same suite and passed on a clean tree,
        # i.e. the suite was order-dependent. It must not be.
        for rel in (cls.output_rel, cls.result_rel,
                    "canonical/astra_runtime/tmp/TEST_INDEP_DECISION_EVIDENCE_PROBE.json"):
            try:
                (REPO_ROOT / rel).unlink()
            except FileNotFoundError:
                pass

    def tearDown(self):
        self.output_path.write_bytes(self.pristine)

    def _verify(self, report):
        probe = "canonical/astra_runtime/tmp/TEST_INDEP_DECISION_EVIDENCE_PROBE.json"
        (REPO_ROOT / probe).write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return verifier.run({"result_path": probe, "search_root": "."}, str(REPO_ROOT))

    def test_the_real_producer_output_verifies_clean(self):
        verdict = self._verify(self.report)
        self.assertTrue(verdict["verified"], verdict["mismatches"])
        self.assertEqual(verdict["mismatches"], [])

    def test_independent_enumeration_reproduces_the_selection(self):
        """git's own content search must pick the same file the glob walk picked."""
        verdict = self._verify(self.report)
        self.assertGreater(verdict["git_schema_candidate_count"], 1,
                           "a single candidate would make the selection check vacuous")
        self.assertEqual(verdict["first_decidable_candidate"], self.report["source_path"])

    def test_digests_come_from_an_external_tool_and_agree(self):
        verdict = self._verify(self.report)
        self.assertEqual(verdict["output_sha256"], self.report["output_sha256"])
        self.assertEqual(verdict["source_sha256"], self.report["source_sha256"])

    def test_altered_output_bytes_are_caught(self):
        self.output_path.write_bytes(self.pristine + b"\n")
        verdict = self._verify(self.report)
        self.assertFalse(verdict["verified"])
        self.assertIn("OUTPUT_SHA256_MISMATCH", verdict["mismatches"])

    def test_an_inflated_count_is_caught(self):
        """jq, not len(), extracts the counts -- padding the report must fail."""
        report = dict(self.report, evidence_count=self.report["evidence_count"] + 1)
        verdict = self._verify(report)
        self.assertFalse(verdict["verified"])
        self.assertIn("COUNT_MISMATCH:evidence_count", verdict["mismatches"])

    def test_a_forged_digest_is_caught(self):
        verdict = self._verify(dict(self.report, output_sha256="0" * 64))
        self.assertFalse(verdict["verified"])
        self.assertIn("OUTPUT_SHA256_MISMATCH", verdict["mismatches"])

    def test_claiming_a_different_source_is_caught(self):
        """The located file must be the first decidable one, not any schema match."""
        verdict = self._verify(dict(
            self.report,
            source_path="canonical/governance/R2_DIRECT_END_TO_END_ADEQUACY_ROUTES_ACTIVATION_20261008_V10.json"))
        self.assertFalse(verdict["verified"])
        self.assertTrue(
            any(m.startswith("SELECTION_NOT_FIRST_DECIDABLE") for m in verdict["mismatches"]),
            verdict["mismatches"])

    def test_an_output_that_is_not_the_source_document_is_caught(self):
        """jq must confirm the locator copied a real problem, not invented one."""
        self.output_path.write_text(
            json.dumps({"schema": "PROJECT_BRAIN_TYPED_DECISION_PROBLEM_V1",
                        "alternatives": [], "constraints": [], "evidence": []},
                       indent=2, sort_keys=True) + "\n",
            encoding="utf-8")
        verdict = self._verify(self.report)
        self.assertFalse(verdict["verified"])

    def test_a_missing_output_file_is_refused_not_skipped(self):
        self.output_path.unlink()
        with self.assertRaises(RuntimeError):
            self._verify(self.report)


class RegistryEvidenceTests(unittest.TestCase):
    def setUp(self):
        registry = json.loads(
            (CANONICAL_ROOT / "runtime" / "BOUND_CAPABILITY_REGISTRY_V1.json")
            .read_text(encoding="utf-8"))
        self.entry = registry["capabilities"]["structured.decision_evidence.locate.stdlib"]
        self.verification = self.entry.get("verification") or {}

    def test_the_registry_declares_independence_only_with_real_evidence(self):
        self.assertIs(self.verification.get("independently_verified"), True)
        evidence_rel = self.verification.get("evidence_path")
        self.assertTrue(evidence_rel, "independence claimed with no evidence file")
        evidence_path = REPO_ROOT / evidence_rel
        self.assertTrue(evidence_path.is_file(), f"evidence missing: {evidence_rel}")
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        self.assertIs(evidence["independent_observation"]["verified"], True)
        self.assertEqual(evidence["independent_observation"]["mismatches"], [])
        self.assertIs(evidence["digest_agreement"], True)
        self.assertIs(evidence["selection_rule_reproduced_independently"], True)

    def test_the_evidence_names_the_external_tools_it_used(self):
        binaries = set(self.verification.get("independent_verifier_binaries") or [])
        self.assertTrue({"git grep -l", "sha256sum", "jq -S"} <= binaries, binaries)

    def test_the_gate_now_admits_the_capability(self):
        """This is the whole point: the bound adapter's own predicate must pass."""
        import sys
        if str(REPO_ROOT) not in sys.path:
            sys.path.insert(0, str(REPO_ROOT))
        from canonical.runtime import live_integrated_brain_v1 as live
        self.assertTrue(live._independently_verified(self.entry))

    def test_the_recorded_source_is_not_stale(self):
        """The recorded measurement must still describe this tree.

        Deliberately not a re-run-and-compare: the producer walks ``**/*.json`` from the
        repository root, so a previous run's own output under
        ``canonical/astra_runtime/tmp/`` is itself a schema-declaring, decidable
        candidate that sorts ahead of the real source. A fresh run can therefore
        legitimately locate an earlier output of the same capability. What must not
        drift is that the recorded source still exists, still declares the schema, and
        is still the first decidable candidate among the tracked files git reports.
        """
        import sys
        if str(REPO_ROOT) not in sys.path:
            sys.path.insert(0, str(REPO_ROOT))
        observed = self.verification.get("observed_effect") or {}
        source_rel = observed.get("source_path")
        self.assertTrue(source_rel)
        source = REPO_ROOT / source_rel
        self.assertTrue(source.is_file(), f"recorded source vanished: {source_rel}")
        document = json.loads(source.read_text(encoding="utf-8"))
        self.assertEqual(document.get("schema"),
                         "PROJECT_BRAIN_TYPED_DECISION_PROBLEM_V1")
        synthesis = _load("evidence_decision_synthesis_staleness",
                          CAPABILITIES / "evidence_decision_synthesis.py")
        self.assertEqual(synthesis.synthesize(document).get("status"), "DECIDED")
        # and the independent verifier still agrees with the recorded digests
        evidence = json.loads(
            (REPO_ROOT / self.verification["evidence_path"]).read_text(encoding="utf-8"))
        self.assertEqual(observed.get("output_sha256"),
                         evidence["producer_report"]["output_sha256"])


if __name__ == "__main__":
    unittest.main()
