import json, tempfile
from pathlib import Path
from canonical.runtime.prequalification_stage_a_generic import evaluate

LEDGER="canonical/capabilities/opus55/SESSION_WINDOW_DEBUG_RANK16_CONTAMINATION_LEDGER_V1.json"
TASK="session-window-debug"
RANK=16
HASH="5df6bc292b2d76c3f5832db8e6ef134a1cb5030fcc965ee6997381243e64e49d"

FILES={
"canonical/capabilities/opus55/TB4_V5_TARGET_VERSION_LOCK_V1.json":{"status":"FROZEN_X","benchmark_ref":"452bf305c6daa62fc59061d22133a7cbc7c1572e","stage1_target_success_fraction":0.664,"target_model":"Claude Opus 5.5"},
LEDGER:{"task":TASK,"rank":RANK,"task_identity_sha256":HASH,"benchmark_ref":"452bf305c6daa62fc59061d22133a7cbc7c1572e","state":"UNEXPOSED__STAGE_A_PRE_EXPOSURE","instruction_read":False,"hidden_verifier_read":False,"task_specific_hints_read":False,"task_specific_web_or_repo_search":False,"task_command_executed":False,"clean_for_stage_b_exposure":True,"disqualifying_exposure_events":[],"prior_exposure_search":{"search_complete":True,"searched_surfaces":["brain_code","runner_code","brain_branches","runner_branches","brain_commits","runner_commits","brain_prs","runner_prs"],"brain_code_hits":0,"runner_code_hits":0,"brain_branch_hits":0,"runner_branch_hits":0,"brain_commit_hits":0,"runner_commit_hits":0,"brain_pr_hits":0,"runner_pr_hits":0}},
"canonical/capabilities/opus55/GENERIC_EXECUTION_SURFACE_CERTIFICATE_20261001_V1.json":{"status":"STAGE_A_GENERIC_SURFACE_PASS__TASK_SPECIFIC_SURFACE_UNCLAIMED"},
"canonical/capabilities/opus55/INDEPENDENT_ACCEPTANCE_MODEL_EVIDENCE_V1.json":{"runner":{"source_exact_match":True,"tests_run":6,"tests_passed":6},"heldout_selection":{"result":"BLOCKED_TERMINAL_SUBMISSION_AS_REQUIRED__X"}},
"canonical/capabilities/opus55/REQUIREMENT_GRAPH_KERNEL_001.json":{"status":"INDEPENDENT_VERIFICATION_PASS__X","runner":{"exact_source_match":True,"conclusion":"success"},"donor_runtime_required":False,"independently_verified_behaviors":["SEEDED_REQUIREMENT_MUTATION_SUITE_HAS_ZERO_SURVIVORS_ON_VERIFICATION_CORPUS"]},
"canonical/capabilities/opus55/TB4_V5_STAGE1_STATISTICAL_PROMOTION_PLAN_V1.json":{"status":"FROZEN_X","benchmark_ref":"452bf305c6daa62fc59061d22133a7cbc7c1572e","target_success_fraction":0.664,"replay":False,"cherry_picking":False},
"canonical/governance/DONOR_DELETION_AND_DEPENDENCY_ACCOUNTING_PROTOCOL_V1.json":{"status":"ACTIVE_GENERIC_PROTOCOL__X","fail_closed":True,"pass_rule":"BEHAVIOR_PRESERVED_AND_UNDECLARED_DEPENDENCY_COUNT_ZERO"},
"canonical/governance/PREQUALIFICATION_FAILURE_IMMUNITY_V1.json":{"staged_admission":{"stage_a_pre_exposure":{"required":["TARGET_VERSION_LOCK","QUALIFICATION_CONTAMINATION_LEDGER_CREATED_WITH_PRE_EXPOSURE_IDENTITY","GENERAL_EXECUTION_SURFACE_CERTIFICATE","INDEPENDENT_ACCEPTANCE_MECHANISM_VERIFIED","REQUIREMENT_GRAPH_AND_MUTATION_MECHANISM_VERIFIED","STATISTICAL_PROMOTION_PLAN_FROZEN_IF_BENCHMARK_SCORE_WILL_BE_USED","GENERIC_DONOR_DELETION_AND_DEPENDENCY_ACCOUNTING_PROTOCOL_AVAILABLE","NO_TASK_SPECIFIC_SEARCH_OR_HINT_ACCESS","COMPLETE_8_SURFACE_PRIOR_EXPOSURE_SEARCH_INCLUDING_BRAIN_PRS","TOTAL_STAGE_C_EXECUTION_AND_TERMINAL_BUDGET_GUARD_VERIFIED"]}}},
"canonical/governance/RUNNER_TOTAL_STAGE_C_BUDGET_GUARD_VERIFICATION_20261001_V1.json":{"status":"INDEPENDENT_PASS__MERGED__RANK19_PREEXPOSURE_ELIGIBLE","repair":{"runner_repo":"moxnixmdj/verification-capsule-runner","pr":359,"merge_commit":"bd586c994a601871bc868272e07bdd2a5dd01e54","behavior":["STAGE_C_LEASE_REQUIRES_EXPLICIT_NONNEGATIVE_EXECUTION_AND_TERMINAL_BUDGETS","EVERY_ACCEPTED_BUILDER_BURST_CONSUMES_ONE_EXECUTION_UNIT_BEFORE_ANY_TASK_COMMAND_RUNS","BUILDER_BURST_REJECTED_WHEN_EXECUTION_COUNT_USED_GTE_EXECUTION_COUNT_ALLOWED","TERMINAL_VERIFIER_UNIT_CONSUMED_BEFORE_HIDDEN_VERIFIER_INVOCATION","TERMINAL_SUBMISSION_REJECTED_WHEN_TERMINAL_COUNT_USED_GTE_TERMINAL_VERIFIER_COUNT_ALLOWED","MISSING_OR_ZERO_BUDGET_FAILS_CLOSED"]},"independent_verification":[{"workflow":"Verify independent acceptance gate","run_id":36921835282,"conclusion":"success"},{"workflow":"Stage lease promotion regression","run_id":36921835030,"conclusion":"success"},{"workflow":"Execution Guard Regression","run_id":36921835135,"conclusion":"success"}]},
"canonical/governance/PER_ACTION_CANONICAL_LEASE_REVALIDATION_VERIFICATION_20261001_V1.json":{"status":"VERIFIED_AND_MERGED__RANK15_REVOCATION_ESCAPE_CLASS_BLOCKED","runner":{"verification_tests_failed":0,"verification_tests_passed":9}}
}

