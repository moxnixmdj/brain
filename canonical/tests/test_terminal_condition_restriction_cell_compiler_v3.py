from __future__ import annotations
import json
import tempfile
from pathlib import Path

from canonical.runtime.terminal_condition_restriction_cell_compiler_v3 import (
    compile_condition_cells_v3, git_blob_sha_bytes, ConditionRestrictionV3Error
)

def _write(root: Path, rel: str, obj) -> str:
    p=root/rel; p.parent.mkdir(parents=True,exist_ok=True)
    data=(json.dumps(obj,sort_keys=True)+"\n").encode()
    p.write_bytes(data)
    return git_blob_sha_bytes(data)

def _base(root: Path):
    matrix={
        "shared_condition_matrix":[
            {"condition":"C1","mapped_family_union":["F1","F2"]},
            {"condition":"HONESTY_AND_COMPLETION_INTEGRITY","mapped_family_union":["F2"]},
        ]
    }
    source={"result":"PASS"}
    source_sha=_write(root,"evidence/f1.json",source)
    ledger={"claims":[{
        "predicate_id":"P1","family":"F1","state":"PROVED",
        "scope_complete":True,"independent_or_objective":True,
        "objective_ceiling":True,
        "scope_completeness":{"all_admissible_target_inputs_proved":True,"formal_completeness":True},
        "source_path":"evidence/f1.json","source_sha":source_sha
    }]}
    msha=_write(root,"matrix.json",matrix)
    lsha=_write(root,"ledger.json",ledger)
    return matrix,ledger,msha,lsha,source_sha

def test_ledger_universal_closes_only_mapped_family_cells():
    with tempfile.TemporaryDirectory() as d:
        root=Path(d); matrix,ledger,msha,lsha,_=_base(root)
        out=compile_condition_cells_v3(matrix=matrix,ledger=ledger,repo_root=root,matrix_path="matrix.json",matrix_sha=msha,ledger_path="ledger.json",ledger_sha=lsha)
        assert out["total_cells"]==3
        assert out["closed_cells"]==1
        assert out["honesty_closed_cells"]==0

def test_nonuniversal_ledger_claim_does_not_close():
    with tempfile.TemporaryDirectory() as d:
        root=Path(d); matrix,ledger,msha,_,_= _base(root)
        ledger["claims"][0]["scope_completeness"]["formal_completeness"]=False
        lsha=_write(root,"ledger.json",ledger)
        out=compile_condition_cells_v3(matrix=matrix,ledger=ledger,repo_root=root,matrix_path="matrix.json",matrix_sha=msha,ledger_path="ledger.json",ledger_sha=lsha)
        assert out["closed_cells"]==0

def test_ledger_source_blob_mismatch_fails_claim_closed():
    with tempfile.TemporaryDirectory() as d:
        root=Path(d); matrix,ledger,msha,_,_= _base(root)
        ledger["claims"][0]["source_sha"]="0"*40
        lsha=_write(root,"ledger.json",ledger)
        out=compile_condition_cells_v3(matrix=matrix,ledger=ledger,repo_root=root,matrix_path="matrix.json",matrix_sha=msha,ledger_path="ledger.json",ledger_sha=lsha)
        assert out["closed_cells"]==0

def test_composite_receipt_closes_only_bytes_declared_conditions():
    with tempfile.TemporaryDirectory() as d:
        root=Path(d); matrix,ledger,msha,lsha,_=_base(root)
        src_sha=_write(root,"evidence/f2.json",{"result":"PASS"})
        receipt={
            "matrix":{"path":"matrix.json","git_blob_sha":msha},
            "family":"F2","covered_conditions":["C1"],
            "proof_class":"OBJECTIVE_CEILING","scope_complete":True,"independent_or_objective":True,
            "source":{"path":"evidence/f2.json","git_blob_sha":src_sha}
        }
        rsha=_write(root,"receipts/f2.json",receipt)
        out=compile_condition_cells_v3(matrix=matrix,ledger=ledger,repo_root=root,matrix_path="matrix.json",matrix_sha=msha,ledger_path="ledger.json",ledger_sha=lsha,composite_receipts=[{"path":"receipts/f2.json","git_blob_sha":rsha}])
        assert out["closed_cells"]==2
        assert out["honesty_closed_cells"]==0

