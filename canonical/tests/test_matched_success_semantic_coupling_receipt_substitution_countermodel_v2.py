from canonical.runtime.matched_success_semantic_coupling_contract_v2 import compile_coupling
from canonical.tests.test_matched_success_semantic_coupling_contract_v2 import base


def test_v2_currently_accepts_unbound_run_and_details_claims_countermodel():
    x = base()

    # These are fabricated semantic claims. The existing receipt objects are
    # intentionally left unchanged because V2 does not bind receipt bytes to
    # these load-bearing fields.
    row = next(
        r for r in x["classes"]
        if r["class_id"] == "CODING_DEBUG_TOOL_DISCOVERY"
    )
    row["details"]["debug_localizes_injected_failure"] = True
    row["details"]["tool_route_admissible"] = True
    row["details"]["repaired_output_passes_original_oracle"] = True

    # The contract has no details receipt and no run-semantics digest binding.
    assert "details_receipt" not in row
    assert "run_semantics_sha256" not in row["true_run"]

    out = compile_coupling(x)

    # A sound next version must reject this evidence shape. V2 currently passes,
    # which is the constructive substitution counterexample.
    assert out["status"] != "PASS__INTERVENTIONAL_SEMANTIC_COUPLING_CONTRACT"
