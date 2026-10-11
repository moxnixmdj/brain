"""Verify exact source bytes bound by CURRENT_FRONTIER_REUSE_SOURCE_LOCK."""
from __future__ import annotations
import hashlib
from pathlib import Path
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_FRONTIER_SOURCE_LOCK_VERIFY_V1"

def _hash(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()

def verify_source_lock(root: Path, lock: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    bad=[]; verified={}
    for sid,row in sorted(lock.items()):
        rel=row.get('path'); expected=row.get('sha256')
        if not isinstance(rel,str) or not isinstance(expected,str):
            bad.append({"source_id":sid,"reason":"LOCK_ROW_INVALID"}); continue
        p=root/rel
        if not p.is_file():
            bad.append({"source_id":sid,"reason":"FILE_MISSING","path":rel}); continue
        actual=_hash(p)
        if actual!=expected:
            bad.append({"source_id":sid,"reason":"SHA256_MISMATCH","expected":expected,"actual":actual}); continue
        verified[sid]=actual
    if bad:
        return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","source_lock_authority":False,"failures":bad,
                "terminal_authority":False,"terminal_credit_delta":0,"incremental_spend_usd":0}
    return {"schema":SCHEMA,"pass":True,"status":"PASS__ALL_SOURCE_LOCK_BYTES_EXACT","source_lock_authority":True,
            "verified":verified,"terminal_authority":False,"terminal_credit_delta":0,"incremental_spend_usd":0}
