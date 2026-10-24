"""A refusal must say what to fix, about the capability that was asked for.

Measured through the front door on 8a721233, 42 of the 72 verified capabilities
named in prose refused without telling the caller what was missing, and some
described a DIFFERENT capability's problem instead:

    ask for  text.file.write   ->  "shell.command.run:argv:not_stated"
    ask for  chart.raster.scene_graph.v1
                               ->  "chart.raster.scene_graph.v1:named_but_other_selected:python..."

Naming whatever the fallback path happened to trip over is not a diagnosis anyone
can act on.  Two causes: the boundary reported the capability the walk landed on
rather than the one that was named, and when the body itself raised, the boundary
re-raised it untouched.
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

TEMPLATE_INPUT = re.compile(r"\$\{input\.([A-Za-z0-9_]+)\}")
OWNED = ("output_path", "result_path")


def _reg():
    return gc._platform_admissible_registry(dict(load_verified_registry()))


def _registry():
    return json.loads(
        (ROOT / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json").read_text()
    )["capabilities"]


def _prose(cid):
    stem = re.sub(r"\.py\.auto\.v\d+$", "", cid.rsplit("/", 1)[-1])
    return "Run the " + stem.replace("_", " ").replace(".", " ") + "."


def _required_inputs(entry):
    """The inputs this capability needs, minus the outputs we are allowed to place."""
    roles = set(TEMPLATE_INPUT.findall(json.dumps(entry.get("action_template") or {})))
    return {r for r in roles
            if r not in OWNED
            and not r.endswith("_output_path")
            and not r.endswith("_result_path")}


class RefusalNamesWhatWasAskedForTest(unittest.TestCase):

    def test_a_refusal_names_the_capability_asked_for_not_the_one_it_landed_on(self):
        """The exact defect: text.file.write used to be refused as shell.command.run."""
        with self.assertRaises(front.GoalCompilationFailure) as ctx:
            front.compile_goal("Run the text file write.", _reg(), ROOT)
        detail = str(ctx.exception.detail)
        self.assertIn("text.file.write", detail)
        self.assertNotIn("shell.command.run", detail)
        self.assertIn("content", detail)      # the input that was never given

    def test_the_gaps_are_that_capability_s_own_required_inputs(self):
        """Naming the capability is not enough; the inputs must be its real ones."""
        reg = _reg()
        cap = "chart.raster.scene_graph.v1"
        with self.assertRaises(front.GoalCompilationFailure) as ctx:
            front.compile_goal(_prose(cap), reg, ROOT)
        detail = str(ctx.exception.detail)
        self.assertIn(cap, detail)
        named = set(detail.rsplit(":", 1)[-1].split(","))
        required = _required_inputs(_registry()[cap])
        self.assertTrue(named & required,
                        "reported %s, capability requires %s" % (named, required))
        self.assertTrue(named <= required | {"inputs"},
                        "reported inputs the capability does not have: %s" % (named - required))

    def test_no_refusal_across_the_whole_class_blames_a_different_capability(self):
        """All 72: a refusal either routes, or its subject is the capability named."""
        reg = _reg()
        registry = _registry()
        caps = sorted(registry)
        self.assertGreaterEqual(len(caps), 72)
        misattributed = []
        actionable = 0
        for cap in caps:
            goal = _prose(cap)
            try:
                compiled = front.compile_goal(goal, reg, ROOT)
            except front.GoalCompilationFailure as fail:
                detail = str(fail.detail or "")
                if not detail.startswith(cap):
                    # the subject of the diagnosis is something else entirely
                    if ":" in detail and not detail.startswith(cap):
                        other = detail.split(":", 1)[0]
                        if other in registry and other != cap:
                            misattributed.append((cap, other))
                            continue
                if cap in detail:
                    actionable += 1
                continue
            self.assertEqual(compiled.get("selected_capability"), cap, goal)
        self.assertEqual(misattributed, [],
                         "refusals blaming a different capability: %s" % misattributed)
        self.assertGreaterEqual(actionable, 60,
                                "only %d of %d refusals name the capability" % (actionable, len(caps)))

    def test_a_body_failure_does_not_hide_the_contract_that_was_not_stated(self):
        """Mechanism: force the body to raise about something else entirely and
        prove the boundary replaces it with the named capability's own contract."""
        reg = _reg()
        cap = "chart.raster.scene_graph.v1"
        required = _required_inputs(_registry()[cap])
        original = front._compile_goal_body

        def raising_body(goal, admissible, root):
            front._NAMED_EXPECTATION.set(cap)
            raise front.GoalCompilationFailure(
                "GOAL_COMPILATION_NO_VERIFIED_CAPABILITY_MATCH",
                "some.other.capability:argv:not_stated")

        front._compile_goal_body = raising_body
        try:
            with self.assertRaises(front.GoalCompilationFailure) as ctx:
                front.compile_goal(_prose(cap), reg, ROOT)
        finally:
            front._compile_goal_body = original
        detail = str(ctx.exception.detail)
        self.assertTrue(detail.startswith(cap), detail)
        self.assertNotIn("some.other.capability", detail)
        self.assertTrue(set(detail.rsplit(":", 1)[-1].split(",")) & required,
                        "detail %r does not mention any of %s" % (detail, required))

    def test_no_refusal_anywhere_in_the_class_has_a_foreign_subject(self):
        """All 72, directly: every refusal's subject is the capability named."""
        reg = _reg()
        registry = _registry()
        foreign = []
        for cap in sorted(registry):
            try:
                front.compile_goal(_prose(cap), reg, ROOT)
            except front.GoalCompilationFailure as fail:
                detail = str(fail.detail or "")
                if detail and not detail.startswith(cap):
                    foreign.append((cap, detail[:60]))
        self.assertEqual(foreign, [], "refusals with a foreign subject: %s" % foreign)

    def test_stating_the_input_still_routes(self):
        """The positive control: this is a better diagnosis, not a blanket refusal."""
        pdf = "canonical/astra_runtime/tmp/REFUSAL_DIAGNOSIS_PROBE.pdf"
        target = ROOT / pdf
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            target.write_bytes(b"%PDF-1.4\n")
        compiled = front.compile_goal(
            "Run the pdf extract text pypdf on %s." % pdf, _reg(), ROOT)
        self.assertEqual(compiled.get("selected_capability"), "pdf.extract.text.pypdf")
        self.assertEqual((compiled.get("inputs") or {}).get("pdf_path"), pdf)


if __name__ == "__main__":
    unittest.main(verbosity=2)
