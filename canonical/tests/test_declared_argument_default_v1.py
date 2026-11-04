"""The template language can finally say "the goal's value, else this default".

THE DEFECT THIS REPLACES
------------------------
On 73f773d two registry rows froze `search_root` as a bare literal:

    source.candidates.enumerate.stdlib         search_root = "canonical/runtime"
    structured.decision_evidence.locate.stdlib search_root = "canonical"

A bare literal never enters `world_binding_v1`'s precedence chain
(`GOAL > DEMONSTRATED RECEIPT > WORLD HEURISTIC`) because it is not a placeholder.
It is never bound, so nothing can override it, and `render_args` emits it
unchanged.  The effective precedence was:

    FROZEN LITERAL > GOAL

Measured: `Find the function in the python source root <X> ...` enumerated 400
files under `canonical/runtime` while `<X>` was never read, and returned
PASS__RAW_GOAL_EXECUTED_AND_EXACT_SEMANTIC_ACCEPTANCE_VERIFIED.

WHY THE OBVIOUS REPAIR IS ALSO WRONG
------------------------------------
Writing `"${input.search_root}"` -- the form 35 rows already use for `source_root`
-- binds the goal's value correctly, and was measured doing so.  But a bare
placeholder makes the row UNBINDABLE when the goal is silent, because
`complete_inputs` reports the slot in `missing` and every caller refuses on a
non-empty `missing`.  So the two available forms were:

    frozen literal    -> the goal can never win
    bare placeholder  -> the goal must always speak

The registry has been forced to choose between them, and that forced choice is
the defect.  A frozen literal is not a default; it is a value that outranks the
sentence.

THE THIRD FORM
--------------
    "${input.search_root | canonical/runtime}"

The binder still TRIES to ground the slot from the goal -- that is what lets the
goal win -- and the default decides only what happens when the try fails.  A slot
filled by its default is reported in `filled_from_declared_default`, so a constant
is never again indistinguishable from a grounded value at the point of use.

These are regression tests under TRUE_CAPABILITY_TEST_LAW_V1.  They pin a
precedence rule.  They are not a capability claim.
"""
import json
import pathlib
import sys
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from canonical.runtime import declared_argument_default_v1 as DAD  # noqa: E402
from canonical.runtime import world_binding_v1 as WB  # noqa: E402

REGISTRY = REPO_ROOT / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"


def _registry():
    return json.loads(REGISTRY.read_text(encoding="utf-8"))["capabilities"]


def _entry(**args):
    return {"capability_id": "x", "action_template": {"type": "invoke_capability", "args": args}}


class TheDefaultIsDataNotAGuessTests(unittest.TestCase):

    def test_a_declared_default_is_read_from_the_template(self):
        e = _entry(search_root="${input.search_root | canonical/runtime}",
                   glob="${input.glob | **/*.py}", output_path="${input.output_path}")
        self.assertEqual(DAD.declared_defaults(e),
                         {"search_root": "canonical/runtime", "glob": "**/*.py"})

    def test_a_row_that_declares_nothing_is_untouched(self):
        e = _entry(search_root="${input.search_root}", output_path="${input.output_path}")
        self.assertEqual(DAD.declared_defaults(e), {})
        self.assertEqual(DAD.required_names(e), ["output_path", "search_root"])

    def test_a_declared_slot_is_not_required_from_the_binder(self):
        e = _entry(search_root="${input.search_root | canonical/runtime}",
                   output_path="${input.output_path}")
        self.assertEqual(DAD.required_names(e), ["output_path"])

    def test_two_different_defaults_for_one_name_are_refused(self):
        e = _entry(a="${input.a | one}", b="${input.a | two}")
        self.assertEqual(DAD.conflicting_defaults(e), ["a"])
        with self.assertRaises(KeyError) as ctx:
            WB.render_args(e, {})
        self.assertIn("AMBIGUOUS_DECLARED_DEFAULT", str(ctx.exception))


class TheGoalOutranksTheDefaultTests(unittest.TestCase):

    def test_the_goal_wins_when_it_speaks(self):
        e = _entry(search_root="${input.search_root | canonical/runtime}")
        out = WB.render_args(e, {"search_root": "some/stated/root"})
        self.assertEqual(out["search_root"], "some/stated/root")

    def test_the_default_applies_only_when_the_goal_is_silent(self):
        e = _entry(search_root="${input.search_root | canonical/runtime}")
        self.assertEqual(WB.render_args(e, {})["search_root"], "canonical/runtime")

    def test_a_bound_empty_string_still_loses_to_the_default(self):
        """Whitespace is not a value.  A blank binding must not shadow the default."""
        e = _entry(search_root="${input.search_root | canonical/runtime}")
        self.assertEqual(WB.render_args(e, {"search_root": "  "})["search_root"],
                         "canonical/runtime")

    def test_a_plain_placeholder_is_still_substituted(self):
        """The defaulted form must not disable ordinary substitution."""
        e = _entry(objective="${input.goal}", search_root="${input.search_root | canonical/runtime}")
        out = WB.render_args(e, {"goal": "do the thing"})
        self.assertEqual(out["objective"], "do the thing")
        self.assertEqual(out["search_root"], "canonical/runtime")

    def test_an_undeclared_unbound_slot_still_fails_closed(self):
        """The default is a declaration, not a licence to invent values."""
        e = _entry(output_path="${input.output_path}")
        with self.assertRaises(KeyError) as ctx:
            WB.render_args(e, {})
        self.assertIn("UNBOUND_TEMPLATE_ARGUMENT", str(ctx.exception))


