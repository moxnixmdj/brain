"""Verified composition wrapper for one SEC CompanyConcept source-native semantic acquisition."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime.bound_capabilities import sec_companyconcept_source_native as producer
from canonical.runtime import sec_companyconcept_source_native_verify_v1 as verifier
from canonical.runtime.source_traceable_semantic_ir import compile_semantic_ir

SCHEMA = "PROJECT_BRAIN_SEC_COMPANYCONCEPT_SOURCE_NATIVE_VERIFIED_V1"


def _safe_existing(root: Path, raw: Any) -> Path:
    root = root.resolve()
    path = (root / str(raw or "")).resolve()
    if path == root or root not in path.parents or not path.is_file():
        raise RuntimeError("VERIFIED_WRAPPER_OUTPUT_PATH_INVALID")
    return path


def run(args: Mapping[str, Any], root: Any) -> dict[str, Any]:
    if not isinstance(args, Mapping):
        raise RuntimeError("ARGS_NOT_OBJECT")
    root = Path(root).resolve()
    produced = producer.run(args, root)
    if produced.get("independent_verification_required") is not True:
        raise RuntimeError("PRODUCER_VERIFICATION_BOUNDARY_DRIFT")
    if produced.get("output_verified") is not False:
        raise RuntimeError("PRODUCER_SELF_VERIFICATION_FORBIDDEN")

    raw_path = str(produced.get("raw_output_path") or "")
    semantic_path = str(produced.get("semantic_output_path") or "")
    check = verifier.verify(root=root, raw_path=raw_path, semantic_path=semantic_path)
    if check.get("verified") is not True:
        raise RuntimeError("INDEPENDENT_BYTE_TO_SEMANTIC_VERIFICATION_FAILED")
    if check.get("full_contract_rederived_from_raw_bytes") is not True:
        raise RuntimeError("FULL_CONTRACT_REDERIVATION_REQUIRED")
    if produced.get("raw_output_sha256") != check.get("source_sha256"):
        raise RuntimeError("PRODUCER_VERIFIER_SOURCE_SHA_MISMATCH")
    if produced.get("concept_qname") != check.get("concept_qname"):
        raise RuntimeError("PRODUCER_VERIFIER_CONCEPT_MISMATCH")
    if produced.get("fact_row_count") != check.get("fact_row_count"):
        raise RuntimeError("PRODUCER_VERIFIER_FACT_COUNT_MISMATCH")

    semantic_file = _safe_existing(root, semantic_path)
    semantic = json.loads(semantic_file.read_text(encoding="utf-8"))
    contract = semantic.get("semantic_contract")
    if not isinstance(contract, Mapping):
        raise RuntimeError("SEMANTIC_CONTRACT_MISSING_AFTER_VERIFICATION")
    ir = compile_semantic_ir(contract)
    if ir.get("status") != "COMPILED":
        raise RuntimeError("SEMANTIC_IR_NOT_CLEAN_COMPILED:" + str(ir.get("status")))

    return {
        "schema": SCHEMA,
        "status": "PASS__SEC_COMPANYCONCEPT_SOURCE_NATIVE_INDEPENDENTLY_VERIFIED_AND_COMPILED",
        "output_verified": True,
        "source_native_identity_extracted": True,
        "concept_qname": produced["concept_qname"],
        "fact_row_count": produced["fact_row_count"],
        "raw_output_path": raw_path,
        "raw_output_sha256": produced["raw_output_sha256"],
        "semantic_output_path": semantic_path,
        "semantic_output_sha256": produced["semantic_output_sha256"],
        "independent_verifier_status": check["status"],
        "full_contract_rederived_from_raw_bytes": True,
        "semantic_ir_status": ir["status"],
        "semantic_authority_claimed": False,
        "custom_taxonomy_covered": False,
        "raw_prose_wsd_claimed": False,
        "terminal_authority": False,
        "incremental_spend_usd": 0,
    }
}
