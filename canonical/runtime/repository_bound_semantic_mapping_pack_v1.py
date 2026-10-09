"""Repository-bound semantic mapping pack authority V1."""
from __future__ import annotations
from copy import deepcopy
from hashlib import sha1,sha256
import json
from pathlib import Path
from typing import Any,Mapping,Sequence
from canonical.runtime.authenticated_source_phrase_atom_bridge_v1 import (
    AUTHORITY_SCHEMA as LEXICON_AUTHORITY_SCHEMA,
    LEXICON_SCHEMA,
    lexicon_sha256,
)
from canonical.runtime.source_aligned_definitional_entailment_v1 import (
    CONCEPT_DEFINITION_AUTHORITY_SCHEMA,
    definition_sha256,
)

PACK_SCHEMA="PROJECT_BRAIN_SEMANTIC_MAPPING_PACK_V1"
VERIFY_SCHEMA="PROJECT_BRAIN_SEMANTIC_MAPPING_PACK_VERIFY_V1"
ROOT=Path(__file__).resolve().parents[2]
_HEX=set("0123456789abcdef")

class SemanticPackError(ValueError): pass

def _canon(x:Any)->bytes:
    return json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode()
def _sha(x:Any)->str: return sha256(_canon(x)).hexdigest()
def _sha_ok(x:Any,n:int=64)->bool:
    s=str(x or "").lower(); return len(s)==n and all(c in _HEX for c in s)
def _text(x:Any)->str: return " ".join(str(x if x is not None else "").strip().split())
def _git_blob(raw:bytes)->str:
    return sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def _normalize_definition(row:Mapping[str,Any],scope_id:str)->dict[str,Any]:
    if not isinstance(row,Mapping): raise SemanticPackError("CONCEPT_DEFINITION_NOT_OBJECT")
    if _text(row.get("scope_id"))!=scope_id: raise SemanticPackError("CONCEPT_DEFINITION_SCOPE_MISMATCH")
    cid=_text(row.get("concept_id")); kind=_text(row.get("definition_kind")).upper()
    atoms=row.get("definition_atoms")
    if not cid: raise SemanticPackError("CONCEPT_ID_REQUIRED")
    if kind!="EXACT_CONJUNCTION": raise SemanticPackError("CONCEPT_DEFINITION_KIND_UNSUPPORTED")
    if not isinstance(atoms,Sequence) or isinstance(atoms,(str,bytes)) or not atoms: raise SemanticPackError("CONCEPT_DEFINITION_ATOMS_REQUIRED")
    vals=[]
    for i,a in enumerate(atoms):
        a=_text(a)
        if not a: raise SemanticPackError(f"CONCEPT_DEFINITION_ATOM_INVALID:{i}")
        if a in vals: raise SemanticPackError("CONCEPT_DEFINITION_ATOM_DUPLICATE:"+a)
        vals.append(a)
    out={"scope_id":scope_id,"concept_id":cid,"definition_kind":"EXACT_CONJUNCTION","definition_atoms":sorted(vals)}
    definition_sha256(out)
    return out