def materialize(tmp, files=FILES):
    for p,o in files.items():
        q=Path(tmp)/p; q.parent.mkdir(parents=True,exist_ok=True); q.write_text(json.dumps(o))

def test_clean_complete_exposure_search_passes():
    with tempfile.TemporaryDirectory() as td:
        materialize(td)
        out=evaluate(Path(td),LEDGER,TASK,RANK,HASH)
        assert out["pass"] is True and out["task_execution_authorized"] is False

def test_instruction_read_fails():
    with tempfile.TemporaryDirectory() as td:
        materialize(td); p=Path(td)/LEDGER; o=json.loads(p.read_text()); o["instruction_read"]=True; p.write_text(json.dumps(o))
        assert evaluate(Path(td),LEDGER,TASK,RANK,HASH)["pass"] is False

def test_prior_exposure_hit_fails():
    with tempfile.TemporaryDirectory() as td:
        materialize(td); p=Path(td)/LEDGER; o=json.loads(p.read_text()); o["prior_exposure_search"]["runner_pr_hits"]=1; p.write_text(json.dumps(o))
        assert evaluate(Path(td),LEDGER,TASK,RANK,HASH)["pass"] is False

def test_revocation_guard_missing_fails():
    with tempfile.TemporaryDirectory() as td:
        materialize(td); p=Path(td)/"canonical/governance/PER_ACTION_CANONICAL_LEASE_REVALIDATION_VERIFICATION_20261001_V1.json"; o=json.loads(p.read_text()); o["runner"]["verification_tests_failed"]=1; p.write_text(json.dumps(o))
        assert evaluate(Path(td),LEDGER,TASK,RANK,HASH)["pass"] is False

