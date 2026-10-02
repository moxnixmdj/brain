"""Execute the verified abductive residual compiler on the matched-scope child cone."""
from __future__ import annotations
import json
from pathlib import Path

from canonical.runtime.abductive_residual_theorem_v1 import evaluate

ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "canonical/governance/MATCHED_SCOPE_ABDUCTIVE_RESIDUAL_INPUT_V1.json"


def execute() -> dict:
    doc = json.loads(INPUT.read_text(encoding="utf-8"))
    payload = {
        "targets": doc["targets"],
        "baseline_facts": doc["baseline_facts"],
        "implications": doc["implications"],
    }
    out = evaluate(payload)
    expected = doc["expected"]

    assert out["status"] == "EXACT_WEAKEST_SUFFICIENT_RESIDUALS_COMPUTED", out
    assert out["target_count"] == expected["target_count"], out
    assert out["verified_rule_count"] == expected["verified_rule_count"], out
    assert len(out["primitive_residual_facts"]) == expected["primitive_residual_fact_count"], out
    assert out["minimum_joint_residual_size"] == expected["minimum_joint_residual_size"], out
    assert len(out["shared_residual_groups"]) == expected["shared_residual_group_count"], out
    assert out["all_targets_reachable"] is expected["all_targets_reachable"], out

    for target in doc["targets"]:
        row = out["target_residuals"][target]
        assert row["reachable"] is True, (target, row)
        assert row["minimum_residual_size"] == 2, (target, row)
        assert len(row["minimum_residual_sets"]) == 1, (target, row)
        expected_pair = sorted(
            x["if_all"]
            for x in doc["implications"]
            if x["then"] == [target]
        )[0]
        assert row["minimum_residual_sets"][0] == sorted(expected_pair), (target, row)

    assert out["capability_credit_delta"] == 0
    assert out["family_credit_delta"] == 0
    assert out["execution_authority"] is False
    assert out["promotion_authority"] is False
    return out


def main() -> int:
    print(json.dumps(execute(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
