from __future__ import annotations

import copy
import hashlib

from canonical.runtime.finance_proof_carrying_source_gate_v1 import (
    configured_finance_terminal_decision,
    verify_source_semantic_coverage,
)
from canonical.runtime.source_contract_compiler import atomize_source, semantic_unit_id


TEXT = "Rule A must apply.\nException B must be preserved.\n"
SOURCE = "finance-test"


def bundle():
    atoms = atomize_source(TEXT, SOURCE)
    assert len(atoms) == 2
    units = []
    dispositions = []
    requirements = []
    manifest_rows = []
    for i, atom in enumerate(atoms, 1):
        sid = semantic_unit_id(atom.atom_id, 0, len(atom.text))
        rid = f"R{i}"
        eid = f"E{i}"
        unit = {
            "atom_id": atom.atom_id,
            "start": 0,
            "end": len(atom.text),
            "text_sha256": hashlib.sha256(atom.text.encode()).hexdigest(),
            "kind": "BEHAVIOR",
            "semantic_fingerprint": f"finance-semantic-{i}",
            "rationale": "operative finance source semantics",
        }
        units.append(unit)
        dispositions.append({
            "atom_id": atom.atom_id,
            "kind": "BEHAVIOR",
            "rationale": "operative finance source",
            "requirement_ids": [rid],
        })
        requirements.append({
            "id": rid,
            "source_atom_ids": [atom.atom_id],
            "source_semantic_unit_ids": [sid],
            "evidence_ids": [eid],
        })
        manifest_rows.append({
            "id": f"u{i:04d}",
            "start": atom.start,
            "end": atom.end,
            "evidence_ids": [eid],
        })
    return {
        "source_id": SOURCE,
        "source_text": TEXT,
        "source_coverage_manifest": {"units": manifest_rows},
        "source_semantic_coverage": {
            "dispositions": dispositions,
            "requirements": requirements,
            "extractor_units": {
                "extractor-a": copy.deepcopy(units),
                "extractor-b": copy.deepcopy(units),
            },
        },
    }


def test_complete_chain_passes():
    out = verify_source_semantic_coverage(bundle())
    assert out["pass"] is True, out


def test_missing_source_semantic_unit_fails_closed():
    b = bundle()
    b["source_semantic_coverage"]["extractor_units"]["extractor-b"].pop()
    out = verify_source_semantic_coverage(b)
    assert out["pass"] is False
    assert any("SEMANTIC_" in x for x in out["errors"])


def test_extractor_semantic_disagreement_fails_closed():
    b = bundle()
    b["source_semantic_coverage"]["extractor_units"]["extractor-b"][0]["semantic_fingerprint"] = "different"
    out = verify_source_semantic_coverage(b)
    assert out["pass"] is False
    assert any(x.startswith("SEMANTIC_EXTRACTOR_DISAGREEMENT:") for x in out["errors"])


def test_manifest_evidence_without_semantic_requirement_fails_closed():
    b = bundle()
    b["source_coverage_manifest"]["units"][0]["evidence_ids"].append("ORPHAN")
    out = verify_source_semantic_coverage(b)
    assert out["pass"] is False
    assert "SOURCE_MANIFEST_EVIDENCE_WITHOUT_SEMANTIC_REQUIREMENT:ORPHAN" in out["errors"]


def test_requirement_evidence_not_in_source_manifest_fails_closed():
    b = bundle()
    b["source_semantic_coverage"]["requirements"][0]["evidence_ids"] = ["MISSING"]
    out = verify_source_semantic_coverage(b)
    assert out["pass"] is False
    assert any(x.startswith("REQUIREMENT_EVIDENCE_NOT_IN_SOURCE_MANIFEST:R1:") for x in out["errors"])


def test_invalid_source_blocks_before_downstream_judgment():
    b = bundle()
    b["source_semantic_coverage"]["extractor_units"]["extractor-b"][0]["semantic_fingerprint"] = "different"
    out = configured_finance_terminal_decision({"decision": "CONCLUDE"}, b)
    assert out["accepted"] is False
    assert out["status"] == "TERMINAL_BLOCKED"
    assert "FINANCE_SOURCE_SEMANTIC_COVERAGE_FAIL_CLOSED" in out["errors"]
