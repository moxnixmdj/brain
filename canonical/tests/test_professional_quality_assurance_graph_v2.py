from __future__ import annotations
import copy
import json
import unittest
from pathlib import Path

from canonical.runtime import assurance_closure_compiler_v1 as kernel

ROOT = Path(__file__).resolve().parents[2]
GRAPH = ROOT / "canonical/governance/PROFESSIONAL_QUALITY_ASSURANCE_GRAPH_20261009_V2.json"
CATALOG = ROOT / "canonical/governance/PROFESSIONAL_QUALITY_DOMAIN_DEFEATER_CATALOG_20261009_V2.json"
REUSE = ROOT / "canonical/governance/PROFESSIONAL_QUALITY_EXISTING_EVIDENCE_REUSE_MATRIX_20261009_V1.json"

EXPECTED_ROOTS = {
    "R1_TARGET_SPECIFICATION",
    "R2_CANDIDATE_SEARCH",
    "R3_REALIZATION_OBSERVATION",
    "R4_MEASUREMENT_CONSTRUCT",
    "R5_EVALUATOR_REFERENCE",
    "R6_EVIDENCE_GROUNDING_DEPENDENCE",
    "R7_CAUSAL_PRESCRIPTIVE",
    "R8_POPULATION_CONTEXT_OPERATOR",
    "R9_TEMPORAL_DEPLOYMENT",
    "R10_ANALYSIS_DECISION",
    "R11_ADAPTIVE_INTEGRITY_SECURITY",
    "R12_META_COMPOSITION_CLOSURE",
}

def load():
    return json.loads(GRAPH.read_text()), json.loads(CATALOG.read_text())

def catalog_errors(graph, catalog):
    errors = []
    roots = set(graph.get("root_ids") or [])
    if roots != EXPECTED_ROOTS:
        errors.append("ROOT_SET_MISMATCH")
    nodes = {n.get("id"): n for n in graph.get("nodes", []) if isinstance(n, dict)}
    challenges = catalog.get("challenges") or []
    if catalog.get("root_count") != 12:
        errors.append("ROOT_COUNT_INVALID")
    if catalog.get("challenge_count") != len(challenges):
        errors.append("CHALLENGE_COUNT_MISMATCH")
    seen = set()
    covered = set()
    for row in challenges:
        cid = row.get("id")
        if not cid or cid in seen:
            errors.append("CHALLENGE_ID_INVALID_OR_DUPLICATE")
            continue
        seen.add(cid)
        refs = set(row.get("root_ids") or [])
        if not refs or not refs.issubset(EXPECTED_ROOTS):
            errors.append("CHALLENGE_ROOT_MAPPING_INVALID:" + cid)
        covered |= refs
        node = nodes.get(cid)
        if not node or node.get("type") != "DEFEATER" or node.get("status") != "OPEN":
            errors.append("CHALLENGE_DEFEATER_NODE_MISSING:" + cid)
        for rid in refs:
            rnode = nodes.get(rid) or {}
            if cid not in (rnode.get("defeated_by") or []):
                errors.append("ROOT_DEFEATER_BINDING_MISSING:" + rid + ":" + cid)
        if row.get("terminal_pass_forbidden") is not True:
            errors.append("CHALLENGE_PASS_NOT_FORBIDDEN:" + cid)
    if covered != EXPECTED_ROOTS:
        errors.append("ROOT_WITHOUT_CHALLENGE")
    for rid in EXPECTED_ROOTS:
        rnode = nodes.get(rid) or {}
        deps = rnode.get("depends_on") or []
        if len(deps) != 1:
            errors.append("ROOT_CLOSURE_OBLIGATION_INVALID:" + rid)
            continue
        onode = nodes.get(deps[0]) or {}
        if onode.get("type") != "OBLIGATION" or onode.get("status") != "OPEN":
            errors.append("ROOT_CLOSURE_OBLIGATION_NOT_OPEN:" + rid)
    return sorted(set(errors))

