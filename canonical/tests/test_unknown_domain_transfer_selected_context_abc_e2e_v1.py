from canonical.runtime.unknown_domain_transfer_selected_context_abc_e2e_verifier_v1 import verify, _route_pure
from pathlib import Path
import tempfile

def test_current_unknown_domain_e2e_candidate_verifies():
    out=verify()
    assert out["pass"] is True,out
    assert out["production_or_terminal_cases_generated"]==0
    assert out["terminal_credit_delta"]==0
    assert all(not hits for hits in out["route_purity_hits"].values())

def test_material_effect_import_is_rejected():
    with tempfile.TemporaryDirectory() as td:
        p=Path(td)/"x.py"
        p.write_text("import subprocess\nsubprocess.run(['x'])\n",encoding="utf-8")
        hits=_route_pure(p)
        assert any(x.startswith("IMPORT:subprocess") for x in hits)
        assert any(x=="CALL:run" for x in hits)

def test_filesystem_effect_is_rejected():
    with tempfile.TemporaryDirectory() as td:
        p=Path(td)/"x.py"
        p.write_text("open('x','w')\n",encoding="utf-8")
        assert "CALL:open" in _route_pure(p)
