"""Brain-native exact artifact-type semantic receipt V1.

Deterministically observes the actual artifact type from exact bytes and emits
a bounded semantic-satisfaction receipt for SEM_ARTIFACT_TYPE only when the
observed type equals the exact structured target type.

No filename-only authority, no arbitrary semantic judgment, no quality or
benchmark authority.
"""
from __future__ import annotations

from hashlib import sha1,sha256
import json
from pathlib import Path
from typing import Any,Mapping
import zipfile

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_ARTIFACT_TYPE_SEMANTIC_RECEIPT_V1"
BRIDGE_RECEIPT_SCHEMA="PROJECT_BRAIN_PROFESSIONAL_TASK_OBLIGATION_SEMANTIC_RECEIPT_V1"
CAPABILITY_ID="professional.artifact.type_semantic_receipt.v1"
OBLIGATION_ID="SEM_ARTIFACT_TYPE"

ALIASES={
 "PDF":"PDF",
 "DOCX":"DOCX","WORD":"DOCX","WORD_DOCUMENT":"DOCX",
 "XLSX":"XLSX","EXCEL":"XLSX","SPREADSHEET":"XLSX",
 "PPTX":"PPTX","POWERPOINT":"PPTX","PRESENTATION":"PPTX",
 "PNG":"PNG",
 "JPG":"JPEG","JPEG":"JPEG",
}


class ArtifactTypeSemanticError(ValueError): pass


def _canon(v:Any)->str:
    return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False)


def _sha(v:Any)->str:
    return sha256(_canon(v).encode("utf-8")).hexdigest()


def _safe(root:str|Path,raw:Any)->Path:
    base=Path(root).resolve()
    p=(base/str(raw or "")).resolve()
    if p!=base and base not in p.parents:
        raise ArtifactTypeSemanticError("PATH_OUTSIDE_REPOSITORY")
    if not p.is_file() or p.is_symlink():
        raise ArtifactTypeSemanticError("ARTIFACT_FILE_INVALID")
    return p


def _normalize_target(raw:Any)->str:
    key=str(raw or "").strip().upper().replace(" ","_")
    out=ALIASES.get(key)
    if out is None:
        raise ArtifactTypeSemanticError("TARGET_ARTIFACT_TYPE_UNSUPPORTED:"+key)
    return out


def _zip_type(path:Path)->str|None:
    try:
        with zipfile.ZipFile(path,"r") as z:
            if z.testzip() is not None:
                raise ArtifactTypeSemanticError("ZIP_CRC_FAILURE")
            names=set(z.namelist())
    except zipfile.BadZipFile:
        return None
    hits=[]
    if "word/document.xml" in names: hits.append("DOCX")
    if "xl/workbook.xml" in names: hits.append("XLSX")
    if "ppt/presentation.xml" in names: hits.append("PPTX")
    if len(hits)>1:
        raise ArtifactTypeSemanticError("AMBIGUOUS_OOXML_TYPE")
    return hits[0] if hits else None


def observe_type(path:Path)->str:
    head=path.read_bytes()[:16]
    if head.startswith(b"%PDF-"): return "PDF"
    if head.startswith(b"\x89PNG\r\n\x1a\n"): return "PNG"
    if len(head)>=3 and head[:3]==b"\xff\xd8\xff": return "JPEG"
    z=_zip_type(path)
    if z is not None: return z
    raise ArtifactTypeSemanticError("ARTIFACT_TYPE_UNRECOGNIZED")


def verify_and_receipt(args:Any,root:str|Path)->dict[str,Any]:
    if not isinstance(args,Mapping):
        raise ArtifactTypeSemanticError("ARGS_NOT_OBJECT")
    required=(
      "path","task_id","task_sha256","target_artifact_type",
      "obligation_semantics_sha256","obligation_universe_digest","target_scope_id",
    )
    missing=[k for k in required if k not in args]
    extra=sorted(set(args)-set(required))
    if missing: raise ArtifactTypeSemanticError("ARGS_MISSING:"+",".join(missing))
    if extra: raise ArtifactTypeSemanticError("ARGS_UNKNOWN:"+",".join(extra))
    task_id=str(args["task_id"] or "").strip()
    if not task_id: raise ArtifactTypeSemanticError("TASK_ID_REQUIRED")
    hashes={}
    for k in ("task_sha256","obligation_semantics_sha256","obligation_universe_digest"):
        v=str(args[k] or "").strip().lower()
        if len(v)!=64 or any(c not in "0123456789abcdef" for c in v):
            raise ArtifactTypeSemanticError("HASH_INVALID:"+k)
        hashes[k]=v
    scope=str(args["target_scope_id"] or "").strip()
    if not scope.startswith("scope://professional-task-fulfillment/"):
        raise ArtifactTypeSemanticError("TARGET_SCOPE_ID_INVALID")
    p=_safe(root,args["path"])
    data=p.read_bytes();artifact_sha=sha256(data).hexdigest()
    target=_normalize_target(args["target_artifact_type"])
    observed=observe_type(p)
    suffix=p.suffix.lower()
    suffix_expected={
      "PDF":{".pdf"},"DOCX":{".docx"},"XLSX":{".xlsx"},
      "PPTX":{".pptx"},"PNG":{".png"},"JPEG":{".jpg",".jpeg"},
    }[observed]
    suffix_consistent=suffix in suffix_expected
    matched=observed==target and suffix_consistent
    evidence={
      "schema":SCHEMA,
      "capability_id":CAPABILITY_ID,
      "task_id":task_id,
      "task_sha256":hashes["task_sha256"],
      "artifact_sha256":artifact_sha,
      "source_path":str(p.relative_to(Path(root).resolve())),
      "target_artifact_type":target,
      "observed_artifact_type":observed,
      "suffix":suffix,
      "suffix_consistent_with_observed_type":suffix_consistent,
      "type_matches_target":matched,
      "obligation_id":OBLIGATION_ID,
      "obligation_semantics_sha256":hashes["obligation_semantics_sha256"],
      "obligation_universe_digest":hashes["obligation_universe_digest"],
      "target_scope_id":scope,
      "external_general_purpose_model_runtime_dependency_count":0,
    }
    evidence_sha=_sha(evidence)
    if not matched:
        return {
          **evidence,
          "status":"FAIL_CLOSED__ARTIFACT_TYPE_MISMATCH",
          "pass":False,
          "semantic_satisfaction_proved":False,
          "evidence_sha256":evidence_sha,
          "receipt":None,
          "quality_authority":False,
          "benchmark_score_authority":False,
          "terminal_authority":False,
        }
    receipt={
      "schema":BRIDGE_RECEIPT_SCHEMA,
      "task_id":task_id,
      "task_sha256":hashes["task_sha256"],
      "artifact_sha256":artifact_sha,
      "obligation_id":OBLIGATION_ID,
      "obligation_semantics_sha256":hashes["obligation_semantics_sha256"],
      "obligation_universe_digest":hashes["obligation_universe_digest"],
      "target_scope_id":scope,
      "verdict":"PASS",
      "semantic_satisfaction_proved":True,
      "producer_id":CAPABILITY_ID,
      "evidence_sha256":evidence_sha,
    }
    return {
      **evidence,
      "status":"PASS__EXACT_ARTIFACT_TYPE_SEMANTIC_SATISFACTION",
      "pass":True,
      "semantic_satisfaction_proved":True,
      "evidence_sha256":evidence_sha,
      "receipt":receipt,
      "quality_authority":False,
      "benchmark_score_authority":False,
      "terminal_authority":False,
      "incremental_spend_usd":0,
    }
