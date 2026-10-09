from __future__ import annotations

import json

from canonical.runtime import sec_issuer_extension_cross_filing_stability_v1 as pairwise
from canonical.runtime import sec_issuer_extension_cross_filing_stability_v2 as group
from canonical.tests.test_sec_issuer_extension_cross_filing_stability_v1 import (
    DOC,
    LOCAL,
    make,
)


def members(*rows):
    return [
        {
            "xsd_path": row["xsd"],
            "label_path": row["label"],
            "semantic_path": row["semantic"],
        }
        for row in rows
    ]


def test_three_stable_filings_are_proved_in_one_certificate(tmp_path):
    a = make(tmp_path, "a", accession="000032019323000077", date="20230930")
    b = make(tmp_path, "b", accession="000032019324000123", date="20240928")
    c = make(tmp_path, "c", accession="000032019325000079", date="20250927")
    out = group.verify_group(root=tmp_path, members=members(a, b, c))
    assert out["pass"] is True, out
    assert out["bounded_group_semantic_contract_stable"] is True
    assert out["bounded_group_semantic_stability_authority"] is True
    assert out["member_count"] == 3
    assert len(out["filing_directories"]) == 3
    assert len(set(out["filing_directories"])) == 3
    assert out["relation"] == (
        "SAME_BRAIN_OWNED_SEMANTIC_CONTRACT_ACROSS_BOUNDED_FILING_SET"
    )
    assert len(out["stability_receipt_sha256"]) == 64


def test_group_equality_agrees_with_pairwise_v1_on_two_members(tmp_path):
    a = make(tmp_path, "a", accession="000032019324000123", date="20240928")
    b = make(tmp_path, "b", accession="000032019325000079", date="20250927")
    p = pairwise.verify_pair(
        root=tmp_path,
        left_xsd_path=a["xsd"],
        left_label_path=a["label"],
        left_semantic_path=a["semantic"],
        right_xsd_path=b["xsd"],
        right_label_path=b["label"],
        right_semantic_path=b["semantic"],
    )
    g = group.verify_group(root=tmp_path, members=members(a, b))
    assert p["pass"] is True and p["cross_filing_semantic_contract_stable"] is True
    assert g["pass"] is True and g["bounded_group_semantic_contract_stable"] is True
    assert g["semantic_signature"] == p["semantic_signature"]


def test_one_drifting_filing_yields_exact_signature_partition(tmp_path):
    a = make(tmp_path, "a", accession="000032019323000077", date="20230930")
    b = make(tmp_path, "b", accession="000032019324000123", date="20240928")
    c = make(
        tmp_path,
        "c",
        accession="000032019325000079",
        date="20250927",
        doc=DOC + " Changed.",
    )
    out = group.verify_group(root=tmp_path, members=members(a, b, c))
    assert out["pass"] is True, out
    assert out["bounded_group_semantic_contract_stable"] is False
    assert out["signature_partition_count"] == 2
    sizes = sorted(len(row["member_indexes"]) for row in out["signature_partitions"])
    assert sizes == [1, 2]
    assert "documentation_label" in out["differing_fields"]
    assert out["relation"] == "SEMANTIC_CONTRACT_DIFFERS_WITHIN_BOUNDED_FILING_SET"


def test_cross_issuer_group_fails_closed(tmp_path):
    a = make(tmp_path, "a", accession="000032019324000123", date="20240928")
    b = make(
        tmp_path,
        "b",
        cik="789019",
        accession="000078901925000001",
        date="20250927",
    )
    out = group.verify_group(root=tmp_path, members=members(a, b))
    assert out["pass"] is False
    assert out["reason"] == "CROSS_ISSUER_GROUP_FORBIDDEN"


def test_duplicate_filing_directory_fails_closed(tmp_path):
    a = make(tmp_path, "a", accession="000032019324000123", date="20240928")
    b = make(tmp_path, "b", accession="000032019324000123", date="20240928")
    out = group.verify_group(root=tmp_path, members=members(a, b))
    assert out["pass"] is False
    assert out["reason"] == "DISTINCT_FILING_DIRECTORIES_REQUIRED"


def test_local_name_mismatch_fails_closed(tmp_path):
    a = make(tmp_path, "a", accession="000032019324000123", date="20240928")
    b = make(
        tmp_path,
        "b",
        accession="000032019325000079",
        date="20250927",
        local="OtherConcept",
    )
    out = group.verify_group(root=tmp_path, members=members(a, b))
    assert out["pass"] is False
    assert out["reason"] == "LOCAL_NAME_MISMATCH"


def test_tampered_semantic_member_cannot_mint_group_stability(tmp_path):
    a = make(tmp_path, "a", accession="000032019323000077", date="20230930")
    b = make(tmp_path, "b", accession="000032019324000123", date="20240928")
    c = make(tmp_path, "c", accession="000032019325000079", date="20250927")
    path = tmp_path / c["semantic"]
    obj = json.loads(path.read_text(encoding="utf-8"))
    obj["documentation_label"] = "invented"
    path.write_text(json.dumps(obj), encoding="utf-8")
    out = group.verify_group(root=tmp_path, members=members(a, b, c))
    assert out["pass"] is False
    assert out["reason"] == "UPSTREAM_CONCEPT_SEMANTICS_REDERIVATION_FAILED"


def test_member_count_is_bounded_without_touching_files(tmp_path):
    one = group.verify_group(root=tmp_path, members=[{}])
    assert one["pass"] is False
    assert one["reason"] == "MEMBER_COUNT_OUT_OF_BOUNDS"

    many = group.verify_group(
        root=tmp_path,
        members=[{} for _ in range(group.MAX_MEMBERS + 1)],
    )
    assert many["pass"] is False
    assert many["reason"] == "MEMBER_COUNT_OUT_OF_BOUNDS"


def test_group_certificate_never_escalates_identity_or_terminal_authority(tmp_path):
    a = make(tmp_path, "a", accession="000032019323000077", date="20230930")
    b = make(tmp_path, "b", accession="000032019324000123", date="20240928")
    c = make(tmp_path, "c", accession="000032019325000079", date="20250927")
    out = group.verify_group(root=tmp_path, members=members(a, b, c))
    assert out["pass"] is True, out
    assert out["concept_identity_authority"] is False
    assert out["standard_taxonomy_equivalence_authority"] is False
    assert out["future_stability_claimed"] is False
    assert out["open_world_finance_semantics_complete"] is False
    assert out["policy_adequacy_authority"] is False
    assert out["execution_authority"] is False
    assert out["acceptance_authority"] is False
    assert out["promotion_authority"] is False
    assert out["terminal_authority"] is False
    assert out["terminal_credit_delta"] == 0
