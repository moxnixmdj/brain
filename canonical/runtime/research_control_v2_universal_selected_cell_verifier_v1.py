from __future__ import annotations

import hashlib
import json
from pathlib import Path

from canonical.runtime import research_control_information_safe_candidate as candidate
from canonical.runtime import research_control_information_safe_proof as v1
from canonical.runtime import research_control_information_safe_proof_v2 as v2

ROOT = Path(__file__).resolve().parents[2]
GOV = "canonical/governance/RESEARCH_CONTROL_V2_UNIVERSAL_SELECTED_CELL_20261007_V1.json"

EXPECTED = {
    "canonical/action_intents/ACTION_INTENT_RESEARCH_CONTROL_V2_TOTALITY_20261007_V1.json": "2150ae98b2367e0a93b2904f41fe22c99df054d6",
    "canonical/runtime/research_control_information_safe_proof.py": "16c47efee0e0e38f479163d1285d7079798efdaf",
    "canonical/verification/RESEARCH_CONTROL_INFORMATION_SAFE_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json": "860cd929e3b7fdab6befec5bf052479dc4ae41ac",
    "canonical/runtime/research_control_information_safe_candidate.py": "cd6bf6e4163bbba64878b856766b1af4372d68bc",
    "canonical/runtime/research_control_information_safe_proof_v2.py": "a8d41a84b0368d0a9467173856912cc48742dcf1",
    "canonical/tests/test_research_control_information_safe_v2.py": "f2348d1837f05c950ca1c9293698060d150e9b20",
    "canonical/governance/TERMINAL_NOW_V18_INSTANT_CLOSURE_ROUTE_FALSIFICATION_20261007_V1.json": "794d1a6df9b2f062e0dee51d890a304a3dd04746",
    "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V16.json": "f9f095de0d64ff11ff2e176728123ea54875e316",
    "canonical/governance/U_EXHAUSTION_SCOPE_COMPLETE_CERTIFICATE_LEVERAGE_GUARD_20261007_V1.json": "b819801f7f7d19be843e5fdc3b7646bc2b1e749d",
    GOV: "29048c2665f7cb619a22b76f0bf54d9534bba520",
}


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def load(path: str):
    return json.loads((ROOT / path).read_text())


