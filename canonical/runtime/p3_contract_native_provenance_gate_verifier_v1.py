from __future__ import annotations

import json

from canonical.runtime import contract_native_brain_candidate as candidate
from canonical.runtime import contract_native_proof_suites as suite

P3 = "EVIDENCE_TO_AUDIENCE_SYNTHESIS_001"


def verify() -> dict:
    errors: list[str] = []
    checked = 0

    for seed in range(500):
        for difficulty in range(1, 6):
            case = suite.generate_case(P3, seed, difficulty)
            public = suite.public_task(case)
            if "_oracle" in public:
                errors.append(f"ORACLE_LEAK:{seed}:{difficulty}")
                continue
            try:
                got = candidate.solve(public)
                verdict = suite.score_case(case, got)
            except Exception as exc:
                errors.append(f"EXCEPTION:{seed}:{difficulty}:{type(exc).__name__}")
                continue
            checked += 1
            if verdict.get("pass") is not True:
                errors.append(f"BASE_CASE_FAIL:{seed}:{difficulty}:{verdict.get('reasons')}")
                continue

            selected = got.get("selected_claims")
            provenance = got.get("provenance_by_claim")
            if not isinstance(selected, list) or not isinstance(provenance, dict):
                errors.append(f"PROVENANCE_OUTPUT_SCHEMA:{seed}:{difficulty}")
                continue
            public_by_id = {
                row["claim_id"]: list(row["provenance"])
                for row in public["task"]["evidence"]
            }
            expected = {claim_id: public_by_id[claim_id] for claim_id in selected}
            if provenance != expected:
                errors.append(f"PUBLIC_PROVENANCE_NOT_EXACT:{seed}:{difficulty}")

    seed80 = suite.generate_case(P3, 80, 1)
    rows80 = {row["claim_id"]: row for row in seed80["task"]["evidence"]}
    if any(rows80[cid]["support"] == "unsupported" for cid in seed80["_oracle"]["required"]):
        errors.append("SEED80_REQUIRED_UNSUPPORTED_REGRESSION")

    mutations = [
        ("missing", 505),
        ("mismatch", 506),
        ("orphan", 507),
    ]
    mutation_results: dict[str, list[str]] = {}
    for kind, seed in mutations:
        case = suite.generate_case(P3, seed, 5)
        got = candidate.solve(suite.public_task(case))
        if not got["selected_claims"]:
            errors.append(f"MUTATION_NO_SELECTED:{kind}")
            continue
        victim = got["selected_claims"][0]
        if kind == "missing":
            del got["provenance_by_claim"][victim]
            prefix = "PROVENANCE_MISSING:"
        elif kind == "mismatch":
            got["provenance_by_claim"][victim] = ["FORGED-SOURCE"]
            prefix = "PROVENANCE_MISMATCH:"
        else:
            victim = got["selected_claims"][-1]
            got["selected_claims"] = [x for x in got["selected_claims"] if x != victim]
            got["uncertainty_claims"] = [x for x in got["uncertainty_claims"] if x != victim]
            prefix = "PROVENANCE_WITHOUT_SELECTED_CLAIM:"
        verdict = suite.score_case(case, got)
        reasons = list(verdict.get("reasons") or [])
        mutation_results[kind] = reasons
        if verdict.get("pass") is True or not any(str(x).startswith(prefix) for x in reasons):
            errors.append(f"MUTATION_SURVIVED:{kind}:{reasons}")

    return {
        "schema": "PROJECT_BRAIN_P3_CONTRACT_NATIVE_PROVENANCE_GATE_VERIFIER_V1",
        "status": "PASS__PROVENANCE_PRESERVATION_EXECUTABLE_AND_MUTATION_LOAD_BEARING" if not errors else "FAIL_CLOSED",
        "pass": not errors,
        "base_cases_checked": checked,
        "mutation_results": mutation_results,
        "seed80_required_support_repaired": "SEED80_REQUIRED_UNSUPPORTED_REGRESSION" not in errors,
        "errors": errors,
        "terminal": False,
        "terminal_credit_delta": 0,
    }


if __name__ == "__main__":
    out = verify()
    print(json.dumps(out, indent=2, sort_keys=True))
    raise SystemExit(0 if out["pass"] else 1)
