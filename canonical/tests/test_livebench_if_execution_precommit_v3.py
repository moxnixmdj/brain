import copy,json
from pathlib import Path
from canonical.runtime.livebench_if_execution_precommit_v3 import verify_precommit
ROOT=Path(__file__).resolve().parents[2]
MANIFEST=ROOT/"canonical/governance/LIVEBENCH_IF_EXECUTION_PRECOMMIT_V3.json"
def load(): return json.loads(MANIFEST.read_text())
def test_exact_v3_manifest_passes_zero_credit():
    o=verify_precommit(load()); assert o["precommit_pass"] is True
    assert o["legacy_environment_preflight_proved"] is False
    assert o["terminal_cases_consumed_this_epoch"]==0
    assert o["execution_authority"] is False
def test_candidate_mutation_fails():
    x=load(); x["candidate"]["commit"]="0"*40
    assert verify_precommit(x)["precommit_pass"] is False
def test_dispatch_cutoff_mutation_fails():
    x=load(); x["scorer"]["dispatch_cutoff"]="2025-11-26"
    assert verify_precommit(x)["precommit_pass"] is False
def test_missing_legacy_file_fails():
    x=load(); x["scorer"]["verifier_files"]=[r for r in x["scorer"]["verifier_files"] if r[0]!="livebench/if_runner/instruction_following_eval/evaluation_main.py"]
    assert verify_precommit(x)["precommit_pass"] is False
def test_missing_legacy_dependency_fails():
    x=load(); x["environment"]["packages"]=[r for r in x["environment"]["packages"] if r[0]!="langdetect"]
    assert verify_precommit(x)["precommit_pass"] is False
def test_repair_contamination_fails():
    for f in ("repair_design_terminal_prompt_content_used","repair_design_candidate_response_used","repair_design_score_used"):
        x=load(); x["case_exposure"][f]=True
        assert verify_precommit(x)["precommit_pass"] is False
