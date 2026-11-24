#!/usr/bin/env python3
"""Contract: raw prose becomes a typed action quotient only through explicit slots.

Tests cover fail-closed prose, external-store editability, exact packet shape,
GDSK composition, distinct-verifier/source closure, and no-model/no-network/
no-parameter static boundaries. No benchmark task or hidden answer is used.
"""
from __future__ import annotations

import ast
import copy
import hashlib
import json
import pathlib
import unittest

from canonical.runtime import goal_directed_sufficient_knowing_v1 as gdsk
from canonical.runtime import raw_instruction_purpose_binder_v1 as binder

ROOT = pathlib.Path(__file__).resolve().parents[2]
STORE_PATH = ROOT / "canonical/astra_runtime/state/RAW_INSTRUCTION_PURPOSE_TEMPLATE_STORE_V1.json"
BINDER_PATH = ROOT / "canonical/runtime/raw_instruction_purpose_binder_v1.py"


def request() -> dict:
    return {
        "schema": "BRAIN_TYPED_PURPOSE_BINDING_REQUEST_V1",
        "raw_instruction": "Create `result.txt` with the exact literal `hello` in a bounded file workspace.",
        "template_id": "create_literal_file",
        "quoted_slots": {"path": "result.txt", "literal": "hello"},
        "environment_evidence": {
            "source": "BOUNDED_ENVIRONMENT_SCAN",
            "scope": {"closed_world": True, "bounded_enumerated": True},
            "evidence_ref": "file-name-scan-sha256:test",
            "falsifier": "path absent from bounded scan or scan not exhaustive",
        },
        "distinct_verifier": {
            "source": "DISTINCT_VERIFIER",
            "scope": {"closed_world": True, "bounded_enumerated": True},
            "evidence_ref": "runner-owned-exact-state-check",
            "falsifier": "exact byte state differs from quoted literal",
        },
        "distinct_from_producer": True,
        "visible_scan_atoms": ["result.txt"],
        "domain": "software_repository",
        "action_universe_complete": True,
        "hypothesis_model": [
            {"id": "v_safe", "probability": 0.5, "utilities": {"A1": 1.0, "A2": 0.0}},
            {"id": "v_unsafe", "probability": 0.5, "utilities": {"A1": 0.0, "A2": 1.0}},
        ],
        "unknown_evidence": {
            "label": "K1_SCOPED_FACT",
            "decision_relevant": True,
            "source": {
                "source": "DISTINCT_VERIFIER",
                "scope": {"closed_world": True, "bounded_enumerated": True},
                "evidence_ref": "runner-owned-exact-state-check",
                "falsifier": "typed test command class changes action ordering",
            },
            "distinct_from_producer": True,
            "evidence_ref": "runner-owned-exact-state-check",
            "falsifier": "typed test command class changes action ordering",
        },
        "query_cost": 0.0,
    }


def store() -> dict:
    return json.loads(STORE_PATH.read_text(encoding="utf-8"))


