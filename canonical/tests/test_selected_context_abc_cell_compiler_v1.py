import json
from pathlib import Path
from canonical.runtime.selected_context_abc_cell_compiler_v1 import compile_cell

ROOT=Path(__file__).resolve().parents[2]
MANIFEST=ROOT/"canonical/governance/LIVEBENCH_IF_SELECTED_CONTEXT_ABC_CELL_INPUT_20261007_V1.json"

def load():
    return json.loads(MANIFEST.read_text(encoding="utf-8"))

def test_livebench_seed_compiles_under_generic_cell_contract():
    out=compile_cell(load())
    assert out["pass"] is True,out
    assert out["status"]=="PASS__STRUCTURAL_PROOF_CARRYING_ABC_CELL"
    assert out["route_file_count"]==6
    assert out["verified_check_count"]==10
    assert out["terminal_credit_delta"]==0

def test_scope_claim_tamper_fails_closed():
    x=load()
    x["target_scope"]["checks"][0]["equals"]=False
    out=compile_cell(x)
    assert out["pass"] is False
    assert "TARGET_SCOPE_CHECK_FAIL" in out["errors"][0]

def test_route_blob_tamper_fails_closed():
    x=load()
    x["selected_route"]["operative_files"][0]["git_blob_sha"]="0"*40
    out=compile_cell(x)
    assert out["pass"] is False
    assert "ROUTE_BLOB_DRIFT" in out["errors"][0]

def test_nonzero_credit_fails_closed():
    x=load()
    x["accounting"]["terminal_credit_delta"]=1
    out=compile_cell(x)
    assert out["pass"] is False
    assert "NONZERO_CREDIT_OR_SPEND" in out["errors"][0]
