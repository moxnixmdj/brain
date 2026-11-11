"""The one model can execute a stated read-only command under admitted confinement.

Measured 2026-11-09. The carrier was already built and already wired into
brain_one_model_v3. It could not produce a PASS because of a SCOPE mismatch at the
join, and the failure was reported as an isolation failure.

Two rewrites were tried and BOTH were wrong:

  bare operand + carrier cwd "."      -> ran in the repository, sort died "cannot read"
  absolute operand + carrier cwd X    -> carrier stages a workspace-relative view;
                                         an absolute host path is not in it

The answer is neither: the operand is already relative to the workspace the sentence
names, so pass that workspace as the carrier's cwd and leave the words alone.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.runtime import admitted_confinement_execution_v1 as carrier
from canonical.runtime import brain_one_model_v3 as model

BASE = ROOT / "canonical" / "astra_runtime" / "tmp"


def _ws(rows: int = 8) -> Path:
    BASE.mkdir(parents=True, exist_ok=True)
    d = Path(tempfile.mkdtemp(prefix="carrier_", dir=str(BASE)))
    (d / "data.txt").write_text("\n".join(f"svc-{i}" for i in range(rows)) + "\n")
    return d


def test_the_carrier_runs_a_read_only_command_under_confinement():
    d = _ws()
    out = carrier.execute_confined(["sort", "-u", "data.txt"], workspace_root=str(d))
    assert out["pass"] is True, out.get("status")
    assert out["confined"] is True
    assert out["live_workspace_untouched"] is True
    assert out["exit"] == 0
    assert len([l for l in (out["stdout"] or "").splitlines() if l.strip()]) == 8


def test_the_one_model_reaches_the_carrier_layer_and_passes():
    d = _ws()
    out = model.resolve("sort -u data.txt", root=str(d), execute=True)
    assert out["layer"] == "ADMITTED_CONFINEMENT", out.get("detail")
    assert out["pass"] is True
    assert out["carried"]["confined"] is True
    assert out["carried"]["live_workspace_untouched"] is True


def test_an_absolute_operand_is_not_what_the_carrier_wants():
    """Records the failed variant so it is not re-derived."""
    d = _ws()
    out = carrier.execute_confined(["sort", "-u", str(d / "data.txt")], workspace_root=str(d))
    assert out["pass"] is False
    assert out["exit"] == 2


def test_a_write_flag_is_refused_before_the_carrier_starts():
    d = _ws()
    for argv, expect in ((["sed", "-i", "s/a/b/", "data.txt"], "REFUSED__WRITE_FLAG_STATED:sed -i"),
                         (["sort", "-o", "out.txt", "data.txt"], "REFUSED__WRITE_FLAG_STATED:sort -o")):
        out = carrier.execute_confined(argv, workspace_root=str(d))
        assert out["pass"] is False
        assert out["status"] == expect, out["status"]


def test_awk_cannot_escape_by_shelling_out():
    """awk is admitted as a read-only program, so system() must be unreachable.

    Measured: the marker file was never created and the carrier never reported a pass.
    """
    d = _ws()
    marker = Path("/tmp/brain_escape_marker_test_v1")
    if marker.exists():
        marker.unlink()
    out = carrier.execute_confined(['awk', f'BEGIN{{system("touch {marker}")}}'],
                                   workspace_root=str(d))
    assert out["pass"] is False
    assert not marker.exists(), "awk system() reached the host"


def test_the_carrier_never_claims_a_pass_when_the_command_fails():
    d = _ws()
    out = carrier.execute_confined(["cat", "definitely-not-here.txt"], workspace_root=str(d))
    assert out["pass"] is False
    assert out["exit"] != 0
