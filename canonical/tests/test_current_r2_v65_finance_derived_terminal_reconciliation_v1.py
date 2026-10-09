import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
R2=ROOT/"canonical/governance/CURRENT_R2_DECISION_INTELLIGENCE.json"
PTR=ROOT/"canonical/governance/CURRENT_R2_DIRECT_ROUTE_ADMISSIONS.json"
VER=ROOT/"canonical/verification/R2_FINANCE_DERIVED_TERMINAL_SIGNATURES_DIRECT_ADEQUACY_VERIFY_20261009_V1.json"
PRO=ROOT/"canonical/verification/R2_FINANCE_DERIVED_TYPED_TERMINALS_LIVE_PROMOTION_VERIFY_20261009_V1.json"
CAN=ROOT/"canonical/governance/R2_DIRECT_ROUTE_DEPLOYMENT_CANDIDATE_FINANCE_DERIVED_TYPED_TERMINALS_20261009_V1.json"
def blob(p):
 d=p.read_bytes(); h=hashlib.sha1(); h.update(b"blob "+str(len(d)).encode()+b"\0"+d); return h.hexdigest()
def test_r2_v65_reconciles_derived_terminal_route_without_overclaim():
 r=json.loads(R2.read_text()); p=json.loads(PTR.read_text())
 m=json.loads((ROOT/p["target"]["path"]).read_text())
 assert r["status"].startswith("ACTIVE_CURRENT_R2_AUTHORITY__V65__FORTY_DIRECT_ROUTES")
 assert r["scheduler_result"]["direct_route_count"]==40
 assert m["admission_count"]==3
 row=r["finance_derived_typed_terminal_signatures_direct_adequacy"]
 assert row["candidate_git_blob_sha"]==blob(CAN)
 assert row["route_verification_git_blob_sha"]==blob(VER)
 assert row["live_promotion_verification_git_blob_sha"]==blob(PRO)
 assert row["current_dynamic_admissions_git_blob_sha"]==blob(ROOT/p["target"]["path"])
 assert row["terminal_signatures_derived_not_caller_asserted"] is True
 assert row["raw_prose_to_typed_decision_problem_correctness_proved"] is False
 assert row["open_world_plain_text_mention_completeness_proved"] is False
 assert row["global_finance_semantic_tail_closed"] is False
 rec=r["r2_v65_finance_derived_terminal_reconciliation"]
 assert rec["current_dynamic_admission_count"]==3
 assert rec["finance_tail_closed"] is False
 assert rec["universal_escape_obstruction_class_proved"] is False
 assert rec["acceptance_credit_delta"]==0 and rec["terminal_credit_delta"]==0
