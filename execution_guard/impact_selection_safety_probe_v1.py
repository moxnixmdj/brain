"""Compare the change-impact slice with a full suite on four real regressions.

Each disposable project starts with a passing suite. A one-line change then
breaks one test while leaving a directly selected smoke test green. The probe
runs both the selected tests and the full suite; selecting a green subset while
omitting the failing test is unsafe. It makes no claim about any wider corpus.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime.bound_capabilities import python_change_impact_testselect as selector  # noqa: E402


CASES = {
    "transitive_renamed_import": {
        "pkg/bridge.py": "from pkg.calc import target as renamed\n\ndef run():\n    return renamed()\n",
        "tests/test_affected.py": "from pkg.bridge import run\n\ndef test_affected():\n    assert run() == 1\n",
    },
    "dynamic_import_and_getattr": {
        "tests/test_affected.py": (
            "import importlib\n\ndef test_affected():\n"
            "    module = importlib.import_module('pkg.calc')\n"
            "    assert getattr(module, 'target')() == 1\n"
        ),
    },
    "wildcard_import_indirect_call": {
        "tests/test_affected.py": (
            "from pkg.calc import *\n\ndef test_affected():\n"
            "    indirect = target\n    assert indirect() == 1\n"
        ),
    },
    "pytest_fixture_dependency": {
        "tests/conftest.py": (
            "import pytest\nfrom pkg.calc import target\n\n@pytest.fixture\n"
            "def fixture_value():\n    return target()\n"
        ),
        "tests/test_affected.py": (
            "def test_affected(fixture_value):\n    assert fixture_value == 1\n"
        ),
    },
}


def _write(root: Path, relative: str, contents: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(contents, encoding="utf-8")


def _pytest(root: Path, paths: list[str]) -> tuple[int, str]:
    env = dict(os.environ, PYTEST_DISABLE_PLUGIN_AUTOLOAD="1", PYTHONDONTWRITEBYTECODE="1")
    env["PYTHONPATH"] = str(root)
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", *paths],
        cwd=root, env=env, capture_output=True, text=True, timeout=30, check=False,
    )
    return proc.returncode, (proc.stdout + proc.stderr)[-1200:]


def measure() -> dict:
    rows = []
    with tempfile.TemporaryDirectory(prefix="brain-impact-selection-") as temporary:
        for label, files in CASES.items():
            root = Path(temporary) / label
            _write(root, "pkg/__init__.py", "")
            _write(root, "pkg/calc.py", "def target():\n    return 1\n")
            _write(root, "tests/test_smoke.py", (
                "from pkg.calc import target\n\ndef test_smoke():\n"
                "    assert isinstance(target(), int)\n"
            ))
            for path, contents in files.items():
                _write(root, path, contents)
            before_rc, before_output = _pytest(root, ["tests"])
            _write(root, "pkg/calc.py", "def target():\n    return 2\n")
            _write(root, "change.diff", (
                "--- a/pkg/calc.py\n+++ b/pkg/calc.py\n"
                "@@ -1,2 +1,2 @@\n def target():\n-    return 1\n+    return 2\n"
            ))
            result = selector.run({
                "source_root": ".", "diff_path": "change.diff",
                "test_roots": ["tests"], "output_path": "selection.json",
            }, root)
            selection = json.loads((root / result["output_path"]).read_text(encoding="utf-8"))
            selected = selection["selected_tests"]
            selected_rc, selected_output = _pytest(root, selected) if selected else (None, "")
            full_rc, full_output = _pytest(root, ["tests"])
            missed = (before_rc == 0 and selected_rc == 0 and full_rc != 0
                      and "tests/test_affected.py" not in selected
                      and "test_affected" in full_output)
            rows.append({
                "case": label,
                "baseline_full_suite_rc": before_rc,
                "selected_tests": selected,
                "selected_suite_rc": selected_rc,
                "changed_full_suite_rc": full_rc,
                "omitted_failing_test": missed,
                "candidate_test_count": result["candidate_test_count"],
                "selector_output_verified": result["output_verified"],
                "baseline_output_tail": before_output[-400:],
                "selected_output_tail": selected_output[-400:],
                "changed_full_output_tail": full_output[-400:],
            })
    unsafe = sum(row["omitted_failing_test"] for row in rows)
    return {
        "schema": "BRAIN_IMPACT_SELECTION_SAFETY_PROBE_V1",
        "status": "FAIL__GREEN_SLICE_MISSED_REGRESSION" if unsafe else "NO_GREEN_SLICE_MISSED_OBSERVED",
        "case_count": len(rows), "unsafe_count": unsafe, "rows": rows,
        "scope": "four disposable Python projects; not a corpus-wide rate",
        "terminal_authority": False,
    }


def main() -> int:
    report = measure()
    print(json.dumps(report, indent=2, sort_keys=True))
    return 1 if report["unsafe_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