class TestProfessionalQualityAssuranceGraphV2(unittest.TestCase):
    def test_domain_graph_is_representable_but_open(self):
        graph, catalog = load()
        self.assertEqual(catalog_errors(graph, catalog), [])
        out = kernel.evaluate(graph)
        self.assertTrue(out["closure_gates"]["representation_closure"], out)
        self.assertFalse(out["closure_gates"]["proof_closure"], out)
        self.assertFalse(out["closure_gates"]["execution_closure"], out)
        self.assertFalse(out["closure_gates"]["adversarial_closure"], out)
        self.assertTrue(out["existing_kernel_expressive"], out)
        self.assertFalse(out["new_primitive_required"], out)
        self.assertFalse(out["pass"], out)
        self.assertFalse(out["terminal_authority"], out)
        self.assertEqual(out["terminal_credit_delta"], 0)

    def test_all_80_known_attack_classes_bind_to_existing_roots(self):
        graph, catalog = load()
        self.assertEqual(catalog["challenge_count"], 80)
        self.assertEqual(len(catalog["challenges"]), 80)
        self.assertEqual(catalog_errors(graph, catalog), [])

    def test_cross_layer_assurance_failures_are_explicit(self):
        _, catalog = load()
        ids = {row["id"] for row in catalog["challenges"]}
        required = {
            "C71_JOINT_ASSURANCE_MULTIPLICITY",
            "C72_UNGROUNDED_RISK_TOLERANCE",
            "C73_BASE_RATE_PRECISION_LAUNDERING",
            "C74_EXECUTION_FAILURE_FAIL_OPEN",
            "C75_STALE_CERT_AFTER_DEPENDENCY_CHANGE",
            "C76_SELECTIVE_EVIDENCE_PACKET",
            "C77_PROVENANCE_OR_RECEIPT_FORGERY",
            "C78_CONTEXT_TRUNCATION_OBLIGATION_DROP",
            "C79_FALLBACK_EVALUATOR_SCOPE_WEAKENING",
            "C80_OPTIONAL_STOPPING_OR_REPEATED_TESTING",
        }
        self.assertTrue(required.issubset(ids))

    def test_every_known_defeater_counterproves_when_activated(self):
        graph, catalog = load()
        for row in catalog["challenges"]:
            g = copy.deepcopy(graph)
            nodes = {n["id"]: n for n in g["nodes"]}
            nodes[row["id"]]["status"] = "SUPPORTED"
            out = kernel.evaluate(g)
            self.assertEqual(out["status"], "COUNTERPROVED", row["id"])
            self.assertIn(row["id"], out["active_defeater_ids"], row["id"])
            self.assertFalse(out["pass"], row["id"])
            self.assertFalse(out["terminal_authority"], row["id"])
            self.assertEqual(out["terminal_credit_delta"], 0, row["id"])

    def test_existing_evidence_reuse_map_is_scoped_and_nonpromotional(self):
        _, catalog = load()
        reuse = json.loads(REUSE.read_text())
        rows = reuse["roots"]
        self.assertEqual(reuse["root_count"], 12)
        self.assertEqual({row["id"] for row in rows}, EXPECTED_ROOTS)
        self.assertEqual(reuse["conclusions"]["closed_root_count"], 0)
        self.assertEqual(reuse["conclusions"]["reusable_partial_evidence_root_count"], 12)
        self.assertFalse(reuse["conclusions"]["terminal_authority"])
        self.assertEqual(reuse["accounting"]["terminal_credit_delta"], 0)
        for row in rows:
            self.assertNotIn("CLOSED", row["state"])
            self.assertTrue(row["evidence"])
            self.assertTrue(row["residual"])
            for ev in row["evidence"]:
                self.assertTrue(ev["path"].startswith("canonical/"))
                self.assertRegex(ev["git_blob_sha"], r"^[0-9a-f]{40}$")
                self.assertTrue(ev["status"])
                self.assertTrue(ev["supports"])

    def test_unknown_primitive_is_the_new_architecture_trigger(self):
        graph, _ = load()
        g = copy.deepcopy(graph)
        g["nodes"].append({"id":"alien","type":"UNMODELED_QUALITY_MAGIC","status":"OPEN"})
        g["nodes"][0]["depends_on"] = ["alien"]
        out = kernel.evaluate(g)
        self.assertTrue(out["new_primitive_required"], out)
        self.assertIn("UNMODELED_QUALITY_MAGIC", out["unsupported_primitive_types"])

    def test_unmapped_challenge_is_rejected_by_domain_binding(self):
        graph, catalog = load()
        c = copy.deepcopy(catalog)
        c["challenges"].append({
            "id":"C999_UNMAPPED",
            "root_ids":["R999_NOT_REAL"],
            "attack":"synthetic canary",
            "status":"OPEN",
            "terminal_pass_forbidden":True,
        })
        c["challenge_count"] += 1
        self.assertIn("CHALLENGE_ROOT_MAPPING_INVALID:C999_UNMAPPED", catalog_errors(graph, c))

if __name__ == "__main__":
    unittest.main()
