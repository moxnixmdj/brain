import hashlib
import json

from canonical.runtime.effect_broker_receipt_resolver_v2 import git_blob_id
from canonical.runtime.lossless_raw_task_contract_v1 import compile_contract
from canonical.runtime.lossless_raw_task_acceptance_gate_v1 import (
    RECEIPT_SCHEMA,
    VERIFY_SCHEMA,
    evaluate,
    verify,
)


def canon(x):
    return json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def write_json(root, rel, doc):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    raw = canon(doc).encode()
    p.write_bytes(raw)
    return {"path": rel, "git_blob_sha": git_blob_id(raw, object_format="sha1")}


def contract():
    return compile_contract(
        "Create a PDF. It must be under 1 MB.",
        source_id="user",
        routing_target_effects=["pdf.created"],
    )


def pair(root, c, row, candidate, *, suffix):
    rd = {
        "schema": RECEIPT_SCHEMA,
        "task_contract_sha256": c["task_contract_sha256"],
        "task_sha256": c["task_sha256"],
        "obligation_id": row["obligation_id"],
        "segment_sha256": row["segment_sha256"],
        "candidate_sha256": candidate,
        "verifier_class": "DETERMINISTIC",
        "verifier_id": "test-verifier",
        "accepted": True,
    }
    rr = write_json(root, f"canonical/verification/r-{suffix}.json", rd)
    vd = {
        "schema": VERIFY_SCHEMA,
        "subject_git_blob_sha": rr["git_blob_sha"],
        "task_contract_sha256": c["task_contract_sha256"],
        "task_sha256": c["task_sha256"],
        "obligation_id": row["obligation_id"],
        "segment_sha256": row["segment_sha256"],
        "candidate_sha256": candidate,
        "verifier_class": "DETERMINISTIC",
        "verifier_id": "test-verifier",
        "accepted": True,
        "pass": True,
        "independent_verified": True,
        "acceptance_semantics_verified": True,
        "independent_verifier_id": "independent-test",
    }
    vr = write_json(root, f"canonical/verification/v-{suffix}.json", vd)
    return {"receipt": rr, "verification": vr}


def test_complete_consistent_claims_remain_unresolved_without_authenticated_verifiers(tmp_path):
    c = contract()
    candidate = hashlib.sha256(b"candidate").hexdigest()
    rows = c["acceptance_contract"]["obligations"]
    refs = [pair(tmp_path, c, row, candidate, suffix=str(i)) for i, row in enumerate(rows)]
    out = evaluate(c, candidate_sha256=candidate, obligation_receipts=refs, repo_root=tmp_path)
    assert out["pass"] is False, out
    assert out["status"] == "UNRESOLVED__INDEPENDENT_ACCEPTANCE_NOT_AUTHENTICATED"
    assert out["accepted_obligation_count"] == 0
    assert out["accepted_obligations"] == []
    assert out["structurally_consistent_receipt_count"] == len(rows)
    assert out["routing_effects_were_acceptance_authority"] is False
    verdict = verify({"task_contract": c, "candidate_sha256": candidate, "repo_root": tmp_path},
                     {"obligation_receipts": refs})
    assert verdict["pass"] is False
    assert verdict["status"] == "NEED_MORE_INFORMATION"
    assert verdict["verified_output"] is None


def test_missing_constraint_obligation_stays_unresolved(tmp_path):
    c = contract()
    candidate = hashlib.sha256(b"candidate").hexdigest()
    rows = c["acceptance_contract"]["obligations"]
    refs = [pair(tmp_path, c, rows[0], candidate, suffix="0")]
    out = evaluate(c, candidate_sha256=candidate, obligation_receipts=refs, repo_root=tmp_path)
    assert out["pass"] is False
    assert out["status"] == "UNRESOLVED__RAW_TASK_ACCEPTANCE_OBLIGATIONS_MISSING"
    assert rows[1]["obligation_id"] in out["missing_obligation_ids"]


def test_receipt_for_different_candidate_cannot_accept_this_candidate(tmp_path):
    c = contract()
    good_candidate = hashlib.sha256(b"candidate").hexdigest()
    other_candidate = hashlib.sha256(b"other").hexdigest()
    rows = c["acceptance_contract"]["obligations"]
    refs = [
        pair(tmp_path, c, row, other_candidate, suffix=str(i))
        for i, row in enumerate(rows)
    ]
    out = evaluate(c, candidate_sha256=good_candidate, obligation_receipts=refs, repo_root=tmp_path)
    assert out["pass"] is False
    assert any("CANDIDATE" in e.upper() for e in out["errors"])


def test_duplicate_obligation_receipt_fails_closed(tmp_path):
    c = contract()
    candidate = hashlib.sha256(b"candidate").hexdigest()
    row = c["acceptance_contract"]["obligations"][0]
    ref = pair(tmp_path, c, row, candidate, suffix="x")
    out = evaluate(c, candidate_sha256=candidate, obligation_receipts=[ref, ref], repo_root=tmp_path)
    assert out["pass"] is False
    assert any("DUPLICATE_ACCEPTANCE_RECEIPT" in e for e in out["errors"])


def test_independent_verification_must_bind_exact_receipt(tmp_path):
    c = contract()
    candidate = hashlib.sha256(b"candidate").hexdigest()
    row = c["acceptance_contract"]["obligations"][0]
    ref = pair(tmp_path, c, row, candidate, suffix="x")
    # Point verification at an unrelated but structurally valid receipt blob.
    wrong = write_json(tmp_path, "canonical/verification/wrong.json", {
        "schema": RECEIPT_SCHEMA,
        "task_contract_sha256": c["task_contract_sha256"],
        "task_sha256": c["task_sha256"],
        "obligation_id": row["obligation_id"],
        "segment_sha256": row["segment_sha256"],
        "candidate_sha256": candidate,
        "verifier_class": "DETERMINISTIC",
        "verifier_id": "other",
        "accepted": True,
    })
    ref["receipt"] = wrong
    out = evaluate(c, candidate_sha256=candidate, obligation_receipts=[ref], repo_root=tmp_path)
    assert out["pass"] is False
    assert any("ACCEPTANCE_VERIFY_SUBJECT_MISMATCH" in e for e in out["errors"])
