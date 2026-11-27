"""Two general laws the SWE-bench Pro V2 eval wiring exposed (Iter 85 STEP 3).

1. Modality must be chosen by WORKSPACE SHAPE, not by the instruction's wording:
   a tree that ships an executable test harness is a codebase task even when the
   issue text never says "fix" (real benchmark issues describe behaviour).
2. When nothing in the workspace was changed, the kernel must NOT report VERIFIED:
   a green visible suite with a hidden graded behaviour is exactly the SWE-bench
   shape, and "ALREADY_PASSING" used to surface as a successful solve.
"""
from __future__ import annotations

import pathlib
import sys
import tempfile

from canonical.runtime import brain_unified_model_v1 as UM
from canonical.runtime import universal_epistemic_kernel_v1 as UEK


def _seed_repo(root: pathlib.Path, *, with_tests: bool = True) -> None:
    (root / "pkg").mkdir(parents=True, exist_ok=True)
    (root / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    (root / "pkg" / "core.py").write_text(
        "def label(row):\n    return row.name.upper()\n", encoding="utf-8"
    )
    if with_tests:
        (root / "tests").mkdir(parents=True, exist_ok=True)
        (root / "tests" / "test_core.py").write_text(
            "from types import SimpleNamespace\n"
            "from pkg.core import label\n\n"
            "def test_normal():\n"
            "    assert label(SimpleNamespace(name='abc')) == 'ABC'\n",
            encoding="utf-8",
        )
        (root / "pytest.ini").write_text("[pytest]\npythonpath = .\n", encoding="utf-8")


# Behaviour-only issue text: no "fix", no "repair", no exception name, no "pytest".
BEHAVIOUR_ONLY_ISSUE = (
    "The label(row) helper should return an upper-cased name for a present name and "
    "the empty string '' when row.name is missing (None), so callers never receive "
    "None from label(row)."
)


def test_test_harness_shape_selects_swe_modality_without_intent_keywords() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp) / "repo"
        root.mkdir()
        _seed_repo(root)
        assert not any(w in BEHAVIOUR_ONLY_ISSUE.lower() for w in ("fix", "repair", "pytest", "traceback"))
        fr = UEK.sense_local_frontier(root, BEHAVIOUR_ONLY_ISSUE)
        assert fr["modality"] == "swe_codebase", fr["modality"]

        # The same source tree with NO test harness stays outside the codebase
        # modality: the law keys on the harness, not on "some python exists".
        bare = pathlib.Path(tmp) / "bare"
        bare.mkdir()
        _seed_repo(bare, with_tests=False)
        fr_bare = UEK.sense_local_frontier(bare, BEHAVIOUR_ONLY_ISSUE)
        assert fr_bare["modality"] != "swe_codebase", fr_bare["modality"]


def test_green_visible_suite_with_unproven_behaviour_fails_closed() -> None:
    """No verified patch => no claim of a solve, even though the visible suite is green."""
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp) / "repo"
        root.mkdir()
        _seed_repo(root)  # visible tests pass on the buggy source
        out = UM.open_model().solve(
            BEHAVIOUR_ONLY_ISSUE,
            inputs={
                "workspace": str(root),
                "python_exe": sys.executable,
                "allow_web": False,
                "timeout_s": 60.0,
            },
            mode="EPISTEMIC",
        )
        er = out.get("epistemic_result") or {}
        # The law under test: no verified patch -> no claim of a solve. The exact
        # status depends on which fallback ran (NO_DEFECT_EVIDENCE when the visible
        # suite is simply green; FAILED when a synthesizer path timed out), so pin
        # the invariant instead of a string.
        assert out["pass"] is False, out
        assert out["status"] == "FAIL_CLOSED", out["status"]
        assert er["status"] != "VERIFIED", er
        assert er.get("swe_result", {}).get("patched_file") is None, er
        assert out["model_calls"] == 0
        assert out["parameters_stored"] == 0
        # And nothing was silently edited behind our back.
        assert (root / "pkg" / "core.py").read_text(encoding="utf-8") == (
            "def label(row):\n    return row.name.upper()\n"
        )
