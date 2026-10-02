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
    "authority_status", "progress_credit",
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
                # reporting rule: no consequential claim is canonical without current-base OBS + trusted guard
                self.assertTrue(r["authority_status"].startswith("PROVISIONAL_ANALYSIS"), r["authority_status"])
                self.assertTrue(r["progress_credit"].startswith("ZERO"), r["progress_credit"])
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


    def test_billing_receipt_follows_the_weak_surface_kill_rule(self):
        r = _load(BILLING)
        align = r["law_alignment"]
        self.assertIn("EXECUTION_LEVERAGE_AND_ANTI_DRIFT_LAW_V1", align["law"])
        self.assertIn("conflicts with hard $0", align["consequence"])
        self.assertIn("retired surface", r["next_action"])


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
            {"OWNER_COMPUTED_OR_PRIVATE": 8, "THIRD_PARTY_RUNNABLE_IN_PRINCIPLE": 3, "UNRESOLVED": 4},
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
        allowed = {"AGREES", "EXTENDS", "AGREES_AND_QUESTIONS_DISCHARGEABILITY", "QUESTIONS_SCOPE_EQUIVALENCE"}
        for item in relations:
            with self.subTest(artifact=item["artifact"]):
                self.assertIn(item["relation"], allowed)
                self.assertTrue((ROOT / item["artifact"]).is_file(), item["artifact"])
                self.assertTrue(item["detail"].strip())
        self.assertTrue(
            any(i["relation"] == "AGREES_AND_QUESTIONS_DISCHARGEABILITY" and "INFERENCE" in i["detail"] for i in relations),
            "the dischargeability concern must stay labelled as an inference",
        )

    def test_automationbench_scope_mismatch_defect_is_pinned_to_primary_sources(self):
        row = next(r for r in self.receipt["public_bar_rows"] if r["predicate_id"] == "AUTOMATIONBENCH_GE_40")
        self.assertTrue(row["third_party_reproducibility"].startswith("UNRESOLVED__PUBLIC_SURFACE_BUT_BAR_COMES_FROM_THE_PRIVATE"))
        self.assertEqual(row["registry_acceptance"], "AutomationBench >= 40.0%")
        primaries = [e for e in row["evidence"] if e["class"] == "OFFICIAL_PRIMARY"]
        self.assertTrue(any("github.com/zapier/AutomationBench" in e["url"] and "held-out private task set" in e["excerpt"] for e in primaries))
        self.assertTrue(any("50.3%" in e["excerpt"] for e in primaries), "public-600 Opus 5 baseline must be quoted")
        defect = {d["id"]: d for d in self.receipt["defect_findings"]}["AUTOMATIONBENCH_BAR_SCOPE_MISMATCH"]
        self.assertIn("false-success hazard", defect["consequence"])
        self.assertIn("scope-equivalence", defect["consequence"])
        self.assertGreaterEqual(len(defect["fixes_for_owner_reconciliation_not_adopted"]), 2)
        self.assertIn("medium for the exact official value", defect["confidence"])
        self.assertIn("Opus 4.8 scores 41.00%", row["note"])
        self.assertIn("3_RUNNABLE_NEED_A_PINNED_GENERATOR__4_UNRESOLVED", self.receipt["status"])

    def test_livebench_metric_and_release_defect_is_pinned_to_sources(self):
        defect = {d["id"]: d for d in self.receipt["defect_findings"]}["LIVEBENCH_IF_METRIC_AND_RELEASE_ALIGNMENT"]
        primaries = [e for e in defect["evidence"] if e["class"] == "OFFICIAL_PRIMARY"]
        text = " ".join(e["excerpt"] for e in primaries)
        self.assertIn("(score_1 + score_2) / 2", text)
        self.assertIn("results['strict']", text)
        self.assertIn("2025-11-25", text)
        self.assertIn("latest entry 2026-01-08".lower(), text.lower())
        self.assertIn("prompt-level loose accuracy of IFBench", text)
        for e in primaries:
            self.assertIn("LiveBench/LiveBench/blob/8f8e5c381a16e3f24257776edd53471fe86f8091/", e["url"])
        self.assertGreaterEqual(len(defect["fixes_for_owner_reconciliation_not_adopted"]), 3)
        self.assertIn("direction of the error is not fixed", defect["consequence"])
        self.assertIn("dataset schema was inferred", defect["confidence"])
        # the repo-side claims quoted by the receipt must be what the repo files say (skip if they were later changed)
        for e in (x for x in defect["evidence"] if x["class"] == "REPO"):
            if not (ROOT / e["path"]).is_file() or _git_blob_sha(e["path"]) != e["git_blob_sha"]:
                continue
            blob = (ROOT / e["path"]).read_text(encoding="utf-8")
            self.assertIn("PROMPT_LEVEL_LOOSE_ACCURACY_IS_PUBLICLY_DECLARED_REPORTED_METRIC" if "BINDING" in e["path"] else "LiveBench 2026-06-25 Instruction Following", blob)

    def test_kit_readme_states_the_corrected_metric_and_does_not_endorse_the_repo_binding(self):
        readme = (ROOT / "livebench_if_generation_v1" / "README.md").read_text(encoding="utf-8")
        self.assertIn("ifbench_process_results", readme)
        self.assertIn("0.5 * [all instructions followed] + 0.5 * [fraction of instructions followed]", readme)
        self.assertIn("CAUTION", readme)
        self.assertIn("LIVEBENCH_IF_METRIC_AND_RELEASE_ALIGNMENT", readme)
        self.assertNotIn("declared metric = prompt-level loose accuracy", readme)
        self.assertIn("--assert-no-frozen-questions", readme)
        self.assertIn("--frozen-release-min 2025-11-25", readme)

    def test_livebench_row_records_the_open_model_update(self):
        row = next(r for r in self.receipt["public_bar_rows"] if r["predicate_id"] == "LIVEBENCH_IF_GE_65_7")
        self.assertTrue(any("livebench.ai" in e["url"] and e["class"] == "OFFICIAL_PRIMARY" for e in row["evidence"]))
        self.assertIn("UPDATE", row["note"])
        self.assertIn("CORRECTION", self.receipt["conclusion"])

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

    def test_priced_uplift_experiment_recomputes_from_recorded_constants(self):
        from statistics import NormalDist

        ev = self.premises["P12_PRICED_UPLIFT_EXPERIMENT"]["evidence"]
        consts = self.premises["P6_COMPUTED_FREE_TIER_VS_ONE_PASS"]["evidence"]["constants"]
        z = NormalDist()
        n = 89
        for row in ev["power_table"]:
            sd, d = row["sd_of_per_task_paired_difference"], row["true_uplift"]
            se = sd / n ** 0.5
            power = z.cdf(d / se - z.inv_cdf(0.975)) + z.cdf(-d / se - z.inv_cdf(0.975))
            with self.subTest(sd=sd, uplift=d):
                self.assertAlmostEqual(row["power_two_sided_alpha_0_05"], power, delta=0.0006)
                self.assertAlmostEqual(row["ci95_half_width_points"], 1.96 * se * 100, delta=0.06)

        tokens = {"LOW_0.57M_TOKENS_PER_TRIAL": 52e6 / 91, "HIGH_10.7M_TOKENS_PER_TRIAL": 970e6 / 91}

        def usd_per_million(model, mix):
            price = consts["models_neurons_per_million_tokens"][model]
            share = consts["token_mixes"][mix]
            return sum(price[k] * share[k] for k in share) / 1000 * consts["usd_per_1000_neurons"]

        for row in ev["budget_table"]:
            expected = row["total_trials"] * tokens[row["tokens_per_trial_label"]] / 1e6 * usd_per_million(row["model"], row["mix"])
            with self.subTest(budget=row["model"], mix=row["mix"], k=row["trials_per_task"]):
                self.assertEqual(row["total_trials"], 89 * row["trials_per_task"] * 2)
                self.assertAlmostEqual(row["estimated_usd"], expected, delta=0.01)
        for row in ev["micro_pilot_table"]:
            expected = row["total_trials"] * tokens[row["tokens_per_trial_label"]] / 1e6 * usd_per_million(row["model"], row["mix"])
            with self.subTest(pilot=row["mix"], tokens=row["tokens_per_trial_label"]):
                self.assertEqual(row["total_trials"], 12)
                self.assertAlmostEqual(row["estimated_usd"], expected, delta=0.01)
        fact = self.premises["P12_PRICED_UPLIFT_EXPERIMENT"]["fact"]
        usd = [r["estimated_usd"] for r in ev["budget_table"]]
        pilot = [r["estimated_usd"] for r in ev["micro_pilot_table"]]
        self.assertIn(f"${min(usd):,.0f} to ${max(usd):,.0f}", fact)
        self.assertIn(f"${min(pilot):,.2f} to ${max(pilot):,.2f}", fact)
        self.assertIn("not measurements", fact)
        self.assertIn("decision_rule_proposal", ev)

    def test_livebench_if_open_models_exceed_the_bar_arithmetic(self):
        ev = self.premises["P13_LIVEBENCH_IF_OPEN_WEIGHTS_EXCEED_THE_BAR"]["evidence"]
        bar = ev["bar"]
        self.assertEqual(bar, 65.7)
        above = [r for r in ev["rows"] if r["livebench_instruction_following"] > bar]
        for r in ev["rows"]:
            self.assertEqual(r["margin_vs_opus_5_5_bar"], round(r["livebench_instruction_following"] - bar, 1), r["model"])
            self.assertTrue(r["open_weights"])
        fact = self.premises["P13_LIVEBENCH_IF_OPEN_WEIGHTS_EXCEED_THE_BAR"]["fact"]
        self.assertIn(f"{len(above)} open-weights rows", fact)
        on_cf = [r for r in above if r["workers_ai_id_by_name_only"]]
        self.assertTrue(on_cf)
        pricing_fact = self.premises["P2_WORKERS_AI_PINNED_MODELS"]["fact"]
        for r in on_cf:
            self.assertIn(r["workers_ai_id_by_name_only"].split("/", 1)[1], pricing_fact, r["model"])
        below = [r for r in ev["rows"] if r["livebench_instruction_following"] <= bar]
        self.assertTrue(below, "context rows at or below the bar must be kept to avoid a cherry-picked list")
        self.assertTrue(any("release date was not recorded" in c for c in ev["caveats"]))
        self.assertIn("external capability provider", self.premises["P13_LIVEBENCH_IF_OPEN_WEIGHTS_EXCEED_THE_BAR"]["ownership_caveat"])

    def test_livebench_if_pass_cost_grid_recomputes(self):
        p = self.premises["P14_LIVEBENCH_IF_PASS_COST"]
        ev = p["evidence"]
        for g in ev["grid"]:
            pin, pout = ev["models_neurons_per_million_tokens_input_output"][g["model"]]
            neurons = g["questions"] * (ev["input_tokens_per_question"] * pin / 1e6 + g["output_tokens_per_question"] * pout / 1e6)
            with self.subTest(model=g["model"], n=g["questions"], out=g["output_tokens_per_question"]):
                self.assertAlmostEqual(g["neurons_per_pass"], neurons, delta=1)
                self.assertAlmostEqual(g["free_days_per_pass"], neurons / ev["free_neurons_per_day"], delta=0.01)
                self.assertAlmostEqual(g["paid_usd_per_pass_estimate"], neurons / 1000 * ev["usd_per_1000_neurons"], delta=0.01)
        days = [g["free_days_per_pass"] for g in ev["grid"]]
        usd = [g["paid_usd_per_pass_estimate"] for g in ev["grid"]]
        self.assertIn(f"{min(days):.1f} to {max(days):.1f} days", p["fact"])
        self.assertIn(f"${min(usd):.2f} to ${max(usd):.2f}", p["fact"])
        concl = self.receipt["conclusion"]
        self.assertIn(f"{min(days):.1f} to {max(days):.1f} days", concl)
        self.assertIn(f"${min(usd):.2f} to ${max(usd):.2f}", concl)
        self.assertIn("parametric grid, not a measurement", p["fact"])

    def test_census_no_longer_repeats_the_wrong_metric(self):
        p13 = self.premises["P13_LIVEBENCH_IF_OPEN_WEIGHTS_EXCEED_THE_BAR"]
        self.assertIn("AGGREGATOR", p13["scorer_state"])
        self.assertNotIn("prompt-level loose accuracy)", p13["scorer_state"].split("differs from")[0])
        self.assertIn("strict mean-of-two", self.receipt["reconciliation"]["answer"])
        self.assertTrue(any("matches no release" in c for c in p13["evidence"]["caveats"]))
        self.assertTrue(any(u.startswith("Metric alignment") for u in self.receipt["reconciliation"]["unverified_parts"]))

    def test_correction_and_reconciliation_are_explicit(self):
        self.assertIn("was wrong", self.receipt["correction_notice"])
        rec = self.receipt["reconciliation"]
        self.assertEqual(rec["question"], "What is the shortest verified path from the current state to the terminal capability now?")
        self.assertIn("LIVEBENCH_IF_GE_65_7", rec["answer"])
        self.assertTrue(rec["verified_parts"] and rec["unverified_parts"])
        self.assertTrue(any(r["relation"] == "CORRECTS" for r in self.receipt["relation_to_prior_work"]))

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
