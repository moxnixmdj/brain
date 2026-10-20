"""Two independent oracles must agree -- in BOTH directions.

Agreement on positives alone proves nothing: two oracles that always say
"violation" would agree perfectly.  These tests therefore pin the negative
control too: on correct programs both oracles must stay silent.
"""
from __future__ import annotations

import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "capabilities" / "true" / "generators"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "runtime" / "bound_capabilities"))

import python_contract_mutation_gen_v1 as G  # noqa: E402
import concrete_execution_oracle as CONC  # noqa: E402
import crosshair_contract_oracle as SMT  # noqa: E402


def _smt(source: str) -> str:
    with tempfile.TemporaryDirectory() as d:
        root = pathlib.Path(d)
        tp = root / "t.py"
        tp.write_text(source)
        return SMT.run({"target_path": tp.as_posix(),
                        "output_path": (root / "o.json").as_posix()}, str(root))["status"]


def _conc(source: str) -> str:
    return "VIOL" if CONC.check_source(source)["violations"] else "CLEAN"


def test_the_oracles_agree_on_a_sample_of_violations():
    for inst in G.generate(12):
        assert _smt(inst["source"]) == "CONTRACT_VIOLATION_FOUND", inst["instance_id"]
        assert _conc(inst["source"]) == "VIOL", inst["instance_id"]


def test_neither_oracle_fires_on_correct_programs():
    """The negative control.  False positives would void the whole claim."""
    checked = 0
    for fam in G.FAMILIES:
        ks = sorted({c[1] for c in G._combinations()
                     if c[0]["name"] == fam["name"]})[:3]
        for k in ks:
            contract = G._render(fam["contract"], k)
            expr = G._render(fam["correct"], k)
            src = f'def f(x: int) -> int:\n    """{contract}"""\n    return {expr}\n'
            assert _smt(src) == "CONTRACTS_HOLD", (fam["name"], k, src)
            assert _conc(src) == "CLEAN", (fam["name"], k, src)
            checked += 1
    assert checked >= 12


def test_the_concrete_oracle_is_model_free():
    assert CONC.MODEL_DEPENDENCY_COUNT == 0
    out = CONC.run({"source": 'def f(x: int) -> int:\n    """post: _ == x * 2"""\n    return x + 2\n'}, ".")
    assert out["model_dependency_count"] == 0
    # A concrete oracle may witness, never prove absence.
    assert out["proves_absence"] is False