class TheBinderForgivesADeclaredSlotAndOnlyThatTests(unittest.TestCase):

    ROOT = pathlib.Path(REPO_ROOT).resolve()
    STATED = "canonical/astra_runtime/tmp/declared_default_probe/pkg"

    @classmethod
    def setUpClass(cls):
        probe = cls.ROOT / "canonical/astra_runtime/tmp/declared_default_probe"
        (probe / "pkg").mkdir(parents=True, exist_ok=True)
        (probe / "pkg" / "calc.py").write_text(
            "def used(a, b):\n    return a + b\n\n\ndef never_called(x):\n    return x * 2\n",
            encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        import shutil
        shutil.rmtree(cls.ROOT / "canonical/astra_runtime/tmp/declared_default_probe",
                      ignore_errors=True)

    def _goal(self, root=None):
        return ("Find the function in the python source root %s that is never "
                "executed, and write its name to "
                "canonical/astra_runtime/tmp/declared_default_probe/a.json"
                % (root or self.STATED))

    def test_the_stated_root_is_bound_from_the_goal(self):
        entry = _registry()["source.candidates.enumerate.stdlib"]
        completed = WB.complete_inputs(self._goal(), self.ROOT, entry)
        self.assertEqual(completed["inputs"].get("search_root"), self.STATED)
        self.assertEqual(completed["missing"], [])
        rendered = WB.render_args(entry, completed["inputs"])
        self.assertEqual(rendered["search_root"], self.STATED)

    def test_a_silent_goal_is_not_missing_the_declared_slot(self):
        """The whole point: no longer forced to choose between literal and refusal."""
        entry = _registry()["source.candidates.enumerate.stdlib"]
        silent = ("Enumerate the candidate source files, rank them by lexical "
                  "relevance to the objective, and write the report to "
                  "canonical/astra_runtime/tmp/declared_default_probe/b.json")
        completed = WB.complete_inputs(silent, self.ROOT, entry)
        self.assertEqual(completed["missing"], [])
        self.assertIn("search_root", completed["filled_from_declared_default"])
        rendered = WB.render_args(entry, completed["inputs"])
        self.assertEqual(rendered["search_root"], "canonical/runtime")

    def test_the_constant_is_reported_not_hidden(self):
        entry = _registry()["source.candidates.enumerate.stdlib"]
        silent = ("Enumerate the candidate source files, rank them by lexical "
                  "relevance to the objective, and write the report to "
                  "canonical/astra_runtime/tmp/declared_default_probe/c.json")
        completed = WB.complete_inputs(silent, self.ROOT, entry)
        self.assertEqual(completed["filled_from_declared_default"]["search_root"],
                         "canonical/runtime")

    def test_no_registry_row_has_resurrected_a_frozen_read_root(self):
        """Neither of the two measured rows may go back to a bare literal."""
        registry = _registry()
        for cid in ("source.candidates.enumerate.stdlib",
                    "structured.decision_evidence.locate.stdlib"):
            args = registry[cid]["action_template"]["args"]
            with self.subTest(capability=cid):
                self.assertIn("${input.search_root", args["search_root"],
                              "a bare literal outranks the sentence")

    def test_every_frozen_literal_left_is_structurally_required(self):
        """A frozen literal is only legitimate where no goal could ever supply it.

        `package = "@dfinity/cbor"` names WHICH package the row encodes; the
        sentence cannot supply it, and the adapter has no default.  `search_root`
        is a directory the sentence routinely names, and the adapter already
        defaults it.  The distinction is measurable, so it is pinned.
        """
        import re
        placeholder = re.compile(r"\$\{input\.")
        allowed = {
            ("auto.npm.dfinity-cbor", "package"),
            ("auto.npm.msgpack-msgpack", "package"),
            ("auto.npm.shelacek-ubjson", "package"),
        }
        frozen = set()
        for cid, entry in _registry().items():
            args = (entry.get("action_template") or {}).get("args") or {}
            if not isinstance(args, dict):
                continue
            for key, value in args.items():
                if (isinstance(value, str) and not placeholder.search(value)
                        and key != "capability_id"
                        and ("/" in value or key.endswith(("_root", "_path", "_dir")))):
                    frozen.add((cid, key))
        self.assertEqual(frozen, allowed)


if __name__ == "__main__":
    unittest.main()
