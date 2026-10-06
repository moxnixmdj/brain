from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SAT = ROOT / "canonical/governance/COMPOSITION_CRITICAL_INVARIANT_ACTIVE_AUTHORITY_SATURATION_20261006_V1.json"

EXPECTED_SHAS = {
    "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json":"562536d9ba3f245a6bd24490a1eb3b30f27e0c3a",
    "canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json":"62394e5b7d221ec9f69c3458f669e40e253a9d09",
    "canonical/governance/OPUS55_MATCHED_COMPARATOR_SUPERPORTFOLIO_V1.json":"d9ac894594ebcd2883520f7b7977a3548420541c",
    "canonical/governance/OPUS55_MATCHED_TARGET_NORMALIZATION_PROVENANCE_V3.json":"72a5cd689f55df84de73693371264f02ef4e7226",
    "canonical/governance/COMPOSITION_CURRENT_AUTHORITY_V8.json":"815a0583ff2688d37b31bd5cbb650129bbd52174",
    "canonical/verification/COMPOSITION_CURRENT_AUTHORITY_V8_SPRITE_VERIFICATION_20261006_V1.json":"be9aaa41b2356954eef851cf593632136b10c5ac",
    "canonical/governance/COMPOSITION_ZERO_CRITICAL_INVARIANT_MINIMUM_PREMISE_CUT_20261005_V1.json":"cad34e4a8912b2ffa07d73d94c9651f2852d7247",
    "canonical/verification/COMPOSITION_ZERO_CRITICAL_INVARIANT_MINIMUM_PREMISE_CUT_CONNECTOR_VERIFICATION_20261005_V1.json":"db2c3c1dc7c2e2bd6f9b0e50b6c543e8bac79d90",
    "canonical/governance/COMPOSITION_ACCEPTANCE_QUOTIENT_CAPSULE_MINIMUM_CUT_20261005_V1.json":"0fa324b09681f7a4b2c9f01d8c7337ab4d87dc4f",
    "canonical/verification/COMPOSITION_ACCEPTANCE_QUOTIENT_CAPSULE_MINIMUM_CUT_WOLFRAM_VERIFICATION_20261005_V1.json":"1e19a96a3d8b45816bf898763f13cce5fded2c8e",
    "canonical/governance/OPUS55_COMPOSITIONAL_TRACE_REFINEMENT_TERMINAL_REDUCER_20261005_V1.json":"741c354c705a77972ba051dcc62917bfc53fa941",
    "canonical/verification/OPUS55_COMPOSITIONAL_TRACE_REFINEMENT_WOLFRAM_VERIFICATION_20261005_V1.json":"69baf09701eaeb59e105d0f95310d97023a25ef1",
    "canonical/runtime/composition_critical_invariant_aggregator_v1.py":"c83e63294318733fd7cab2a33a82ed6b9640ae50",
    "canonical/tests/test_composition_critical_invariant_aggregator_v1.py":"10d4db9dc166f13435318ad5eb8dbe4331a1cdeb",
}

PRED = "COMPOSITION_ZERO_CRITICAL_INVARIANT_FAILURES"


def load(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def find_predicate_row(doc):
    for row in doc.get("predicates", []):
        if row.get("id") == PRED:
            return row
    raise AssertionError("PREDICATE_ROW_MISSING")


def verify() -> dict[str, object]:
    sat = json.loads(SAT.read_text(encoding="utf-8"))
    universe = {row["path"]: row["git_blob_sha"] for row in sat["active_authority_universe"]}
    assert universe == EXPECTED_SHAS
    assert sat["saturation_result"]["files_checked"] == 14
    assert sat["saturation_result"]["terminal_noncompensability_binding_count"] == 0

    registry = load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json")
    row = find_predicate_row(registry)
    assert row["acceptance"] == "No critical composition invariant fails."
    assert row["execution_binding"] == "canonical/governance/OPUS55_MATCHED_COMPARATOR_SUPERPORTFOLIO_V1.json"

    norm = load("canonical/governance/OPUS55_MATCHED_TARGET_NORMALIZATION_PROVENANCE_V3.json")
    target = next(x for x in norm["targets"] if x.get("predicate_id") == PRED)
    atoms = {x["atom"] for x in target["atom_sources"]}
    assert atoms == {
        "invariant:zero_critical_composition_failures",
        "invariant:cross_component_state_loss_zero_or_noncritical",
        "invariant:evidence_provenance_complete",
    }
    assert all(
        set(s.keys()) <= {"document", "literal"}
        for atom in target["atom_sources"]
        for s in atom["sources"]
    )

    v8 = load("canonical/governance/COMPOSITION_CURRENT_AUTHORITY_V8.json")
    terminal = v8["current_parent_composition_requirements"]["terminal_comparison"]
    assert PRED in terminal
    assert "COMPOSITION_TERMINAL_SUCCESS_NONINFERIOR" in terminal

    cut = load("canonical/governance/COMPOSITION_ZERO_CRITICAL_INVARIANT_MINIMUM_PREMISE_CUT_20261005_V1.json")
    p1 = next(x for x in cut["residual_premises"] if x["id"] == "P1_CROSS_COMPONENT_STATE_PRESERVATION")
    assert "VERIFIED_ROLLBACK_REESTABLISHES" in p1["statement"]

    capsule = load("canonical/governance/COMPOSITION_ACCEPTANCE_QUOTIENT_CAPSULE_MINIMUM_CUT_20261005_V1.json")
    c2 = next(x for x in capsule["remaining_boundary_obligations"] if x["id"] == "C2_CRITICAL_INVARIANT_UNIVERSE_TOTALITY")
    assert "NO_CRITICAL_COMPOSITION_INVARIANT_FAILS" in c2["statement"].replace(" ", "_").upper()

    reducer = load("canonical/governance/OPUS55_COMPOSITIONAL_TRACE_REFINEMENT_TERMINAL_REDUCER_20261005_V1.json")
    reducer_text = json.dumps(reducer, sort_keys=True).upper()
    assert "REESTABLISH" in reducer_text
    assert "NO_HIDDEN_COMPOSITION_DEBT" in reducer_text

    aggregator_text = (ROOT / "canonical/runtime/composition_critical_invariant_aggregator_v1.py").read_text(encoding="utf-8").lower()
    assert "critical" in aggregator_text
    assert "terminal_noncompensable" not in aggregator_text
    assert "noncompensable" not in aggregator_text

    authority_text = "\n".join((ROOT / p).read_text(encoding="utf-8").lower() for p in EXPECTED_SHAS)
    for forbidden in ("terminally_noncompensable", "terminally noncompensable"):
        assert forbidden not in authority_text

    verdict = sat["necessity_verdict"]
    assert verdict["bare_predicate_necessary"] is False
    assert verdict["minimum_repair"].startswith("REMOVE_ONLY_THE_BARE_ZERO_INTERNAL_FAILURE_TRUTH_ID")
    assert sat["accounting"]["terminal_credit_delta"] == 0

    return {
        "status": "PASS__ACTIVE_AUTHORITY_SATURATED__BARE_ZERO_INTERNAL_FAILURE_NECESSITY_FALSIFIED",
        "files_checked": 14,
        "predicate": PRED,
        "registry_truth_changed": False,
        "necessary_cut_delta_if_activated": -1,
        "terminal_credit_delta": 0,
    }


if __name__ == "__main__":
    print(json.dumps(verify(), sort_keys=True))
