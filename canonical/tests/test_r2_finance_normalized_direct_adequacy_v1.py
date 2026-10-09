from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from canonical.runtime import r2_finance_normalized_direct_adequacy_v1 as route

ROOT = Path(__file__).resolve().parents[2]
TMP = ROOT / "canonical" / "astra_runtime" / "tmp"


def _decision(evidence):
    return {
        "schema": "PROJECT_BRAIN_TYPED_DECISION_PROBLEM_V1",
        "decision_id": "finance-normalized-test",
        "question": "Which alternative is supported?",
        "alternatives": [{"id": "ALLOW", "label": "ALLOW"}],
        "constraints": [],
        "evidence": evidence,
        "policy": {
            "minimum_support_ratio": 1.0,
            "maximum_conflict_ratio": 0.0,
            "minimum_independent_support_groups": len(evidence),
            "minimum_net_margin": 0.0,
        },
    }


def _evidence(source_id, rid, eid, claim):
    return {
        "id": eid,
        "alternative": "ALLOW",
        "relation": "SUPPORTS",
        "confidence": 1.0,
        "strength": 1.0,
        "independence_group": rid,
        "claim": claim,
        "provenance": [{"source": source_id, "ref": rid}],
    }


def _supervisory_package():
    sid = "normalized-finance-rules-v1"
    rows = {
        "rules": [
            {"id": "rule-1", "claim": "Rule R1 applies.", "evidence_id": "e-rule"}
        ],
        "facts": [
            {"id": "fact-1", "claim": "Entity is in scope.", "evidence_id": "e-fact"}
        ],
        "exceptions": [
            {"id": "exception-1", "claim": "No exception applies.", "evidence_id": "e-ex"}
        ],
        "escalations": [
            {"id": "escalation-1", "claim": "No escalation required.", "evidence_id": "e-esc"}
        ],
        "disclosures": [
            {"id": "disclosure-1", "claim": "Disclosure D1 is required.", "evidence_id": "e-disc"}
        ],
        "ambiguities": [],
    }
    evidence = [
        _evidence(sid, "rule-1", "e-rule", "Rule R1 applies."),
        _evidence(sid, "fact-1", "e-fact", "Entity is in scope."),
        _evidence(sid, "exception-1", "e-ex", "No exception applies."),
        _evidence(sid, "escalation-1", "e-esc", "No escalation required."),
        _evidence(sid, "disclosure-1", "e-disc", "Disclosure D1 is required."),
    ]
    return {
        "schema": "PROJECT_BRAIN_FINANCE_NORMALIZED_DECISION_PACKAGE_V1",
        "leaf_id": "SUPERVISORY_AND_COMPLIANCE_NUANCE_OUTSIDE_PUBLIC_BAR_SCOPE",
        "source_mode": "AUTHORITATIVE_NORMALIZED_RULES",
        "source_id": sid,
        "source_universe": rows,
        "decision_problem": _decision(evidence),
    }


def _document_package():
    sid = "frozen-structured-document-v1"
    rows = {
        "facts": [
            {"id": "fact-1", "claim": "Revenue is 10.", "evidence_id": "e-fact"}
        ],
        "cross_references": [
            {"id": "xref-1", "claim": "Note 2 supports revenue.", "evidence_id": "e-xref"}
        ],
        "contradictions": [
            {"id": "contradiction-1", "claim": "No contradiction remains.", "evidence_id": "e-con"}
        ],
        "exceptions": [
            {"id": "exception-1", "claim": "No material exception remains.", "evidence_id": "e-ex"}
        ],
        "reconciliations": [
            {
                "id": "rec-1",
                "claim": "Revenue reconciles exactly.",
                "evidence_id": "e-rec",
                "lhs": "10.00",
                "rhs": "10",
                "tolerance": "0",
            }
        ],
        "ambiguities": [],
    }
    evidence = [
        _evidence(sid, "fact-1", "e-fact", "Revenue is 10."),
        _evidence(sid, "xref-1", "e-xref", "Note 2 supports revenue."),
        _evidence(sid, "contradiction-1", "e-con", "No contradiction remains."),
        _evidence(sid, "exception-1", "e-ex", "No material exception remains."),
        _evidence(sid, "rec-1", "e-rec", "Revenue reconciles exactly."),
    ]
    return {
        "schema": "PROJECT_BRAIN_FINANCE_NORMALIZED_DECISION_PACKAGE_V1",
        "leaf_id": "DOCUMENT_SPECIFIC_ANALYSIS_LEAVES_OUTSIDE_PUBLIC_BAR_SCOPE",
        "source_mode": "FROZEN_STRUCTURED_DOCUMENT",
        "source_id": sid,
        "source_universe": rows,
        "decision_problem": _decision(evidence),
    }