def _normalize_pack(value:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(value,Mapping): raise SemanticPackError("PACK_REQUIRED")
    if value.get("schema")!=PACK_SCHEMA: raise SemanticPackError("PACK_SCHEMA_INVALID")
    pid=_text(value.get("pack_id")); scope=_text(value.get("scope_id"))
    if not pid: raise SemanticPackError("PACK_ID_REQUIRED")
    if not scope: raise SemanticPackError("PACK_SCOPE_REQUIRED")
    lex=value.get("phrase_lexicon")
    if not isinstance(lex,Mapping) or lex.get("schema")!=LEXICON_SCHEMA: raise SemanticPackError("PHRASE_LEXICON_INVALID")
    if _text(lex.get("scope_id"))!=scope: raise SemanticPackError("PHRASE_LEXICON_SCOPE_MISMATCH")
    lexicon_sha256(lex)
    defs=value.get("concept_definitions")
    if not isinstance(defs,Sequence) or isinstance(defs,(str,bytes)) or not defs: raise SemanticPackError("CONCEPT_DEFINITIONS_REQUIRED")
    normalized_defs=[]; ids=set()
    for row in defs:
        d=_normalize_definition(row,scope)
        if d["concept_id"] in ids: raise SemanticPackError("CONCEPT_ID_DUPLICATE:"+d["concept_id"])
        ids.add(d["concept_id"]); normalized_defs.append(d)
    normalized_defs.sort(key=lambda x:x["concept_id"])
    refs=value.get("source_refs",[])
    if not isinstance(refs,Sequence) or isinstance(refs,(str,bytes)): raise SemanticPackError("SOURCE_REFS_INVALID")
    normalized_refs=[]
    for i,row in enumerate(refs):
        if not isinstance(row,Mapping): raise SemanticPackError(f"SOURCE_REF_NOT_OBJECT:{i}")
        r={k:_text(row.get(k)) for k in ("authority","document","section","url")}
        if not all(r.values()): raise SemanticPackError(f"SOURCE_REF_FIELDS_REQUIRED:{i}")
        normalized_refs.append(r)
    normalized_refs.sort(key=lambda r:(r["authority"],r["document"],r["section"],r["url"]))
    return {"schema":PACK_SCHEMA,"pack_id":pid,"scope_id":scope,"phrase_lexicon":deepcopy(dict(lex)),
            "concept_definitions":normalized_defs,"source_refs":normalized_refs}

def pack_sha256(value:Mapping[str,Any])->str:
    return _sha(_normalize_pack(value))

def _base(status:str,passed:bool,**extra:Any)->dict[str,Any]:
    return {"schema":"PROJECT_BRAIN_REPOSITORY_BOUND_SEMANTIC_MAPPING_PACK_V1","status":status,"pass":passed,
            "phrase_lexicon_semantics_authenticated":False,"concept_definitions_authenticated":False,
            "source_authority_reviewed":False,"semantic_truth_authority":False,
            "execution_authority":False,"acceptance_authority":False,"promotion_authority":False,
            "terminal_authority":False,"terminal_credit_delta":0,**extra}

def load_verified_pack(pack:Mapping[str,Any],verification_ref:Mapping[str,Any],*,repo_root:str|Path|None=None)->dict[str,Any]:
    root=Path(repo_root).resolve() if repo_root is not None else ROOT
    try:
        normalized=_normalize_pack(pack); psha=_sha(normalized)
        if not isinstance(verification_ref,Mapping): raise SemanticPackError("VERIFICATION_REF_REQUIRED")
        rel=str(verification_ref.get("path") or "").strip(); expected=str(verification_ref.get("git_blob_sha") or "").strip()
        p=Path(rel)
        if not rel or p.is_absolute() or ".." in p.parts or not rel.startswith("canonical/verification/"):
            raise SemanticPackError("VERIFICATION_PATH_INVALID")
        base=(root/"canonical"/"verification").resolve(strict=False)
        full=(root/p).resolve(strict=False)
        if not full.is_relative_to(base): raise SemanticPackError("VERIFICATION_PATH_INVALID")
        probe=root/p
        if any(part.is_symlink() for part in [probe,*probe.parents] if part!=root and root in part.parents):
            raise SemanticPackError("VERIFICATION_SYMLINK_FORBIDDEN")
        if not probe.is_file(): raise SemanticPackError("VERIFICATION_FILE_MISSING")
        raw=probe.read_bytes(); actual=_git_blob(raw)
        if actual!=expected: raise SemanticPackError("VERIFICATION_BLOB_DRIFT:"+actual)
        doc=json.loads(raw.decode("utf-8"))
        if not isinstance(doc,Mapping): raise SemanticPackError("VERIFICATION_JSON_NOT_OBJECT")
        req={"schema":VERIFY_SCHEMA,"pass":True,"independent_verified":True,"pack_id":normalized["pack_id"],
             "scope_id":normalized["scope_id"],"pack_sha256":psha,
             "phrase_lexicon_semantics_authenticated":True,"concept_definitions_authenticated":True,
             "source_authority_reviewed":True,"verification_authority_mutated":False}
        bad=[k for k,v in req.items() if doc.get(k)!=v]
        if bad: raise SemanticPackError("PACK_VERIFICATION_BINDING_INVALID:"+",".join(sorted(bad)))
        return _base("PASS__REPOSITORY_BOUND_SEMANTIC_MAPPING_PACK_AUTHENTICATED",True,
                     pack_id=normalized["pack_id"],scope_id=normalized["scope_id"],pack_sha256=psha,
                     phrase_lexicon=normalized["phrase_lexicon"],concept_definitions=normalized["concept_definitions"],
                     source_refs=normalized["source_refs"],verification_ref={"path":rel,"git_blob_sha":actual},
                     verification=deepcopy(dict(doc)),phrase_lexicon_semantics_authenticated=True,
                     concept_definitions_authenticated=True,source_authority_reviewed=True,semantic_truth_authority=True)
    except Exception as exc:
        return _base("FAIL_CLOSED",False,reason=type(exc).__name__+":"+str(exc))

def _require_verified(v:Mapping[str,Any])->None:
    if not isinstance(v,Mapping) or v.get("pass") is not True or v.get("semantic_truth_authority") is not True:
        raise ValueError("VERIFIED_SEMANTIC_PACK_REQUIRED")

def make_lexicon_authority_verifier(verified_pack:Mapping[str,Any]):
    _require_verified(verified_pack)
    lex=deepcopy(dict(verified_pack["phrase_lexicon"]))
    def verify(_receipt):
        core={"pass":True,"schema":LEXICON_AUTHORITY_SCHEMA,"lexicon_id":_text(lex.get("lexicon_id")),
              "scope_id":verified_pack["scope_id"],"lexicon_sha256":lexicon_sha256(lex),
              "surface_to_atom_semantics_authenticated":True,"lexicon_scope_authenticated":True,
              "verification_authority_mutated":False}
        return {**core,"receipt_sha256":_sha(core)}
    return verify

def make_concept_definition_verifier(verified_pack:Mapping[str,Any],concept_id:str):
    _require_verified(verified_pack); cid=_text(concept_id)
    row=next((deepcopy(dict(x)) for x in verified_pack.get("concept_definitions",[]) if x.get("concept_id")==cid),None)
    if row is None: raise ValueError("CONCEPT_NOT_IN_VERIFIED_PACK:"+cid)
    def verify(_receipt):
        core={"pass":True,"schema":CONCEPT_DEFINITION_AUTHORITY_SCHEMA,**row,
              "definition_sha256":definition_sha256(row),"definition_semantics_authenticated":True,
              "verification_authority_mutated":False}
        return {**core,"receipt_sha256":_sha(core)}
    return verify
