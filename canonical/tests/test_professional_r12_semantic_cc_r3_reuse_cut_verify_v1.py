from __future__ import annotations
import json
from pathlib import Path
import shutil
import tempfile

from canonical.runtime import professional_r12_semantic_cc_r3_reuse_cut_verify_v1 as v


def _copy_fixture(tmp: Path) -> None:
    root=Path(__file__).resolve().parents[2]
    paths=[v.CUT,*[rel for rel,_ in v.PINS.values()]]
    for rel in paths:
        src=root/rel
        dst=tmp/rel
        dst.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(src,dst)


def _write(path: Path, doc) -> None:
    path.write_text(json.dumps(doc,indent=2)+"\n",encoding="utf-8")


def test_current_exact_reuse_cut_passes():
    out=v.verify()
    assert out["pass"] is True,out
    assert out["proved_by_reuse_count"]==2
    assert out["open_root_contract_clause_count"]==6
    assert out["stronger_material_defeater_obligation_open"] is True
    assert out["unknown_defeater_completeness_proved"] is False
    assert out["cc_r3_terminal_closure_proved"] is False


def test_c8_cannot_be_promoted_from_synthetic_positive_execution_cases():
    with tempfile.TemporaryDirectory() as d:
        tmp=Path(d);_copy_fixture(tmp)
        cut=json.loads((tmp/v.CUT).read_text())
        row=next(x for x in cut["clause_reuse"] if x["id"]=="R12C8_NONVACUITY")
        row["state"]="PROVED_BY_REUSE"
        cut["derived"]["proved_by_reuse_count"]=3
        cut["derived"]["open_root_contract_clause_count"]=5
        _write(tmp/v.CUT,cut)
        out=v.verify(repo_root=tmp)
    assert out["pass"] is False
    assert out["reason"]=="CUT_PROVED_SET_OVER_OR_UNDERCLAIM"


def test_unknown_defeater_completeness_must_remain_open():
    with tempfile.TemporaryDirectory() as d:
        tmp=Path(d);_copy_fixture(tmp)
        cut=json.loads((tmp/v.CUT).read_text())
        cut["stronger_target_predicate_residual"]["state"]="PROVED"
        cut["stronger_target_predicate_residual"]["unknown_defeater_completeness_proved"]=True
        _write(tmp/v.CUT,cut)
        out=v.verify(repo_root=tmp)
    assert out["pass"] is False
    assert out["reason"]=="STRONGER_TARGET_RESIDUAL_OVERCLAIM"


def test_same_subject_clause_cannot_be_silently_reopened_or_replaced():
    with tempfile.TemporaryDirectory() as d:
        tmp=Path(d);_copy_fixture(tmp)
        cut=json.loads((tmp/v.CUT).read_text())
        row=next(x for x in cut["clause_reuse"] if x["id"]=="R12C2_SAME_SUBJECT_ROOT_CONJUNCTION")
        row["state"]="OPEN"
        cut["derived"]["proved_by_reuse_count"]=1
        cut["derived"]["open_root_contract_clause_count"]=7
        _write(tmp/v.CUT,cut)
        out=v.verify(repo_root=tmp)
    assert out["pass"] is False
    assert out["reason"]=="CUT_PROVED_SET_OVER_OR_UNDERCLAIM"
