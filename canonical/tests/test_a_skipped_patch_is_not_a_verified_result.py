"""A patch that reports success and writes no byte is not a patch that applied.

`git apply` walks up from the current directory to find a repository, and resolves every
path in the diff against THAT root. The four diff gates -- full testgate, coverage,
mutation, perf -- all copy the tree under review into a scratch directory *inside the
repository* and drop `.git` from the copy, so `git apply` inside the copy found the
enclosing repository and silently skipped the patch:

    $ git -C <scratch> apply -v fix.diff
    rc=0                                 # success
    err: Skipped patch 'calc.py'.
    $ cat <scratch>/calc.py
    return a - b                         # unchanged

Exit status 0, no file written. The gate then ran the suite against the unpatched tree and
reported the result as a verdict on the patch. `python.repo.diff_apply_full_testgate.v1`
measured before the fix: `gate FAIL`, `failing_tests ["test_calc.py::CalcTest::test_add"]`
-- a failing test the diff existed to fix -- and a suite that was already green would have
been a false PASS.

The tests below are the two directions plus the invariant that stops either gate from
re-introducing a bare `git apply`.
"""
from __future__ import annotations

import ast
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
GATE_DIR = REPO_ROOT / "canonical" / "runtime" / "bound_capabilities"
TMP_ROOT = REPO_ROOT / "canonical" / "astra_runtime" / "tmp"

GATES = (
    "python_repo_diff_apply_full_testgate",
    "python_review_diff_coverage_gate",
    "python_review_diff_mutation_gate",
    "python_review_diff_perf_gate",
)

SOURCE = "def add(a: int, b: int) -> int:\n    return a - b\n"
TEST = (
    "import unittest\n"
    "from calc import add\n"
    "\n"
    "\n"
    "class CalcTest(unittest.TestCase):\n"
    "    def test_add(self):\n"
    "        self.assertEqual(add(2, 3), 5)\n"
)
FIX_DIFF = (
    "diff --git a/calc.py b/calc.py\n"
    "--- a/calc.py\n"
    "+++ b/calc.py\n"
    "@@ -1,2 +1,2 @@\n"
    " def add(a: int, b: int) -> int:\n"
    "-    return a - b\n"
    "+    return a + b\n"
)
NOOP_DIFF = (
    "diff --git a/calc.py b/calc.py\n"
    "--- a/calc.py\n"
    "+++ b/calc.py\n"
    "@@ -1,2 +1,2 @@\n"
    " def add(a: int, b: int) -> int:\n"
    "-    return a - b\n"
    "+    return a - b\n"
)


def _anchor(tmp: Path, diff_text: str) -> tuple[Path, Path]:
    """A fixture tree under the repo (adapter paths are repo-root relative) + its diff."""
    anchor = tmp / "anchor"
    anchor.mkdir(parents=True, exist_ok=True)
    (anchor / "calc.py").write_text(SOURCE, encoding="utf-8")
    (anchor / "test_calc.py").write_text(TEST, encoding="utf-8")
    diff = tmp / "fix.diff"
    diff.write_text(diff_text, encoding="utf-8")
    return anchor, diff


def _door(capability_id: str, args: dict):
    """Invoke through route admission; returns (admitted, artifact-or-refusal)."""
    import io
    import contextlib

    sys.path.insert(0, str(REPO_ROOT))
    from canonical.runtime import live_brain_route_admission_v1 as admission

    registry = json.loads(
        (REPO_ROOT / "canonical" / "runtime" / "BOUND_CAPABILITY_REGISTRY_V1.json")
        .read_text(encoding="utf-8")
    )["capabilities"]
    row = registry[capability_id]
    envelope = {
        "capability_id": capability_id,
        "adapter_module": row["adapter_module"],
        "entrypoint": row["entrypoint"],
        "source": row["source"],
        "incremental_spend_usd": 0,
    }
    supplied = dict(args)
    supplied["capability_id"] = capability_id
    action = {
        "type": "invoke_capability",
        "args": supplied,
        "expect": row["action_template"]["expect"],
    }
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            return True, admission.run_adapter_locally(envelope, action)
    except BaseException as exc:  # the door refuses by raising
        return False, str(exc)