def _write(path, doc):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _request(input_path, output_path):
    return {
        "task_id": "finance-normalized-direct-test",
        "goal": (
            "From the authoritative normalized finance package at "
            + input_path.relative_to(ROOT).as_posix()
            + ", synthesize and independently verify the finance decision and save it to "
            + output_path.relative_to(ROOT).as_posix()
            + "."
        ),
    }


def test_supervisory_authoritative_normalized_package_passes():
    TMP.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=TMP) as td:
        work = Path(td)
        src = work / "package.json"
        out = work / "decision.json"
        _write(src, _supervisory_package())
        result = route.run(_request(src, out), repo_root=ROOT)
        assert result["pass"] is True, result
        assert result["direct_adequacy_authority"] is True
        assert result["acceptance_receipt"]["producer_independent"] is True
        assert result["leaf_id"].startswith("SUPERVISORY")
        assert out.is_file()


def test_document_structured_package_with_exact_reconciliation_passes():
    TMP.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=TMP) as td:
        work = Path(td)
        src = work / "package.json"
        out = work / "decision.json"
        _write(src, _document_package())
        result = route.run(_request(src, out), repo_root=ROOT)
        assert result["pass"] is True, result
        assert result["acceptance_receipt"]["source_record_count"] == 5


def test_omitted_source_record_evidence_fails_closed_and_rolls_back():
    TMP.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=TMP) as td:
        work = Path(td)
        src = work / "package.json"
        out = work / "decision.json"
        old = b"old-output\n"
        out.write_bytes(old)
        package = _supervisory_package()
        package["decision_problem"]["evidence"] = package["decision_problem"]["evidence"][:-1]
        _write(src, package)
        result = route.run(_request(src, out), repo_root=ROOT)
        assert result["pass"] is False
        assert result["rollback_complete"] is True
        assert out.read_bytes() == old
        assert "SOURCE_TO_DECISION_EVIDENCE_SET_MISMATCH" in result["reason"]


def test_unresolved_ambiguity_fails_closed():
    TMP.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=TMP) as td:
        work = Path(td)
        src = work / "package.json"
        out = work / "decision.json"
        package = _supervisory_package()
        package["source_universe"]["ambiguities"] = [
            {"id": "amb-1", "claim": "Scope could mean A or B.", "evidence_id": ""}
        ]
        _write(src, package)
        result = route.run(_request(src, out), repo_root=ROOT)
        assert result["pass"] is False
        assert "UNRESOLVED_AMBIGUITY_PRESENT" in result["reason"]


def test_claim_or_provenance_mismatch_fails_closed():
    TMP.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=TMP) as td:
        work = Path(td)
        src = work / "package.json"
        out = work / "decision.json"
        package = _supervisory_package()
        package["decision_problem"]["evidence"][0]["claim"] = "Different claim."
        package["decision_problem"]["evidence"][1]["provenance"] = [
            {"source": package["source_id"], "ref": "wrong"}
        ]
        _write(src, package)
        result = route.run(_request(src, out), repo_root=ROOT)
        assert result["pass"] is False
        assert (
            "SOURCE_CLAIM_DECISION_CLAIM_MISMATCH" in result["reason"]
            or "SOURCE_PROVENANCE_BINDING_MISSING" in result["reason"]
        )


def test_failed_reconciliation_fails_closed():
    TMP.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=TMP) as td:
        work = Path(td)
        src = work / "package.json"
        out = work / "decision.json"
        package = _document_package()
        package["source_universe"]["reconciliations"][0]["rhs"] = "11"
        _write(src, package)
        result = route.run(_request(src, out), repo_root=ROOT)
        assert result["pass"] is False
        assert "RECONCILIATION_FAILED" in result["reason"]
