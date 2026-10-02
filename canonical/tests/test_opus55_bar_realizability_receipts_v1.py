"""Machine checks for the 2026-10-02 realizability decision receipts.

The three receipts are point-in-time records:

* canonical/reasoning/2026-10-02_GITHUB_ACTIONS_BILLING_ROOT_CAUSE_RECONCILIATION_V1.json
* canonical/reasoning/2026-10-02_TB4_ATTAINABILITY_RAISE_ANALYSIS_V1.json
* canonical/reasoning/2026-10-02_PUBLIC_BAR_MEASURABILITY_AND_SUBSTRATE_FEASIBILITY_V1.json
* canonical/reasoning/2026-10-02_ZERO_COST_SUBSTRATE_ROUTE_CENSUS_V1.json

Structural and zero-credit invariants are always checked. Numeric claims are
re-derived with the repository's own code, but only against the exact source
bytes (git blob SHAs) the receipt pinned. If a pinned source later changes, the
numeric checks skip instead of failing: the receipt is then superseded by a
newer source, not wrong. This test never writes into the repository tree.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
import unittest
from math import comb
from pathlib import Path

from canonical.runtime.attainability_cut_compiler_v1 import evaluate

ROOT = Path(__file__).resolve().parents[2]
REASONING = ROOT / "canonical" / "reasoning"
BILLING = "2026-10-02_GITHUB_ACTIONS_BILLING_ROOT_CAUSE_RECONCILIATION_V1"
TB4 = "2026-10-02_TB4_ATTAINABILITY_RAISE_ANALYSIS_V1"
BARS = "2026-10-02_PUBLIC_BAR_MEASURABILITY_AND_SUBSTRATE_FEASIBILITY_V1"
CENSUS = "2026-10-02_ZERO_COST_SUBSTRATE_ROUTE_CENSUS_V1"
RECEIPT_IDS = (BILLING, TB4, BARS, CENSUS)

REQUIRED_RECEIPT_KEYS = (
    "schema", "date", "decision_id", "status", "canonical_base_commit",
    "real_objective", "governing_invariants", "material_premises",
    "evidence_refs", "conclusion", "selected_route",
    "rejected_material_alternatives", "uncertainties", "assumptions",
    "non_goals", "next_action", "supersession_conditions",
)
ZERO_FIELDS = (
    "capability_credit_delta", "family_credit_delta",
    "new_reality_units_consumed", "incremental_spend_usd",
)
BILLING_TEXT = (
    "The job was not started because recent account payments have failed or "
    "your spending limit needs to be increased."
)


def _load(receipt_id: str) -> dict:
    return json.loads((REASONING / f"{receipt_id}.json").read_text(encoding="utf-8"))


def _git_blob_sha(rel: str) -> str:
    data = (ROOT / rel).read_bytes()
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def _pins(receipt: dict) -> list[tuple[str, str]]:
    """Every (path, git_blob_sha) pair pinned inside the receipt's premises."""
    out: list[tuple[str, str]] = []

    def walk(node):
        if isinstance(node, dict):
            if "path" in node and "git_blob_sha" in node:
                out.append((node["path"], node["git_blob_sha"]))
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(receipt["material_premises"])
    return out


def _stale_pins(receipt: dict) -> list[str]:
    stale = []
    for rel, sha in _pins(receipt):
        if not (ROOT / rel).is_file() or _git_blob_sha(rel) != sha:
            stale.append(rel)
    return stale


