from pathlib import Path
from canonical.runtime.nonactuating_terminal_helpers_nonamplification_v1 import prove

ROOT = Path(__file__).resolve().parents[2]

def test_nonactuating_helpers_do_not_amplify_authority():
    out = prove(ROOT)
    assert out["pass"] is True, out
    assert out["nonamplification_verified"] is True
    assert out["subject_count"] == 3
    assert out["no_direct_external_effect_calls"] is True
    assert out["no_authority_true_literals"] is True
    assert out["execution_authority"] is False
    assert out["terminal_authority"] is False
    assert out["terminal_credit_delta"] == 0

def test_nonamplification_is_content_bound():
    out = prove(ROOT)
    assert all(len(row["git_blob_sha"]) == 40 for row in out["subjects"])