class TestAGateThatSkippedItsPatch(unittest.TestCase):
    def setUp(self):
        TMP_ROOT.mkdir(parents=True, exist_ok=True)
        self.tmp = Path(tempfile.mkdtemp(prefix="gitapply_", dir=str(TMP_ROOT)))
        self.addCleanup(shutil.rmtree, self.tmp, True)

    # -- the invariant: no gate may call `git apply` behind the module's back -----------
    def test_no_gate_runs_git_apply_outside_the_proving_module(self):
        offenders = []
        for name in GATES:
            tree = ast.parse((GATE_DIR / f"{name}.py").read_text(encoding="utf-8"))
            uses_module = False
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module and \
                        node.module.endswith("scratch_git_apply_v1"):
                    uses_module = True
                if not isinstance(node, ast.Call):
                    continue
                flat = ast.unparse(node).replace("'", '"')
                if '"git"' in flat and '"apply"' in flat:
                    offenders.append(f"{name}:{node.lineno}")
            if not uses_module:
                offenders.append(f"{name}: does not import apply_to_scratch")
        self.assertEqual([], offenders,
                         "a gate applied a diff without proving the tree changed")

    # -- direction 1: the leak is gone; the patch actually lands -----------------------
    def test_a_patch_inside_the_repo_actually_reaches_the_scratch_copy(self):
        from canonical.runtime.scratch_git_apply_v1 import apply_to_scratch

        anchor, diff = _anchor(self.tmp, FIX_DIFF)
        scratch = self.tmp / "scratch"
        shutil.copytree(anchor, scratch,
                        ignore=shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache"))
        # Without the ceiling this is rc=0 with the patch skipped, because the scratch copy
        # lives inside the repository. Assert the negative first: raw git leaks upward.
        leaked = subprocess.run(["git", "apply", "--check", str(diff)],
                                cwd=str(scratch), capture_output=True, text=True)
        self.assertEqual(0, leaked.returncode)
        toplevel = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                                  cwd=str(scratch), capture_output=True, text=True).stdout
        self.assertEqual(str(REPO_ROOT), toplevel.strip(),
                         "fixture is not exposed to the enclosing repository")
        # And the module does not leak: the tree changes.
        self.assertEqual(("OK", ""), apply_to_scratch(diff, scratch))
        self.assertIn("return a + b", (scratch / "calc.py").read_text(encoding="utf-8"))

    # -- direction 2: success with no change is a refusal -------------------------------
    def test_a_patch_that_changes_no_byte_is_refused(self):
        from canonical.runtime.scratch_git_apply_v1 import apply_to_scratch

        anchor, diff = _anchor(self.tmp, NOOP_DIFF)
        scratch = self.tmp / "scratch"
        shutil.copytree(anchor, scratch,
                        ignore=shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache"))
        refusal, detail = apply_to_scratch(diff, scratch)
        self.assertEqual("DIFF_APPLIED_BUT_TREE_UNCHANGED", refusal)
        self.assertTrue(detail)

    # -- the gate itself: green on a real fix, red on a patch that fixes nothing --------
    def test_the_full_testgate_passes_only_when_the_patch_is_the_reason(self):
        anchor, diff = _anchor(self.tmp, FIX_DIFF)
        nofix = self.tmp / "nofix.diff"
        nofix.write_text(FIX_DIFF.replace("    return a + b\n",
                                          "    return a - b\n").replace(
            "@@ -1,2 +1,2 @@\n def add(a: int, b: int) -> int:\n-    return a - b\n+    return a - b\n",
            "@@ -1,2 +1,2 @@\n-def add(a: int, b: int) -> int:\n"
            "+def add(a: int, b: int) -> int:  # same behaviour\n     return a - b\n"),
            encoding="utf-8")

        def run(diff_path: Path, tag: str):
            return _door("python.repo.diff_apply_full_testgate.v1", {
                "anchor_path": str(anchor.relative_to(REPO_ROOT)),
                "diff_path": str(diff_path.relative_to(REPO_ROOT)),
                "python_executable": sys.executable,
                "timeout_s": 180,
                "output_path": str((self.tmp / f"out_{tag}.json").relative_to(REPO_ROOT)),
            })

        pytest_available = subprocess.run(
            [sys.executable, "-m", "pytest", "--version"],
            capture_output=True, text=True).returncode == 0
        if not pytest_available:
            # Fail-closed without the substrate: the gate must refuse, never guess a pass.
            admitted, refusal = run(diff, "fix")
            self.assertFalse(admitted, "gate admitted a suite it could not run")
            self.assertIn("gate", refusal)
            return

        admitted, envelope = run(diff, "fix")
        self.assertTrue(admitted, f"a real fix was refused: {envelope}")
        self.assertEqual("PASS", envelope["gate"])
        artifact = json.loads((self.tmp / "out_fix.json").read_text(encoding="utf-8"))
        self.assertEqual("PASS", artifact["gate"])
        self.assertEqual([], artifact["failing_tests"])
        self.assertEqual("test_calc.py", artifact["test_files"][0])

        # A patch that applies cleanly but fixes nothing must still be red: this is the
        # direction that a skipped patch would silently have turned green.
        admitted, refusal = run(nofix, "nofix")
        self.assertFalse(admitted, "the gate passed a patch that fixed nothing")
        self.assertIn("FAIL", refusal)


if __name__ == "__main__":
    unittest.main()
