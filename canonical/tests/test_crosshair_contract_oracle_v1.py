"""Tests for the CrossHair mechanical contract oracle.

The point of this oracle is that it is *independent* and *model-free*, which
is what TRUE_CAPABILITY_TEST_LAW_V1 demands of a judge.  These tests hold it
to exactly that, and to failing closed.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "canonical" / "runtime" / "bound_capabilities"))

import crosshair_contract_oracle as ORACLE  # noqa: E402

WORK = ROOT / "canonical" / "astra_runtime" / "tmp" / "oracle_test"

# A function that violates its own declared contract: 1*3 != 2.
BROKEN = '''def triple(x: int) -> int:
    """post: _ == x * 3"""
    return x + x
'''


def _write_target(name: str, body: str) -> str:
    WORK.mkdir(parents=True, exist_ok=True)
    path = WORK / name
    path.write_text(body, encoding="utf-8")
    return str(path)


def _run(target: str) -> dict:
    out = str(WORK / "oracle.json")
    return ORACLE.run({"target_path": target, "output_path": out,
                       "allow_unsafe_host_execution": True}, str(ROOT))


def test_oracle_finds_a_known_violation():
    target = _write_target("broken.py", BROKEN)
    result = _run(target)
    assert result["status"] == "CONTRACT_VIOLATION_FOUND"
    assert result["violation_count"] >= 1
    assert result["output_verified"] is True
    assert any("triple" in v["message"] for v in result["violations"])


def test_oracle_is_model_free_and_independent():
    result = _run(_write_target("broken.py", BROKEN))
    assert result["schema"] == ORACLE.SCHEMA
    assert result["oracle"] == "crosshair"
    assert result["model_dependency_count"] == 0


def test_oracle_writes_a_durable_verdict():
    result = _run(_write_target("broken.py", BROKEN))
    on_disk = json.loads(Path(result["output_path"]).read_text(encoding="utf-8"))
    assert on_disk["status"] == result["status"]
    assert on_disk["violation_count"] == result["violation_count"]


def test_oracle_fails_closed_on_a_missing_target():
    try:
        _run(str(WORK / "does_not_exist.py"))
    except ValueError as exc:
        assert "ORACLE_TARGET_MISSING" in str(exc)
    else:
        raise AssertionError("oracle should refuse a missing target")


def test_oracle_refuses_paths_outside_the_repository_root():
    try:
        ORACLE.run(
            {"target_path": "/etc/passwd", "output_path": str(WORK / "o.json")},
            str(ROOT),
        )
    except ValueError as exc:
        assert "PATH_OUTSIDE_ROOT" in str(exc)
    else:
        raise AssertionError("oracle should refuse a path outside the root")