def test_composite_wrong_matrix_binding_rejected():
    with tempfile.TemporaryDirectory() as d:
        root=Path(d); matrix,ledger,msha,lsha,_=_base(root)
        src_sha=_write(root,"evidence/f2.json",{"result":"PASS"})
        receipt={
            "matrix":{"path":"matrix.json","git_blob_sha":"0"*40},
            "family":"F2","covered_conditions":["HONESTY_AND_COMPLETION_INTEGRITY"],
            "proof_class":"OBJECTIVE_CEILING","scope_complete":True,"independent_or_objective":True,
            "source":{"path":"evidence/f2.json","git_blob_sha":src_sha}
        }
        rsha=_write(root,"receipts/f2.json",receipt)
        out=compile_condition_cells_v3(matrix=matrix,ledger=ledger,repo_root=root,matrix_path="matrix.json",matrix_sha=msha,ledger_path="ledger.json",ledger_sha=lsha,composite_receipts=[{"path":"receipts/f2.json","git_blob_sha":rsha}])
        assert out["honesty_closed_cells"]==0
        assert any(x["reason"]=="MATRIX_BINDING_MISMATCH" for x in out["rejections"])

def test_composite_unmapped_condition_rejected():
    with tempfile.TemporaryDirectory() as d:
        root=Path(d); matrix,ledger,msha,lsha,_=_base(root)
        src_sha=_write(root,"evidence/f2.json",{"result":"PASS"})
        receipt={
            "matrix":{"path":"matrix.json","git_blob_sha":msha},
            "family":"F1","covered_conditions":["HONESTY_AND_COMPLETION_INTEGRITY"],
            "proof_class":"OBJECTIVE_CEILING","scope_complete":True,"independent_or_objective":True,
            "source":{"path":"evidence/f2.json","git_blob_sha":src_sha}
        }
        rsha=_write(root,"receipts/bad.json",receipt)
        out=compile_condition_cells_v3(matrix=matrix,ledger=ledger,repo_root=root,matrix_path="matrix.json",matrix_sha=msha,ledger_path="ledger.json",ledger_sha=lsha,composite_receipts=[{"path":"receipts/bad.json","git_blob_sha":rsha}])
        assert any(str(x["reason"]).startswith("UNMAPPED_CONDITION") for x in out["rejections"])

def test_top_level_matrix_blob_mismatch_fails_hard():
    with tempfile.TemporaryDirectory() as d:
        root=Path(d); matrix,ledger,msha,lsha,_=_base(root)
        try:
            compile_condition_cells_v3(matrix=matrix,ledger=ledger,repo_root=root,matrix_path="matrix.json",matrix_sha="0"*40,ledger_path="ledger.json",ledger_sha=lsha)
        except ConditionRestrictionV3Error as e:
            assert "MATRIX_BLOB_IDENTITY_MISMATCH" in str(e)
        else:
            raise AssertionError("bad matrix sha accepted")

def test_duplicate_condition_fails_hard():
    with tempfile.TemporaryDirectory() as d:
        root=Path(d); matrix,ledger,msha,lsha,_=_base(root)
        matrix["shared_condition_matrix"].append({"condition":"C1","mapped_family_union":["F1"]})
        msha=_write(root,"matrix.json",matrix)
        try:
            compile_condition_cells_v3(matrix=matrix,ledger=ledger,repo_root=root,matrix_path="matrix.json",matrix_sha=msha,ledger_path="ledger.json",ledger_sha=lsha)
        except ConditionRestrictionV3Error as e:
            assert "DUPLICATE_CONDITION" in str(e)
        else:
            raise AssertionError("duplicate condition accepted")

def run_all():
    tests=[
      test_ledger_universal_closes_only_mapped_family_cells,
      test_nonuniversal_ledger_claim_does_not_close,
      test_ledger_source_blob_mismatch_fails_claim_closed,
      test_composite_receipt_closes_only_bytes_declared_conditions,
      test_composite_wrong_matrix_binding_rejected,
      test_composite_unmapped_condition_rejected,
      test_top_level_matrix_blob_mismatch_fails_hard,
      test_duplicate_condition_fails_hard,
    ]
    for t in tests: t()
    return len(tests)

if __name__=="__main__":
    print(f"PASS {run_all()}/8")
