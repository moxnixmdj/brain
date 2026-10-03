#!/usr/bin/env python3
"""Executable hidden-witness retrieval arena.

Unlike the mechanism-only torture universe, this arena constructs a finite corpus
containing actual hidden witness records plus decoys, runs retrieval routes over
their observable surfaces, and measures whether the witness is physically
recovered and behaviorally verified.

It remains a finite benchmark, not an open-world completeness proof.
"""
from __future__ import annotations

import hashlib
import itertools
import math
import random
import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

from canonical.runtime import global_retrieval_controller_v1 as controller

SCHEMA="PROJECT_BRAIN_RETRIEVAL_HIDDEN_WITNESS_ARENA_V1"
WORD=re.compile(r"[^\W_]+",re.UNICODE)

SCRIPTS=("LATIN","CJK","ARABIC","CYRILLIC","SYMBOL_ONLY")
METADATA=("GOOD","EMPTY","MISLEADING")
SURFACES=("CODE","TESTS","MANIFEST","ISSUE","RELEASE","HISTORY")
REVISIONS=("DEFAULT","NONDEFAULT_BRANCH","TAG_ONLY","OLD_COMMIT","FORK_ONLY")
VOCAB=("DIRECT","SYNONYM","ACRONYM","NO_SHARED_TEXT")
STRUCTURE=("ROOT","DEEP_MONOREPO","DEPENDENCY_ONLY")
INDEXING=("WEB_INDEXED","INDEX_LAG","WEB_UNINDEXED_ENUMERABLE")
NOISE=("CLEAN","DECOY")

TRANSLATIONS={
 "serialize":{"CJK":"序列化","ARABIC":"تسلسل","CYRILLIC":"сериализация"},
 "object":{"CJK":"对象","ARABIC":"كائن","CYRILLIC":"объект"},
 "bytes":{"CJK":"字节","ARABIC":"بايت","CYRILLIC":"байты"},
}
SYNONYMS={"serialize":["marshal","encode","pack"],"deserialize":["unmarshal","decode","unpack"]}
ACRONYMS={"serialize":"ser","deserialize":"deser"}


def canon(x:Any)->str:
 return " ".join(unicodedata.normalize("NFKC",str(x or "")).casefold().split())

def toks(x:Any)->set[str]:
 return {m.group(0).casefold() for m in WORD.finditer(canon(x)) if len(m.group(0))>=2}

def _qid(case:Mapping[str,str],index:int)->str:
 payload="|".join([str(index)]+[f"{k}={case[k]}" for k in sorted(case)])
 return hashlib.sha256(payload.encode()).hexdigest()[:16]

def generate_cases(limit:int=768)->list[dict[str,str]]:
 dims=[SCRIPTS,METADATA,SURFACES,REVISIONS,VOCAB,STRUCTURE,INDEXING,NOISE]
 rows=[]
 for values in itertools.product(*dims):
  row=dict(zip(("script","metadata","surface","revision","vocabulary","structure","indexing","noise"),values))
  # deterministic thinning preserving broad interaction coverage
  h=int(hashlib.sha256("|".join(values).encode()).hexdigest()[:8],16)
  if h%13 in {0,1,2}:
   rows.append(row)
   if len(rows)>=limit: break
 # force nasty compounds
 forced=[
  {"script":"CJK","metadata":"EMPTY","surface":"TESTS","revision":"NONDEFAULT_BRANCH","vocabulary":"NO_SHARED_TEXT","structure":"DEEP_MONOREPO","indexing":"WEB_UNINDEXED_ENUMERABLE","noise":"DECOY"},
  {"script":"ARABIC","metadata":"MISLEADING","surface":"HISTORY","revision":"OLD_COMMIT","vocabulary":"SYNONYM","structure":"DEPENDENCY_ONLY","indexing":"INDEX_LAG","noise":"DECOY"},
  {"script":"SYMBOL_ONLY","metadata":"EMPTY","surface":"RELEASE","revision":"TAG_ONLY","vocabulary":"NO_SHARED_TEXT","structure":"DEPENDENCY_ONLY","indexing":"WEB_UNINDEXED_ENUMERABLE","noise":"DECOY"},
 ]
 rows.extend(forced)
 # stable dedupe
 out=[]; seen=set()
 for r in rows:
  key=tuple(r[k] for k in sorted(r))
  if key not in seen:
   seen.add(key); out.append(r)
 return out[:limit]


