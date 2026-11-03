"""A drift report must report drift without becoming a licence to re-pin.

69 of the measured 789 real failures are `*_DRIFT`: a module records a git blob sha and re-checks
it at import. Every legitimate change to a pinned file breaks the pin, so the repository cannot
distinguish "stale, nothing happened" from "stale because something happened" without a person
reading the diff. A tool that printed "re-pin these" would end the repository's mediation
invariants one convenient afternoon at a time.

So the pins here are: it FINDS the drifts; it JOINS them to measured failures rather than
guessing; and it refuses to say what to do about them.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / "scripts/pinned_invariant_report_v1.py"


def _run(tmp_path: Path) -> dict:
    out = tmp_path / "pins.json"
    subprocess.run([sys.executable, str(TOOL), "--json", str(out)],
                   cwd=ROOT, check=True, capture_output=True, text=True, timeout=600)
    return json.loads(out.read_text(encoding="utf-8"))


def test_it_finds_the_pins_that_hold_security_invariants(tmp_path):
    doc = _run(tmp_path)
    modules = {r["module"] for r in doc["rows"]}
    assert "canonical/runtime/root3_child_process_channel_registry_v1.py" in modules, (
        "the process-creation registry's pins are exactly what this must see")
    assert doc["summary"]["pins"] > 50


def test_each_row_points_at_a_measured_failure_not_a_guess(tmp_path):
    """The join is the point. A guessed pin-vs-file comparison misfires on pins that
    deliberately name another file (`EXPECTED_SUITE_BLOB`, `_BASIS_BLOB`)."""
    doc = _run(tmp_path)
    for row in doc["rows"]:
        assert "measured_drift_failures" in row
    flagged = [r for r in doc["rows"] if (r["measured_drift_failures"] or 0) > 0]
    assert flagged, "no pin is joined to a measured drift failure; the report is guessing"


def test_it_never_says_re_pin(tmp_path):
    doc = _run(tmp_path)
    assert doc["authority"].startswith("NONE")
    blob = json.dumps(doc).lower()
    for forbidden in ("safe to update", "simply re-pin", "go ahead"):
        assert forbidden not in blob
    assert any("benign" in x.lower() for x in doc["what_this_cannot_tell_you"])


def test_it_refuses_to_import_the_modules_it_audits(tmp_path):
    """Importing a drift-checking registry raises, which would make the inventory measure
    nothing and look like 'no drift found' -- the most dangerous possible answer."""
    doc = _run(tmp_path)
    assert doc["summary"]["pins"] > 0, (
        "zero pins found almost certainly means the tool imported the modules and stopped at "
        "the first raise")
    # The tool must find pins in modules that RAISE on import. If it imported them, the first
    # raise would end the scan, so a module known to raise being present is proof it did not.
    modules = {r["module"] for r in doc["rows"]}
    assert "canonical/runtime/root3_child_process_channel_registry_v1.py" in modules
    source = TOOL.read_text(encoding="utf-8")
    assert "import_module" not in source and "exec(" not in source
