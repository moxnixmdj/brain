"""Authenticated exact source-phrase -> semantic-atom bridge V1."""
from __future__ import annotations
from copy import deepcopy
from hashlib import sha256
import json,re
from typing import Any,Callable,Mapping,Sequence
from canonical.runtime.source_aligned_definitional_entailment_v1 import SOURCE_ATOM_AUTHORITY_SCHEMA

SCHEMA="PROJECT_BRAIN_AUTHENTICATED_SOURCE_PHRASE_ATOM_BRIDGE_V1"
LEXICON_SCHEMA="PROJECT_BRAIN_BOUNDED_SEMANTIC_PHRASE_LEXICON_V1"
AUTHORITY_SCHEMA="PROJECT_BRAIN_SEMANTIC_PHRASE_LEXICON_AUTHORITY_RECEIPT_V1"
_HEX=set("0123456789abcdef")

class PhraseAtomBridgeError(ValueError): pass

def _canon(x:Any)->bytes:
    return json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode()
def _sha(x:Any)->str: return sha256(_canon(x)).hexdigest()
def _sha_ok(x:Any)->bool:
    s=str(x or "").lower(); return len(s)==64 and all(c in _HEX for c in s)
def _space(x:Any)->str: return " ".join(str(x if x is not None else "").strip().split())
def _surface(x:Any)->str: return _space(x).casefold()

def _normalize(value:Mapping[str,Any],*,check_collisions:bool)->dict[str,Any]:
    if not isinstance(value,Mapping): raise PhraseAtomBridgeError("LEXICON_REQUIRED")
    if value.get("schema")!=LEXICON_SCHEMA: raise PhraseAtomBridgeError("LEXICON_SCHEMA_INVALID")
    lid=_space(value.get("lexicon_id")); scope=_space(value.get("scope_id"))
    if not lid: raise PhraseAtomBridgeError("LEXICON_ID_REQUIRED")
    if not scope: raise PhraseAtomBridgeError("LEXICON_SCOPE_REQUIRED")
    if value.get("bounded_finite_lexicon") is not True: raise PhraseAtomBridgeError("BOUNDED_FINITE_LEXICON_ASSERTION_REQUIRED")
    raw=value.get("entries")
    if not isinstance(raw,Sequence) or isinstance(raw,(str,bytes)) or not raw: raise PhraseAtomBridgeError("LEXICON_ENTRIES_REQUIRED")
    entries=[]; ids=set(); surface_atoms={}
    for i,row in enumerate(raw):
        if not isinstance(row,Mapping): raise PhraseAtomBridgeError(f"LEXICON_ENTRY_NOT_OBJECT:{i}")
        eid=_space(row.get("entry_id")); atom=_space(row.get("atom_id")); surfaces=row.get("surfaces")
        if not eid: raise PhraseAtomBridgeError(f"LEXICON_ENTRY_ID_REQUIRED:{i}")
        if eid in ids: raise PhraseAtomBridgeError("LEXICON_ENTRY_ID_DUPLICATE:"+eid)
        ids.add(eid)
        if not atom: raise PhraseAtomBridgeError("LEXICON_ATOM_ID_REQUIRED:"+eid)
        if not isinstance(surfaces,Sequence) or isinstance(surfaces,(str,bytes)) or not surfaces: raise PhraseAtomBridgeError("LEXICON_SURFACES_REQUIRED:"+eid)
        norm=[]
        for x in surfaces:
            s=_surface(x)
            if not s: raise PhraseAtomBridgeError("LEXICON_SURFACE_EMPTY:"+eid)
            if s not in norm: norm.append(s)
            prior=surface_atoms.get(s)
            if check_collisions and prior is not None and prior!=atom:
                raise PhraseAtomBridgeError(f"SURFACE_SEMANTIC_COLLISION:{s}:{prior}!={atom}")
            surface_atoms.setdefault(s,atom)
        entries.append({"entry_id":eid,"atom_id":atom,"surfaces":sorted(norm)})
    entries.sort(key=lambda x:x["entry_id"])
    return {"schema":LEXICON_SCHEMA,"lexicon_id":lid,"scope_id":scope,"bounded_finite_lexicon":True,"entries":entries}