def test_brain_pr_prior_exposure_fails():
    with tempfile.TemporaryDirectory() as td:
        materialize(td); p=Path(td)/LEDGER; o=json.loads(p.read_text())
        o["prior_exposure_search"]["brain_pr_hits"]=1
        p.write_text(json.dumps(o))
        out=evaluate(Path(td),LEDGER,TASK,RANK,HASH)
        assert out["pass"] is False
        # v1 replaced the blanket NOT_CLEAN predicate with a classification
        # model: an unclassified nonzero raw hit is incomplete classification.
        assert "PRIOR_EXPOSURE_HIT_CLASSIFICATION_INCOMPLETE" in out["failed_predicates"]

def test_missing_exposure_surface_fails():
    with tempfile.TemporaryDirectory() as td:
        materialize(td); p=Path(td)/LEDGER; o=json.loads(p.read_text())
        del o["prior_exposure_search"]["brain_pr_hits"]
        p.write_text(json.dumps(o))
        out=evaluate(Path(td),LEDGER,TASK,RANK,HASH)
        assert out["pass"] is False
        assert "PRIOR_EXPOSURE_SEARCH_FIELDS_MISSING" in out["failed_predicates"]

def test_incomplete_exposure_search_fails():
    with tempfile.TemporaryDirectory() as td:
        materialize(td); p=Path(td)/LEDGER; o=json.loads(p.read_text())
        o["prior_exposure_search"]["search_complete"]=False
        p.write_text(json.dumps(o))
        out=evaluate(Path(td),LEDGER,TASK,RANK,HASH)
        assert out["pass"] is False
        assert "PRIOR_EXPOSURE_SEARCH_INCOMPLETE" in out["failed_predicates"]

def test_policy_without_eight_surface_requirement_fails():
    # Regression: this fixture silently omitted the eight-surface policy item
    # after the reducer began requiring it, which made every case in this module
    # fail closed with STAGE_A_POLICY_INCOMPLETE while asserting a pass.
    pol="canonical/governance/PREQUALIFICATION_FAILURE_IMMUNITY_V1.json"
    files={k:(json.loads(json.dumps(v)) if isinstance(v,dict) else v) for k,v in FILES.items()}
    req=files[pol]["staged_admission"]["stage_a_pre_exposure"]["required"]
    req.remove("COMPLETE_8_SURFACE_PRIOR_EXPOSURE_SEARCH_INCLUDING_BRAIN_PRS")
    with tempfile.TemporaryDirectory() as td:
        materialize(td,files)
        out=evaluate(Path(td),LEDGER,TASK,RANK,HASH)
        assert out["pass"] is False
        assert "STAGE_A_POLICY_INCOMPLETE" in out["failed_predicates"]

def test_unmerged_runner_budget_guard_fails():
    bud="canonical/governance/RUNNER_TOTAL_STAGE_C_BUDGET_GUARD_VERIFICATION_20261001_V1.json"
    files={k:(json.loads(json.dumps(v)) if isinstance(v,dict) else v) for k,v in FILES.items()}
    files[bud]["status"]="PROPOSED__NOT_MERGED"
    with tempfile.TemporaryDirectory() as td:
        materialize(td,files)
        out=evaluate(Path(td),LEDGER,TASK,RANK,HASH)
        assert out["pass"] is False
        assert "TOTAL_STAGE_C_EXECUTION_AND_TERMINAL_BUDGET_GUARD" in out["failed_predicates"]

def test_later_rank_lease_revalidation_still_passes():
    lea="canonical/governance/PER_ACTION_CANONICAL_LEASE_REVALIDATION_VERIFICATION_20261001_V1.json"
    files={k:(json.loads(json.dumps(v)) if isinstance(v,dict) else v) for k,v in FILES.items()}
    files[lea]["status"]="VERIFIED_AND_MERGED__RANK22_REVOCATION_ESCAPE_CLASS_BLOCKED"
    with tempfile.TemporaryDirectory() as td:
        materialize(td,files)
        assert evaluate(Path(td),LEDGER,TASK,RANK,HASH)["pass"] is True
