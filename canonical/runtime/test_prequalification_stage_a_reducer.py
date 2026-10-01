import json, tempfile
from pathlib import Path
from canonical.runtime.prequalification_stage_a_reducer import evaluate

BASE={
"canonical/capabilities/opus55/TB4_V5_TARGET_VERSION_LOCK_V1.json":{"status":"FROZEN_BEFORE_RANK15_INSTRUCTION_EXPOSURE","benchmark_ref":"452bf305c6daa62fc59061d22133a7cbc7c1572e","stage1_target_success_fraction":0.664,"target_model":"Claude Opus 5.5"},
"canonical/capabilities/opus55/GENERIC_EXECUTION_SURFACE_CERTIFICATE_20261001_V1.json":{"status":"STAGE_A_GENERIC_SURFACE_PASS__TASK_SPECIFIC_SURFACE_UNCLAIMED"},
"canonical/capabilities/opus55/INDEPENDENT_ACCEPTANCE_MODEL_EVIDENCE_V1.json":{"runner":{"source_exact_match":True,"tests_run":6,"tests_passed":6},"heldout_selection":{"result":"BLOCKED_TERMINAL_SUBMISSION_AS_REQUIRED__X"}},
"canonical/capabilities/opus55/REQUIREMENT_GRAPH_KERNEL_001.json":{"status":"INDEPENDENT_VERIFICATION_PASS__X","runner":{"exact_source_match":True,"conclusion":"success"},"donor_runtime_required":False,"independently_verified_behaviors":["SEEDED_REQUIREMENT_MUTATION_SUITE_HAS_ZERO_SURVIVORS_ON_VERIFICATION_CORPUS"]},
"canonical/capabilities/opus55/TB4_V5_STAGE1_STATISTICAL_PROMOTION_PLAN_V1.json":{"status":"FROZEN_BEFORE_RANK15_INSTRUCTION_EXPOSURE","benchmark_ref":"452bf305c6daa62fc59061d22133a7cbc7c1572e","target_success_fraction":0.664,"replay":False,"cherry_picking":False},
"canonical/governance/DONOR_DELETION_AND_DEPENDENCY_ACCOUNTING_PROTOCOL_V1.json":{"status":"ACTIVE_GENERIC_PROTOCOL__X","fail_closed":True,"pass_rule":"BEHAVIOR_PRESERVED_AND_UNDECLARED_DEPENDENCY_COUNT_ZERO"},
"canonical/governance/PREQUALIFICATION_FAILURE_IMMUNITY_V1.json":{"staged_admission":{"stage_a_pre_exposure":{"required":["TARGET_VERSION_LOCK","QUALIFICATION_CONTAMINATION_LEDGER_CREATED_WITH_PRE_EXPOSURE_IDENTITY","GENERAL_EXECUTION_SURFACE_CERTIFICATE","INDEPENDENT_ACCEPTANCE_MECHANISM_VERIFIED","REQUIREMENT_GRAPH_AND_MUTATION_MECHANISM_VERIFIED","STATISTICAL_PROMOTION_PLAN_FROZEN_IF_BENCHMARK_SCORE_WILL_BE_USED","GENERIC_DONOR_DELETION_AND_DEPENDENCY_ACCOUNTING_PROTOCOL_AVAILABLE","NO_TASK_SPECIFIC_SEARCH_OR_HINT_ACCESS"]}}}
}
R15="canonical/capabilities/opus55/WDM_DESIGN_RANK15_CONTAMINATION_LEDGER_V1.json"
R16="canonical/capabilities/opus55/SESSION_WINDOW_DEBUG_RANK16_CONTAMINATION_LEDGER_V1.json"

def ledger(task,rank):
    return {"task":task,"rank":rank,"benchmark_ref":"452bf305c6daa62fc59061d22133a7cbc7c1572e","state":"UNEXPOSED__STAGE_A_PRE_EXPOSURE","instruction_read":False,"hidden_verifier_read":False,"task_specific_hints_read":False,"task_specific_web_or_repo_search":False,"task_command_executed":False,"clean_for_stage_b_exposure":True,"disqualifying_exposure_events":[]}

def materialize(tmp, extra=None):
    files=dict(BASE)
    files[R15]=ledger("wdm-design",15)
    files[R16]=ledger("session-window-debug",16)
    if extra: files.update(extra)
    for p,o in files.items():
        q=Path(tmp)/p; q.parent.mkdir(parents=True,exist_ok=True); q.write_text(json.dumps(o))

def test_rank15_backward_compatible_pass():
    with tempfile.TemporaryDirectory() as td:
        materialize(td)
        out=evaluate(Path(td),R15)
        assert out["pass"] is True and out["task"]=="wdm-design" and out["rank"]==15
        assert out["task_execution_authorized"] is False

def test_rank16_generic_pass():
    with tempfile.TemporaryDirectory() as td:
        materialize(td)
        out=evaluate(Path(td),R16)
        assert out["pass"] is True and out["task"]=="session-window-debug" and out["rank"]==16
        assert out["task_execution_authorized"] is False

def test_task_specific_search_fails_for_any_task():
    with tempfile.TemporaryDirectory() as td:
        bad=ledger("session-window-debug",16); bad["task_specific_web_or_repo_search"]=True
        materialize(td,{R16:bad})
        assert evaluate(Path(td),R16)["pass"] is False

def test_instruction_exposure_fails_stage_a():
    with tempfile.TemporaryDirectory() as td:
        bad=ledger("session-window-debug",16); bad["instruction_read"]=True
        materialize(td,{R16:bad})
        assert evaluate(Path(td),R16)["pass"] is False

def test_missing_identity_fails():
    with tempfile.TemporaryDirectory() as td:
        bad=ledger("",16)
        materialize(td,{R16:bad})
        out=evaluate(Path(td),R16)
        assert out["pass"] is False
        assert "QUALIFICATION_IDENTITY" in out["failed_predicates"]

def test_missing_mutation_evidence_fails():
    with tempfile.TemporaryDirectory() as td:
        bad=dict(BASE["canonical/capabilities/opus55/REQUIREMENT_GRAPH_KERNEL_001.json"])
        bad["independently_verified_behaviors"]=[]
        materialize(td,{"canonical/capabilities/opus55/REQUIREMENT_GRAPH_KERNEL_001.json":bad})
        assert evaluate(Path(td),R16)["pass"] is False
