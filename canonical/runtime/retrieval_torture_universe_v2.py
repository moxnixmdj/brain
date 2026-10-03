#!/usr/bin/env python3
"""Deterministic retrieval torture universe v2.

This is not an open-world completeness proof. It is a large finite architectural
counterexample generator. Every observable fixture declares which mechanisms
are required to make it discoverable. Inaccessible/private fixtures are
correctly classified UNKNOWN instead of NONEXISTENT.
"""
from __future__ import annotations
import itertools, json
from typing import Any

SCHEMA="PROJECT_BRAIN_RETRIEVAL_TORTURE_UNIVERSE_V2"

DIMENSIONS={
 "script":["LATIN","CJK","ARABIC","CYRILLIC","DEVANAGARI","MIXED","SYMBOL_ONLY"],
 "metadata":["GOOD","EMPTY","MISLEADING"],
 "surface":["CODE","SYMBOLS","MANIFEST","TESTS","ISSUE","HISTORY","RELEASE","PACKAGE"],
 "revision":["DEFAULT","NONDEFAULT_BRANCH","TAG_ONLY","OLD_COMMIT","FORK_ONLY","MIRROR_ONLY"],
 "vocabulary":["DIRECT","SYNONYM","ACRONYM","HISTORICAL_TERM","NO_SHARED_TEXT"],
 "popularity":["POPULAR","ZERO_STAR"],
 "structure":["ROOT","DEEP_MONOREPO","DEPENDENCY_ONLY","SUBMODULE_ONLY"],
 "noise":["CLEAN","SEO_SPAM","DECOY"],
 "indexing":["WEB_INDEXED","INDEX_LAG","WEB_UNINDEXED_ENUMERABLE"],
 "access":["PUBLIC","INACCESSIBLE"],
}

MECHANISM_RULES={
 "script":{
  "CJK":"UNICODE_MULTILINGUAL_QUERYING","ARABIC":"UNICODE_MULTILINGUAL_QUERYING",
  "CYRILLIC":"UNICODE_MULTILINGUAL_QUERYING","DEVANAGARI":"UNICODE_MULTILINGUAL_QUERYING",
  "MIXED":"UNICODE_MULTILINGUAL_QUERYING","SYMBOL_ONLY":"TECHNICAL_ANCHOR_QUERYING",
 },
 "metadata":{"EMPTY":"CONTENT_INSPECTION","MISLEADING":"CONTENT_INSPECTION"},
 "surface":{
  "CODE":"CONTENT_INSPECTION","SYMBOLS":"MULTI_SURFACE_INSPECTION","MANIFEST":"MULTI_SURFACE_INSPECTION",
  "TESTS":"MULTI_SURFACE_INSPECTION","ISSUE":"MULTI_SURFACE_INSPECTION",
  "HISTORY":"REVISION_AND_HISTORY_ENUMERATION","RELEASE":"REVISION_AND_HISTORY_ENUMERATION",
  "PACKAGE":"MULTI_SURFACE_INSPECTION",
 },
 "revision":{
  "NONDEFAULT_BRANCH":"REVISION_AND_HISTORY_ENUMERATION","TAG_ONLY":"REVISION_AND_HISTORY_ENUMERATION",
  "OLD_COMMIT":"REVISION_AND_HISTORY_ENUMERATION","FORK_ONLY":"DEPENDENCY_AND_REFERENCE_GRAPH_EXPANSION",
  "MIRROR_ONLY":"DEPENDENCY_AND_REFERENCE_GRAPH_EXPANSION",
 },
 "vocabulary":{
  "SYNONYM":"TECHNICAL_ANCHOR_QUERYING","ACRONYM":"TECHNICAL_ANCHOR_QUERYING",
  "HISTORICAL_TERM":"DEPENDENCY_AND_REFERENCE_GRAPH_EXPANSION",
  "NO_SHARED_TEXT":"QUERYLESS_BOUNDED_ENUMERATION",
 },
 "popularity":{"ZERO_STAR":"PROVENANCE_AWARE_RERANKING"},
 "structure":{
  "DEEP_MONOREPO":"CONTENT_INSPECTION","DEPENDENCY_ONLY":"DEPENDENCY_AND_REFERENCE_GRAPH_EXPANSION",
  "SUBMODULE_ONLY":"DEPENDENCY_AND_REFERENCE_GRAPH_EXPANSION",
 },
 "noise":{"SEO_SPAM":"PROVENANCE_AWARE_RERANKING","DECOY":"PROVENANCE_AWARE_RERANKING"},
 "indexing":{
  "INDEX_LAG":"QUERYLESS_BOUNDED_ENUMERATION",
  "WEB_UNINDEXED_ENUMERABLE":"QUERYLESS_BOUNDED_ENUMERATION",
 },
}

