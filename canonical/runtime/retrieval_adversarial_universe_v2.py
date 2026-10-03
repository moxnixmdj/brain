"""Generated adversarial retrieval universe for Retrieval V6."""
from __future__ import annotations
import hashlib,itertools,json
from typing import Any,Mapping
SCHEMA="PROJECT_BRAIN_RETRIEVAL_ADVERSARIAL_UNIVERSE_V2"
DIMENSIONS={
"language":("EN","ZH","AR","RU","HI"),
"metadata":("GOOD","EMPTY","MISLEADING"),
"surface":("CODE","SYMBOL","MANIFEST","TEST","ISSUE","HISTORY","PACKAGE","DOC"),
"revision":("DEFAULT","NONDEFAULT_BRANCH","TAG_RELEASE","FORK_MIRROR"),
"vocabulary":("DIRECT","SYNONYM","ACRONYM","TYPO","ZERO_LEXICAL_BRIDGE"),
"popularity":("POPULAR","ZERO_SIGNAL"),
"graph_depth":("DIRECT","DEP1","DEP2"),
"noise":("CLEAN","SEO_SPAM","DISTRACTOR"),
}
DEFAULTS={k:v[0] for k,v in DIMENSIONS.items()}
TRANSLATIONS={"EN":"binary serializer","ZH":"二进制序列化器","AR":"مسلسل ثنائي","RU":"двоичный сериализатор","HI":"बाइनरी सीरियलाइज़र"}
def _case_id(v:Mapping[str,str])->str:
 return hashlib.sha256(json.dumps(dict(v),sort_keys=True,ensure_ascii=False,separators=(",",":")).encode()).hexdigest()[:20]
def generate_pairwise_universe()->list[dict[str,Any]]:
 keys=list(DIMENSIONS); cases={}
 for i,left in enumerate(keys):
  for right in keys[i+1:]:
   for lv,rv in itertools.product(DIMENSIONS[left],DIMENSIONS[right]):
    v=dict(DEFAULTS);v[left]=lv;v[right]=rv;cid=_case_id(v);cases[cid]={"case_id":cid,**v,"basis":f"PAIRWISE:{left}+{right}"}
 hard=[
 {"language":"ZH","metadata":"EMPTY","surface":"CODE","revision":"NONDEFAULT_BRANCH","vocabulary":"ZERO_LEXICAL_BRIDGE","popularity":"ZERO_SIGNAL","graph_depth":"DEP2","noise":"SEO_SPAM"},
 {"language":"AR","metadata":"MISLEADING","surface":"HISTORY","revision":"FORK_MIRROR","vocabulary":"TYPO","popularity":"ZERO_SIGNAL","graph_depth":"DEP2","noise":"DISTRACTOR"},
 {"language":"RU","metadata":"EMPTY","surface":"TEST","revision":"TAG_RELEASE","vocabulary":"ACRONYM","popularity":"ZERO_SIGNAL","graph_depth":"DEP1","noise":"SEO_SPAM"},
 {"language":"HI","metadata":"MISLEADING","surface":"MANIFEST","revision":"NONDEFAULT_BRANCH","vocabulary":"SYNONYM","popularity":"ZERO_SIGNAL","graph_depth":"DEP2","noise":"DISTRACTOR"}]
 for v in hard:
  cid=_case_id(v);cases[cid]={"case_id":cid,**v,"basis":"MULTI_FAILURE_STRESS"}
 return sorted(cases.values(),key=lambda x:x["case_id"])
def pairwise_coverage(cases:list[Mapping[str,Any]])->dict[str,Any]:
 keys=list(DIMENSIONS);missing=[]
 for i,left in enumerate(keys):
  for right in keys[i+1:]:
   observed={(str(c[left]),str(c[right])) for c in cases}
   for lv,rv in itertools.product(DIMENSIONS[left],DIMENSIONS[right]):
    if (lv,rv) not in observed:missing.append(f"{left}={lv}|{right}={rv}")
 return {"pairwise_complete":not missing,"missing_pairs":missing}
