"""Exact binary artifact materializer.

If a caller already possesses the exact target bytes and their frozen SHA-256,
writing the native artifact is deterministic and format-agnostic. This isolates
artifact execution mechanics from the upstream problem of deriving the correct
target representation.

No semantic, layout, or validity authority is claimed.
"""
from __future__ import annotations
import hashlib
from pathlib import Path

def sha256(data:bytes)->str:
    return hashlib.sha256(data).hexdigest()

def materialize_exact_artifact(
    output_path:str|Path,
    *,
    target_bytes:bytes,
    expected_target_sha256:str,
    source_path:str|Path|None=None,
    expected_source_sha256:str|None=None,
)->dict:
    dst=Path(output_path)
    if not isinstance(target_bytes,bytes):
        return {"status":"FAIL_CLOSED","reason":"TARGET_BYTES_INVALID"}
    if not isinstance(expected_target_sha256,str) or len(expected_target_sha256)!=64:
        return {"status":"FAIL_CLOSED","reason":"TARGET_SHA_INVALID"}
    if sha256(target_bytes)!=expected_target_sha256:
        return {"status":"FAIL_CLOSED","reason":"TARGET_SHA_MISMATCH"}

    if source_path is not None:
        src=Path(source_path)
        if not src.is_file():
            return {"status":"FAIL_CLOSED","reason":"SOURCE_MISSING"}
        if not isinstance(expected_source_sha256,str) or len(expected_source_sha256)!=64:
            return {"status":"FAIL_CLOSED","reason":"SOURCE_SHA_REQUIRED"}
        data=src.read_bytes()
        if sha256(data)!=expected_source_sha256:
            return {"status":"FAIL_CLOSED","reason":"SOURCE_SHA_MISMATCH"}

    dst.parent.mkdir(parents=True,exist_ok=True)
    tmp=dst.with_name(dst.name+".brain-tmp")
    try:
        tmp.write_bytes(target_bytes)
        written=tmp.read_bytes()
        if written!=target_bytes or sha256(written)!=expected_target_sha256:
            tmp.unlink(missing_ok=True)
            return {"status":"FAIL_CLOSED","reason":"ROUNDTRIP_MISMATCH"}
        tmp.replace(dst)
    except Exception as exc:
        tmp.unlink(missing_ok=True)
        return {"status":"FAIL_CLOSED","reason":"WRITE_FAILED","error":type(exc).__name__}

    return {
        "status":"PASS",
        "output_path":str(dst),
        "target_sha256":expected_target_sha256,
        "byte_count":len(target_bytes),
        "scope":"EXACT_TARGET_BYTES_TO_NATIVE_ARTIFACT_BYTES",
        "semantic_authority":False,
        "format_validity_authority":False,
        "terminal_authority":False,
    }