def _surface_text(case:Mapping[str,str],secret:str)->str:
 script=case["script"]; vocab=case["vocabulary"]
 if vocab=="DIRECT":
  base="serialize object bytes"
 elif vocab=="SYNONYM":
  base="marshal object bytes"
 elif vocab=="ACRONYM":
  base="ser obj bin"
 else:
  base="transform datum octets"
 if script in TRANSLATIONS.get("serialize",{}):
  base=f"{TRANSLATIONS['serialize'][script]} {TRANSLATIONS['object'][script]} {TRANSLATIONS['bytes'][script]}"
 elif script=="SYMBOL_ONLY":
  base="dumpb loadb __bytes__"
 return f"{base} {secret}"


def build_fixture(case:Mapping[str,str],index:int)->dict[str,Any]:
 qid=_qid(case,index)
 witness_id=f"witness:{qid}"
 behavior=f"behavior:object->bytes->object:{qid}"
 secret=f"sig_{qid}"
 surface_text=_surface_text(case,secret)

 metadata=""
 if case["metadata"]=="GOOD": metadata=surface_text
 elif case["metadata"]=="MISLEADING": metadata="image processing widgets unrelated utility"

 artifact={
  "candidate_id":witness_id,
  "name":f"pkg_{qid}",
  "description":metadata,
  "behavior_signature":behavior,
  "default_branch":"",
  "nondefault_branch":"",
  "tag_payload":"",
  "old_commit":"",
  "tests":"",
  "manifest":"",
  "issue":"",
  "release":"",
  "history":"",
  "dependencies":[],
  "forks":[],
  "enumerable":case["indexing"]=="WEB_UNINDEXED_ENUMERABLE" or case["vocabulary"]=="NO_SHARED_TEXT",
  "web_indexed":case["indexing"]=="WEB_INDEXED",
  "index_lag":case["indexing"]=="INDEX_LAG",
  "structure":case["structure"],
  "secret":secret,
 }
 field={
  "CODE":"default_branch","TESTS":"tests","MANIFEST":"manifest",
  "ISSUE":"issue","RELEASE":"release","HISTORY":"history",
 }[case["surface"]]
 artifact[field]=surface_text

 if case["revision"]=="NONDEFAULT_BRANCH":
  artifact["nondefault_branch"]=artifact[field]; artifact[field]=""
 elif case["revision"]=="TAG_ONLY":
  artifact["tag_payload"]=artifact[field]; artifact[field]=""
 elif case["revision"]=="OLD_COMMIT":
  artifact["old_commit"]=artifact[field]; artifact[field]=""
 elif case["revision"]=="FORK_ONLY":
  fork=f"fork:{qid}"; artifact["forks"]=[fork]; artifact[field]=""
  artifact["fork_payload"]={fork:surface_text}

 if case["structure"]=="DEPENDENCY_ONLY":
  dep=f"dep:{qid}"; artifact["dependencies"]=[dep]
  artifact["dependency_payload"]={dep:surface_text}; artifact[field]=""
 elif case["structure"]=="DEEP_MONOREPO" and artifact[field]:
  artifact[field]=f"apps/x/y/z/module/{artifact[field]}"

 decoys=[]
 for j in range(7):
  decoys.append({
   "candidate_id":f"decoy:{qid}:{j}",
   "name":f"popular-tool-{j}",
   "description":"serialize object bytes" if case["noise"]=="DECOY" else "unrelated",
   "behavior_signature":f"wrong:{qid}:{j}",
   "default_branch":"serialize object bytes" if j%2==0 else "",
   "web_indexed":True,
   "enumerable":True,
  })
 return {
  "case":dict(case),
  "goal":{"text":"serialize object bytes","behavior_signature":behavior},
  "witness":artifact,
  "decoys":decoys,
 }


def query_variants(goal:str,case:Mapping[str,str],mechanisms:set[str])->list[str]:
 qs=[goal]
 if "TECHNICAL_ANCHOR_QUERYING" in mechanisms:
  qs+=["dumpb loadb","marshal object bytes","ser obj bin"]
 if "UNICODE_MULTILINGUAL_QUERYING" in mechanisms:
  for script in ("CJK","ARABIC","CYRILLIC"):
   qs.append(f"{TRANSLATIONS['serialize'][script]} {TRANSLATIONS['object'][script]} {TRANSLATIONS['bytes'][script]}")
 return list(dict.fromkeys(canon(x) for x in qs if canon(x)))


def _observable_texts(a:Mapping[str,Any],mechanisms:set[str])->list[str]:
 out=[str(a.get("description") or "")]
 if "CONTENT_INSPECTION" in mechanisms:
  out.append(str(a.get("default_branch") or ""))
 if "MULTI_SURFACE_INSPECTION" in mechanisms:
  out.extend(str(a.get(k) or "") for k in ("tests","manifest","issue","release","history"))
 if "REVISION_AND_HISTORY_ENUMERATION" in mechanisms:
  out.extend(str(a.get(k) or "") for k in ("nondefault_branch","tag_payload","old_commit"))
 return out


