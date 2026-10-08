"""Direct head-to-head Crowd-BT sign certificate.

For a frozen set of Brain-vs-Target comparisons partitioned by judge, suppose:
  * every judge quality eta_j is independently proved to satisfy eta_j > 1/2,
  * ties are counted as half-wins,
  * each judge has Brain wins >= Brain losses.

Then every maximum-likelihood optimum of the direct Crowd-BT latent strength
difference has Brain >= Target. This does not reproduce a full owner leaderboard Elo.

Proof sketch:
For z > 0, let p_j(z) be judge j's probability of preferring Brain.
Crowd-BT gives p_j(-z)=1-p_j(z). Therefore
  L(z)-L(-z) = sum_j (wins_j-losses_j) * logit(p_j(z)).
When eta_j > 1/2, logit(p_j(z)) > 0 for z > 0. If every margin is nonnegative,
L(z) >= L(-z), so no negative optimum can dominate its reflected positive point.
If all margins are zero, the likelihood is symmetric and maximized at z=0.
"""
from __future__ import annotations

from fractions import Fraction
from typing import Any, Mapping


class DirectCrowdBTError(ValueError):
    pass


def _int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise DirectCrowdBTError(f"{label}_MUST_BE_NONNEGATIVE_INTEGER")
    return value


def certify(task: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(task, Mapping):
        raise DirectCrowdBTError("TASK_INVALID")

    rows = task.get("judges")
    if not isinstance(rows, list) or not rows:
        raise DirectCrowdBTError("JUDGES_REQUIRED")

    seen = set()
    parsed = []
    for row in rows:
        if not isinstance(row, Mapping) or not row.get("id"):
            raise DirectCrowdBTError("JUDGE_ROW_INVALID")
        jid = str(row["id"])
        if jid in seen:
            raise DirectCrowdBTError(f"DUPLICATE_JUDGE:{jid}")
        seen.add(jid)

        wins = _int(row.get("wins"), f"{jid}_WINS")
        ties = _int(row.get("ties"), f"{jid}_TIES")
        losses = _int(row.get("losses"), f"{jid}_LOSSES")
        expected = row.get("expected_comparisons")
        if expected is not None:
            expected = _int(expected, f"{jid}_EXPECTED_COMPARISONS")
            if wins + ties + losses != expected:
                raise DirectCrowdBTError(f"{jid}_COMPARISON_COUNT_MISMATCH")

        receipt = row.get("quality_gt_half_receipt")
        if not isinstance(receipt, Mapping):
            raise DirectCrowdBTError(f"{jid}_QUALITY_GT_HALF_RECEIPT_REQUIRED")
        path = receipt.get("path")
        sha = receipt.get("git_blob_sha")
        if not isinstance(path, str) or not path.strip() or not isinstance(sha, str) or len(sha) != 40:
            raise DirectCrowdBTError(f"{jid}_QUALITY_GT_HALF_RECEIPT_INVALID")

        parsed.append({
            "id": jid,
            "wins": wins,
            "ties": ties,
            "losses": losses,
            "margin": wins - losses,
            "quality_gt_half_receipt": {"path": path, "git_blob_sha": sha},
        })

    noninferior = all(r["margin"] >= 0 for r in parsed)
    strict = noninferior and any(r["margin"] > 0 for r in parsed)

    return {
        "schema": "PROJECT_BRAIN_DIRECT_CROWD_BT_MARGIN_CERTIFICATE_V1",
        "status": (
            "PASS__DIRECT_CROWD_BT_NONINFERIOR"
            if noninferior
            else "FAIL_CLOSED__PER_JUDGE_MARGIN_NEGATIVE"
        ),
        "conditional_noninferiority": noninferior,
        "strict_positive_direction": strict,
        "judge_summary": parsed,
        "theorem": (
            "IF_EACH_BOUND_JUDGE_HAS_ETA_GT_HALF_AND_BRAIN_WINS_GE_LOSSES_FOR_EACH_JUDGE_"
            "THEN_DIRECT_BRAIN_MINUS_TARGET_CROWD_BT_MLE_STRENGTH_DIFFERENCE_IS_NONNEGATIVE"
        ),
        "ties_count_as_half_wins": True,
        "owner_exact_elo_reproduction": False,
        "semantic_premise_verified_by_this_runtime": False,
        "hard_nonclaims": [
            "Does not prove the supplied eta>1/2 receipts are semantically valid.",
            "Does not reproduce Artificial Analysis historical graph, active sampling, or official Elo.",
            "Does not establish judge-prompt or submission-presentation equivalence.",
            "Does not by itself prove scope completeness of the comparison set.",
        ],
        "terminal_authority": False,
        "promotion_authority": False,
        "terminal_credit_delta": 0,
    }
