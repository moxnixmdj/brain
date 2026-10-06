from __future__ import annotations

from typing import Any, Mapping

from canonical.runtime.terminal_frontier_factorizer_v2 import factorize

EXPECTED_DELETED = {
    "COMPOSITION_COMPONENT_SCOPED_PROOFS",
    "ARTIFACT_AA_BRIEFCASE_GE_1822",
}
EXPECTED_ALIASES = {
    "PROFESSIONAL_KNOWLEDGE_WORK": "PROWORK_AA_BRIEFCASE_GE_1822",
    "ARTIFACT_CREATION": "PROWORK_AA_BRIEFCASE_GE_1822",
}
EXPECTED_ROUTES = {"J": 0, "G": 0, "T": 0, "D": 15, "U": 15}


class Current30Error(ValueError):
    pass


def verify(
    coverage: Mapping[str, Any],
    aa_truth_repair: Mapping[str, Any],
    aa_verification: Mapping[str, Any],
) -> dict[str, Any]:
    f = factorize()
    if f["atomic_count"] != 22 or f["meta_count"] != 8 or f["truth_obligation_count"] != 30:
        raise Current30Error("FACTORIZER_COUNT_MISMATCH")
    if set(f["deleted_nonnecessary"]) != EXPECTED_DELETED:
        raise Current30Error("FACTORIZER_DELETION_SET_MISMATCH")
    if f["family_truth_aliases"] != EXPECTED_ALIASES:
        raise Current30Error("FACTORIZER_FAMILY_ALIAS_MISMATCH")
    if f["truth_obligations_deleted"] != 2:
        raise Current30Error("FACTORIZER_DELETION_COUNT_MISMATCH")

    if coverage.get("schema") != "PROJECT_BRAIN_CURRENT_TERMINAL_COVERAGE_PARTITION_V3":
        raise Current30Error("COVERAGE_SCHEMA_INVALID")
    pred = coverage.get("predecessor")
    if not isinstance(pred, Mapping) or pred.get("git_blob_sha") != "436af64fcbf233c38f85eb4815526f52e847c1f9":
        raise Current30Error("V2_PREDECESSOR_SHA_MISMATCH")

    projection = coverage.get("projection")
    if not isinstance(projection, Mapping):
        raise Current30Error("PROJECTION_REQUIRED")
    if projection.get("truth_obligations") != 30:
        raise Current30Error("OPEN_TRUTH_COUNT_MISMATCH")
    if projection.get("load_bearing_atomic_open") != 22 or projection.get("meta_open") != 8:
        raise Current30Error("ATOMIC_META_COUNT_MISMATCH")
    if projection.get("route_counts") != EXPECTED_ROUTES:
        raise Current30Error("ROUTE_COUNTS_MISMATCH")
    if sum(EXPECTED_ROUTES.values()) != 30:
        raise Current30Error("ROUTE_SUM_INTERNAL_ERROR")
    if projection.get("truth_obligations_deleted") != 2:
        raise Current30Error("DELETION_COUNT_MISMATCH")
    if projection.get("terminal") is not False:
        raise Current30Error("TERMINAL_MUST_REMAIN_FALSE")

    repairs = coverage.get("truth_repairs")
    if not isinstance(repairs, list):
        raise Current30Error("TRUTH_REPAIRS_REQUIRED")
    ids = {row.get("id") for row in repairs if isinstance(row, Mapping)}
    if ids != EXPECTED_DELETED:
        raise Current30Error("TRUTH_REPAIR_SET_MISMATCH")

    aliases = coverage.get("family_truth_aliases")
    if aliases != EXPECTED_ALIASES:
        raise Current30Error("COVERAGE_FAMILY_ALIAS_MISMATCH")

    root = coverage.get("root_cause_touching")
    if not isinstance(root, Mapping):
        raise Current30Error("ROOT_COUNTS_REQUIRED")
    if root.get("root1_positive_gap_count") != 0:
        raise Current30Error("ROOT1_DRIFT")
    if root.get("root2_touching_count") != 17:
        raise Current30Error("ROOT2_COUNT_MISMATCH")
    if root.get("root3_touching_count") != 8:
        raise Current30Error("ROOT3_COUNT_MISMATCH")

    if aa_truth_repair.get("schema") != "PROJECT_BRAIN_AA_BRIEFCASE_DUPLICATE_TRUTH_NECESSITY_COUNTERMODEL_V1":
        raise Current30Error("AA_TRUTH_REPAIR_MISSING")
    candidate = aa_truth_repair.get("candidate_repair")
    if not isinstance(candidate, Mapping):
        raise Current30Error("AA_CANDIDATE_REPAIR_MISSING")
    if candidate.get("delete_from_current_load_bearing_truth_count") != "ARTIFACT_AA_BRIEFCASE_GE_1822":
        raise Current30Error("AA_DELETE_TARGET_DRIFT")
    if candidate.get("family_truth_aliases") != EXPECTED_ALIASES:
        raise Current30Error("AA_ALIAS_DRIFT")

    if aa_verification.get("schema") != "PROJECT_BRAIN_AA_BRIEFCASE_DUPLICATE_TRUTH_SPRITE_VERIFICATION_V1":
        raise Current30Error("AA_INDEPENDENT_VERIFICATION_MISSING")
    if "PASS" not in str(aa_verification.get("status")):
        raise Current30Error("AA_INDEPENDENT_VERIFICATION_NOT_PASS")

    accounting = coverage.get("accounting")
    if not isinstance(accounting, Mapping):
        raise Current30Error("ACCOUNTING_REQUIRED")
    for key in (
        "terminal_credit_delta",
        "acceptance_credit_delta",
        "family_credit_delta",
        "capability_credit_delta",
        "ownership_credit_delta",
    ):
        if accounting.get(key) != 0:
            raise Current30Error("CREDIT_INFLATION:" + key)

    return {
        "status": "PASS__30_CURRENT_OPEN_TRUTHS__22_ATOMIC_PLUS_8_META__D15_U15__TWO_VERIFIED_NECESSITY_DELETIONS__ZERO_CREDIT",
        "open_truth_obligations": 30,
        "load_bearing_atomic_open": 22,
        "meta_open": 8,
        "deleted_nonnecessary": sorted(EXPECTED_DELETED),
        "route_counts": EXPECTED_ROUTES,
        "root2_touching_count": 17,
        "root3_touching_count": 8,
        "terminal": False,
        "terminal_credit_delta": 0,
    }
