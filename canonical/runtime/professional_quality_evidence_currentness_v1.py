"""Professional-quality evidence currentness gate V1.

Reads the existing professional-quality reuse matrix and verifies that every
content-addressed evidence reference still resolves to the declared Git blob.
It never upgrades semantic or execution authority.
"""
from __future__ import annotations
from hashlib import sha1
import json
from pathlib import Path
from typing import Any

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_EVIDENCE_CURRENTNESS_V1"
DEFAULT_MATRIX="canonical/governance/PROFESSIONAL_QUALITY_EXISTING_EVIDENCE_REUSE_MATRIX_20261009_V1.json"
MUTABLE_POINTER_PATHS=frozenset({
    "canonical/governance/CURRENT_ASSURANCE_CLOSURE_COMPILER.json",
    "canonical/governance/CURRENT_R2_DECISION_INTELLIGENCE.json",
})

def git_blob_sha(path: Path) -> str:
    data=path.read_bytes()
    return sha1(f"blob {len(data)}\0".encode("ascii")+data).hexdigest()

def evaluate(repo_root: str | Path, matrix_path: str=DEFAULT_MATRIX) -> dict[str, Any]:
    root=Path(repo_root)
    matrix_file=root/matrix_path
    if not matrix_file.is_file():
        return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":"MATRIX_MISSING","terminal_authority":False,"terminal_credit_delta":0}
    matrix=json.loads(matrix_file.read_text())
    rows=[]; stale=[]; broken=[]; fresh=0
    for root_row in matrix.get("roots") or []:
        rid=root_row.get("id")
        for ev in root_row.get("evidence") or []:
            rel=ev.get("path"); expected=ev.get("git_blob_sha"); p=root/str(rel)
            if not p.is_file():
                state="MISSING_EVIDENCE_FILE"; actual=None; broken.append((rid,rel,state))
            else:
                actual=git_blob_sha(p)
                if actual==expected:
                    state="FRESH"; fresh+=1
                elif rel in MUTABLE_POINTER_PATHS:
                    state="STALE_REBIND_REQUIRED"; stale.append((rid,rel,expected,actual))
                else:
                    state="BROKEN_EVIDENCE_BINDING"; broken.append((rid,rel,state))
            rows.append({"root_id":rid,"path":rel,"expected_git_blob_sha":expected,"actual_git_blob_sha":actual,"state":state,"supports":ev.get("supports")})
    passed=not stale and not broken
    status=("FAIL_CLOSED__BROKEN_EVIDENCE_BINDING" if broken else "OPEN__STALE_MUTABLE_EVIDENCE_REBIND_REQUIRED" if stale else "PASS__ALL_EVIDENCE_REFERENCES_CURRENT")
    return {
        "schema":SCHEMA,"pass":passed,"status":status,
        "evidence_entry_count":len(rows),"fresh_count":fresh,
        "stale_rebind_count":len(stale),"broken_binding_count":len(broken),
        "rows":rows,
        "next_required_edge":("REBIND_STALE_MUTABLE_POINTERS_AND_REVALIDATE_SUPPORT" if stale and not broken else "REPAIR_BROKEN_CONTENT_ADDRESSED_EVIDENCE" if broken else None),
        "semantic_truth_authority":False,"execution_authority":False,
        "terminal_authority":False,"terminal_credit_delta":0,"incremental_spend_usd":0,
    }
