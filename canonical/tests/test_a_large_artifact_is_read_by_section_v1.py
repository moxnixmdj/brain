"""A large artifact is not automatically an unanswerable one.

Measured 2026-10-31 on `34f867a`:

    "Find the callers of binding_view in canonical/runtime"
      -> python.source.symbols.index.ast
      -> writes 105.8 MB
      -> FAIL_CLOSED__ANSWER_SHAPE_UNSERVED (ARTIFACT_TOO_LARGE), 16.5-18.7 s

    the same sentence about ONE FILE
      -> 293 ms, PASS

The gate's ``MAX_ARTIFACT_BYTES`` exists because loading 108 MB to look for a field that is not
there costs ~2 s and 1.5 GB of RSS.  It should not stop the gate paying for the 1.5 MB that IS
the answer.  The rule these tests pin:

    over the cap, the gate decodes the artifact's LEADING top-level members inside a small
    budget and stops at the first member that does not fit.

Each value is decoded whole or not at all, so the delivered answer is byte-identical to the
member in the file.  When nothing fits, the original refusal stands, unchanged -- which is the
one direction that must never move.
"""

from __future__ import annotations

import json
import pathlib
import tempfile
import unittest

from canonical.runtime import answer_shape_v1 as shape


class _Base(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name)

    def _result(self, inner: dict, cid: str = "python.source.symbols.index.ast") -> dict:
        return {"pass": True, "execution": [{"capability_id": cid, "result": inner}]}

    def _large(self, name: str, sections: list[tuple[str, object]], pad: int) -> pathlib.Path:
        """A JSON object whose first members are real and whose tail is over the cap.

        ``sort_keys`` is used deliberately: the writer must not be trusted to order its keys,
        so the test states the order it writes and the reader must survive both.
        """
        path = self.root / name
        head = "{" + ", ".join(
            json.dumps(key) + ": " + json.dumps(value) for key, value in sections)
        body = head + ', "bulk": "' + "x" * pad + '"}'
        path.write_text(body, encoding="utf-8")
        self.assertGreater(path.stat().st_size, shape.MAX_ARTIFACT_BYTES)
        return path


class TheAnswerIsDeliveredFromTheLeadingSection(_Base):
    def test_an_answer_before_the_cap_is_delivered_exactly(self) -> None:
        callers = {"build_plan": ["plan_report"], "admit": ["_solve_body"]}
        path = self._large("index.json", [("callers_of", callers)], shape.MAX_ARTIFACT_BYTES)
        result = self._result({"output_path": str(path), "file_count": 3})
        reasons = shape.deliver("Find the callers of build_plan in pkg", result, self.root)
        self.assertEqual(reasons, [])
        answer = result["answer"]
        self.assertEqual(answer["noun"], "caller")
        self.assertEqual(answer["field"], "callers_of")
        # The sentence names one key; the other key is not part of the answer.
        self.assertEqual(answer["value"], {"build_plan": ["plan_report"]})
        self.assertEqual(answer["count"], 1)
        self.assertFalse(answer["truncated"])

    def test_the_member_is_decoded_whole_or_not_at_all(self) -> None:
        """A member that does not fit is dropped, never shortened into a wrong value.

        The fixture is ``{"totals": {...}, "bulk": "<16 MB of text>"}``: the small member is
        delivered because it fits, and the giant one is dropped because it does not.  A reader
        that returned a *prefix* of the giant string would be inventing a value; this one
        returns no member at all.
        """
        path = self._large("index2.json", [("totals", {"files": 3, "files_ok": True})],
                           shape.MAX_ARTIFACT_BYTES)
        payload, reason = shape._read_sections(path)
        self.assertIsNone(reason)
        self.assertEqual(payload, {"totals": {"files": 3, "files_ok": True}})
        self.assertNotIn("bulk", payload)

    def test_nothing_readable_still_refuses_with_the_original_reason(self) -> None:
        path = self.root / "spaces.json"
        with open(path, "wb") as handle:
            handle.write(b"{" + b" " * (shape.MAX_ARTIFACT_BYTES + 1) + b"}")
        payload, reason = shape._read_sections(path)
        self.assertIsNone(payload)
        self.assertTrue(reason.startswith("ARTIFACT_TOO_LARGE"), reason)
        result = self._result({"output_path": str(path), "duplicate_group_count": 3},
                              cid="code.index.tree_sitter.incremental.v1")
        reasons = shape.deliver("Find duplicated code in canonical/runtime", result,
                                self.root)
        self.assertTrue(any("ARTIFACT_TOO_LARGE" in reason for reason in reasons), reasons)
        self.assertNotIn("answer", result)

    def test_a_non_object_artifact_is_not_answered_from(self) -> None:
        path = self.root / "list.json"
        path.write_text("[" + "1, " * (shape.MAX_ARTIFACT_BYTES // 3) + "1]", encoding="utf-8")
        payload, reason = shape._read_sections(path)
        self.assertIsNone(payload)
        self.assertEqual(reason, "ARTIFACT_NOT_A_JSON_OBJECT")

    def test_the_read_costs_the_section_not_the_file(self) -> None:
        """The budget is a bound on work, so the read must not scale with the artifact."""
        callers = {"build_plan": ["plan_report"]}
        path = self._large("index3.json", [("callers_of", callers)], 24 * 1024 * 1024)
        with path.open("rb") as handle:
            self.assertGreater(len(handle.read()), shape.MAX_SECTION_BYTES * 2)
        payload, reason = shape._read_sections(path)
        self.assertIsNone(reason)
        self.assertEqual(payload["callers_of"], callers)


if __name__ == "__main__":
    unittest.main()
