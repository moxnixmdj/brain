"""GDPval-AA Crowd-BT direct-attachment sign certificate.

Conditional theorem only. This runtime does not discover judge qualities, reproduce
Artificial Analysis' owner fit, or mint terminal credit.

Public Crowd-BT relation:
  q_k(d) = eta_k * sigma(d) + (1-eta_k) * (1-sigma(d))
where d is Brain-minus-Opus latent strength and eta_k is judge quality.

At d = 0, q_k = 1/2 for every eta_k. If eta_k >= 1/2, q_k(d) is
nondecreasing in d. Therefore, for any judge whose effective Brain wins are at
least its effective losses (ties count as half-win and half-loss), that judge's
binomial log-likelihood cannot improve by moving from d=0 into d<0. If this
holds for every judge and at least one judge is provably informative
(eta_k > 1/2 with at least one comparison), the direct Brain-vs-Opus likelihood
has no maximizer at d<0.

If Brain appears in the fitted comparison graph only through Brain-vs-Opus edges,
the full unregularized MLE factorizes after reparameterizing s_B = s_O + d:
all pre-existing graph terms are independent of d, while all new Brain terms are
in the direct likelihood. Hence the fitted Brain-minus-Opus sign is determined
by the direct attachment likelihood without reconstructing the historical graph.

Semantic premises require independent proof receipts.
"""
from __future__ import annotations

import re
from fractions import Fraction
from typing import Any, Mapping

_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


class CrowdBTSignBridgeError(ValueError):
    pass


def _f(value: Any, label: str) -> Fraction:
    if isinstance(value, bool):
        raise CrowdBTSignBridgeError(f"{label}_BOOL_FORBIDDEN")
    try:
        return Fraction(str(value))
    except Exception as exc:
        raise CrowdBTSignBridgeError(f"{label}_INVALID:{value}") from exc


def _nonnegative_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise CrowdBTSignBridgeError(f"{label}_MUST_BE_NONNEGATIVE_INT")
    return value


def _receipts(value: Any, label: str) -> list[dict[str, str]]:
    if not isinstance(value, list) or not value:
        raise CrowdBTSignBridgeError(f"{label}_RECEIPTS_REQUIRED")
    out: list[dict[str, str]] = []
    for row in value:
        if not isinstance(row, Mapping):
            raise CrowdBTSignBridgeError(f"{label}_RECEIPT_INVALID")
        path = row.get("path")
        sha = row.get("git_blob_sha")
        if not isinstance(path, str) or not path.strip():
            raise CrowdBTSignBridgeError(f"{label}_PATH_INVALID")
        if not isinstance(sha, str) or not _SHA_RE.fullmatch(sha):
            raise CrowdBTSignBridgeError(f"{label}_SHA_INVALID")
        out.append({"path": path, "git_blob_sha": sha})
    return out


def certify(task: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(task, Mapping):
        raise CrowdBTSignBridgeError("TASK_INVALID")

    crowd_bt_receipts = _receipts(task.get("crowd_bt_semantic_receipts"), "CROWD_BT")
    graph_receipts = _receipts(task.get("direct_attachment_graph_receipts"), "DIRECT_ATTACHMENT")
    mle_receipts = _receipts(task.get("mle_objective_receipts"), "MLE_OBJECTIVE")

    rows = task.get("judges")
    if not isinstance(rows, list) or not rows:
        raise CrowdBTSignBridgeError("JUDGES_REQUIRED")

    seen: set[str] = set()
    judges: list[dict[str, Any]] = []
    all_noninferior_votes = True
    informative_strict = False

    for row in rows:
        if not isinstance(row, Mapping) or not row.get("id"):
            raise CrowdBTSignBridgeError("JUDGE_ROW_INVALID")
        jid = str(row["id"])
        if jid in seen:
            raise CrowdBTSignBridgeError(f"DUPLICATE_JUDGE:{jid}")
        seen.add(jid)

        wins = _nonnegative_int(row.get("brain_wins"), f"{jid}_BRAIN_WINS")
        losses = _nonnegative_int(row.get("opus_wins"), f"{jid}_OPUS_WINS")
        ties = _nonnegative_int(row.get("ties"), f"{jid}_TIES")
        eta_lower = _f(row.get("eta_lower"), f"{jid}_ETA_LOWER")
        eta_upper = _f(row.get("eta_upper", 1), f"{jid}_ETA_UPPER")

        if eta_lower < Fraction(1, 2) or eta_upper > 1 or eta_lower > eta_upper:
            raise CrowdBTSignBridgeError(f"{jid}_ETA_BOUNDS_NOT_NONADVERSARIAL")

        # Twice the effective counts avoids floating point:
        # tie = 1/2 Brain win + 1/2 Opus win.
        brain_effective2 = 2 * wins + ties
        opus_effective2 = 2 * losses + ties
        majority_or_tie = brain_effective2 >= opus_effective2
        all_noninferior_votes = all_noninferior_votes and majority_or_tie

        total = wins + losses + ties
        if total > 0 and eta_lower > Fraction(1, 2):
            informative_strict = True

        judges.append({
            "id": jid,
            "brain_wins": wins,
            "opus_wins": losses,
            "ties": ties,
            "brain_effective_wins_x2": brain_effective2,
            "opus_effective_wins_x2": opus_effective2,
            "brain_effective_not_below_opus": majority_or_tie,
            "eta_lower": str(eta_lower),
            "eta_upper": str(eta_upper),
        })

    passed = all_noninferior_votes and informative_strict

    blockers: list[str] = []
    if not all_noninferior_votes:
        blockers.append("AT_LEAST_ONE_JUDGE_HAS_MORE_EFFECTIVE_OPUS_WINS_THAN_BRAIN_WINS")
    if not informative_strict:
        blockers.append("NO_JUDGE_IS_PROVED_STRICTLY_INFORMATIVE_ABOVE_ETA_HALF")

    return {
        "schema": "PROJECT_BRAIN_GDPVAL_CROWDBT_DIRECT_SIGN_BRIDGE_RESULT_V1",
        "status": "PASS__CONDITIONAL_DIRECT_CROWDBT_NONINFERIORITY" if passed else "UNKNOWN__PREMISES_INSUFFICIENT",
        "conditional_brain_minus_opus_mle_nonnegative": passed,
        "judges": judges,
        "blockers": blockers,
        "proof_receipts": {
            "crowd_bt_semantics": crowd_bt_receipts,
            "direct_attachment_graph": graph_receipts,
            "unregularized_mle_objective": mle_receipts,
        },
        "theorem": [
            "CROWDBT_EQUAL_STRENGTH_PREDICTS_HALF_FOR_EVERY_JUDGE_QUALITY",
            "ETA_GE_HALF_MAKES_JUDGE_PREFERENCE_PROBABILITY_NONDECREASING_IN_BRAIN_MINUS_OPUS_STRENGTH",
            "PER_JUDGE_EFFECTIVE_WINS_GE_LOSSES_IMPLIES_NO_DIRECT_LIKELIHOOD_GAIN_ANYWHERE_BELOW_EQUAL_STRENGTH",
            "DIRECT_ONLY_BRAIN_ATTACHMENT_FACTORIZES_BRAIN_MINUS_OPUS_DIFFERENCE_FROM_PREEXISTING_GRAPH_UNDER_UNREGULARIZED_MLE",
        ],
        "strictly_less_than_old_660_cell_condition": True,
        "semantic_premises_verified_by_this_runtime": False,
        "owner_exact_reproduction": False,
        "sandwich_ci_reproduced": False,
        "terminal_authority": False,
        "promotion_authority": False,
        "terminal_credit_delta": 0,
    }
