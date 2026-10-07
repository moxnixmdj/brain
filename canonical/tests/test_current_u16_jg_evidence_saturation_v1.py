import json
from pathlib import Path

from canonical.runtime.current_u16_jg_evidence_saturation_v1 import (
    U16,
    compile_u16_saturation,
)

LEDGER = Path(__file__).parents[1] / "governance" / "CURRENT_U16_JG_EVIDENCE_SATURATION_20261006_V1.json"


def load():
    return json.loads(LEDGER.read_text(encoding="utf-8"))


def test_exact_u16_set_and_saturation_passes():
    out = compile_u16_saturation(load())
    assert out["u_item_count"] == 16
    assert out["bound_j_certificate_count"] == 0
    assert out["bound_g_certificate_count"] == 0
    assert out["bound_t_certificate_count"] == 0
    assert out["future_theorem_impossibility_claimed"] is False
    assert out["terminal_credit"] is False


def test_missing_u_item_fails_closed():
    x = load()
    x["items"] = x["items"][:-1]
    try:
        compile_u16_saturation(x)
    except ValueError as e:
        assert "U16_ID_SET_MISMATCH" in str(e)
    else:
        raise AssertionError("expected fail closed")


def test_unsaturated_item_fails_closed():
    x = load()
    x["items"][0]["scan_state"] = "PARTIAL"
    try:
        compile_u16_saturation(x)
    except ValueError as e:
        assert "UNSATURATED" in str(e)
    else:
        raise AssertionError("expected fail closed")
