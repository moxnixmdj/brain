#!/usr/bin/env python3
from __future__ import annotations

import copy
import json

from canonical.runtime.acceptance_quotient_simulation_v4 import (
    verify_acceptance_quotient_certificate_v4 as verify_v4,
)
from canonical.runtime.acceptance_quotient_simulation_v5 import (
    acceptance_domain_sha256,
    brain_macroedge_sha256,
    verify_acceptance_quotient_certificate_v5 as verify_v5,
)


def receipt(path: str, sha: str, **flags):
    return {"path": path, "git_blob_sha": sha, **flags}


def base_certificate():
    cert = {
        "target_states": ["t0", "t1"],
        "brain_states": ["b0", "b1"],
        "initial_target_states": ["t0"],
        "initial_brain_states": ["b0"],
        "terminal_target_states": ["t1"],
        "terminal_brain_states": ["b1"],
        "relation": [["t0", "b0"], ["t1", "b1"]],
        "abstraction_receipt": receipt(
            "canonical/verification/abstraction.json", "1" * 40,
            acceptance_complete=True,
            load_bearing_observations_complete=True,
            target_conservative_coverage=True,
            independent_or_objective=True,
        ),
        "relation_soundness_receipt": receipt(
            "canonical/verification/relation.json", "2" * 40,
            acceptance_preorder_sound=True,
            load_bearing_dimensions_complete=True,
            scope_complete=True,
            independent_or_objective=True,
        ),
        "terminal_acceptance_receipt": receipt(
            "canonical/verification/terminal.json", "3" * 40,
            terminal_noninferiority_sound=True,
            scope_complete=True,
            independent_or_objective=True,
        ),
        "acceptance_semantics_class": "UNIVERSAL_ZERO_VIOLATION",
        "distribution_free_dominance_receipt": receipt(
            "canonical/verification/zero-violation.json", "9" * 40,
            universal_zero_violation_proved=True,
            absolute_bound_proved=True,
            scope_complete=True,
            independent_or_objective=True,
        ),
        "target_cut_edges": [{"id": "e0", "from": "t0", "to": "t1"}],
        "brain_macro_edges": [
            {
                "from": "b0",
                "to": "b1",
                "covers_target_edge_ids": ["e0"],
                "scope_authority_invariant": False,
                "realizability_receipt": receipt(
                    "canonical/verification/realizable.json", "4" * 40,
                    scope_complete=True,
                    universal_from_abstract_class=True,
                    independent_or_objective=True,
                ),
                "scope_authority_receipt": receipt(
                    "canonical/verification/scope.json", "5" * 40,
                    invariant_holds=True,
                    scope_complete=True,
                    universal_over_realizations=True,
                    independent_or_objective=True,
                ),
            }
        ],
    }
    domain = acceptance_domain_sha256(cert)
    policy = {
        "policy_id": "owned-policy-v1",
        "policy_git_blob_sha": "6" * 40,
        "policy_epoch": "2026-10-05T02:32Z",
        "claimed_domain_sha256": domain,
    }
    cert["causal_strategy_receipt"] = receipt(
        "canonical/verification/strategy.json", "7" * 40,
        **policy,
        single_owned_policy=True,
        complete_on_claimed_domain=True,
        history_adapted=True,
        no_future_or_target_oracle=True,
        existential_matches_induced_by_policy=True,
        independent_or_objective=True,
    )
    edge = cert["brain_macro_edges"][0]
    edge["causal_policy_binding_receipt"] = receipt(
        "canonical/verification/edge-policy.json", "8" * 40,
        **policy,
        brain_edge_sha256="0" * 64,
        induced_by_bound_policy=True,
        choice_uses_current_or_past_information_only=True,
        no_target_edge_or_future_branch_oracle=True,
        scope_complete=True,
        independent_or_objective=True,
    )
    edge["causal_policy_binding_receipt"]["brain_edge_sha256"] = brain_macroedge_sha256(edge)
    return cert


def require(name, cond, out):
    if not cond:
        raise AssertionError(name + ":" + json.dumps(out, sort_keys=True))


def main():
    tests = []

    good = base_certificate()
    out = verify_v5(good)
    require("GOOD", out.get("status") == "PASS", out)
    tests.append("GOOD")

    split = copy.deepcopy(good)
    split["brain_macro_edges"][0]["causal_policy_binding_receipt"]["policy_id"] = "different-policy"
    legacy = verify_v4(split)
    fixed = verify_v5(split)
    require("LEGACY_V4_SPLIT_POLICY_WITNESS", legacy.get("status") == "PASS", legacy)
    require(
        "V5_REJECTS_SPLIT_POLICY",
        fixed.get("status") == "FAIL_CLOSED"
        and "SPLIT_POLICY_BINDING" in fixed.get("reason", ""),
        fixed,
    )
    tests.extend(["LEGACY_V4_SPLIT_POLICY_WITNESS", "V5_REJECTS_SPLIT_POLICY"])

    stale_domain = copy.deepcopy(good)
    stale_domain["target_states"].append("t2")
    out = verify_v5(stale_domain)
    require(
        "DOMAIN_REBIND",
        out.get("status") == "FAIL_CLOSED"
        and "DOMAIN_BINDING_MISMATCH" in out.get("reason", ""),
        out,
    )
    tests.append("DOMAIN_REBIND")

    stale_edge = copy.deepcopy(good)
    stale_edge["brain_macro_edges"][0]["nonsemantic_extra"] = "mutation"
    out = verify_v5(stale_edge)
    require(
        "EDGE_CONTENT_REBIND",
        out.get("status") == "FAIL_CLOSED"
        and "CONTENT_BINDING_MISMATCH" in out.get("reason", ""),
        out,
    )
    tests.append("EDGE_CONTENT_REBIND")

    bad_epoch = copy.deepcopy(good)
    bad_epoch["brain_macro_edges"][0]["causal_policy_binding_receipt"]["policy_epoch"] = "other"
    out = verify_v5(bad_epoch)
    require(
        "EPOCH_SPLIT",
        out.get("status") == "FAIL_CLOSED"
        and "SPLIT_POLICY_BINDING" in out.get("reason", ""),
        out,
    )
    tests.append("EPOCH_SPLIT")

    malformed = copy.deepcopy(good)
    malformed["causal_strategy_receipt"]["policy_git_blob_sha"] = "not-a-sha"
    out = verify_v5(malformed)
    require(
        "MALFORMED_POLICY_BLOB",
        out.get("status") == "FAIL_CLOSED"
        and "POLICY_GIT_BLOB_SHA_INVALID" in out.get("reason", ""),
        out,
    )
    tests.append("MALFORMED_POLICY_BLOB")

    return {
        "schema": "PROJECT_BRAIN_ACCEPTANCE_QUOTIENT_SIMULATION_V5_SELFTEST",
        "status": "PASS",
        "pass": True,
        "test_count": len(tests),
        "tests": tests,
        "independent": False,
        "wolfram_counterexample_independently_checked": True,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "ownership_credit_delta": 0,
    }


if __name__ == "__main__":
    print(json.dumps(main(), indent=2, sort_keys=True))
