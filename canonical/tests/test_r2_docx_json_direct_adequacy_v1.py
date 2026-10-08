from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from canonical.runtime import r2_docx_json_direct_adequacy_v1 as docx


def goal(source: str, output: str) -> str:
    return (
        f"Create {output} from the normalized JSON {source} with title "
        "Browser Submission Report, paragraph Verified browser submission, "
        "and a two-column table with headers Field and Value containing one row "
        "for each of customer_name, size, topping, and final_url using their "
        "values from the normalized JSON."
    )


def source_payload() -> dict:
    return {
        "submission": {
            "customer_name": "PROJECT BRAIN",
            "size": "Medium",
            "topping": "bacon",
            "final_url": "https://example.test",
        }
    }


class R2DocxJsonDirectAdequacyV1Tests(unittest.TestCase):
    def _root(self, td: str):
        root = Path(td)
        src_rel = "canonical/tmp/source.json"
        out_rel = "canonical/tmp/report.docx"
        src = root / src_rel
        src.parent.mkdir(parents=True, exist_ok=True)
        src.write_text(
            json.dumps(source_payload(), sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return root, src_rel, out_rel, src

    def _write_execution_artifacts(
        self,
        root: Path,
        *,
        source_rel: str,
        output_rel: str,
        goal_text: str,
        docx_bytes: bytes = b"PK\x03\x04DOCX",
        sidecar_override: dict | None = None,
    ):
        output = root / output_rel
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(docx_bytes)
        sidecar = Path(str(output) + ".intent.json")
        payload = {
            "schema": "PROJECT_BRAIN_DOCUMENT_JSON_INTENT_V1",
            "source_goal": goal_text,
            "source_json_path": source_rel,
            "output_path": output_rel,
        }
        if sidecar_override:
            payload.update(sidecar_override)
        sidecar.write_text(
            json.dumps(payload, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return output, sidecar

    def _raw_success(self, pf: dict) -> dict:
        return {
            "pass": True,
            "compiled_capability_id": docx.CAPABILITY_ID,
            "raw_goal_sha256": pf["goal_sha256"],
            "raw_source_coverage_complete": True,
        }

    def _verified_evidence(
        self,
        *,
        root: Path,
        source_rel: str,
        output_rel: str,
        goal_text: str,
    ) -> dict:
        data = json.loads((root / source_rel).read_text(encoding="utf-8"))
        expected = docx.independent_docx_verifier._expected_json(goal_text, data)
        return {
            "verified": True,
            "producer_independent_verifier": True,
            "source_record_verified": True,
            "path": output_rel,
            "source_json_path": source_rel,
            "intent_source_goal": goal_text,
            "intent_derived_expected": expected,
        }

    def test_exact_goal_preflight_binds_verified_docx_pair(self):
        with tempfile.TemporaryDirectory() as td:
            root, src_rel, out_rel, _ = self._root(td)
            g = goal(src_rel, out_rel)
            out = docx.preflight(
                {"task_id": "docx", "goal": g},
                repo_root=root,
            )
        self.assertTrue(out["matched"], out)
        self.assertEqual(out["capability_id"], docx.CAPABILITY_ID)
        self.assertEqual(
            out["verifier_capability_id"],
            docx.VERIFIER_CAPABILITY_ID,
        )
        self.assertEqual(out["json_path"], src_rel)
        self.assertEqual(out["output_path"], out_rel)
        self.assertFalse(out["preflight_execution_authority"])
        self.assertEqual(out["transaction_scope"], "DOCX_PLUS_INTENT_SIDECAR")

    def test_extra_unmodeled_instruction_does_not_match(self):
        with tempfile.TemporaryDirectory() as td:
            root, src_rel, out_rel, _ = self._root(td)
            g = goal(src_rel, out_rel) + " Then email it."
            out = docx.preflight(
                {"task_id": "docx", "goal": g},
                repo_root=root,
            )
        self.assertFalse(out["pass"])
        self.assertFalse(out["matched"])
        self.assertEqual(out["status"], "NOT_APPLICABLE")

    def test_success_requires_independent_semantic_reopen(self):
        with tempfile.TemporaryDirectory() as td:
            root, src_rel, out_rel, _ = self._root(td)
            g = goal(src_rel, out_rel)
            pf = docx.preflight(
                {"task_id": "docx", "goal": g},
                repo_root=root,
            )

            def execute(_request):
                self._write_execution_artifacts(
                    root,
                    source_rel=src_rel,
                    output_rel=out_rel,
                    goal_text=g,
                )
                return self._raw_success(pf)

            with patch.object(docx.live_bound, "run_raw_goal", side_effect=execute):
                out = docx.run(
                    {"task_id": "docx", "goal": g},
                    repo_root=root,
                    verifier_provider=lambda _pf: self._verified_evidence(
                        root=root,
                        source_rel=src_rel,
                        output_rel=out_rel,
                        goal_text=g,
                    ),
                )

            self.assertTrue(out["pass"], out)
            self.assertTrue(out["semantic_acceptance_complete"])
            self.assertTrue(out["actual_goal_satisfaction_verified"])
            self.assertTrue(out["policy_adequacy_authority"])
            self.assertTrue(out["transaction_committed"])
            self.assertFalse(out["terminal_authority"])
            self.assertTrue((root / out_rel).is_file())
            self.assertTrue(Path(str(root / out_rel) + ".intent.json").is_file())

    def test_new_artifacts_are_removed_when_execution_fails(self):
        with tempfile.TemporaryDirectory() as td:
            root, src_rel, out_rel, _ = self._root(td)
            g = goal(src_rel, out_rel)

            def execute(_request):
                self._write_execution_artifacts(
                    root,
                    source_rel=src_rel,
                    output_rel=out_rel,
                    goal_text=g,
                )
                return {"pass": False, "status": "EXECUTION_FAILED"}

            with patch.object(docx.live_bound, "run_raw_goal", side_effect=execute):
                out = docx.run(
                    {"task_id": "docx", "goal": g},
                    repo_root=root,
                )

            self.assertFalse(out["pass"])
            self.assertTrue(out["transaction_rolled_back"])
            self.assertFalse((root / out_rel).exists())
            self.assertFalse(Path(str(root / out_rel) + ".intent.json").exists())

    def test_preexisting_docx_and_sidecar_restore_byte_for_byte(self):
        with tempfile.TemporaryDirectory() as td:
            root, src_rel, out_rel, _ = self._root(td)
            g = goal(src_rel, out_rel)
            output = root / out_rel
            output.parent.mkdir(parents=True, exist_ok=True)
            old_docx = b"OLD_DOCX_BYTES"
            old_sidecar = b"OLD_INTENT_BYTES"
            output.write_bytes(old_docx)
            sidecar = Path(str(output) + ".intent.json")
            sidecar.write_bytes(old_sidecar)

            def execute(_request):
                self._write_execution_artifacts(
                    root,
                    source_rel=src_rel,
                    output_rel=out_rel,
                    goal_text=g,
                    docx_bytes=b"NEW_DOCX_BYTES",
                )
                return {"pass": False, "status": "EXECUTION_FAILED"}

            with patch.object(docx.live_bound, "run_raw_goal", side_effect=execute):
                out = docx.run(
                    {"task_id": "docx", "goal": g},
                    repo_root=root,
                )

            self.assertFalse(out["pass"])
            self.assertEqual(output.read_bytes(), old_docx)
            self.assertEqual(sidecar.read_bytes(), old_sidecar)

    def test_forged_intent_sidecar_is_rejected_before_verifier(self):
        with tempfile.TemporaryDirectory() as td:
            root, src_rel, out_rel, _ = self._root(td)
            g = goal(src_rel, out_rel)
            pf = docx.preflight(
                {"task_id": "docx", "goal": g},
                repo_root=root,
            )

            def execute(_request):
                self._write_execution_artifacts(
                    root,
                    source_rel=src_rel,
                    output_rel=out_rel,
                    goal_text=g,
                    sidecar_override={"source_goal": "EASIER FORGED GOAL"},
                )
                return self._raw_success(pf)

            verifier = unittest.mock.Mock()
            with patch.object(docx.live_bound, "run_raw_goal", side_effect=execute):
                out = docx.run(
                    {"task_id": "docx", "goal": g},
                    repo_root=root,
                    verifier_provider=verifier,
                )

            self.assertFalse(out["pass"])
            self.assertEqual(out["reason"], "DOCX_INTENT_SIDECAR_BINDING_MISMATCH")
            self.assertTrue(out["transaction_rolled_back"])
            verifier.assert_not_called()
            self.assertFalse((root / out_rel).exists())

    def test_independent_verifier_failure_rolls_back_both_artifacts(self):
        with tempfile.TemporaryDirectory() as td:
            root, src_rel, out_rel, _ = self._root(td)
            g = goal(src_rel, out_rel)
            pf = docx.preflight(
                {"task_id": "docx", "goal": g},
                repo_root=root,
            )

            def execute(_request):
                self._write_execution_artifacts(
                    root,
                    source_rel=src_rel,
                    output_rel=out_rel,
                    goal_text=g,
                )
                return self._raw_success(pf)

            evidence = self._verified_evidence(
                root=root,
                source_rel=src_rel,
                output_rel=out_rel,
                goal_text=g,
            )
            evidence["verified"] = False
            with patch.object(docx.live_bound, "run_raw_goal", side_effect=execute):
                out = docx.run(
                    {"task_id": "docx", "goal": g},
                    repo_root=root,
                    verifier_provider=lambda _pf: evidence,
                )

            self.assertFalse(out["pass"])
            self.assertEqual(
                out["status"],
                "OPEN__INDEPENDENT_DOCX_ACCEPTANCE_DID_NOT_VERIFY",
            )
            self.assertTrue(out["transaction_rolled_back"])
            self.assertFalse((root / out_rel).exists())
            self.assertFalse(Path(str(root / out_rel) + ".intent.json").exists())

    def test_source_mutation_during_execution_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root, src_rel, out_rel, source = self._root(td)
            g = goal(src_rel, out_rel)
            pf = docx.preflight(
                {"task_id": "docx", "goal": g},
                repo_root=root,
            )

            def execute(_request):
                self._write_execution_artifacts(
                    root,
                    source_rel=src_rel,
                    output_rel=out_rel,
                    goal_text=g,
                )
                source.write_text(
                    json.dumps({"customer_name": "MUTATED"}) + "\n",
                    encoding="utf-8",
                )
                return self._raw_success(pf)

            with patch.object(docx.live_bound, "run_raw_goal", side_effect=execute):
                out = docx.run(
                    {"task_id": "docx", "goal": g},
                    repo_root=root,
                )

            self.assertFalse(out["pass"])
            self.assertEqual(
                out["reason"],
                "DOCX_SOURCE_JSON_CHANGED_DURING_EXECUTION",
            )
            self.assertTrue(out["transaction_rolled_back"])

    def test_verifier_semantics_digest_must_match_preflight(self):
        with tempfile.TemporaryDirectory() as td:
            root, src_rel, out_rel, _ = self._root(td)
            g = goal(src_rel, out_rel)
            pf = docx.preflight(
                {"task_id": "docx", "goal": g},
                repo_root=root,
            )

            def execute(_request):
                self._write_execution_artifacts(
                    root,
                    source_rel=src_rel,
                    output_rel=out_rel,
                    goal_text=g,
                )
                return self._raw_success(pf)

            evidence = self._verified_evidence(
                root=root,
                source_rel=src_rel,
                output_rel=out_rel,
                goal_text=g,
            )
            evidence["intent_derived_expected"] = {
                "title": "FORGED",
                "paragraphs": ["Verified browser submission"],
                "headers": ["Field", "Value"],
                "rows": [["customer_name", "PROJECT BRAIN"]],
            }
            with patch.object(docx.live_bound, "run_raw_goal", side_effect=execute):
                out = docx.run(
                    {"task_id": "docx", "goal": g},
                    repo_root=root,
                    verifier_provider=lambda _pf: evidence,
                )

            self.assertFalse(out["pass"])
            self.assertTrue(out["transaction_rolled_back"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