class ReceiptStructureTests(unittest.TestCase):
    def test_receipts_are_well_formed_and_zero_credit(self):
        for rid in RECEIPT_IDS:
            with self.subTest(receipt=rid):
                r = _load(rid)
                for key in REQUIRED_RECEIPT_KEYS:
                    self.assertIn(key, r, key)
                self.assertEqual(r["schema"], "PROJECT_BRAIN_REASONING_DECISION_RECEIPT_V1")
                self.assertEqual(r["decision_id"], rid)
                self.assertRegex(r["canonical_base_commit"], r"^[0-9a-f]{40}$")
                for key in ZERO_FIELDS:
                    self.assertEqual(r[key], 0, key)
                self.assertIs(r["execution_authority"], False)
                self.assertIs(r["promotion_authority"], False)
                for key in ("material_premises", "rejected_material_alternatives",
                            "uncertainties", "non_goals", "supersession_conditions"):
                    self.assertTrue(r[key], key)

    def test_repo_evidence_paths_exist(self):
        for rid in RECEIPT_IDS:
            r = _load(rid)
            for ref in r["evidence_refs"]:
                if ref.startswith("canonical/"):
                    with self.subTest(receipt=rid, ref=ref):
                        self.assertTrue((ROOT / ref).is_file(), ref)
            for rel, _sha in _pins(r):
                with self.subTest(receipt=rid, pinned=rel):
                    self.assertTrue((ROOT / rel).is_file(), rel)


class BillingReceiptTests(unittest.TestCase):
    def test_annotation_text_and_onset_are_consistent(self):
        r = _load(BILLING)
        premises = {p["id"]: p for p in r["material_premises"]}
        self.assertIn(BILLING_TEXT, premises["P1_ANNOTATION_TEXT"]["fact"])
        p2 = premises["P2_CONSISTENCY"]["evidence"]["structured"]
        self.assertEqual(p2["zero_step_failed_jobs"], p2["jobs_with_identical_billing_annotation"])
        p3 = premises["P3_ONSET"]["evidence"]["structured"]
        self.assertLess(p3["last_success_utc"], p3["first_failure_after_success_utc"])
        self.assertEqual(p3["runs_in_window_01_53_45_to_03_20_00"]["success"], 0)
        self.assertNotIn("EXACT_CAUSE_IS_BILLING_OR_QUOTA", json.dumps(r["rejected_material_alternatives"]))


class Tb4ReceiptTests(unittest.TestCase):
    def setUp(self):
        self.receipt = _load(TB4)
        stale = _stale_pins(self.receipt)
        if stale:
            self.skipTest(f"receipt is a point-in-time record; pinned sources changed: {stale}")
        manifest_rel = "canonical/governance/TB4_ATTAINABILITY_EVIDENCE_MANIFEST_V1.json"
        manifest = json.loads((ROOT / manifest_rel).read_text(encoding="utf-8"))
        self.base = {
            k: manifest[k]
            for k in (
                "total_task_count", "trials_per_task", "required_successes",
                "hardware_incompatible_task_identities",
                "irreversibly_zero_hardware_compatible_tasks",
                "completed_creditable_tasks",
            )
        }
        self.premises = {p["id"]: p for p in self.receipt["material_premises"]}

    def test_baseline_is_impossible_at_180(self):
        out = evaluate(self.base)
        self.assertEqual(out["upper_bound_successes"], 180)
        self.assertEqual(out["remaining_creditable_task_count"], 36)
        self.assertEqual(out["attainability_state"], "IMPOSSIBLE")

    def test_carrier_only_scenarios_reproduce(self):
        table = self.premises["P3_SCENARIOS_CARRIER_ONLY"]["evidence"]["table"]
        self.assertEqual(len(table), 13)
        for row in table:
            k = row["hardware_incompatible_tasks_made_compatible_and_creditable"]
            spec = copy.deepcopy(self.base)
            spec["hardware_incompatible_task_identities"] = spec["hardware_incompatible_task_identities"][k:]
            out = evaluate(spec)
            with self.subTest(k=k):
                self.assertEqual(out["upper_bound_successes"], row["upper_bound_successes"])
                self.assertEqual(out["attainability_state"], row["attainability_state"])
                self.assertEqual(round(220 / out["upper_bound_successes"] * 100, 1), row["required_trial_pass_rate_percent"])
        reachable = [r for r in table if r["attainability_state"] != "IMPOSSIBLE"]
        first = min(reachable, key=lambda r: r["hardware_incompatible_tasks_made_compatible_and_creditable"])
        self.assertEqual(first["hardware_incompatible_tasks_made_compatible_and_creditable"], 8)
        self.assertEqual(first["required_trial_pass_rate_percent"], 100.0)

    def test_revival_scenarios_reproduce(self):
        table = self.premises["P4_SCENARIOS_REVIVAL"]["evidence"]["table"]
        for row in table:
            j = row["all_12_incompatible_added_and_irreversibly_zero_tasks_revived"]
            spec = copy.deepcopy(self.base)
            spec["hardware_incompatible_task_identities"] = []
            spec["irreversibly_zero_hardware_compatible_tasks"] = spec["irreversibly_zero_hardware_compatible_tasks"][j:]
            out = evaluate(spec)
            with self.subTest(j=j):
                self.assertEqual(out["upper_bound_successes"], row["upper_bound_successes"])
                self.assertEqual(round(220 / out["upper_bound_successes"] * 100, 1), row["required_trial_pass_rate_percent"])

    def test_reference_system_cannot_meet_its_own_bar(self):
        expected = round(0.664 * 180, 1)
        self.assertLess(expected, 220)
        self.assertIn(f"{expected}", self.premises["P5_REFERENCE_SYSTEM_CONSISTENCY"]["fact"])
        p = sum(comb(330, i) * 0.664 ** i * 0.336 ** (330 - i) for i in range(220, 331))
        self.assertIn(f"{p:.3f}", self.premises["P6_POINT_ESTIMATE_COIN_FLIP"]["fact"])
        self.assertTrue(0.40 < p < 0.55)


