from __future__ import annotations

import hashlib
import json
from pathlib import Path

from canonical.runtime import r2_finance_normalized_decision_direct_adequacy_v1 as d


def _dump(path: Path, value) -> bytes:
    raw = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return raw


def _git_blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def _problem():
    return {
        "schema": "PROJECT_BRAIN_TYPED_DECISION_PROBLEM_V1",
        "decision_id": "finance-d1",
        "question": "Which finance policy?",
        "alternatives": [{"id": "APPLY", "label": "Apply"}, {"id": "ABSTAIN", "label": "Abstain"}],
        "constraints": [],
        "evidence": [
            {
                "id": "rule",
                "alternative": "APPLY",
                "relation": "SUPPORTS",
                "confidence": 1.0,
                "strength": 1.0,
                "independence_group": "rule-g",
                "claim": "authoritative normalized rule",
                "provenance": [{"source": "normalized-package", "ref": "rule-1"}],
            },
            {
                "id": "exception",
                "alternative": "APPLY",
                "relation": "SUPPORTS",
                "confidence": 1.0,
                "strength": 1.0,
                "independence_group": "exception-g",
                "claim": "authoritative normalized exception state",
                "provenance": [{"source": "normalized-package", "ref": "exception-1"}],
            },
        ],
        "policy": {
            "minimum_support_ratio": 0.6,
            "maximum_conflict_ratio": 0.5,
            "minimum_independent_support_groups": 1,
            "minimum_net_margin": 0.1,
        },
    }


def _goal(
    package="canonical/tmp/finance_package.json",
    output="canonical/tmp/finance_result.json",
):
    return (
        f"Using the authorized normalized finance decision package at {package}, "
        f"synthesize the verified finance decision and save it to {output}."
    )


def _fixture(root: Path, *, extra_unbound_evidence: bool = False):
    decision_rel = "canonical/tmp/decision.json"
    package_rel = "canonical/tmp/finance_package.json"
    authority_rel = "canonical/tmp/finance_authority.json"
    verification_rel = "canonical/tmp/finance_authority_verify.json"

    problem = _problem()
    if extra_unbound_evidence:
        problem["evidence"].append(
            {
                "id": "hidden-extra",
                "alternative": "APPLY",
                "relation": "SUPPORTS",
                "confidence": 1.0,
                "strength": 1.0,
                "independence_group": "extra-g",
                "claim": "unbound",
                "provenance": [{"source": "bad", "ref": "x"}],
            }
        )
    decision_raw = _dump(root / decision_rel, problem)
    package = {
        "schema": d.PACKAGE_SCHEMA,
        "package_id": "finance-p1",
        "leaf_id": d.FINANCE_SUPERVISORY,
        "decision_problem_path": decision_rel,
        "decision_problem_sha256": hashlib.sha256(decision_raw).hexdigest(),
        "source_items": [
            {"id": "rule-1", "role": "RULE", "evidence_ids": ["rule"]},
            {"id": "exception-1", "role": "EXCEPTION", "evidence_ids": ["exception"]},
        ],
        "reconciliation_checks": [{"id": "r1", "lhs": "10.00", "rhs": "10.0", "tolerance": "0"}],
        "authorization_binding": {
            "authority_path": authority_rel,
            "verification_path": verification_rel,
        },
    }
    package_raw = _dump(root / package_rel, package)
    package_sha = hashlib.sha256(package_raw).hexdigest()
    authority = {
        "schema": d.AUTHORITY_SCHEMA,
        "status": "ACTIVE",
        "authority_id": "test-authority",
        "package_path": package_rel,
        "package_sha256": package_sha,
        "leaf_ids": [d.FINANCE_SUPERVISORY],
        "complete_source_universe": True,
        "normalized_semantics_authoritative": True,
    }
    authority_raw = _dump(root / authority_rel, authority)
    verification = {
        "schema": d.VERIFY_SCHEMA,
        "pass": True,
        "subject_git_blob_sha": _git_blob(authority_raw),
        "package_sha256": package_sha,
        "verified_leaf_ids": [d.FINANCE_SUPERVISORY],
        "complete_source_universe_verified": True,
        "normalized_semantics_authoritative_verified": True,
    }
    _dump(root / verification_rel, verification)
    return package_rel