def verify():
    errors: list[str] = []

    for path, expected in EXPECTED.items():
        p = ROOT / path
        if not p.is_file():
            errors.append("SOURCE_MISSING:" + path)
            continue
        actual = git_blob_sha(p.read_bytes())
        if actual != expected:
            errors.append("SOURCE_DRIFT:" + path + ":" + actual)

    gov = load(GOV)
    v2_source = (ROOT / "canonical/runtime/research_control_information_safe_proof_v2.py").read_text()
    candidate_source = (ROOT / "canonical/runtime/research_control_information_safe_candidate.py").read_text()

    # Reproduce the exact V1 counterexample.
    old_case = v1.generate_case(766, 0)
    old_ids = [x["source_id"] for x in old_case["source_catalog"]]
    if len(old_ids) == len(set(old_ids)):
        errors.append("V1_COUNTEREXAMPLE_NO_LONGER_REPRODUCES_DUPLICATE")
    if old_ids.count("S-R2-40168") != 2:
        errors.append("V1_COUNTEREXAMPLE_ID_DRIFT")
    old_out = v1.run_episode(old_case, candidate.next_action)
    if old_out.get("pass") is not False or old_out.get("reason") != "ACTION_BUDGET_EXHAUSTED":
        errors.append("V1_COUNTEREXAMPLE_VERDICT_DRIFT:" + str(old_out))

    # The same coordinates must pass in V2 with total source identity.
    new_case = v2.generate_case(766, 0)
    new_ids = [x["source_id"] for x in new_case["source_catalog"]]
    if len(new_ids) != len(set(new_ids)):
        errors.append("V2_SOURCE_IDENTITY_NOT_TOTAL")
    new_out = v2.run_episode(new_case, candidate.next_action)
    if new_out.get("pass") is not True:
        errors.append("V2_COUNTEREXAMPLE_NOT_REPAIRED:" + str(new_out))

    # Bind the case-independent proof to the exact source structure.
    required_v2_tokens = [
        "for slot in range(3)",
        'f"S-{rid}-{slot}-{r.randrange(10000, 99999)}"',
        "first_supports = (seed + i + ordinal) % 2 == 0",
        '"authority": 0.96',
        '"authority": 0.93',
        '"authority": 0.70',
        "budget = 3 * n + 1",
        "run_episode = v1.run_episode",
    ]
    for token in required_v2_tokens:
        if token not in v2_source:
            errors.append("V2_PROOF_TOKEN_MISSING:" + token)

    required_candidate_tokens = [
        "unresolved=[x for x in reqs",
        "admissible.sort(key=lambda x:(-float(x.get(\"authority\",0.0))",
        '"action":"SEARCH"',
        '"action":"STOP"',
    ]
    for token in required_candidate_tokens:
        if token not in candidate_source:
            errors.append("CANDIDATE_POLICY_TOKEN_MISSING:" + token)

    selected = gov.get("selected_cell") or {}
    if selected.get("behavior_id") != "ITERATIVE_RESEARCH_EVIDENCE_CONTROL_001":
        errors.append("BEHAVIOR_ID_DRIFT")
    if selected.get("selected_cell_scope_complete") is not True:
        errors.append("SELECTED_CELL_SCOPE_NOT_COMPLETE")
    if selected.get("direct_e2e") is not True:
        errors.append("DIRECT_E2E_NOT_ASSERTED")
    if selected.get("scope_complete_class_closure") is not True:
        errors.append("SCOPE_COMPLETE_CLASS_CLOSURE_NOT_BOUND")
    if selected.get("progress_kind") != "REUSABLE_PARAMETERIZED_LAW_OVER_THE_ENTIRE_EXACT_V2_GENERATOR_CLASS__NOT_FINITE_POINT_CELL_ACCUMULATION":
        errors.append("ANTI_CHURN_PROGRESS_KIND_INVALID")
    if selected.get("open_world_research_scope_complete") is not False:
        errors.append("OPEN_WORLD_OVERCLAIM")

    formal = gov.get("independent_formal_check") or {}
    for key in (
        "excluded_middle",
        "exactly_one_of_boolean_complements",
        "budget_all_integers_n_ge_3",
    ):
        if formal.get(key) is not True:
            errors.append("FORMAL_CHECK_MISSING:" + key)

    consequence = gov.get("abc_consequence") or {}
    if consequence.get("proposed_D_B_region") != "RESEARCH_CONTROL_INFO_SAFE_V2_ALL_GENERATED_CASES":
        errors.append("DB_REGION_DRIFT")
    if consequence.get("unknown_domain_family_closed") is not False:
        errors.append("UNKNOWN_DOMAIN_OVERCLAIM")
    if consequence.get("research_control_open_world_closed") is not False:
        errors.append("RESEARCH_CONTROL_OVERCLAIM")
    if consequence.get("u_exhaustion_guard_compliance") != "LEGAL__CLOSES_A_PROVED_SCOPE_COMPLETE_PARAMETERIZED_RESIDUAL_CLASS__DOES_NOT_USE_CERTIFICATE_COUNT_AS_PROGRESS_PROXY":
        errors.append("U_EXHAUSTION_GUARD_NOT_SATISFIED")

    accounting = gov.get("accounting") or {}
    for key in (
        "incremental_spend_usd",
        "fresh_reality_units_consumed",
        "terminal_cases_consumed",
        "acceptance_credit_delta",
        "family_credit_delta",
        "capability_credit_delta",
        "ownership_credit_delta",
        "terminal_credit_delta",
    ):
        if accounting.get(key) != 0:
            errors.append("NONZERO_ACCOUNTING:" + key)

    return {
        "schema": "PROJECT_BRAIN_RESEARCH_CONTROL_V2_UNIVERSAL_SELECTED_CELL_VERIFY_V1",
        "status": (
            "PASS__V1_UNIVERSAL_ROUTE_FALSIFIED__V2_COLLISION_TOTAL_SELECTED_CELL_SOUNDLY_BOUND__ZERO_CREDIT"
            if not errors
            else "FAIL_CLOSED"
        ),
        "pass": not errors,
        "errors": errors,
        "v1_counterexample_reproduced": not any(x.startswith("V1_COUNTEREXAMPLE") for x in errors),
        "v2_counterexample_repaired": not any(x.startswith("V2_") and "TOKEN" not in x for x in errors),
        "selected_cell_scope_complete": not errors,
        "open_world_research_scope_complete": False,
        "unknown_domain_family_closed": False,
        "terminal": False,
        "terminal_credit_delta": 0,
    }


if __name__ == "__main__":
    out = verify()
    print(json.dumps(out, indent=2, sort_keys=True))
    raise SystemExit(0 if out["pass"] else 1)
