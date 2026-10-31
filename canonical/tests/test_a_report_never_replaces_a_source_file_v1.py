"""A capability's report must never be committed over a source file.

Measured 2026-10-31: commit 665959c5be ("The gap is reachability, not
capability") replaced canonical/tests/test_declared_input_derivation_v1.py --
a pinned measurement module -- with the adapter's own result JSON:

    {"capability_id":"test.slice.never_miss.v1", ... "verified":true}

The module still exists, still has a .py name, and cannot be imported: the
pinned selection measurements it holds were silently deleted, and the report
that replaced them claims verified:true.  Nothing in the tree noticed, because
every guard asks whether a capability RAN, not whether the run destroyed the
evidence it was supposed to produce.

The invariant is content, not intent: no .py file in this repository may be a
JSON receipt under a Python name.
"""
from __future__ import annotations

import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCANNED = ("canonical", "execution_guard")


def _python_sources():
    for top in SCANNED:
        base = ROOT / top
        if not base.is_dir():
            continue
        for path in base.rglob("*.py"):
            yield path


def _receipt_header(text: str) -> str | None:
    """The schema string when this file opens as a JSON object, else None."""
    head = text.lstrip()[:4096]
    if not head.startswith("{"):
        return None
    try:
        parsed = json.loads(head[: head.rindex("}") + 1]) if "}" in head else None
    except ValueError:
        parsed = None
    if isinstance(parsed, dict) and parsed.get("schema"):
        return str(parsed.get("schema"))
    # A truncated receipt is still a receipt: the file is not Python.
    return "UNPARSED_JSON_OBJECT" if '"schema"' in head else None


class NoReportReplacesASourceFileTests(unittest.TestCase):
    def test_the_scan_is_not_vacuous(self):
        files = list(_python_sources())
        self.assertGreater(len(files), 500, "the invariant must cover the tree it protects")

    def test_no_python_file_is_a_receipt(self):
        found = []
        for path in _python_sources():
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            schema = _receipt_header(text)
            if schema:
                found.append(f"{path.relative_to(ROOT).as_posix()}:{schema}")
        self.assertEqual(found, [], "a capability report replaced a source file: " + ", ".join(found))

    def test_the_restored_measurement_module_still_holds_its_measurements(self):
        """The file the receipt replaced is Python and still measures selection."""
        path = ROOT / "canonical/tests/test_declared_input_derivation_v1.py"
        text = path.read_text(encoding="utf-8")
        self.assertIsNone(_receipt_header(text))
        compile(text, str(path), "exec")
        self.assertIn("unittest", text)


if __name__ == "__main__":
    unittest.main()