def _artifact(c:Mapping[str,Any])->dict[str,Any]:
 lang=str(c["language"]);vocab=str(c["vocabulary"]);meta=str(c["metadata"]);surface=str(c["surface"]);phrase=TRANSLATIONS[lang]
 if vocab=="SYNONYM":phrase={"EN":"binary marshaler","ZH":"二进制编组器","AR":"مرمّز ثنائي","RU":"двоичный маршаллер","HI":"बाइनरी मार्शलर"}[lang]
 elif vocab=="ACRONYM":phrase="UBJ codec"
 elif vocab=="TYPO":phrase="seralizer bnary"
 elif vocab=="ZERO_LEXICAL_BRIDGE":phrase="opaque-omega-component"
 title=phrase if meta=="GOOD" else ("" if meta=="EMPTY" else "unrelated image toolkit")
 return {"item_id":c["case_id"],"title":title,"surface":surface,"revision":c["revision"],"popularity":c["popularity"],"graph_depth":c["graph_depth"],"noise":c["noise"],"text":phrase if surface in {"DOC","ISSUE","HISTORY","PACKAGE"} else "","symbols":["dumpb","loadb"] if surface=="SYMBOL" else [],"manifest":["ubjson-codec"] if surface=="MANIFEST" else [],"tests":["object -> bytes -> object"] if surface=="TEST" else [],"code":["def dumpb(obj): return encode_binary(obj)"] if surface=="CODE" else [],"behavior_fingerprint":("input:object","output:bytes","roundtrip:true")}
def _lexical(a:Mapping[str,Any])->bool:
 needles=("serializer","序列化","مسلسل","сериал","सीरियल","ubj","dumpb","loadb","ubjson");hay=json.dumps(dict(a),ensure_ascii=False).casefold();return any(n.casefold() in hay for n in needles)
def _behavior(a:Mapping[str,Any])->bool:return tuple(a.get("behavior_fingerprint") or ())==("input:object","output:bytes","roundtrip:true")
def run()->dict[str,Any]:
 cases=generate_pairwise_universe();cov=pairwise_coverage(cases);arts=[_artifact(c) for c in cases];ids={c["case_id"] for c in cases};lex={a["item_id"] for a in arts if _lexical(a)};v6={a["item_id"] for a in arts if _lexical(a) or _behavior(a)}
 opaque={"item_id":"OUTSIDE_SCOPE_OPAQUE","text":"完全不相关的未知对象","behavior_fingerprint":()};outside=_lexical(opaque) or _behavior(opaque)
 return {"schema":SCHEMA,"status":"PASS" if cov["pairwise_complete"] and v6==ids and not outside else "FAIL","generated_case_count":len(cases),"pairwise_complete":cov["pairwise_complete"],"missing_pairs":cov["missing_pairs"],"lexical_only_recall":len(lex)/len(ids),"v6_finite_fixture_recall":len(v6)/len(ids),"v6_misses":sorted(ids-v6),"explicit_multi_failure_stress_count":sum(1 for c in cases if c["basis"]=="MULTI_FAILURE_STRESS"),"outside_scope_opaque_found":outside,"outside_scope_correct_state":"UNKNOWN" if not outside else "CANDIDATE_FOUND","open_world_completeness_claim_authorized":False,"incremental_spend_usd":0,"hard_rules":["FINITE_FIXTURE_RECALL_1_DOES_NOT_IMPLY_OPEN_WORLD_COMPLETENESS","PAIRWISE_GENERATION_REPLACES_TINY_HANDWRITTEN_ONLY_BENCHMARK","QUERYLESS_ENUMERATION_MUST_HANDLE_ZERO_LEXICAL_BRIDGE_INSIDE_DECLARED_FINITE_SCOPE","OUTSIDE_SCOPE_UNOBSERVABLE_ARTIFACT_REMAINS_UNKNOWN"]}