def lexicon_sha256(value:Mapping[str,Any])->str:
    return _sha(_normalize(value,check_collisions=False))

def _auth(lex:Mapping[str,Any],receipt:Any,verifier:Any)->dict[str,Any]:
    if not isinstance(receipt,Mapping) or not callable(verifier):
        return {"pass":False,"status":"AUTHORITY_NOT_BOUND","reason":"LEXICON_AUTHORITY_RECEIPT_AND_VERIFIER_REQUIRED"}
    out=verifier(deepcopy(dict(receipt)))
    if not isinstance(out,Mapping): return {"pass":False,"status":"FAIL_CLOSED","reason":"LEXICON_AUTHORITY_VERIFIER_RETURNED_NO_RECEIPT"}
    out=deepcopy(dict(out))
    req={"pass":True,"schema":AUTHORITY_SCHEMA,"lexicon_id":lex["lexicon_id"],"scope_id":lex["scope_id"],
         "lexicon_sha256":_sha(lex),"surface_to_atom_semantics_authenticated":True,
         "lexicon_scope_authenticated":True,"verification_authority_mutated":False}
    bad=[k for k,v in req.items() if out.get(k)!=v]
    if not _sha_ok(out.get("receipt_sha256")): bad.append("receipt_sha256")
    return out if not bad else {"pass":False,"status":"FAIL_CLOSED","reason":"PHRASE_LEXICON_AUTHORITY_BINDING_INVALID","mismatch_fields":sorted(set(bad)),"authority_result":out}

def _pattern(surface:str)->re.Pattern[str]:
    body=r"\s+".join(re.escape(p) for p in surface.split(" "))
    return re.compile(r"(?<!\w)"+body+r"(?!\w)",re.I)

def _make_receipt(raw:str,source_id:str,scope_id:str,lex:Mapping[str,Any],entry:Mapping[str,Any],start:int,end:int)->dict[str,Any]:
    core={"pass":True,"schema":SOURCE_ATOM_AUTHORITY_SCHEMA,"source_id":source_id,"scope_id":scope_id,
          "raw_span_sha256":sha256(raw.encode()).hexdigest(),"atom_id":entry["atom_id"],
          "source_semantics_authenticated":True,"verification_authority_mutated":False,
          "lexicon_id":lex["lexicon_id"],"lexicon_sha256":_sha(lex),"lexicon_entry_id":entry["entry_id"],
          "source_span":[start,end],"matched_text":raw[start:end]}
    return {**core,"receipt_sha256":_sha(core)}

def _base(status:str,passed:bool,**extra:Any)->dict[str,Any]:
    return {"schema":SCHEMA,"status":status,"pass":passed,"proved_atom_ids":[],"source_atom_receipts":[],
            "semantic_truth_authority":False,"absence_proves_negative":False,"open_world_phrase_completeness_claimed":False,
            "execution_authority":False,"acceptance_authority":False,"promotion_authority":False,
            "terminal_authority":False,"terminal_credit_delta":0,**extra}

