"""A capability named in the request is never handed inputs the request did not contain.

PR #6100 stopped a named capability being answered by a DIFFERENT one.  This pins
the second half of the same defect: reaching the right capability with invented
inputs is still a fabricated success.

Measured on 8273253 across the 72 verified capabilities named in prose, 32 routed
to the capability asked for and 28 of those 32 were handed at least one input the
sentence never contained:

    pdf.extract.text.pypdf        pdf_path    = ".../tmp/BOUND_PDF_TEXT_TEST.pdf"
    image.code.decode.zbarimg     path        = ".../canary_frames/000-c-ferry-scan0.png"
    math.numeric_expression.sympy expression  = "sympy"    <- scraped from its own name
    python.source.audit.ast       source_root = "canonical/runtime"

The binder picked a plausible-looking path out of the repository and presented it
as though the caller had supplied it, so the compile reported a success on work
nobody asked for.  Two causes, both pinned here: the hook that reads the name
skips whatever is already selected, so a self-route was never recorded as named;
and nothing held the winning binding to the caller's own words.
"""
import json
import pathlib
import re
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
for _p in (str(ROOT), str(ROOT / "canonical/runtime"), str(ROOT / "execution_guard")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import goal_compiler as gc                                    # noqa: E402
import goal_front_compiler_v1 as front                        # noqa: E402
from canonical.runtime.live_integrated_brain_v1 import load_verified_registry  # noqa: E402

PDF = "canonical/astra_runtime/tmp/NAMED_INPUT_CONTRACT_PROBE.pdf"


def _reg():
    return gc._platform_admissible_registry(dict(load_verified_registry()))


def _prose(cid):
    """The ordinary sentence that asks for a capability by name and states nothing."""
    stem = re.sub(r"\.py\.auto\.v\d+$", "", cid.rsplit("/", 1)[-1])
    return "Run the " + stem.replace("_", " ").replace(".", " ") + "."


def _bound():
    rows = json.loads(
        (ROOT / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json").read_text())
    return sorted(rows["capabilities"].keys())


def _stated(text, inputs):
    """The caller's own words, per the rule under test."""
    out = {}
    for key, value in dict(inputs or {}).items():
        if isinstance(value, str) and value.strip() and value.strip() in text:
            out[key] = value
    return out


class NamedInputContractTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        target = ROOT / PDF
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            target.write_bytes(b"%PDF-1.4\n")

    def test_naming_a_capability_without_its_input_fails_closed_naming_both(self):
        """The refusal must say which capability and which input was never given."""
        with self.assertRaises(front.GoalCompilationFailure) as ctx:
            front.compile_goal("Run the pdf extract text pypdf.", _reg(), ROOT)
        self.assertEqual(ctx.exception.code, "GOAL_INPUT_BINDING_REQUIRED")
        detail = str(ctx.exception.detail)
        self.assertIn("pdf.extract.text.pypdf", detail)
        self.assertIn("pdf_path", detail)
        self.assertIn("named_but_inputs_not_stated", detail)

    def test_the_same_capability_routes_when_the_caller_states_the_input(self):
        """Not a blanket refusal: state the file and it compiles against that file."""
        for goal in ("Run the pdf extract text pypdf on %s." % PDF,
                     "Extract text with pdf extract text pypdf from %s." % PDF):
            compiled = front.compile_goal(goal, _reg(), ROOT)
            self.assertEqual(compiled.get("selected_capability"),
                             "pdf.extract.text.pypdf", goal)
            self.assertEqual((compiled.get("inputs") or {}).get("pdf_path"), PDF, goal)

    def test_no_named_capability_is_ever_handed_an_input_the_caller_did_not_write(self):
        """The whole class: across all 72, a compile that routes to the named
        capability binds only inputs the sentence actually contains."""
        reg = _reg()
        caps = _bound()
        self.assertGreaterEqual(len(caps), 72)
        invented = []
        routed = 0
        for cap in caps:
            goal = _prose(cap)
            try:
                compiled = front.compile_goal(goal, reg, ROOT)
            except front.GoalCompilationFailure:
                continue
            if compiled.get("selected_capability") != cap:
                continue
            routed += 1
            inputs = compiled.get("inputs") or {}
            for key, value in inputs.items():
                role = str(key)
                if (role in ("output_path", "result_path")
                        or role.endswith("_output_path")
                        or role.endswith("_result_path")):
                    continue          # where an output lands is ours to choose
                if isinstance(value, str) and value.strip() and value.strip() in goal:
                    continue
                if isinstance(value, str) and goal.strip().startswith(value.strip()):
                    continue          # the request bound whole, as role `goal`
                invented.append((cap, role, repr(value)[:60]))
        self.assertEqual(invented, [], "invented inputs: %s" % invented)
        self.assertGreater(routed, 0, "the rule must not refuse everything")

    def test_an_output_destination_is_still_chosen_for_the_caller(self):
        """The rule is about source inputs.  Outputs stay ours to place."""
        unstated = front._inputs_not_stated_by(
            "Run the thing.",
            {"output_path": "canonical/astra_runtime/tmp/whatever.json",
             "result_path": "canonical/astra_runtime/tmp/r.json",
             "spool_output_path": "canonical/astra_runtime/tmp/s.json",
             "audit_result_path": "canonical/astra_runtime/tmp/a.json"})
        self.assertEqual(unstated, [])

    def test_a_dag_reference_is_not_the_caller_stating_an_input(self):
        """A structured default is still a default, whoever computed it."""
        self.assertEqual(
            front._inputs_not_stated_by(
                "Run the knowledge consistency assess.",
                {"evidence_paths": [{"$effect_result": {"field": "output_path"}}],
                 "max_age_s": None}),
            ["evidence_paths", "max_age_s"])

    def test_an_ordinary_sentence_still_names_nothing(self):
        """Widening the name read must not start seeing names in plain English."""
        reg = _reg()
        for goal in ("Write a report to out/report.md about the survey results.",
                     "Summarise the meeting notes into a short paragraph.",
                     "Compute the average latency across the benchmark runs.",
                     "Refactor the parser so the tests still pass.",
                     "Explain what the deployment script does step by step.",
                     "Fix the bug where the file handle leaks on error."):
            self.assertIsNone(
                front._named_receipt_projection(
                    goal, reg, None,
                    names=front.request_states_the_capability_name,
                    include_bound=True), goal)


if __name__ == "__main__":
    unittest.main(verbosity=2)