class RawInstructionPurposeBinderContract(unittest.TestCase):
    def setUp(self) -> None:
        self.request = request()
        self.store = store()

    def test_external_store_is_file_backed_editable_and_empty_of_fact_claims(self) -> None:
        self.assertTrue(STORE_PATH.is_file())
        self.assertTrue(self.store["external_editable"])
        self.assertFalse(self.store["facts_or_skills_in_parameters"])
        self.assertGreaterEqual(len(self.store["templates"]), 2)
        self.assertNotIn("hello", json.dumps(self.store))

    def test_binder_module_is_stdlib_only_and_has_no_model_or_network_roots(self) -> None:
        tree = ast.parse(BINDER_PATH.read_text(encoding="utf-8"))
        roots = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                roots.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                roots.add(node.module.split(".")[0])
        allowed = {"__future__", "argparse", "copy", "hashlib", "json", "math", "pathlib", "re", "typing"}
        self.assertEqual(roots - allowed, set())
        source = BINDER_PATH.read_text(encoding="utf-8").casefold()
        for marker in ("urllib", "requests", "socket", "openai", "torch", "transformers", "subprocess"):
            self.assertNotIn(marker, source)

    def test_explicit_typed_request_binds_to_a_goal_directed_packet(self) -> None:
        result = binder.compile_request(self.request, self.store)
        self.assertEqual(result["status"], "BOUND__TYPED_ACTION_QUOTIENT")
        self.assertIsNone(result.get("reason"))
        packet = result["packet"]
        self.assertEqual(packet["schema"], binder.GDSK_PACKET_SCHEMA)
        self.assertEqual(packet["goal"]["id"], "BOUNDED_CREATE_FILE")
        self.assertEqual([a["id"] for a in packet["actions"]], ["A1", "A2"])
        self.assertTrue(all("{{" not in a["command"] for a in packet["actions"]))
        self.assertTrue(packet["binding_provenance"]["typed_action_quotient"]["complete"])
        self.assertEqual(result["model_calls"], 0)
        self.assertEqual(result["runtime_network_calls"], 0)
        self.assertEqual(result["parameters_written"], 0)
        self.assertFalse(result["trajectory_saved"])

    def test_bound_packet_composes_with_existing_exact_evpi_evaluator(self) -> None:
        result = binder.compile_request(self.request, self.store)
        decision = gdsk.evaluate(result["packet"])
        self.assertEqual(decision["decision"], "K1_QUERY_REQUIRED__ASK_ONLY_THE_DECIDING_QUESTION")
        self.assertEqual(decision["selected_query_count"], 1)
        query = decision["selected_queries"][0]
        self.assertEqual(query["value_of_information_basis"], "EXACT_EVPI")
        self.assertEqual(query["question_source"], "DERIVED_FROM_ACTION_PARTITION")
        self.assertIn("u_test_command", query["question"])

    def test_external_store_can_add_or_remove_templates_without_parameters_or_retraining(self) -> None:
        edited = copy.deepcopy(self.store)
        edited["templates"].append({
            "template_id": "move_visible_file",
            "goal_family": "MOVE_OR_RENAME_FILE",
            "required_slots": ["path", "literal"],
            "output_actions": [
                {"id": "M1", "command_template": "mv -f {{literal}} {{path}}", "requires_unknown": "u_test_command", "requires_value": "v_safe"},
                {"id": "M2", "command_template": "mv -f {{literal}} {{path}}.candidate", "requires_unknown": "u_test_command", "requires_value": "v_unsafe"},
            ],
            "success_predicate": {"kind": "BOUNDED_EXACT_STATE", "checks": ["moved bytes match"]},
            "uncertainty": {"unknown": "u_test_command", "values": ["v_safe", "v_unsafe"]},
        })
        r = copy.deepcopy(self.request)
        r["template_id"] = "move_visible_file"
        r["raw_instruction"] = "Move `source.txt` to `result.txt` in a bounded file workspace."
        r["quoted_slots"] = {"path": "result.txt", "literal": "source.txt"}
        r["visible_scan_atoms"] = ["source.txt", "result.txt"]
        r["hypothesis_model"] = [
            {"id": "v_safe", "probability": 0.5, "utilities": {"M1": 1.0, "M2": 0.0}},
            {"id": "v_unsafe", "probability": 0.5, "utilities": {"M1": 0.0, "M2": 1.0}},
        ]
        self.assertEqual(binder.compile_request(r, edited)["status"], "BOUND__TYPED_ACTION_QUOTIENT")
        r["template_id"] = "create_literal_file"
        self.assertTrue(binder.compile_request(r, {"schema": "BRAIN_EXTERNAL_PURPOSE_TEMPLATE_STORE_V1", "external_editable": True, "facts_or_skills_in_parameters": False, "templates": []})["status"].startswith("REFUSED__"))
        removed = copy.deepcopy(self.store)
        removed["templates"] = [x for x in removed["templates"] if x["template_id"] != "copy_visible_file"]
        self.assertNotIn("copy_visible_file", json.dumps(removed))
        self.assertEqual(binder.compile_request(self.request, removed)["status"], "BOUND__TYPED_ACTION_QUOTIENT")

    def test_arbitrary_prose_is_not_interpreted(self) -> None:
        r = copy.deepcopy(self.request)
        r["raw_instruction"] = "Understand anything in the repository and do the best general repair."
        r["quoted_slots"] = {}
        result = binder.compile_request(r, self.store)
        self.assertEqual(result["status"], "REFUSED__NO_ACTION_QUOTIENT")
        self.assertIn("UNBOUNDED_PURPOSE_WORD", result["reason"])
        self.assertIsNone(result["packet"])

    def test_unquoted_or_extra_slots_fail_closed(self) -> None:
        r = copy.deepcopy(self.request)
        r["quoted_slots"] = {"path": "result.txt", "literal": "not in instruction"}
        refusal = binder.compile_request(r, self.store)
        self.assertIn("SLOT_NOT_QUOTED_IN_RAW_INSTRUCTION", refusal["reason"])
        r = copy.deepcopy(self.request)
        r["quoted_slots"]["invented"] = "x"
        self.assertIn("SLOT_CLOSURE_MISMATCH", binder.compile_request(r, self.store)["reason"])

    def test_unbounded_or_model_dependent_source_fails_closed(self) -> None:
        r = copy.deepcopy(self.request)
        r["environment_evidence"]["scope"]["closed_world"] = False
        self.assertIn("OPEN_WORLD_SCOPE", binder.compile_request(r, self.store)["reason"])
        r = copy.deepcopy(self.request)
        r["unknown_evidence"]["label"] = "K3_MODEL_DEPENDENT"
        self.assertIn("NON_K1_UNCERTAINTY", binder.compile_request(r, self.store)["reason"])

    def test_missing_distinct_verifier_fails_closed(self) -> None:
        r = copy.deepcopy(self.request)
        r["distinct_from_producer"] = False
        self.assertIn("DISTINCT_VERIFIER_NOT_ASSERTED", binder.compile_request(r, self.store)["reason"])

    def test_open_world_completeness_and_invalid_probability_fail_closed(self) -> None:
        r = copy.deepcopy(self.request)
        r["action_universe_complete"] = False
        self.assertIn("ACTION_UNIVERSE_INCOMPLETE", binder.compile_request(r, self.store)["reason"])
        r = copy.deepcopy(self.request)
        r["hypothesis_model"][0]["probability"] = 0.4
        self.assertIn("HYPOTHESIS_PROBABILITIES_NOT_NORMALIZED", binder.compile_request(r, self.store)["reason"])

    def test_no_universal_parser_or_world_fact_warehouse_claims(self) -> None:
        source = BINDER_PATH.read_text(encoding="utf-8")
        self.assertIn("deliberately not a natural-language interpreter", source)
        self.assertIn("fail closed", source.lower())
        self.assertIn("world_fact_warehouse", source)
        self.assertIn("trajectory_saved", source)

    def test_refusal_is_provenance_only_and_never_an_executable_packet(self) -> None:
        refusal = binder.compile_request({"raw_instruction": "unbounded"}, self.store)
        self.assertEqual(refusal["schema"], "BRAIN_TYPED_PURPOSE_BINDING_REFUSAL_V1")
        self.assertIsNone(refusal["packet"])
        self.assertEqual(refusal["model_calls"], 0)
        self.assertEqual(refusal["raw_instruction_sha256"], hashlib.sha256(b"unbounded").hexdigest())

    def test_canonical_hashes_are_stable_and_content_addressed(self) -> None:
        self.assertEqual(binder.canonical_sha256({"b": 1, "a": 2}), binder.canonical_sha256({"a": 2, "b": 1}))
        self.assertNotEqual(binder.canonical_sha256({"a": 2}), binder.canonical_sha256({"a": 3}))


if __name__ == "__main__":
    unittest.main(verbosity=2)