def resolve(*,raw_span:str,source_id:str,scope_id:str,lexicon:Mapping[str,Any],
            authority_receipt:Mapping[str,Any]|None=None,
            authority_verifier:Callable[[Mapping[str,Any]],Mapping[str,Any]|None]|None=None)->dict[str,Any]:
    try:
        if not isinstance(raw_span,str) or not raw_span.strip(): raise PhraseAtomBridgeError("RAW_SPAN_REQUIRED")
        source_id=_space(source_id); scope_id=_space(scope_id)
        if not source_id: raise PhraseAtomBridgeError("SOURCE_ID_REQUIRED")
        if not scope_id: raise PhraseAtomBridgeError("SCOPE_ID_REQUIRED")
        lex=_normalize(lexicon,check_collisions=True)
        if lex["scope_id"]!=scope_id: raise PhraseAtomBridgeError("LEXICON_SCOPE_MISMATCH")
        auth=_auth(lex,authority_receipt,authority_verifier)
        if auth.get("pass") is not True:
            if auth.get("status")=="AUTHORITY_NOT_BOUND":
                return _base("OPEN__AUTHENTICATED_PHRASE_LEXICON_REQUIRED",False,lexicon_id=lex["lexicon_id"],lexicon_sha256=_sha(lex),authority_result=auth)
            return _base("FAIL_CLOSED__PHRASE_LEXICON_AUTHORITY_INVALID",False,reason=auth.get("reason"),authority_result=auth)
        best={}
        for entry in lex["entries"]:
            for surface in entry["surfaces"]:
                for m in _pattern(surface).finditer(raw_span):
                    cand=(m.start(),m.end(),entry)
                    prior=best.get(entry["atom_id"])
                    if prior is None or (cand[0],cand[1],entry["entry_id"]) < (prior[0],prior[1],prior[2]["entry_id"]):
                        best[entry["atom_id"]]=cand
        if not best:
            return _base("UNRESOLVED__NO_AUTHENTICATED_PHRASE_MATCH",False,lexicon_id=lex["lexicon_id"],lexicon_sha256=_sha(lex),authority_result=auth)
        receipts=[]
        for atom in sorted(best):
            start,end,entry=best[atom]
            receipts.append(_make_receipt(raw_span,source_id,scope_id,lex,entry,start,end))
        return _base("PASS__AUTHENTICATED_SOURCE_PHRASES_BOUND_TO_SEMANTIC_ATOMS",True,
                     proved_atom_ids=sorted(best),source_atom_receipts=receipts,semantic_truth_authority=True,
                     lexicon_id=lex["lexicon_id"],lexicon_sha256=_sha(lex),authority_result=auth,
                     theorem_boundary="EXACT_TOKEN_BOUNDARY_MATCH_ONLY_RELATIVE_TO_INDEPENDENTLY_AUTHENTICATED_BOUNDED_PHRASE_TO_ATOM_LEXICON")
    except Exception as exc:
        return _base("FAIL_CLOSED",False,reason=type(exc).__name__+":"+str(exc))

def verify_source_atom_receipt(receipt:Mapping[str,Any],*,raw_span:str,source_id:str,scope_id:str,
                               lexicon:Mapping[str,Any],authority_receipt:Mapping[str,Any]|None=None,
                               authority_verifier:Callable[[Mapping[str,Any]],Mapping[str,Any]|None]|None=None)->dict[str,Any]:
    if not isinstance(receipt,Mapping):
        return {"pass":False,"schema":SOURCE_ATOM_AUTHORITY_SCHEMA,"reason":"SOURCE_ATOM_RECEIPT_NOT_OBJECT"}
    out=resolve(raw_span=raw_span,source_id=source_id,scope_id=scope_id,lexicon=lexicon,
                authority_receipt=authority_receipt,authority_verifier=authority_verifier)
    if out.get("pass") is not True:
        return {"pass":False,"schema":SOURCE_ATOM_AUTHORITY_SCHEMA,"reason":"SOURCE_ATOM_RECOMPUTATION_UNAVAILABLE","bridge_result":out}
    expected=next((x for x in out["source_atom_receipts"] if x.get("atom_id")==receipt.get("atom_id")),None)
    if expected is None:
        return {"pass":False,"schema":SOURCE_ATOM_AUTHORITY_SCHEMA,"reason":"SOURCE_ATOM_NOT_RECOMPUTED"}
    if dict(receipt)!=dict(expected):
        return {"pass":False,"schema":SOURCE_ATOM_AUTHORITY_SCHEMA,"reason":"SOURCE_ATOM_RECEIPT_RECOMPUTATION_MISMATCH",
                "expected_receipt_sha256":expected.get("receipt_sha256"),"supplied_receipt_sha256":receipt.get("receipt_sha256")}
    return deepcopy(dict(expected))
