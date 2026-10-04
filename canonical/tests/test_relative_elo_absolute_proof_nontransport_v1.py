import importlib.util
from pathlib import Path

P=Path(__file__).resolve().parents[1]/"runtime"/"relative_elo_absolute_proof_nontransport_verifier_v1.py"
spec=importlib.util.spec_from_file_location("v",P)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

def test_relative_elo_nontransport_candidate():
    m.check()