def _required(case:dict[str,str])->set[str]:
 out={"MONOTONIC_CANDIDATE_MEMORY","CONDITIONAL_NOVELTY_SCHEDULING","CORRELATED_CHANNEL_DISCOUNT","OPEN_WORLD_UNKNOWN_FIREWALL"}
 for dim, value in case.items():
  rule=MECHANISM_RULES.get(dim,{}).get(value)
  if rule: out.add(rule)
 return out

def generate_pairwise_universe()->list[dict[str,Any]]:
 """Baseline + every nonbaseline singleton + full value-pairs across every dimension pair."""
 dims=list(DIMENSIONS)
 base={d:DIMENSIONS[d][0] for d in dims}
 rows=[]; seen=set()
 def add(c):
  key=tuple(c[d] for d in dims)
  if key in seen:return
  seen.add(key)
  observable=c["access"]=="PUBLIC"
  rows.append({
   "id":f"CASE_{len(rows):05d}",
   "dimensions":dict(c),
   "observable":observable,
   "required_mechanisms":sorted(_required(c)) if observable else ["OPEN_WORLD_UNKNOWN_FIREWALL"],
   "correct_negative_state":"UNKNOWN",
  })
 add(base)
 for d in dims:
  for v in DIMENSIONS[d][1:]:
   c=dict(base);c[d]=v;add(c)
 for i,a in enumerate(dims):
  for b in dims[i+1:]:
   for va,vb in itertools.product(DIMENSIONS[a],DIMENSIONS[b]):
    c=dict(base);c[a]=va;c[b]=vb;add(c)

 # Deterministic three-way interaction expansion. Pairwise coverage alone misses
 # composed failures such as language x history x zero-lexical-overlap. Cap the
 # finite universe to keep CI fast while still creating thousands of distinct
 # counterexamples.
 target_cases=4096
 stop=False
 for ai,a in enumerate(dims):
  if stop: break
  for bi in range(ai+1,len(dims)):
   if stop: break
   b=dims[bi]
   for ci in range(bi+1,len(dims)):
    cdim=dims[ci]
    for va,vb,vc in itertools.product(DIMENSIONS[a],DIMENSIONS[b],DIMENSIONS[cdim]):
     row=dict(base);row[a]=va;row[b]=vb;row[cdim]=vc;add(row)
     if len(rows)>=target_cases:
      stop=True;break
    if stop: break
 # Add deliberately nasty compound cases that pairwise/triple generation does not force.
 compounds=[
  {"script":"CJK","metadata":"EMPTY","revision":"NONDEFAULT_BRANCH","vocabulary":"NO_SHARED_TEXT","popularity":"ZERO_STAR","structure":"DEEP_MONOREPO","noise":"DECOY","indexing":"WEB_UNINDEXED_ENUMERABLE"},
  {"script":"ARABIC","metadata":"MISLEADING","surface":"TESTS","revision":"OLD_COMMIT","vocabulary":"SYNONYM","structure":"DEPENDENCY_ONLY","indexing":"INDEX_LAG"},
  {"script":"SYMBOL_ONLY","metadata":"EMPTY","surface":"RELEASE","revision":"TAG_ONLY","vocabulary":"NO_SHARED_TEXT","structure":"SUBMODULE_ONLY","noise":"SEO_SPAM","indexing":"WEB_UNINDEXED_ENUMERABLE"},
 ]
 for patch in compounds:
  c=dict(base);c.update(patch);add(c)
 return rows

def evaluate(mechanisms:set[str])->dict[str,Any]:
 rows=generate_pairwise_universe()
 observable=[x for x in rows if x["observable"]]
 inaccessible=[x for x in rows if not x["observable"]]
 misses=[]
 for row in observable:
  missing=sorted(set(row["required_mechanisms"])-mechanisms)
  if missing: misses.append({"id":row["id"],"missing":missing,"dimensions":row["dimensions"]})
 return {
  "schema":SCHEMA,
  "status":"PASS" if not misses else "FAIL",
  "generated_case_count":len(rows),
  "observable_case_count":len(observable),
  "inaccessible_case_count":len(inaccessible),
  "architectural_failure_class_coverage":1.0 if not misses else (len(observable)-len(misses))/len(observable),
  "misses":misses[:64],
  "inaccessible_correct_state":"UNKNOWN",
  "open_world_completeness_claim":False,
  "hard_rules":[
   "FINITE_ARCHITECTURAL_COVERAGE_IS_NOT_OPEN_WORLD_RECALL",
   "PAIRWISE_PLUS_COMPOUND_COUNTEREXAMPLES_DO_NOT_PROVE_ALL_FAILURE_CLASSES_EXIST",
   "INACCESSIBLE_PRIVATE_OR_DELETED_WITHOUT_OBSERVABLE_SURVIVOR_REMAINS_UNKNOWN",
   "EVERY_NEW_REAL_MISS_MUST_BECOME_A_PERMANENT_REGRESSION_CASE",
  ],
 }

if __name__=="__main__":
 from canonical.runtime.global_retrieval_controller_v1 import MECHANISMS
 print(json.dumps(evaluate(set(MECHANISMS)),indent=2,sort_keys=True))
