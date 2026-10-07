import json
from canonical.runtime.gdpval_explicit_acceptance_contract_v1 import compile_task

REV="11e7900cdcac61bc4daf59e65feb238acda98fbf"

def _row(prompt):
    return {
        "task_id":"task-1",
        "prompt":prompt,
        "rubric_json":json.dumps([
            {
                "rubric_item_id":"r1",
                "criterion":"The output includes revenue.",
                "score":1,
                "required":True,
                "author_type":"human",
                "tags":["content"],
                "read_only":False,
                "form_content":None,
            }
        ]),
    }

def test_modal_and_rubric_atoms_are_both_preserved():
    out=compile_task(_row("The report must include revenue."),source_revision=REV)
    assert out["status"]=="COMPILED_EXPLICIT_ACCEPTANCE_CONTRACT_WITH_OPEN_COMPLEMENT"
    assert out["explicit_criterion_count"]==1
    assert out["explicit_requirement_count"]==1
    assert out["explicit_acceptance_atom_count"]==2
    kinds={x["kind"] for x in out["explicit_acceptance_atoms"]}
    assert kinds=={"RUBRIC_CRITERION","MODAL_OBLIGATION"}

def test_imperative_is_preserved_without_argument_semantic_invention():
    out=compile_task(_row("Create a summary workbook."),source_revision=REV)
    assert out["explicit_requirement_count"]==1
    req=out["requirements"][0]
    assert req["kind"]=="IMPERATIVE_RAW_ACTION"
    assert req["directive"]["argument_semantics_resolved"] is False

def test_unresolved_prompt_text_remains_open():
    out=compile_task(_row("Background context may matter in ways not stated here."),source_revision=REV)
    assert out["whole_task_semantic_completeness_claim"] is False
    assert out["policy_adequacy_claim"] is False
    assert out["human_preference_adequacy_claim"] is False
    assert out["open_complement"]["unstated_task_meaning_closed"] is False

def test_malformed_rubric_fails_closed():
    row={"task_id":"t","prompt":"Create a report.","rubric_json":"not-json"}
    out=compile_task(row,source_revision=REV)
    assert out["status"]=="FAIL_CLOSED"
    assert out["reason"].startswith("RUBRIC_INDEX_FAIL_CLOSED")

def test_contract_hash_is_deterministic():
    a=compile_task(_row("Create a summary workbook."),source_revision=REV)
    b=compile_task(_row("Create a summary workbook."),source_revision=REV)
    assert a["contract_sha256"]==b["contract_sha256"]

def test_terminal_credit_remains_zero():
    out=compile_task(_row("Create a summary workbook."),source_revision=REV)
    assert out["terminal_authority"] is False
    assert out["promotion_authority"] is False
    assert out["terminal_credit_delta"]==0
