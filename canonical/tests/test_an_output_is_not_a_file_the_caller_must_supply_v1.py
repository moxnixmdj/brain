"""Where a result lands is ours to choose; it is not a file the caller must name.

Rule R9 in the route-admission gate refuses a capability that consumes a FILE when
the request names no file.  That is correct.  But it classified its file inputs as
`k.endswith("_path")`, which swept in output_path and result_path -- so the gate
refused capabilities for missing the one thing they were never supposed to be
given.

Measured on 3b9e6a0d over the 72 verified capabilities named in prose, all five of
the remaining opaque refusals were
`ROUTE_ADMISSION_REJECTED:R9_REQUIRED_FILE_INPUT_UNBOUND` reporting `output_path`
as the unbound input, with no capability named anywhere in the message.

Two fixes, pinned here: the mis-classification, and the silent message.
"""
import json
import pathlib
import re
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
for _p in (str(ROOT), str(ROOT / "canonical/runtime")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from canonical.runtime.live_brain_route_admission_v1 import solve  # noqa: E402


def _prose(cid):
    stem = re.sub(r"\.py\.auto\.v\d+$", "", cid.rsplit("/", 1)[-1])
    return "Run the " + stem.replace("_", " ").replace(".", " ") + "."


class OutputIsNotAConsumedFileTest(unittest.TestCase):

    def test_a_capability_whose_only_file_role_is_an_output_is_not_refused_by_r9(self):
        """grounding.verify takes `goal` and `result_path`.  Both are available from
        the sentence alone, so R9 refusing it was simply wrong -- and it now runs."""
        cap = "plain_goal.bound_capability.grounding.verify.stdlib"
        result = solve({"task_id": "R9_OUTPUT_ROLE", "goal": _prose(cap)})
        self.assertNotEqual(result.get("status"), "FAIL_CLOSED__ROUTE_ADMISSION_REJECTED",
                            json.dumps({k: result.get(k) for k in
                                        ("status", "failure_class", "compiler_detail")}))
        self.assertNotIn("R9_REQUIRED_FILE_INPUT_UNBOUND",
                         str(result.get("failure_class")))
        self.assertIs(result.get("pass"), True, result.get("status"))

    def test_r9_still_guards_a_file_the_capability_really_consumes(self):
        """The rule R9 exists for must survive: pdf_path is consumed, not produced."""
        result = solve({"task_id": "R9_CONSUMED", "goal": "Run the pdf extract text pypdf."})
        self.assertIs(result.get("pass"), False)
        detail = str(result.get("compiler_detail") or "")
        self.assertIn("pdf.extract.text.pypdf", detail)
        self.assertIn("pdf_path", detail)

    def test_a_route_admission_refusal_names_the_capability_and_the_gap(self):
        """No refusal at this layer may be silent about what it rejected."""
        reg = json.loads(
            (ROOT / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json").read_text()
        )["capabilities"]
        silent = []
        for cap in sorted(reg):
            result = solve({"task_id": "R9CENSUS", "goal": _prose(cap)})
            if result.get("status") != "FAIL_CLOSED__ROUTE_ADMISSION_REJECTED":
                continue
            detail = str(result.get("compiler_detail") or "")
            if not detail.startswith(cap):
                silent.append((cap, result.get("failure_class"), detail[:50]))
        self.assertEqual(silent, [],
                         "route-admission refusals that do not name the capability: %s" % silent)

    def test_the_reported_gap_is_never_an_output_role(self):
        """Across the whole class, no refusal blames an output for being unstated."""
        reg = json.loads(
            (ROOT / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json").read_text()
        )["capabilities"]
        blamed = []
        for cap in sorted(reg):
            result = solve({"task_id": "R9OUT", "goal": _prose(cap)})
            if result.get("status") != "FAIL_CLOSED__ROUTE_ADMISSION_REJECTED":
                continue
            detail = str(result.get("compiler_detail") or "")
            gaps = set(detail.rsplit(":", 1)[-1].split(",")) if ":" in detail else set()
            for role in gaps:
                if role in ("output_path", "result_path") or role.endswith(
                        ("_output_path", "_result_path")):
                    blamed.append((cap, role))
        self.assertEqual(blamed, [],
                         "refusals blaming an output role: %s" % blamed)


if __name__ == "__main__":
    unittest.main(verbosity=2)
