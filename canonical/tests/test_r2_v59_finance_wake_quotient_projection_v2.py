import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
P={"q":"canonical/governance/R2_FINANCE_SEMANTIC_WAKE_INFORMATION_QUOTIENT_20261009_V3.json","s":"canonical/governance/ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261009_V56.json","r":"canonical/governance/CURRENT_R2_DECISION_INTELLIGENCE.json","o":"canonical/governance/CURRENT_ONE_SHOT_REALITY_CLOSURE.json","t":"canonical/governance/CURRENT_TERMINAL_AUTHORITY.json"}
E={"q":"62dc4ad2309f392aba22982952cc83484d68092c","s":"63bced83808aa1b0d8277e8aba39dec641ffc185","r":"697e19eaa32dba6c55e6964b78cdf850fec65bac","o":"9013467a7c25ec7a5fb0b7e1b47057c42fcfd8a0","t":"7586707fcf98655b068ab6392e82e7c06eb900b1"}
def b(p):
 d=p.read_bytes(); h=hashlib.sha1(); h.update(b"blob "+str(len(d)).encode()+b"\0"+d); return h.hexdigest()
def L(k):
 p=ROOT/P[k]; assert b(p)==E[k],(k,b(p),E[k]); return json.loads(p.read_text())
def test_latest_main_v59_projection():
 q,s,r,o,t=[L(k) for k in "qsrot"]
 assert len(q["normalization_map"])==11 and len(set(q["normalization_map"].values()))==3
 assert r["status"].startswith("ACTIVE_CURRENT_R2_AUTHORITY__V59__")
 c=r["current_cell_classifications"]["FINANCE_SEMANTIC_ADEQUACY_TAIL"]
 ids={x["id"] for x in c["verified_positive_subregions"]}
 assert "BOUND_REGCAP_LOSS_CUSHION_SAME_SENTENCE_CONTEXTUAL_RELATIVE_SELECTION" in ids
 assert "BOUND_REGCAP_CONTEXTUAL_SOURCE_FACT_PROOFS" in ids
 assert "regcap_contextual_default_domain_mapping" in r and "regcap_context_atom_truth_dispatch" in r
 assert c["state"]=="INTERNAL_UNSOLVED__PENDING_ACQUISITION_OR_EXPERIMENT" and c["information_theoretic_externality_proved"] is False
 assert o["authority"]["current_r2_pointer_git_blob_sha"]==E["r"] and o["authority"]["r2_finance_tail_closed"] is False
 assert "ROOT_NAMESPACE_COLLISION_GUARDED" in t["status"]
 assert t["authoritative_sources"]["coverage_root_namespace_bridge"]["git_blob_sha"]=="fd45e0fcfdd238cdae022fc58ce418c9151186f1"
 assert t["live_truth"]["current_r2_pointer_git_blob_sha"]==E["r"]
 assert t["live_truth"]["r2_finance_wake_decision_effect_class_count"]==3
 assert t["live_truth"]["r2_primary_internal_unsolved_count"]==1 and t["live_truth"]["r2_finance_semantic_tail_closed"] is False
 assert t["live_truth"]["terminal"] is False
 assert t["r2_v59_finance_wake_information_quotient_reconciliation"]["latest_semantic_gains_preserved"] is True
