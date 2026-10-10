from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "canonical/evidence/CURSORBENCH_4_0_VENDOR_PDF_RESULT_ARTIFACT_PACKAGE_EVIDENCE_20261010_V1.json"
REDUCTION = ROOT / "canonical/governance/CURSORBENCH_4_0_VENDOR_PDF_RESULT_ARTIFACT_ROUTE_CLOSURE_20261010_V1.json"
VERIFY = ROOT / "canonical/verification/CURSORBENCH_4_0_VENDOR_PDF_RESULT_ARTIFACT_PACKAGE_INDEPENDENT_VERIFICATION_20261010_V1.json"
OWNER = ROOT / "canonical/evidence/CURSORBENCH_4_0_OWNER_AND_RESULT_ARTIFACT_AUTHORITY_EVIDENCE_20261009_V1.json"
CEILING = ROOT / "canonical/evidence/CURSORBENCH_4_0_PUBLIC_OWNER_SURFACE_CEILING_EVIDENCE_20261010_V1.json"


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    h = hashlib.sha1()
    h.update(b"blob " + str(len(data)).encode("ascii") + b"\0" + data)
    return h.hexdigest()


def test_vendor_pdf_package_route_closure_is_narrow_and_fail_safe():
    e = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    r = json.loads(REDUCTION.read_text(encoding="utf-8"))
    v = json.loads(VERIFY.read_text(encoding="utf-8"))

    assert e["prior_authority"]["owner_result_artifact_evidence"]["git_blob_sha"] == git_blob_sha(OWNER)
    assert e["prior_authority"]["public_owner_surface_ceiling"]["git_blob_sha"] == git_blob_sha(CEILING)
    assert v["subject_evidence"]["git_blob_sha"] == git_blob_sha(EVIDENCE)
    assert v["subject_reduction"]["git_blob_sha"] == git_blob_sha(REDUCTION)

    rows = {row["title"]: row for row in v["verified_exact_pdfs"]}
    assert rows["Claude Opus 5.5 System Card"]["sha256"] == "7311c9c6bbb16d012f1c12c7418b05949fcf7ae3e30d2c40f22050074b2a7378"
    assert rows["Claude Sonnet 5.5 System Card"]["sha256"] == "89cfd6a6d3aa6148eaf23f4a53006950ee7746009f381237c62920c720725785"

    for row in rows.values():
        assert row["embedded_files_name_tree_present"] is False
        assert row["embedded_attachment_count"] == 0
        assert row["file_attachment_annotation_count"] == 0
        assert row["launch_action_count"] == 0
        assert len(row["cursor_related_uris"]) == 1
        assert row["cursor_related_uris"][0]["uri"] == "https://cursor.com/cursorbench"

    assert v["result"]["pass"] is True
    assert v["result"]["vendor_pdf_package_subroute_closed_for_exact_hashes"] is True
    assert v["result"]["direct_private_cursor_result_artifact_retrieved"] is False
    assert v["result"]["route_a_scoring_object_count_closed"] == 0
    assert v["result"]["target_region_membership_created"] is False

    assert e["deduction"]["vendor_pdf_package_retrieval_route_exhausted_for_these_exact_bytes"] is True
    assert e["deduction"]["direct_cursor_result_artifact_retrieved"] is False
    assert e["deduction"]["per_task_grader_output_domain_bound"] is False
    assert e["deduction"]["aggregation_denominator_task_count_pass_count_weights_bound"] is False
    assert e["deduction"]["target_membership_for_T_F_R_S_or_V_bound"] is False

    assert r["reduction"]["rank_1_object_still_open"] is True
    assert r["reduction"]["remaining_route_a_scoring_object_count"] == 2
    assert r["reduction"]["five_region_target_membership_created"] is False
    assert r["accounting"]["acceptance_credit_delta"] == 0
    assert r["accounting"]["terminal_credit_delta"] == 0
    assert r["terminal_authority"] is False
