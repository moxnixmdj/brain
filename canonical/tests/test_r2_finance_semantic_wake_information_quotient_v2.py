import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
Q=ROOT/"canonical/governance/R2_FINANCE_SEMANTIC_WAKE_INFORMATION_QUOTIENT_20261009_V2.json"
S=ROOT/"canonical/governance/ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261009_V56.json"
def blob(p):
 d=p.read_bytes(); h=hashlib.sha1(); h.update(b"blob "+str(len(d)).encode()+b"\0"+d); return h.hexdigest()
def test_v59_finance_wake_quotient_is_total_and_zero_credit():
 q=json.loads(Q.read_text()); s=json.loads(S.read_text())
 assert q["prestate"]["current_r2_git_blob_sha"]=="d45b5cdc0e0bbbfb44d88c37a5761776afbcf5fd"
 assert q["prestate"]["scheduler_git_blob_sha"]=="a7c04b0ceb3b28deacfa078c11e70e7841445d78"
 assert len(q["normalization_map"])==11
 assert set(q["normalization_map"].values())=={"COMMON_POLICY_ADEQUACY_BYPASS","DIRECT_END_TO_END_ADEQUACY_BYPASS","AUTHENTICATED_WORLD_DISCRIMINATOR_OR_CONSTRAINT"}
 assert "BOUND_REGCAP_LOSS_CUSHION_SAME_SENTENCE_CONTEXTUAL_RELATIVE_SELECTION" in q["preserves_current_v58_semantic_gains"]
 assert "BOUND_REGCAP_CONTEXTUAL_SOURCE_FACT_PROOFS" in q["preserves_current_v58_semantic_gains"]
 assert q["theorem"]["does_not_prove_finance_closed"] is True
 assert q["theorem"]["does_not_prove_externality"] is True
 assert q["accounting"]["terminal_credit_delta"]==0
 fq=s["finance_semantic_wake_information_quotient"]
 assert fq["effect_class_count"]==3 and fq["concrete_wake_condition_count"]==11
 assert fq["finance_tail_closed"] is False
 assert fq["information_theoretic_externality_proved"] is False
 assert s["accounting"]["terminal_credit_delta"]==0
