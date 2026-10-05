from __future__ import annotations
import hashlib
import pathlib
from dataclasses import dataclass
from typing import Mapping

SCHEMA="PROJECT_BRAIN_DECLARED_ARTIFACT_EXTRACTOR_V1"

class ArtifactExtractionError(ValueError):
    pass

@dataclass(frozen=True)
class DeclaredArtifact:
    artifact_id:str
    relative_path:str
    media_type:str
    max_bytes:int

def _safe_rel(value:str)->pathlib.PurePosixPath:
    raw=str(value or "").strip().replace("\\","/")
    p=pathlib.PurePosixPath(raw)
    if not raw or p.is_absolute() or ".." in p.parts or "." in p.parts:
        raise ArtifactExtractionError("ARTIFACT_PATH_INVALID")
    return p

def extract_declared_artifacts(
    private_merged_root:str|pathlib.Path,
    declarations:Mapping[str,DeclaredArtifact],
):
    root=pathlib.Path(private_merged_root).resolve()
    out=[]
    seen_paths=set()
    for artifact_id in sorted(declarations):
        decl=declarations[artifact_id]
        if decl.artifact_id!=artifact_id or not artifact_id:
            raise ArtifactExtractionError("ARTIFACT_ID_MISMATCH")
        rel=_safe_rel(decl.relative_path)
        rels=rel.as_posix()
        if rels in seen_paths:
            raise ArtifactExtractionError("DUPLICATE_ARTIFACT_PATH")
        seen_paths.add(rels)
        path=(root/pathlib.Path(*rel.parts)).resolve()
        if path==root or root not in path.parents:
            raise ArtifactExtractionError("ARTIFACT_PATH_ESCAPE")
        if not path.is_file() or path.is_symlink():
            raise ArtifactExtractionError("DECLARED_ARTIFACT_NOT_REGULAR_FILE:"+artifact_id)
        size=path.stat().st_size
        if size<0 or size>int(decl.max_bytes):
            raise ArtifactExtractionError("DECLARED_ARTIFACT_SIZE_INVALID:"+artifact_id)
        raw=path.read_bytes()
        if len(raw)!=size:
            raise ArtifactExtractionError("DECLARED_ARTIFACT_SIZE_RACE:"+artifact_id)
        out.append({
            "artifact_id":artifact_id,
            "relative_path":rels,
            "media_type":decl.media_type,
            "size":size,
            "sha256":hashlib.sha256(raw).hexdigest(),
        })
    return {
        "schema":SCHEMA,
        "status":"PASS",
        "artifact_count":len(out),
        "artifacts":out,
        "filesystem_policy":"ALL_NONDECLARED_PRIVATE_OVERLAY_CHANGES_DISCARDED",
        "durable_commit_authority_created":False,
        "accounting":{"acceptance_credit_delta":0},
    }
