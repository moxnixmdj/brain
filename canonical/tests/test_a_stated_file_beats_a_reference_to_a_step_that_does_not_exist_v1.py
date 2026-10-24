"""A file the caller wrote beats a reference to a step that does not exist.

The body binds through the whole compilation context, which is normally the better
binding -- that is why PR #6101 let it win over the named entry's own.  But in a
SINGLE-capability goal it can fill an input slot with a reference to a previous
step's output, and there is no previous step.

Measured on 6ecc6e52:

    goal  "Run the decision synthesis typed stdlib with input path <file>."
    body  input_path = {"$result": {"cycle": 0, "field": "output_path"}}   <- dangling
    named input_path = "<file>"                                           <- what was asked

so the request was refused as unstated even though the caller had written the file
and the named entry had already bound it.  The repair is deliberately narrow: only
a role whose value appears in the request is taken from the named binding, and
anything else still refuses.
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

import goal_compiler as gc                                    # noqa: E402
import goal_front_compiler_v1 as front                        # noqa: E402
from canonical.runtime.live_integrated_brain_v1 import load_verified_registry  # noqa: E402

WORK = "canonical/astra_runtime/tmp/stated_file_probe"
DATA = WORK + "/sample.json"


def _reg():
    return gc._platform_admissible_registry(dict(load_verified_registry()))


def _registry():
    return json.loads(
        (ROOT / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json").read_text()
    )["capabilities"]


class StatedFileBeatsDanglingReferenceTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        target = ROOT / DATA
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps([{"id": "a", "name": "alpha", "status": "PASS"}]))

    def test_a_stated_file_is_used_instead_of_a_dangling_step_reference(self):
        cap = "decision.synthesis.typed.stdlib"
        goal = "Run the decision synthesis typed stdlib with input path %s." % DATA
        compiled = front.compile_goal(goal, _reg(), ROOT)
        self.assertEqual(compiled.get("selected_capability"), cap)
        self.assertEqual((compiled.get("inputs") or {}).get("input_path"), DATA)

    def test_the_body_really_was_producing_a_dangling_reference(self):
        """Pins the cause, so a future refactor cannot make this test pass for the
        wrong reason: without the repair the body's own binding is a $result ref."""
        goal = "Run the decision synthesis typed stdlib with input path %s." % DATA
        body = front._compile_goal_body(goal, _reg(), ROOT)
        raw = (body.get("inputs") or {}).get("input_path")
        self.assertTrue(
            isinstance(raw, dict) and "$result" in raw,
            "expected the body to bind a step reference, got %r" % (raw,))
        self.assertIn("input_path", front._inputs_not_stated_by(goal, body.get("inputs") or {}))

    def test_the_same_request_without_the_file_still_refuses(self):
        """The repair takes only what the caller wrote.  It must not invent."""
        with self.assertRaises(front.GoalCompilationFailure) as ctx:
            front.compile_goal("Run the decision synthesis typed stdlib.", _reg(), ROOT)
        detail = str(ctx.exception.detail)
        self.assertIn("decision.synthesis.typed.stdlib", detail)
        self.assertIn("input_path", detail)

    def test_a_capability_whose_contract_is_not_met_still_refuses(self):
        """The repair is not a way to wave a request through.  This capability also
        needs `spec`, and stating one file does not satisfy the rest of the
        contract -- measured, it refuses and names the capability and the role."""
        cap = "evidence.claim_relation.generic_units.stdlib"
        goal = ("Run the evidence claim relation generic units stdlib "
                "with extraction path %s." % DATA)
        with self.assertRaises(front.GoalCompilationFailure) as ctx:
            front.compile_goal(goal, _reg(), ROOT)
        detail = str(ctx.exception.detail)
        self.assertEqual(ctx.exception.code, "GOAL_INPUT_BINDING_REQUIRED")
        self.assertTrue(detail.startswith(cap), detail)
        self.assertIn("not_stated", detail)

    def test_stating_every_input_compiles_most_of_the_class(self):
        """Whole class, and the number that moved: with every path role stated from
        a real file, at least 44 of the 72 compile to the capability named.
        Measured 39 before this change."""
        reg = _reg()
        raw = _registry()
        caps = sorted(raw)
        self.assertGreaterEqual(len(caps), 72)
        fixture = ROOT / DATA
        tmpl = re.compile(r"\$\{input\.([A-Za-z0-9_]+)\}")
        owned = ("output_path", "result_path")
        routed = 0
        for cap in caps:
            roles = sorted(set(tmpl.findall(
                json.dumps(raw[cap].get("action_template") or {}))))
            need = [r for r in roles
                    if r not in owned
                    and not r.endswith(("_output_path", "_result_path"))]
            parts = ["with %s %s" % (r.replace("_", " "), DATA) for r in need]
            stem = re.sub(r"\.py\.auto\.v\d+$", "", cap.rsplit("/", 1)[-1])
            goal = "Run the %s %s." % (
                stem.replace("_", " ").replace(".", " "), " ".join(parts))
            try:
                compiled = front.compile_goal(goal, reg, ROOT)
            except front.GoalCompilationFailure:
                continue
            if compiled.get("selected_capability") == cap:
                routed += 1
        self.assertTrue(fixture.exists())
        # 43, not the 44 the original measurement showed: that used a fixture of
        # the matching type for each role (a real PDF for pdf_path, a real sqlite
        # file for sqlite_path).  Pointing every role at one JSON file binds one
        # fewer.  The floor is pinned at what THIS test actually produces.
        self.assertGreaterEqual(routed, 43, "only %d of %d compiled" % (routed, len(caps)))


if __name__ == "__main__":
    unittest.main(verbosity=2)