def test_preflight_accepts_only_content_addressed_authorized_package(tmp_path: Path):
    _fixture(tmp_path)
    out = d.preflight({"task_id": "t1", "goal": _goal()}, repo_root=tmp_path)
    assert out["matched"] is True, out
    assert out["status"] == "DIRECT_ADEQUACY_ROUTE_MATCHED"
    assert out["preflight_execution_authority"] is False
    assert out["leaf_id"] == d.FINANCE_SUPERVISORY
    assert out["source_evidence_ids"] == ["exception", "rule"]


def test_run_recomputes_decision_and_requires_all_source_evidence_to_contribute(tmp_path: Path):
    _fixture(tmp_path)
    out = d.run({"task_id": "t1", "goal": _goal()}, repo_root=tmp_path)
    assert out["pass"] is True, out
    assert out["semantic_acceptance_complete"] is True
    assert out["actual_goal_satisfaction_verified"] is True
    assert out["direct_adequacy_authority"] is True
    assert out["complete_source_to_contributing_evidence_coverage"] is True
    assert out["source_universe_authority_receipt"]["complete_source_universe_verified"] is True
    result = json.loads((tmp_path / "canonical/tmp/finance_result.json").read_text())
    assert result["status"] == "DECIDED"
    assert result["selected_alternative"] == "APPLY"


def test_unbound_decision_evidence_fails_closed_in_preflight(tmp_path: Path):
    _fixture(tmp_path, extra_unbound_evidence=True)
    out = d.preflight({"task_id": "t1", "goal": _goal()}, repo_root=tmp_path)
    assert out["pass"] is False
    assert out["status"] == "FAIL_CLOSED"
    assert "SOURCE_TO_DECISION_EVIDENCE_DOMAIN_MISMATCH" in out["reason"]


def test_authority_tamper_fails_closed(tmp_path: Path):
    _fixture(tmp_path)
    authority = tmp_path / "canonical/tmp/finance_authority.json"
    value = json.loads(authority.read_text())
    value["complete_source_universe"] = False
    _dump(authority, value)
    out = d.preflight({"task_id": "t1", "goal": _goal()}, repo_root=tmp_path)
    assert out["pass"] is False
    assert out["status"] == "FAIL_CLOSED"
    assert "SOURCE_UNIVERSE_COMPLETENESS_NOT_AUTHORIZED" in out["reason"] or "SOURCE_UNIVERSE_VERIFICATION_SUBJECT_MISMATCH" in out["reason"]


def test_noncontributing_source_item_rolls_back(monkeypatch, tmp_path: Path):
    _fixture(tmp_path)
    output = tmp_path / "canonical/tmp/finance_result.json"
    output.write_text('{"old":true}\n', encoding="utf-8")
    old = output.read_bytes()

    original = d.producer.run

    def patched(args, root):
        result = original(args, root)
        path = Path(root) / args["output_path"]
        doc = json.loads(path.read_text())
        selected = doc["selected_alternative"]
        for row in doc["rankings"]:
            if row["alternative"] == selected:
                row["contributing_evidence"] = ["rule"]
        path.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n")
        return result

    monkeypatch.setattr(d.producer, "run", patched)
    monkeypatch.setattr(
        d.verifier,
        "run",
        lambda args, root: {
            "verified": True,
            "reason": "forced-for-source-coverage-test",
            "producer_independent": True,
            "model_dependency_count": 0,
        },
    )
    out = d.run({"task_id": "t1", "goal": _goal()}, repo_root=tmp_path)
    assert out["pass"] is False, out
    assert out["rollback_complete"] is True
    assert output.read_bytes() == old
    assert "NOT_ALL_AUTHORIZED_SOURCE_EVIDENCE_CONTRIBUTES" in out["reason"]


def test_nonmatching_goal_claims_no_scope(tmp_path: Path):
    out = d.preflight({"task_id": "t1", "goal": "Analyze finance."}, repo_root=tmp_path)
    assert out["matched"] is False
    assert out["pass"] is False