class PublicBarReceiptTests(unittest.TestCase):
    def setUp(self):
        self.receipt = _load(BARS)

    def test_row_classification_counts_and_evidence_strength(self):
        rows = self.receipt["public_bar_rows"]
        self.assertEqual(len(rows), 15)
        counts: dict[str, int] = {}
        for row in rows:
            key = row["third_party_reproducibility"].split("__")[0]
            counts[key] = counts.get(key, 0) + 1
            classes = {e["class"] for e in row["evidence"]}
            has_primary = "OFFICIAL_PRIMARY" in classes
            self.assertEqual(
                row["classification_evidence_strength"],
                "HAS_OFFICIAL_PRIMARY_SOURCE" if has_primary else "SECONDARY_SOURCES_ONLY",
                row["predicate_id"],
            )
            for e in row["evidence"]:
                self.assertTrue(e["url"].startswith("https://"), row["predicate_id"])
                self.assertTrue(e["excerpt"].strip(), row["predicate_id"])
        self.assertEqual(
            counts,
            {"OWNER_COMPUTED_OR_PRIVATE": 8, "THIRD_PARTY_RUNNABLE_IN_PRINCIPLE": 4, "UNRESOLVED": 3},
        )
        for row in rows:
            if row["third_party_reproducibility"].startswith(("OWNER", "THIRD_PARTY")):
                self.assertEqual(row["classification_evidence_strength"], "HAS_OFFICIAL_PRIMARY_SOURCE", row["predicate_id"])

    def test_rows_cover_exactly_the_registry_public_bars(self):
        stale = _stale_pins(self.receipt)
        if stale:
            self.skipTest(f"receipt is a point-in-time record; pinned sources changed: {stale}")
        registry = json.loads(
            (ROOT / "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json").read_text(encoding="utf-8")
        )
        expected = {p["id"]: p for p in registry["predicates"] if p["kind"] == "PUBLIC_FIXED_BAR"}
        rows = {r["predicate_id"]: r for r in self.receipt["public_bar_rows"]}
        self.assertEqual(set(rows), set(expected))
        for pid, row in rows.items():
            self.assertEqual(row["registry_acceptance"], expected[pid]["acceptance"], pid)
            self.assertEqual(row["family"], expected[pid]["family"], pid)
            self.assertFalse(row["repo_readiness"]["score_producing_route_ready"], pid)

    def test_repo_route_audit_premise_matches_the_audit_file(self):
        premises = {p["id"]: p for p in self.receipt["material_premises"]}
        pin = premises["P9_REPO_ROUTE_AUDIT_CORROBORATION"]["evidence"]
        rel = pin["path"]
        if not (ROOT / rel).is_file() or _git_blob_sha(rel) != pin["git_blob_sha"]:
            self.skipTest("route audit changed since this receipt; receipt is a point-in-time record")
        audit = json.loads((ROOT / rel).read_text(encoding="utf-8"))
        summary = audit["summary"]
        self.assertEqual(summary["zero_cost_executable_surface_count"], 0)
        self.assertEqual(summary["portfolio_prequalification_pass_count"], 0)
        self.assertEqual(summary["surface_count"], 14)
        self.assertEqual(summary["private_surface_routes_deleted_by_dominance"], 5)

    def test_prior_work_references_exist_and_relations_are_declared(self):
        relations = self.receipt["relation_to_prior_work"]
        self.assertTrue(relations)
        allowed = {"AGREES", "EXTENDS", "AGREES_AND_QUESTIONS_DISCHARGEABILITY"}
        for item in relations:
            with self.subTest(artifact=item["artifact"]):
                self.assertIn(item["relation"], allowed)
                self.assertTrue((ROOT / item["artifact"]).is_file(), item["artifact"])
                self.assertTrue(item["detail"].strip())
        self.assertTrue(
            any(i["relation"] == "AGREES_AND_QUESTIONS_DISCHARGEABILITY" and "INFERENCE" in i["detail"] for i in relations),
            "the dischargeability concern must stay labelled as an inference",
        )

    def test_no_row_claims_credit_or_execution(self):
        blob = json.dumps(self.receipt)
        self.assertNotRegex(blob, r'"(capability|family)_credit_delta":\s*[1-9]')
        self.assertNotIn('"execution_authority": true', blob)
        self.assertIsNotNone(re.search(r"theory.falsification", blob, re.I))