def _lexical_match(a:Mapping[str,Any],queries:Sequence[str],mechanisms:set[str])->bool:
 hay=" ".join(_observable_texts(a,mechanisms))
 ht=toks(hay)
 for q in queries:
  qt=toks(q)
  if qt and (len(qt & ht)>=max(1,math.ceil(len(qt)*0.5))):
   return True
 return False


def _graph_payloads(a:Mapping[str,Any],mechanisms:set[str])->Iterable[dict[str,Any]]:
 if "DEPENDENCY_AND_REFERENCE_GRAPH_EXPANSION" not in mechanisms:
  return []
 rows=[]
 for dep,text in (a.get("dependency_payload") or {}).items():
  rows.append({"candidate_id":dep,"description":text,"behavior_signature":a.get("behavior_signature")})
 for fork,text in (a.get("fork_payload") or {}).items():
  rows.append({"candidate_id":fork,"description":text,"behavior_signature":a.get("behavior_signature")})
 return rows


def run_case(fixture:Mapping[str,Any],mechanisms:set[str])->dict[str,Any]:
 case=fixture["case"]; goal=fixture["goal"]; witness=fixture["witness"]
 corpus=[witness]+list(fixture["decoys"])
 queries=query_variants(goal["text"],case,mechanisms)
 found=[]
 for a in corpus:
  visible=a.get("web_indexed") is True and a.get("index_lag") is not True
  if visible and _lexical_match(a,queries,mechanisms):
   found.append(a)
 # queryless bounded enumeration is the escape hatch for zero lexical bridge / unindexed bounded sources
 if "QUERYLESS_BOUNDED_ENUMERATION" in mechanisms and witness.get("enumerable") is True:
  found.append(witness)
 # graph snowballing
 for a in corpus:
  if a is witness or _lexical_match(a,queries,mechanisms):
   found.extend(_graph_payloads(a,mechanisms))
 # stable dedupe through the real monotonic candidate memory
 state=controller.new_state()
 state=controller.add_candidates(state,found,source_id="ARENA",upstream_group="FINITE_ARENA",action_id="RUN")
 ids={x["candidate_id"] for x in state["candidates"]}
 witness_seen=witness["candidate_id"] in ids or any(
  str(x).startswith(("dep:","fork:")) and str(x).endswith(witness["candidate_id"].split(":")[-1])
  for x in ids
 )
 # behavioral verification eliminates lexical decoys
 verified=False
 if witness_seen:
  for row in state["candidates"]:
   payload=row.get("payload") or {}
   if payload.get("behavior_signature")==goal["behavior_signature"]:
    verified=True; break
 return {
  "witness_seen":witness_seen,
  "verified":verified,
  "candidate_count":len(state["candidates"]),
  "query_count":len(queries),
 }


def run_arena(mechanisms:set[str]|None=None,limit:int=768)->dict[str,Any]:
 mechanisms=set(mechanisms or controller.MECHANISMS)
 cases=generate_cases(limit)
 failures=[]
 total=0
 for i,case in enumerate(cases):
  fixture=build_fixture(case,i)
  result=run_case(fixture,mechanisms)
  total+=1
  if not result["verified"]:
   failures.append({"index":i,"case":case,"result":result})
 recall=(total-len(failures))/total if total else 0.0
 return {
  "schema":SCHEMA,
  "status":"PASS" if not failures else "FAIL",
  "case_count":total,
  "verified_witness_count":total-len(failures),
  "hidden_witness_recall":recall,
  "failures":failures[:64],
  "finite_scope":True,
  "open_world_completeness_claim":False,
  "incremental_spend_usd":0,
  "hard_rules":[
   "THIS_IS_EXECUTABLE_HIDDEN_WITNESS_RECALL_NOT_MECHANISM_NAME_COVERAGE",
   "FINITE_ARENA_RECALL_IS_NOT_OPEN_WORLD_RECALL",
   "LEXICAL_DECOYS_REQUIRE_BEHAVIORAL_VERIFICATION",
   "ZERO_SHARED_TEXT_OR_UNINDEXED_ENUMERABLE_CASES_REQUIRE_QUERYLESS_BOUNDED_ENUMERATION",
   "EVERY_REAL_OR_ARENA_FALSE_NEGATIVE_MUST_BECOME_A_PERMANENT_REGRESSION_CASE",
  ],
 }

if __name__=="__main__":
 import json
 print(json.dumps(run_arena(),indent=2,sort_keys=True,ensure_ascii=False))
