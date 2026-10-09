"""Validation kernel for source-declared OEWN alias bindings."""
from __future__ import annotations
from hashlib import sha256
import json,re
from typing import Any,Mapping,Sequence
from canonical.runtime.oewn_release_sense_universe_v1 import RELEASE_ID,RELEASE_SHA256,SCHEMA as OEWN_SCHEMA

_WS=re.compile(r"\s+")
_ALIAS=re.compile(r"""\busually\s+called\s+(?:an?\s+)?["']([^"']+)["']\s+or\s+["']([^"']+)["']""",re.I)
_TRANS=str.maketrans({"\u201c":'"',"\u201d":'"',"\u2018":"'","\u2019":"'"})

def norm(v:Any)->str:
    return _WS.sub(" ",str(v or "").translate(_TRANS).strip()).casefold()

def digest(v:Any)->str:
    raw=json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode()
    return sha256(raw).hexdigest()

def validate_universe(value:Mapping[str,Any],term:str)->dict[str,Any]:
    if not isinstance(value,Mapping) or value.get("schema")!=OEWN_SCHEMA or value.get("pass") is not True:
        raise ValueError("SENSE_UNIVERSE_INVALID")
    if value.get("release_id")!=RELEASE_ID or value.get("archive_sha256")!=RELEASE_SHA256:
        raise ValueError("SENSE_UNIVERSE_RELEASE_INVALID")
    if value.get("candidate_set_complete_relative_to_release") is not True:
        raise ValueError("SENSE_UNIVERSE_COMPLETENESS_UNPROVED")
    if value.get("open_world_english_sense_completeness_claimed") is not False:
        raise ValueError("OPEN_WORLD_COMPLETENESS_MUST_REMAIN_FALSE")
    if norm(value.get("lemma"))!=term:
        raise ValueError("SENSE_UNIVERSE_LEMMA_MISMATCH")
    senses=value.get("senses")
    if not isinstance(senses,Sequence) or isinstance(senses,(str,bytes)) or not senses:
        raise ValueError("NONEMPTY_SENSE_SET_REQUIRED")
    rows=[]; seen=set()
    for i,row in enumerate(senses):
        if not isinstance(row,Mapping): raise ValueError(f"SENSE_NOT_OBJECT:{i}")
        sid=str(row.get("sense_id") or "").strip(); syn=str(row.get("synset_id") or "").strip()
        members=row.get("members")
        if not sid or not syn or sid in seen: raise ValueError(f"SENSE_ID_INVALID:{i}")
        seen.add(sid)
        if not isinstance(members,Sequence) or isinstance(members,(str,bytes)):
            raise ValueError("SENSE_MEMBERS_REQUIRED:"+sid)
        mm=sorted({norm(x) for x in members if norm(x)})
        if term not in mm: raise ValueError("AMBIGUOUS_TERM_NOT_MEMBER:"+sid)
        rows.append({"sense_id":sid,"synset_id":syn,"part_of_speech":str(row.get("part_of_speech") or ""),"members":mm})
    rows.sort(key=lambda x:(x["part_of_speech"],x["sense_id"],x["synset_id"]))
    material={"release_id":RELEASE_ID,"release_sha256":RELEASE_SHA256,"lemma":term,"senses":rows}
    return {"senses":rows,"sha256":digest(material)}

def declared_pair(text:str)->tuple[str,str]:
    matches=list(_ALIAS.finditer(norm(text)))
    if len(matches)!=1: raise ValueError("EXACT_ONE_SUPPORTED_ALIAS_DECLARATION_REQUIRED")
    a,b=norm(matches[0].group(1)),norm(matches[0].group(2))
    if not a or not b or a==b: raise ValueError("SOURCE_ALIAS_PAIR_INVALID")
    return a,b