class CensusReceiptTests(unittest.TestCase):
    def setUp(self):
        self.receipt = _load(CENSUS)
        self.premises = {p["id"]: p for p in self.receipt["material_premises"]}

    def test_disqualified_and_candidate_routes_cite_primary_sources(self):
        p1 = self.premises["P1_GITHUB_MODELS_RETIRED"]
        self.assertEqual(p1["resolution"], "DISQUALIFIED")
        self.assertEqual(p1["evidence"]["class"], "OFFICIAL_PRIMARY")
        self.assertIn("fully retired", p1["evidence"]["excerpt"])
        for pid in ("P2_WORKERS_AI_PINNED_MODELS", "P3_WORKERS_AI_FREE_ALLOCATION", "P4_OPENROUTER_FREE_TIER"):
            with self.subTest(premise=pid):
                self.assertEqual(self.premises[pid]["evidence"]["class"], "OFFICIAL_PRIMARY")
                self.assertTrue(self.premises[pid]["evidence"]["url"].startswith("https://"))

    def test_throughput_and_cost_table_recompute_from_recorded_constants(self):
        ev = self.premises["P6_COMPUTED_FREE_TIER_VS_ONE_PASS"]["evidence"]
        c = ev["constants"]
        self.assertEqual(c["free_neurons_per_day"], 10000)
        rows = ev["table"]
        self.assertEqual(len(rows), len(c["models_neurons_per_million_tokens"]) * len(c["token_mixes"]) * len(c["tokens_per_pass"]))
        for row in rows:
            price = c["models_neurons_per_million_tokens"][row["model"]]
            share = c["token_mixes"][row["mix"]]
            self.assertAlmostEqual(sum(share.values()), 1.0, places=9)
            npm = sum(price[k] * share[k] for k in share)
            per_day = c["free_neurons_per_day"] / npm * 1e6
            tokens = c["tokens_per_pass"][row["tokens_per_pass_label"]]
            with self.subTest(model=row["model"], mix=row["mix"], tokens=tokens):
                self.assertAlmostEqual(row["neurons_per_million_tokens"], npm, delta=0.1)
                self.assertAlmostEqual(row["free_days_per_pass"], tokens / per_day, delta=0.1)
                self.assertAlmostEqual(
                    row["paid_usd_per_pass_estimate"], tokens / 1e6 * npm / 1000 * c["usd_per_1000_neurons"], delta=0.01
                )
                self.assertGreater(row["free_days_per_pass"], 30)  # never within a month of the free allocation
        # the receipt's own prose must quote the computed extremes
        days = [r["free_days_per_pass"] for r in rows]
        usd = [r["paid_usd_per_pass_estimate"] for r in rows]
        fact = self.premises["P6_COMPUTED_FREE_TIER_VS_ONE_PASS"]["fact"]
        self.assertIn(f"{min(days):,.0f}", fact)
        self.assertIn(f"{max(days):,.0f}", fact)
        self.assertIn(f"${min(usd):,.2f}", fact)
        self.assertIn(f"${max(usd):,.2f}", fact)

    def test_measured_gaps_are_derived_not_asserted(self):
        fc = self.premises["P7_MEASURED_OPEN_WEIGHTS_GAP_FRONTIERCODE"]["derived"]
        self.assertEqual(fc["residual_points"], round(fc["bar"] - fc["best_workers_ai_baseline"], 1))
        tb = self.premises["P8_MEASURED_OPEN_WEIGHTS_GAP_TB4"]["derived"]
        self.assertEqual(tb["residual_points"], round(tb["bar"] - tb["best_open_baseline"], 1))
        self.assertGreater(tb["residual_points"], fc["residual_points"])

    def test_rate_limit_estimate_recomputes(self):
        d = self.premises["P10_WORKERS_AI_RATE_LIMITS"]["derived"]
        self.assertEqual(d["requests_low"], 91 * 52)
        self.assertEqual(d["requests_high"], 91 * 63)
        self.assertEqual(d["hours_at_20_rpm_low"], round(d["requests_low"] / 20 / 60, 1))
        self.assertEqual(d["hours_at_20_rpm_high"], round(d["requests_high"] / 20 / 60, 1))
        self.assertLess(d["hours_at_20_rpm_high"], 24)  # the rate limit is not the binding constraint

    def test_tb21_dev_set_is_name_disjoint_from_frozen_tb4_tasks(self):
        ev = self.premises["P11_TB21_IS_A_NAME_DISJOINT_DEV_SET"]["evidence"]
        names21 = ev["tb21_task_names"]
        self.assertEqual(len(names21), len(set(names21)))
        self.assertEqual(len(names21), ev["result"]["tb21_count"])
        pin = ev["tb4_names_source"]
        if not (ROOT / pin["path"]).is_file() or _git_blob_sha(pin["path"]) != pin["git_blob_sha"]:
            self.skipTest("TB4 sample manifest changed since this receipt; receipt is a point-in-time record")
        sample = json.loads((ROOT / pin["path"]).read_text(encoding="utf-8"))
        tb4 = {t["task"] for t in sample["ordered_tasks"]} | set(sample["known_spent_or_contaminated_exclusions"])
        self.assertEqual(len(tb4), ev["result"]["tb4_count"])
        self.assertEqual(sorted(tb4 & set(names21)), ev["result"]["exact_overlap"])
        self.assertEqual(ev["result"]["exact_overlap"], [])
        import difflib

        near = [
            a for a in names21
            if difflib.get_close_matches(a, sorted(tb4), n=1, cutoff=0.85)
        ]
        self.assertEqual(near, [])
        self.assertIn("NAME only", self.premises["P11_TB21_IS_A_NAME_DISJOINT_DEV_SET"]["fact"])

    def test_non_comparable_evidence_is_excluded_and_dev_protocol_forbids_frozen_cases(self):
        self.assertIn("NOT used as Terminal-Bench 4.0 evidence", self.premises["P9_EXCLUDED_NON_COMPARABLE_EVIDENCE"]["fact"])
        text = json.dumps(self.receipt["proposed_stage_gate_for_owner_reconciliation_not_adopted"])
        self.assertIn("non-frozen development tasks", text)
        self.assertIn("S2 (only if projected uplift", text)
        self.assertEqual(self.receipt["incremental_spend_usd"], 0)


if __name__ == "__main__":
    unittest.main()
