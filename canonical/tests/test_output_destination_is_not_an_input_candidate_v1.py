"""A path the sentence names as a DESTINATION is never a candidate SOURCE.

``canonical/tests/test_capability_selection_retrieval_v1.py`` passed when each of its four
classes ran alone and failed when the module ran as a whole.  The cause was not the test
order as such but an artifact one test legitimately leaves behind: GoalDrivenSelectionTests
executes the goal, so ``x_out.json`` comes into existence, and the later sentence

    read x.json and save the result to x_out.json

then offers the binder two named, type-compatible, existing ``.json`` files.  F7 declines to
bind an output that already exists, so the step spools elsewhere and the sentence's own
destination is left unclaimed - and the input binder counts it:

    BINDING_REFUSED:json_path:2_type_compatible_existing_files_named
    matching = ['.../x.json', '.../x_out.json']

The sentence never offered x_out.json as a source.  It named it as the destination.
"""

import pathlib
import shutil
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
for _p in (ROOT, ROOT / "canonical" / "runtime"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

SCRATCH = ROOT / "canonical/astra_runtime/tmp/test_output_destination_not_input_v1"
MODULE = "canonical/runtime/bounded_claim_support.py"
CID = "brain.module.function.invoke"
IN_REL = (SCRATCH.relative_to(ROOT) / "x.json").as_posix()
OUT_REL = (SCRATCH.relative_to(ROOT) / "x_out.json").as_posix()
SENTENCE = (
    f"Call the function classify_support in {MODULE} with the payload {IN_REL} "
    f"and save the result to {OUT_REL}"
)


def _registry():
    from canonical.runtime import goal_compiler as gc
    from canonical.runtime import live_integrated_brain_v1 as lib

    return gc._platform_admissible_registry(dict(lib.load_verified_registry()))


def _entry():
    entry = dict(_registry()[CID])
    # sel.select admits against the DECLARED contract, which is where the four
    # placeholders live; the executable template carries the zero-input form.
    entry["action_template"] = entry["declared_action_template"]
    return entry


class DestinationIsNotASourceTests(unittest.TestCase):
    def setUp(self) -> None:
        SCRATCH.mkdir(parents=True, exist_ok=True)
        (SCRATCH / "x.json").write_text('{"claim_text": "a", "evidence_text": "a"}', encoding="utf-8")

    def tearDown(self) -> None:
        shutil.rmtree(SCRATCH, ignore_errors=True)

    def test_an_existing_destination_does_not_make_the_stated_input_ambiguous(self):
        """The exact state the module run reaches: the destination is already on disk."""
        from canonical.runtime import goal_front_compiler_v1 as front

        (SCRATCH / "x_out.json").write_text("{}", encoding="utf-8")
        self.assertTrue((SCRATCH / "x_out.json").is_file())

        from canonical.runtime import capability_selection_retrieval_v1 as sel

        decision = sel.select(SENTENCE, _registry(), ROOT)
        # The refusal this fixes, verbatim, must not come back.
        self.assertNotIn("2_type_compatible_existing_files_named", str(decision.get("reason")))
        self.assertEqual(decision["status"], "SELECTED", decision.get("reason"))
        self.assertEqual(decision["selected_capability"], CID)
        # The input the sentence actually named, not its sibling destination.
        self.assertEqual(decision["inputs"]["json_path"], IN_REL)

    def test_only_the_role_anchored_path_is_treated_as_a_destination(self):
        """A type sweep would exclude the real input too; the role must decide."""
        from canonical.runtime import goal_front_compiler_v1 as front

        (SCRATCH / "x_out.json").write_text("{}", encoding="utf-8")
        entry = _entry()
        keys = front.input_keys(entry)
        named = front._named_output_destinations(SENTENCE, entry, keys, ROOT)

        self.assertIn(OUT_REL, named, "the stated destination was not recognised")
        self.assertNotIn(IN_REL, named, "the stated INPUT was misread as a destination")
        self.assertNotIn(MODULE, named, "the module path was misread as a destination")

    def test_without_an_output_role_nothing_is_excluded(self):
        """A sentence that states no destination must not silently lose candidates."""
        from canonical.runtime import goal_front_compiler_v1 as front

        entry = _entry()
        keys = front.input_keys(entry)
        bare = f"Call the function classify_support in {MODULE} with the payload {IN_REL}"
        self.assertEqual(front._named_output_destinations(bare, entry, keys, ROOT), set())

    def test_a_self_overwrite_is_still_refused(self):
        """The one case the tightening may newly refuse: the same path as source and sink."""
        from canonical.runtime import goal_front_compiler_v1 as front
        from canonical.runtime.goal_compiler import GoalCompilationFailure

        same = (SCRATCH.relative_to(ROOT) / "same.json").as_posix()
        (SCRATCH / "same.json").write_text("{}", encoding="utf-8")
        goal = (
            f"Call the function classify_support in {MODULE} with the payload {same} "
            f"and save the result to {same}"
        )
        entry = _entry()
        keys = front.input_keys(entry)
        # The sentence mentions the path twice; the SECOND mention carries the destination
        # role, so recognising it requires looking past the first occurrence.
        self.assertEqual(front._named_output_destinations(goal, entry, keys, ROOT), {same})
        # With the only named file claimed as the sink, there is nothing left to read.
        with self.assertRaises(GoalCompilationFailure):
            front.bind_all_inputs(goal, entry, ROOT, spool=set(), cycle=0)


class SelectionSuiteIsOrderIndependentTests(unittest.TestCase):
    """The symptom this fixes: the module passed class-by-class and failed as a whole."""

    def test_the_selection_module_passes_as_a_whole(self):
        import canonical.tests.test_capability_selection_retrieval_v1 as mod

        suite = unittest.TestLoader().loadTestsFromModule(mod)
        result = unittest.TextTestRunner(stream=open("/dev/null", "w"), verbosity=0).run(suite)
        self.assertEqual(result.errors, [], [str(e[0]) for e in result.errors])
        self.assertEqual(result.failures, [], [str(f[0]) for f in result.failures])


if __name__ == "__main__":
    unittest.main()
