from copy import deepcopy
import importlib.util
import json
from pathlib import Path

P = Path(__file__).resolve().parents[1] / "runtime" / "gdpval_public_rubric_contract_v1.py"
spec = importlib.util.spec_from_file_location("gdpval_public_rubric_contract_v1", P)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)

def item(i: str, criterion: str, score: int = 2):
    return {"rubric_item_id": i, "criterion": criterion, "score": score,
            "required": None, "author_type": "human", "tags": ["true"],
            "read_only": None, "form_content": None}

def rows():
    return [
        {"row_idx": 0, "row": {"task_id": "t0", "rubric_json": json.dumps([item("r0", "Criterion A")])}},
        {"row_idx": 1, "row": {"task_id": "t1", "rubric_json": json.dumps([item("r1", "Criterion B", 3), item("r2", "Criterion C", 1)])}},
    ]

def test_compiles_exact_population_and_never_mints_authority():
    x = mod.compile_population(rows(), expected_task_count=2, expected_item_count=3)
    assert x["status"] == "COMPILED"
    assert (x["task_count"], x["rubric_item_count"], x["unique_rubric_item_id_count"]) == (2, 3, 3)
    assert x["rubric_score_total"] == 6.0
    assert x["exact_public_evaluator_criteria_bound"] is True
    assert x["criterion_semantics_inferred"] is False
    assert x["pairwise_human_preference_law_complete"] is False
    assert x["policy_adequacy_authority"] is False
    assert x["terminal_authority"] is False

def test_population_manifest_is_deterministic_and_content_sensitive():
    a = mod.compile_population(rows())
    b = mod.compile_population(rows())
    assert a["population_manifest_sha256"] == b["population_manifest_sha256"]
    changed = rows()
    payload = json.loads(changed[1]["row"]["rubric_json"])
    payload[0]["criterion"] = "Criterion B changed"
    changed[1]["row"]["rubric_json"] = json.dumps(payload)
    assert mod.compile_population(changed)["population_manifest_sha256"] != a["population_manifest_sha256"]

def test_rejects_duplicate_global_rubric_id():
    bad = rows()
    payload = json.loads(bad[1]["row"]["rubric_json"])
    payload[0]["rubric_item_id"] = "r0"
    bad[1]["row"]["rubric_json"] = json.dumps(payload)
    x = mod.compile_population(bad)
    assert x["status"] == "FAIL_CLOSED"
    assert x["reason"] == "DUPLICATE_RUBRIC_ITEM_ID_GLOBAL"

def test_rejects_noncontiguous_rows_and_wrong_expected_count():
    bad = rows()
    bad[1] = deepcopy(bad[1])
    bad[1]["row_idx"] = 3
    assert mod.compile_population(bad)["reason"] == "ROW_INDICES_NOT_CONTIGUOUS"
    assert mod.compile_population(rows(), expected_task_count=220)["reason"] == "TASK_COUNT_MISMATCH"
    assert mod.compile_population(rows(), expected_item_count=10453)["reason"] == "RUBRIC_ITEM_COUNT_MISMATCH"

def test_rejects_invalid_or_empty_criterion():
    bad = rows()
    bad[0] = deepcopy(bad[0])
    bad[0]["row"]["rubric_json"] = "not-json"
    assert mod.compile_population(bad)["reason"] == "RUBRIC_JSON_INVALID"
    bad2 = rows()
    payload = json.loads(bad2[0]["row"]["rubric_json"])
    payload[0]["criterion"] = "   "
    bad2[0]["row"]["rubric_json"] = json.dumps(payload)
    assert mod.compile_population(bad2)["reason"] == "CRITERION_MISSING"
