"""An ordinary sentence must run the command it states, and be checked for it.

``shell.command.run`` has been a ``VERIFIED_BOUND_CAPABILITY`` with an
independently verified output since PR #6120. Until now it was reachable only
from a sentence that QUOTED a command line -- "Run the shell command cp a b".
Phrased the way a person writes, "Copy the file a to b", it produced no argv at
all. Measured on ``0a87ba6``: **0 of 12** ordinary prose requests ran.

Three things had to change together, and each is pinned here:

1. A sentence stating a command in words yields that command's argv. Every
   program in the table is one the acceptance layer already knows how to judge
   afterwards, and an operand-count mismatch is refused rather than completed --
   an invented operand is an invented side effect.

2. ``solve`` falls through to a chain when the front compiler's selection was
   refused *and the sentence states a command line*. Measured on 0a87ba6, "Compute
   the sha256 of the file a1.txt" ranked ``shell.command.run`` FIRST at score 8,
   could not bind its argv from prose, moved on to ``finance.saccr.credit.addon.v1``
   on the single matched word "compute", and fail-closed that as
   ``R3_WEAK_EVIDENCE`` -- while the composer reached the request in one step.

3. ``sort -o B A`` gets a postcondition. Its promise is the strongest in the
   table because it needs no trust at all: the sorted bytes are recomputed from
   the source, which ``sort`` leaves on disk, and compared with the destination.

These tests read the effect back from the file system. They never trust ``pass``,
``status`` or any producer flag, because the defect classes this family keeps
finding are green verdicts over work that did not happen.
"""

from __future__ import annotations
import json
import os
import re

import shutil
import sys
import time
import pathlib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
RUNTIME = ROOT / "canonical" / "runtime"
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))

import canonical.runtime.composer_route_v1 as _binder  # noqa: E402

# No English words: every path component becomes a goal token, so a directory
# named for the behaviour under test can change which capability is selected.
SCRATCH = "canonical/astra_runtime/tmp/m3v7x"
UNSORTED = "banana\napple\ncherry\n"
SORTED = "apple\nbanana\ncherry\n"

extract_argv = getattr(_binder, "extract_argv", None)


def _argv(text: str):
    if extract_argv is None:
        raise AssertionError("composer_route_v1 has no extract_argv")
    return extract_argv(text)


def _fresh(content: str = UNSORTED) -> str:
    root = ROOT / SCRATCH
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    f = "%s/a1.txt" % SCRATCH
    (ROOT / f).write_text(content, encoding="utf-8")
    return f


def _solve(goal: str):
    from canonical.runtime.live_brain_route_admission_v1 import solve

    return solve({"task_id": "PROSE_%x" % time.perf_counter_ns(), "goal": goal})


def _verified(result) -> bool:
    """Accepted, and accepted for the right reason."""
    return (result.get("pass") is True
            and (result.get("raw_goal_acceptance") or {}).get("pass") is True
            and str(result.get("status") or "").endswith(
                "EXACT_SEMANTIC_ACCEPTANCE_VERIFIED"))


def _stdout(result) -> str | None:
    """The text the run actually produced, or None if it produced none.

    Asserting the argv proves only that a sentence was translated; the answer is
    what the caller asked for.  Read out of the acceptance record the same way
    the class-level helpers in this file read it.
    """
    import json as _json, re as _re
    text = _json.dumps(result, default=str)
    m = _re.search(r'"stdout"\s*:\s*"((?:[^"\\]|\\.)*)"', text)
    return m.group(1).encode().decode("unicode_escape") if m else None


def _ra_compatible_registry():
    """The registry the live gate judges against, loaded the way it loads it."""
    from canonical.runtime import capability_composer_v1 as _comp
    reg = _comp.load_registry()
    return {cid: (e if isinstance(e, dict) else dict(e)) for cid, e in reg.items()}


class TestAnOrdinarySentenceYieldsTheCommandItStates(unittest.TestCase):
    """Half one: the words become the argv, token for token, or nothing."""

    CASES = (
        ("Copy the file {f} to {g}", ["cp", "{f}", "{g}"]),
        ("Move the file {f} to {g}", ["mv", "{f}", "{g}"]),
        ("Remove the file {f}", ["rm", "{f}"]),
        ("Create the directory {d}", ["mkdir", "{d}"]),
        ("Create an empty file {e}", ["touch", "{e}"]),
        ("Read the file {f}", ["cat", "{f}"]),
        ("Count the lines in the file {f}", ["wc", "-l", "{f}"]),
        ("Show the first 2 lines of the file {f}", ["head", "-n", "2", "{f}"]),
        ("Sort the file {f}", ["sort", "{f}"]),
        ("Compute the sha256 of the file {f}", ["sha256sum", "{f}"]),
        # The destination is not the last operand here: sort writes through -o.
        ("Sort the file {f} into {g}", ["sort", "-o", "{g}", "{f}"]),
        # --- the rest of the surface the verifier already knows how to judge.
        # Before this block 11 of those 30 commands were reachable from English
        # and 19 were not; the acceptance machinery for every one of them already
        # existed, and only the translation was missing.
        ("Compute the md5 of the file {f}", ["md5sum", "{f}"]),
        ("Show the unique lines of the file {f}", ["sort", "-u", "{f}"]),
        ("Reverse the lines of the file {f}", ["tac", "{f}"]),
        ("Number the lines of the file {f}", ["nl", "{f}"]),
        ("List the directory {d}", ["ls", "{d}"]),
        ("Show the base name of {f}", ["basename", "{f}"]),
        ("Show the directory name of {f}", ["dirname", "{f}"]),
        ("Show the real path of {f}", ["realpath", "{f}"]),
        ("Show the octal dump of the file {f}", ["od", "{f}"]),
        ("Find the lines in the file {f} matching 'apple'", ["grep", "apple", "{f}"]),
        # --- the counting verbs, the column selector and the literal search.
        ("Count the words in the file {f}", ["wc", "-w", "{f}"]),
        ("Count the bytes in the file {f}", ["wc", "-c", "{f}"]),
        ("Count the characters in the file {f}", ["wc", "-c", "{f}"]),
        # `-s` is asserted here on purpose.  Without it `cut -f 2` prints a line
        # that has no delimiter UNCHANGED, so on a file with no tab in it "the
        # second column" was certified returning the whole file.  `-s` suppresses
        # such a line, which is the truthful answer: there is no second column.
        ("Show the first field of the file {f}", ["cut", "-s", "-f", "1", "{f}"]),
        ("Show the second column of the file {f}", ["cut", "-s", "-f", "2", "{f}"]),
        ("Cut field 3 from the file {f}", ["cut", "-s", "-f", "3", "{f}"]),
        ("Search the file {f} for the exact text 'a.c'", ["fgrep", "a.c", "{f}"]),
        # --- a byte comparison and a pattern search, each reached only by a
        #     sentence that SAYS which question it is asking.
        ("Compare the file {f} and {f} byte by byte", ["cmp", "{f}", "{f}"]),
        ("Compare the file {f} and {f} byte-for-byte", ["cmp", "{f}", "{f}"]),
        # `-s`, and measured: plain `cmp` on two identical files exits 0 having printed
        # nothing, and the adapter raises CLI_EXPECTED_OUTPUT_MISSING -- the command
        # could not answer the very question the sentence asked.  Silent `cmp`
        # answers with its exit status, which is what the sentence wants.
        ("Check whether the file {f} and {f} are identical bytes", ["cmp", "-s", "{f}", "{f}"]),
        ("Search the file {f} for the regex 'a|b'", ["egrep", "a|b", "{f}"]),
        ("Search the file {f} for the extended pattern 'a|b'", ["egrep", "a|b", "{f}"]),
        ("Find the literal string 'b[n' in the file {f}", ["fgrep", "b[n", "{f}"]),
        ("Search the file {f} with an extended search for 'a|b'", ["egrep", "a|b", "{f}"]),
    )

    # Deliberately NOT bound, each measured rather than assumed.
    #
    # `diff` USED to be on this list, and the version of this test that kept it
    # there was right at the time: diff reports "they differ" as exit status 1
    # and the adapter raised on any non-zero exit, so binding it ran a command
    # and then reported failure over work that succeeded.  What changed is that
    # the adapter no longer makes that judgement -- the caller declares the codes
    # that are answers, and the verifier re-runs the command and compares the
    # code.  So diff moved from this list to a positive test below, which is a
    # harder claim than the refusal was.
    #
    # `stat` stays: it prints access and modify times, so running it twice cannot
    # give the same bytes and the re-inspection that makes a reader trustworthy
    # is unavailable.  `cmp` stays out of prose for a different reason -- reaching
    # it would need bare task verbs on the command runner's keywords, which is
    # the move that measurably broke the model's own verifier.
    NO_TRUTHFUL_CHECK = (
        "Show the status of the file {f}",      # stat: timestamps never repeat
    )

    SUBS = (("{f}", "%s/a1.txt" % SCRATCH), ("{g}", "%s/b2.txt" % SCRATCH),
            ("{d}", "%s/d9" % SCRATCH), ("{e}", "%s/e9" % SCRATCH))

    def _fmt(self, argv):
        out = []
        for part in argv:
            for needle, value in self.SUBS:
                part = part.replace(needle, value)
            out.append(part)
        return out

    def test_every_prose_command_binds_the_command_it_stated(self):
        wrong = []
        for template, want in self.CASES:
            goal = self._fmt([template])[0]
            got = _argv(goal)
            if got != self._fmt(want):
                wrong.append((template, got, self._fmt(want)))
        self.assertEqual(wrong, [], "prose command not bound exactly: %r" % wrong)

    def test_a_command_with_no_truthful_check_is_never_bound(self):
        """Never the unverifiable program, whatever else the sentence falls to.

        The claim is about the PROGRAM, not about refusal.  "Show the status of
        the file X" legitimately falls through to the general read rule and
        binds `cat`, which is verifiable and harmless; what it must never do is
        bind `stat`, whose answer cannot be checked.  Asserting None here would
        have been the weaker test -- it would have failed the moment any other
        rule served the sentence, for a reason that has nothing to do with stat.
        """
        banned = {"stat", "diff", "cmp"}
        for template in self.NO_TRUTHFUL_CHECK:
            goal = self._fmt([template])[0]
            argv = _argv(goal)
            program = argv[0] if argv else None
            self.assertNotIn(
                program, banned,
                "bound %r for %r, whose answer this layer cannot verify -- "
                "running it reports failure over work that succeeded"
                % (program, template))

    def test_a_plain_comparison_still_answers_how_they_differ(self):
        """The stealing guard: `cmp` must not take `diff`'s question.

        The first pattern to match wins, and the cmp row sits above the diff row
        so that "byte by byte" reaches cmp at all.  "Compare a against b" asks
        HOW they differ, which only diff answers, so it must not be captured.
        A row placed to win one phrasing is a row that can steal another.
        """
        for sentence in ("Diff the file %s against %s", "Compare the file %s against %s"):
            a, b = "%s/a1.txt" % SCRATCH, "%s/b2.txt" % SCRATCH
            argv = _argv(sentence % (a, b))
            self.assertEqual(argv, ["diff", a, b],
                             "%r lost its route to cmp: %r" % (sentence, argv))

    def test_a_capability_whose_own_precondition_the_sentence_cannot_meet_is_refused_not_run(self):
        """The guard that makes "regular expression" a route again.

        Measured before this existed: the single generic word "expression"
        scored 11 and ranked math.numeric_expression.sympy first, its `variables`
        slot was silently defaulted to `{}`, admission GRANTED it, and the
        calculator then evaluated the caller's own search text as arithmetic --
        NUMERIC_EXPRESSION_VARIABLE_UNBOUND:plum -- displacing the command runner
        that the same sentence had fully and correctly bound.

        The rule applied is not new policy.  It is the capability's own contract,
        which its adapter already enforces by raising that very error; the only
        change is WHEN.  At execution it is a crash that has already displaced a
        correct route.  At admission it is a refusal, and the existing
        composition fallthrough serves the command the sentence stated.
        """
        from canonical.runtime import capability_selection_retrieval_v1 as _sel
        from canonical.runtime import live_integrated_brain_v1 as _L
        entry = _L.load_verified_registry()["math.numeric_expression.sympy"]
        verdict = _sel.admit("Search the file %s for the regular expression 'plum'"
                             % (SCRATCH + "/a1.txt"),
                             "math.numeric_expression.sympy", entry, ROOT)
        self.assertIs(verdict.get("admitted"), False,
                      "a calculator was admitted for a sentence that states no "
                      "variables: %r" % verdict)
        self.assertTrue(str(verdict.get("reason") or "").startswith(
                            "BINDING_REFUSED:TYPED_SCALAR_INPUTS_UNDECLARED:"),
                        "the refusal must carry the prefix the route layer "
                        "listens for, or the fallthrough cannot serve the "
                        "command: %r" % verdict.get("reason"))
        self.assertIn("plum", str(verdict.get("reason")),
                      "the refusal must name the undeclared input it found: %r"
                      % verdict.get("reason"))

    def test_a_real_arithmetic_request_is_still_admitted(self):
        """The guard must not disable the capability it constrains.

        A refusal that fires on everything is not a guard, it is a deletion.  An
        expression of literals declares no names, so it needs no variables and
        must still be admitted -- and so must one whose names ARE declared.
        """
        from canonical.runtime import capability_selection_retrieval_v1 as _sel
        from canonical.runtime import live_integrated_brain_v1 as _L
        entry = _L.load_verified_registry()["math.numeric_expression.sympy"]
        cid = "math.numeric_expression.sympy"
        out = SCRATCH + "/out.json"
        granted = _sel.admit("Evaluate the numeric expression '2 + 3' and write "
                             "the result to %s" % out, cid, entry, ROOT)
        self.assertIs(granted.get("admitted"), True,
                      "the guard disabled literal arithmetic: %r" % granted)
        self.assertEqual(_sel._undeclared_expression_names("2 + 3", "{}"), [],
                         "a literal expression was read as needing variables")
        self.assertIsNone(_sel._undeclared_expression_names("not an expression ;", "{}"),
                          "unparsable text must be left to the adapter, not judged here")
        self.assertEqual(_sel._undeclared_expression_names("plum", "{}"), ["plum"],
                         "an undeclared name was not detected")
        self.assertEqual(_sel._undeclared_expression_names("a + b", '{"a": 1, "b": 2}'),
                         [], "declared variables were reported as missing")

    def test_the_guard_is_scoped_to_the_one_precondition_it_was_written_for(self):
        """39 entries require an effect nothing provides, and this must not touch them.

        Measured, not assumed: refusing a capability merely for having an
        unsatisfied `requires` would have broken all 39, because effects like
        `image.file.available` and `manifest.json.available` are supplied by the
        GOAL stating a path, not by another capability.  This test is the pin on
        that blast radius -- widen the guard and it goes red.
        """
        from canonical.runtime import capability_selection_retrieval_v1 as _sel
        import json as _json
        caps = _json.loads((ROOT / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json")
                           .read_text(encoding="utf-8"))["capabilities"]
        items = caps if isinstance(caps, list) else list(caps.items())
        provided = set()
        for item in items:
            e = item[1] if isinstance(item, tuple) else item
            provided |= {str(x) for x in (e.get("provides") or [])}
        unsatisfied = []
        for item in items:
            e = item[1] if isinstance(item, tuple) else item
            cid = e.get("capability_id") or (item[0] if isinstance(item, tuple) else "")
            if [str(x) for x in (e.get("requires") or []) if str(x) not in provided]:
                unsatisfied.append((cid, [str(x) for x in (e.get("requires") or [])]))
        self.assertGreater(len(unsatisfied), 30,
                           "the measured blast radius shrank, so this pin no "
                           "longer proves anything: %d" % len(unsatisfied))
        scoped = [cid for cid, reqs in unsatisfied
                  if _sel._TYPED_SCALAR_PRECONDITION in reqs]
        self.assertEqual(scoped, ["math.numeric_expression.sympy"],
                         "the guard's precondition is declared by more than the "
                         "one entry it was measured against: %r" % scoped)

    def test_the_phrasing_that_once_hijacked_the_binder_now_reaches_its_command(self):
        """Rewritten, not deleted: this test pinned the limitation as permanent.

        It used to assert that "regular expression" must NOT bind egrep, because
        the phrasing measurably could not reach the command.  The cause was
        admission, not the trigger, so the assertion is now the opposite and is
        checked end to end -- which is the only form that would have caught the
        hijack, since argv was correct the whole time.
        """
        argv = _argv("Search the file %s for the regular expression 'plum|grape'"
                     % (SCRATCH + "/a1.txt"))
        self.assertEqual(argv, ["egrep", "plum|grape", "%s/a1.txt" % SCRATCH],
                         "the phrasing no longer binds egrep: %r" % argv)
        f = _fresh("banana apple\ncherry plum\nfig grape\n")
        result = _solve("Search the file %s for the regular expression 'plum|grape'" % f)
        self.assertTrue(_verified(result),
                        "the phrasing binds egrep but was not verified -- the "
                        "hijack is back: %r / %r"
                        % (result.get("status"), result.get("failure_reason")))
        steps = (result.get("composer_execution") or {}).get("steps") or []
        out = str((steps[0].get("result") or {}).get("stdout") or "")
        self.assertEqual(sorted(out.splitlines()), ["cherry plum", "fig grape"],
                         "the alternation did not match both lines: %r" % out)

    def test_an_ordinary_word_that_draws_a_tie_does_not_cost_the_command(self):
        """Three phrasings of one request must not differ by a routing accident.

        Measured: "Show the files in the directory <d>" ranked shell.command.run
        and source.candidates.enumerate.stdlib at 4 each on the word "files", so
        admission fail-closed R3_WEAK_EVIDENCE with typed_binding_refused unset
        and the composition gate never fired -- while "List the directory <d>"
        and "Show the contents of the directory <d>", the same command over the
        same operand, both ran and were exact-verified.  One ordinary word was
        the whole difference.

        A tie between CAPABILITIES says nothing about the COMMAND, and the
        command is what would be executed: extract_argv refuses on ambiguity by
        construction, so a non-None result is one settled argv.
        """
        same = [_argv("List the directory %s" % (SCRATCH + "/listing")),
                _argv("Show the files in the directory %s" % (SCRATCH + "/listing")),
                _argv("Show the contents of the directory %s" % (SCRATCH + "/listing"))]
        self.assertEqual(same[0], same[1],
                         "the three phrasings do not even state the same command: %r" % same)
        d = SCRATCH + "/listing"
        (ROOT / d).mkdir(parents=True, exist_ok=True)
        (ROOT / d / "one.txt").write_text("x\n", encoding="utf-8")
        (ROOT / d / "two.txt").write_text("y\n", encoding="utf-8")
        for sentence in ("List the directory %s", "Show the files in the directory %s",
                         "Show the contents of the directory %s"):
            result = _solve(sentence % d)
            self.assertTrue(_verified(result),
                            "%r was refused while its synonyms ran -- a tie "
                            "between capabilities cost the command: %r"
                            % (sentence, result.get("status")))
            steps = (result.get("composer_execution") or {}).get("steps") or []
            out = str((steps[0].get("result") or {}).get("stdout") or "")
            self.assertEqual(sorted(out.splitlines()), ["one.txt", "two.txt"],
                             "%r listed the wrong entries: %r" % (sentence, out))

    def test_a_sentence_that_states_no_command_line_still_fails_closed(self):
        """The pin on the widened gate: this is the #6119 data-destruction class.

        The composition gate was widened so that a stated command line is served
        even when the single-capability route was refused for ambiguity.  The
        widening is safe for exactly one reason -- extract_argv is None unless
        the sentence states a command -- so a sentence that states nothing keeps
        failing closed.  Measured before this change and required to be
        unchanged after it: the file must survive untouched.
        """
        f = _fresh("banana\napple\ncherry\n")
        before = (ROOT / f).read_text(encoding="utf-8")
        for sentence in ("Check the file %s", "Verify the file %s"):
            result = _solve(sentence % f)
            self.assertIsNot(result.get("pass"), True,
                             "%r was accepted, which is how a file gets "
                             "overwritten by a report about it: %r"
                             % (sentence, result.get("status")))
            self.assertEqual((ROOT / f).read_text(encoding="utf-8"), before,
                             "%r changed a file it only mentioned" % sentence)

    def test_the_synonyms_that_were_measured_to_bind_nothing_now_bind_their_command(self):
        """Each row here is a phrasing measured to fail, not one invented in advance.

        A hand-written table of patterns refuses every phrasing nobody thought
        to write down.  These four were found by running ordinary sentences
        against the table and keeping only the ones that actually broke.
        """
        f = SCRATCH + "/a1.txt"
        for sentence, expected in (
            ("Duplicate the file %s as %s" % (f, SCRATCH + "/b2.txt"),
             ["cp", f, SCRATCH + "/b2.txt"]),
            ("How many lines are in the file %s" % f, ["wc", "-l", f]),
            ("How many words are in the file %s" % f, ["wc", "-w", f]),
            # head and tail default to 2 lines when the sentence states no
            # count -- the existing contract, asserted here rather than assumed.
            ("Show me the beginning of the file %s" % f, ["head", "-n", "2", f]),
            ("Show me the end of the file %s" % f, ["tail", "-n", "2", f]),
        ):
            self.assertEqual(_argv(sentence), expected,
                             "%r bound %r" % (sentence, _argv(sentence)))

    def test_a_destination_may_be_described_not_only_named(self):
        """The bytes on disk are the assertion, not the status.

        Measured before this: only the bare "to the file X" worked.  Any
        ordinary adjective between the article and the noun -- output, target,
        destination, given, new -- lost the request, in two independent places
        that had drifted apart.  The write itself was never the problem: the
        bytes were correct and the verifier then reported
        STEP_TEXT_PAYLOAD_NOT_IN_THE_REQUEST, a failure reported over work that
        succeeded.
        """
        want = "PROJECT BRAIN"
        for phrase in ("to the file", "to the output file", "to the target file",
                       "to the destination file", "to the output path",
                       "to the given file", "to the new output file"):
            name = "w%d.txt" % (abs(hash(phrase)) % 99999)
            path = SCRATCH + "/" + name
            result = _solve("Write the text '%s' %s %s." % (want, phrase, path))
            self.assertTrue(_verified(result),
                            "%r was refused: %r / %r"
                            % (phrase, result.get("status"),
                               (result.get("raw_goal_acceptance") or {}).get("reason")))
            written = ROOT / path
            self.assertTrue(written.exists(), "%r wrote nothing" % phrase)
            self.assertEqual(written.read_text(encoding="utf-8"), want,
                             "%r wrote the wrong bytes: %r"
                             % (phrase, written.read_text(encoding="utf-8")))

    def test_the_two_destination_readings_must_agree_on_the_same_sentence(self):
        """The drift pin.  This is the bug, and this is what stops it returning.

        The composer decides where a payload goes with _DEST_WORDS, and the
        acceptance layer independently decides whether a payload runs to a
        destination with _BETWEEN_PAYLOAD_AND_DEST.  They are not shared on
        purpose -- an inspector that asks the binder what it meant is not an
        inspector -- but they answer the same question about the same sentence.
        Measured: they had drifted, so one bound a destination the other then
        refused, and a correct write was reported as a payload the request never
        stated.  Widening either one alone moves nothing end to end.
        """
        from canonical.runtime import composer_route_v1 as _cr
        from canonical.runtime import raw_goal_trace_acceptance_v1 as _acc
        payload = "PROJECT BRAIN"
        for phrase in ("to the file", "to the output file", "to the target file",
                       "to the destination file", "into the output path",
                       "to the given file", "to the new output file"):
            path = SCRATCH + "/agree.txt"
            sentence = "Write the text '%s' %s %s." % (payload, phrase, path)
            bound = _cr.extract_content_destination(sentence)
            self.assertEqual(bound, path,
                             "%r: the composer bound %r as the destination"
                             % (phrase, bound))
            self.assertTrue(_acc._payload_runs_to_the_destination(sentence, payload),
                            "%r: the composer bound the destination but the "
                            "inspector refuses the payload -- the two readings "
                            "have drifted apart again" % phrase)

    def test_a_truncated_payload_is_still_refused_by_both_readings(self):
        """The defence the widening must not weaken.

        A truncated payload is still a substring of the sentence that produced
        it, so containment proves nothing.  What distinguishes the payload the
        sentence stated is that the sentence is DONE with it: a destination
        follows immediately.  Allowing a destination to be described widens the
        prefix, never the lookahead, so this must be unchanged.
        """
        from canonical.runtime import raw_goal_trace_acceptance_v1 as _acc
        sentence = ("Write the text 'the results are in the attachment' "
                    "to the output file %s/a1.txt." % SCRATCH)
        for truncated in ("results are", "the results are", "results are in"):
            self.assertFalse(_acc._payload_runs_to_the_destination(sentence, truncated),
                             "a truncated payload %r was accepted -- allowing a "
                             "described destination weakened the defence" % truncated)
        self.assertTrue(_acc._payload_runs_to_the_destination(
            sentence, "the results are in the attachment"),
            "the payload the sentence actually stated was refused")

    def test_a_payload_with_no_stated_destination_does_not_get_one_invented(self):
        """The #6119 pin, at the gate that was widened.

        A stated payload is now enough to reach composition, but only WITH a
        stated destination.  Without one, the only path in the sentence becomes
        the destination by default and a file is overwritten by a report about
        it -- the data-destruction class PR #6119 closed.  Measured unchanged:
        these refuse, and the file survives byte-identical.
        """
        f = _fresh("banana\napple\ncherry\n")
        before = (ROOT / f).read_text(encoding="utf-8")
        # "Read" and "Show" legitimately succeed -- they run `cat` -- so the
        # hazard is not that they are accepted, it is that a file gets CHANGED.
        # Every one of these must leave the bytes alone; the two that state no
        # command at all must also refuse.
        for sentence in ("Check the file %s", "Verify the file %s",
                         "Read the file %s", "Show the file %s"):
            result = _solve(sentence % f)
            self.assertEqual((ROOT / f).read_text(encoding="utf-8"), before,
                             "%r changed a file it only mentioned" % sentence)
        for sentence in ("Check the file %s", "Verify the file %s"):
            result = _solve(sentence % f)
            self.assertIsNot(result.get("pass"), True,
                             "%r was accepted: %r" % (sentence, result.get("status")))
            self.assertEqual((ROOT / f).read_text(encoding="utf-8"), before,
                             "%r changed a file it only mentioned" % sentence)

    def test_the_writer_is_chosen_by_the_payload_not_by_the_alphabet(self):
        """The tiebreak pin.  This was a silent, systematic routing failure.

        Measured before this: "Write the message 'PROJECT BRAIN' into the file X"
        and "Write the string ... to the file X" were routed to json.file.write,
        which correctly refused the plain text and wrote NOTHING.  Neither
        "json" nor "text" appears in those sentences, so the JSON and text
        tokens scored identically on the word "file" and the tie was broken
        ALPHABETICALLY -- which always favours the JSON writer.  The phrasings
        that worked did so by luck: "text", "content" and "output" happen to be
        keywords of the text writer.

        Every role word the brain already recognises as introducing a text
        payload must reach the text writer.
        """
        from canonical.runtime import composer_route_v1 as _cr
        for role in ("text", "content", "message", "string", "word", "line"):
            sentence = ("Write the %s 'PROJECT BRAIN' into the file %s/a1.txt."
                        % (role, SCRATCH))
            chain = (_cr.route(sentence).get("chain") or [None])[0]
            self.assertEqual(chain, "text.file.write",
                             "the role word %r was routed to %r -- a text "
                             "payload reached a JSON writer" % (role, chain))

    def test_a_json_request_is_still_answered_by_the_json_writer(self):
        """The pairing control: the tiebreak demotes, it does not delete.

        A fix that sent every write to the text writer would pass the test above
        and break JSON.  The sentence decides, and a sentence that says json is
        left exactly alone.
        """
        from canonical.runtime import composer_route_v1 as _cr
        sentence = ("Write the json '{\"a\": 1}' to the file %s/a1.json." % SCRATCH)
        chain = (_cr.route(sentence).get("chain") or [None])[0]
        self.assertEqual(chain, "json.file.write",
                         "a JSON request was demoted away from the JSON writer: %r"
                         % chain)

    def test_a_sentence_that_states_no_payload_leaves_the_ranking_alone(self):
        """The scope pin: the tiebreak fires only on a stated text payload.

        It must never promote or demote anything for a sentence that makes no
        claim about payload kind, or it would be deciding questions the sentence
        did not ask.
        """
        from canonical.runtime import composer_route_v1 as _cr
        a, b = SCRATCH + "/a1.txt", SCRATCH + "/b2.txt"
        for sentence, expected in (("Copy the file %s to %s" % (a, b), "shell.command.run"),
                                   ("Count the lines in the file %s" % a, "shell.command.run"),
                                   ("Sort the file %s" % a, "shell.command.run")):
            chain = (_cr.route(sentence).get("chain") or [None])[0]
            self.assertEqual(chain, expected,
                             "%r was rerouted by the payload tiebreak: %r"
                             % (sentence, chain))

    def test_the_write_family_writes_the_stated_bytes_whatever_words_carry_it(self):
        """End to end, with the bytes on disk as the assertion.

        Measured across the whole family -- six role words crossed with ten ways
        of describing a destination -- this went to 60 of 60.  A representative
        slice is pinned here rather than all sixty, so the suite stays fast
        while every role word and every destination shape is still covered.
        """
        want = "PROJECT BRAIN"
        for role in ("text", "content", "message", "string", "word", "line"):
            DESTS = ("to the file", "into the same file", "to the output path")
            for dest in DESTS:
                # A unique name per case.  Measured the hard way: two of these
                # destination phrases are the same length, so a name built from
                # the length collided and the second write hit a file that
                # already existed.
                name = "wf%s%d.txt" % (role[:3], DESTS.index(dest))
                path = SCRATCH + "/" + name
                sentence = "Write the %s '%s' %s %s." % (role, want, dest, path)
                result = _solve(sentence)
                self.assertTrue(_verified(result),
                                "%r was not verified: %r / %r"
                                % (sentence, result.get("status"),
                                   (result.get("raw_goal_acceptance") or {}).get("reason")))
                written = ROOT / path
                self.assertTrue(written.exists(), "%r wrote nothing" % sentence)
                self.assertEqual(written.read_text(encoding="utf-8"), want,
                                 "%r wrote the wrong bytes: %r"
                                 % (sentence, written.read_text(encoding="utf-8")))

    def test_a_capability_with_nowhere_to_put_the_text_cannot_answer_a_write(self):
        """The admission pin.  Measured, and it is not a corner.

        "Write the content 'PROJECT BRAIN' to the output path <f>" was compiled
        to docx.document.verify.intent_ooxml, which raised
        DOCX_INTENT_SIDECAR_MISSING.  Its keywords include "content", "exact",
        "word" and "document", so the sentence matched -- and its only declared
        input is a path, so it could be bound ONLY once that path existed.  The
        identical sentence over a path that did not exist was served correctly.
        A file's mere existence changed which capability answered an ordinary
        write.

        The rule is the capability's own contract, not a keyword list: a
        sentence that states a payload and where it goes cannot be answered by
        a capability with no slot to put the payload in.
        """
        from canonical.runtime import capability_selection_retrieval_v1 as _sel
        from canonical.runtime import live_integrated_brain_v1 as _L
        cid = "docx.document.verify.intent_ooxml"
        entry = _L.load_verified_registry()[cid]
        verdict = _sel.admit("Write the content 'PROJECT BRAIN' to the output "
                             "path %s/a1.txt" % SCRATCH, cid, entry, ROOT)
        self.assertIs(verdict.get("admitted"), False,
                      "a DOCX verifier was admitted for a text write: %r" % verdict)
        self.assertTrue(str(verdict.get("reason") or "").startswith(
                            "BINDING_REFUSED:NO_SLOT_FOR_THE_STATED_PAYLOAD:"),
                        "the refusal must carry the prefix the route layer "
                        "listens for, or the fallthrough cannot serve the "
                        "write: %r" % verdict.get("reason"))
        # The text writer must still be admitted for the same sentence.
        tw = _L.load_verified_registry()["text.file.write"]
        granted = _sel.admit("Write the content 'PROJECT BRAIN' to the output "
                             "path %s/a1.txt" % SCRATCH, "text.file.write", tw, ROOT)
        self.assertIs(granted.get("admitted"), True,
                      "the rule refused the writer that CAN hold the text: %r"
                      % granted)

    def test_a_write_is_answered_the_same_way_whether_or_not_the_file_exists(self):
        """The end-to-end pin on the bug: existence must not choose the route.

        This is the whole defect in one assertion pair.  The same sentence, the
        same bytes, differing only in whether the destination already held
        something -- and one of the two used to be answered by a DOCX verifier.
        """
        want = "PROJECT BRAIN"
        for label, pre in (("absent", None), ("already exists", "stale bytes\n")):
            path = SCRATCH + "/exists_%s.txt" % ("a" if pre is None else "b")
            target = ROOT / path
            if target.exists():
                target.unlink()
            if pre is not None:
                target.write_text(pre, encoding="utf-8")
            sentence = ("Write the content '%s' to the output path %s."
                        % (want, path))
            result = _solve(sentence)
            self.assertTrue(_verified(result),
                            "the target was %s and the write was not verified: "
                            "%r / %r / %r"
                            % (label, result.get("status"),
                               result.get("compiled_capability_id"),
                               result.get("reason")))
            self.assertEqual(target.read_text(encoding="utf-8"), want,
                             "the target was %s and holds the wrong bytes: %r"
                             % (label, target.read_text(encoding="utf-8")))

    def test_the_payload_slot_rule_reaches_only_write_requests(self):
        """The blast-radius pin, measured rather than asserted.

        The rule fires only when the sentence states a payload AND a
        destination.  Over seventeen ordinary sentences -- count, read, show,
        copy, sort, remove, hash, list, search, diff, head, verify, check,
        mkdir, uniq and two writes -- it applies to exactly the two writes.
        Widen the trigger and this goes red.
        """
        from canonical.runtime import capability_selection_retrieval_v1 as _sel
        f = SCRATCH + "/a1.txt"
        b = SCRATCH + "/b2.txt"
        d = SCRATCH + "/listing"
        sentences = [
            "Count the lines in the file %s" % f,
            "Read the file %s" % f,
            "Show the file %s" % f,
            "Copy the file %s to %s" % (f, b),
            "Sort the file %s" % f,
            "Remove the file %s" % f,
            "Compute the sha256 of the file %s" % f,
            "List the directory %s" % d,
            "Search the file %s for the exact text 'apple'" % f,
            "Diff the file %s against %s" % (f, b),
            "Show the first 2 lines of the file %s" % f,
            "Verify the file %s" % f,
            "Check the file %s" % f,
            "Create the directory %s" % d,
            "Show the unique lines of the file %s" % f,
            "Write the content 'X' to the output path %s" % f,
            "Write the text 'X' to the file %s" % f,
        ]
        firing = [s for s in sentences if _sel._states_a_payload_and_its_destination(s)]
        self.assertEqual(len(firing), 2,
                         "the rule now reaches %d of %d ordinary sentences; it "
                         "was measured to reach exactly the two writes: %r"
                         % (len(firing), len(sentences), firing))
        for s in firing:
            self.assertIn("Write", s, "a non-write sentence triggered the rule: %r" % s)

    def test_the_two_commands_that_answer_with_a_status_are_both_reachable(self):
        """Both members of _ANSWER_IS_THE_EXIT_STATUS must be reachable from prose.

        The adapter was taught to report rather than raise for exactly the
        programs enumerated in that table.  A capability the acceptance layer is
        willing to judge, and whose binary is present, that no sentence can
        reach is dead weight in the table.
        """
        from canonical.runtime import composer_route_v1 as _cr
        from canonical.runtime import raw_goal_trace_acceptance_v1 as _acc
        # Reachable means reachable from EITHER prose table: a command that takes
        # an operand is in _PROSE_COMMAND, one that takes a quoted value is in
        # _PROSE_COMMAND_WITH_VALUE.  Reading only the first said grep was dead
        # weight the moment it was added, which was this test's own defect, not
        # the table's.
        progs = ({p for _x, p, _f, _a in _cr._PROSE_COMMAND}
                 | {p for _x, p in _cr._PROSE_COMMAND_WITH_VALUE})
        for program in sorted(_acc._ANSWER_IS_THE_EXIT_STATUS):
            self.assertIn(program, progs,
                          "%s answers with a status and is verifiable, but no "
                          "sentence reaches it" % program)
        # Measured on this host, all five:
        #   grep/egrep/fgrep  0 = a line was selected, 1 = none was, 2 = an error
        #   diff/cmp          0 = they agree, 1 = they differ, 2 = trouble
        self.assertEqual(
            {k: frozenset(v) for k, v in _acc._ANSWER_IS_THE_EXIT_STATUS.items()},
            {p: frozenset({0, 1}) for p in
             ("diff", "cmp", "grep", "egrep", "fgrep")},
        )
        # The hard half of the pin: 2 is NOT an answer for any of them, and each
        # one must be re-run by the inspector -- otherwise a command that could
        # not read its file, or a step that reported a code it did not get, would
        # be accepted.
        for program in sorted(_acc._ANSWER_IS_THE_EXIT_STATUS):
            self.assertNotIn(2, _acc._ANSWER_IS_THE_EXIT_STATUS[program], program)
            self.assertIn(program, _acc._READ_ONLY_COMMANDS,
                          "%s is not re-run, so a lied exit status would go "
                          "unchallenged" % program)

    def test_the_column_number_comes_from_the_sentence_not_from_a_path(self):
        """The regression pin: a digit inside a path is not a stated column.

        Measured before this was fixed, "Show the second column of the file
        canonical/astra_runtime/tmp/z1/a1.txt" bound `cut -f 1` -- the 1 in the
        directory name z1, a number the sentence never stated, outranked the word
        "second".  The scratch directory is named with a digit on purpose so this
        test cannot pass by accident.
        """
        path = "%s/a1.txt" % SCRATCH
        digits = [ch for ch in path if ch.isdigit()]
        # Without a digit in the path this test would pass against the buggy
        # reading too, so it would be proving nothing.  Assert the fixture
        # still has one, and that it is NOT the column the sentence asked for,
        # so a regression returns a different number and is caught.
        self.assertTrue(digits, "the fixture path contains no digit, so this "
                                "test would pass without proving anything")
        self.assertNotIn("2", digits,
                         "the path's own digit equals the stated column, so a "
                         "regression would be invisible: %r" % path)
        argv = _argv("Show the second column of the file %s" % path)
        self.assertEqual(argv, ["cut", "-s", "-f", "2", path],
                         "read a column number out of the path %r (which "
                         "contains %r): %r" % (path, digits, argv))

    def test_a_column_the_sentence_does_not_state_is_not_invented(self):
        """`cut` may not default the way `head` may.

        "Show the first lines" has a conventional answer; "show the fields" has
        no conventional column, so choosing one would be choosing the answer to
        the question that was actually asked.
        """
        self.assertIsNone(_argv("Show the fields of the file %s/a1.txt" % SCRATCH),
                          "invented a column number")

    def test_a_quoted_pattern_shaped_like_a_filename_is_not_a_second_operand(self):
        """The caller's own quoted text must not be counted as a file.

        Measured before this was fixed, "Search the file a1.txt for the exact
        text 'a.c'" was refused for want of arity, because extract_paths read
        'a.c' as a second path.  The value is a value because the caller quoted
        it -- the same evidence that made it the pattern.
        """
        argv = _argv("Search the file %s/a1.txt for the exact text 'a.c'" % SCRATCH)
        self.assertEqual(argv, ["fgrep", "a.c", "%s/a1.txt" % SCRATCH],
                         "the quoted pattern was read as an operand: %r" % argv)

    def test_a_search_for_literal_text_does_not_become_a_pattern(self):
        """`fgrep` for text the sentence calls exact, `grep` otherwise.

        Which program answers is decided by what the sentence SAYS about the
        text, never by inspecting the text for metacharacters -- guessing at the
        caller's own value is how a literal '[' becomes a character class they
        never wrote.
        """
        literal = _argv("Find the literal string 'b[n' in the file %s/a1.txt" % SCRATCH)
        self.assertEqual(literal[0], "fgrep",
                         "a literal search was handed to a pattern matcher: %r" % literal)
        pattern = _argv("Find the lines in the file %s/a1.txt matching 'ap.le'" % SCRATCH)
        self.assertEqual(pattern[0], "grep",
                         "a pattern search was handed to a literal matcher: %r" % pattern)

    def test_a_request_for_a_column_is_not_answered_with_whole_lines(self):
        """The pattern-order pin: `cut` is tried before `head`.

        "Show the first field of the file X" contains both "show" and "first",
        and the first pattern to match wins.  Measured out of order it bound
        `head -n 2` and returned two whole lines when the sentence asked for one
        column -- a wrong answer delivered confidently.
        """
        argv = _argv("Show the first field of the file %s/a1.txt" % SCRATCH)
        self.assertEqual(argv[0], "cut",
                         "a request for one column was answered with whole lines: %r" % argv)

    def test_a_search_that_states_no_pattern_is_refused(self):
        """grep needs a pattern; a sentence that states none binds nothing.

        Rewritten harder, not deleted.  The second assertion used to require that
        "matching 'a' or 'b'" bind NOTHING, on the reasoning that two stated
        patterns are a guess between them.  They are not a guess: for a filter
        over lines, "a or b" states ONE pattern with an alternation in it, and
        `egrep` is the program that reads an alternation.  Refusing was better
        than guessing; building the alternation the sentence actually stated is
        better than refusing, and it is measured here from the argv.
        """
        self.assertIsNone(_argv("Search the file %s/a1.txt" % SCRATCH),
                          "invented a search pattern")
        argv = _argv("Find the lines in %s/a1.txt matching 'a' or 'b'" % SCRATCH)
        self.assertEqual(argv[:2], ["egrep", "a|b"],
                         "two values joined by 'or' are one alternation: %r" % (argv,))

    def test_the_counting_and_column_commands_run_and_report_the_real_numbers(self):
        """Read back from the command's own output, not from a flag."""
        f = _fresh("banana apple\ncherry plum\nfig grape\n")
        expected = {
            "Count the lines in the file %s": "3",
            "Count the words in the file %s": "6",
            "Count the bytes in the file %s": "35",
        }
        wrong = []
        for template, want in expected.items():
            result = _solve(template % f)
            if not _verified(result):
                wrong.append((template, result.get("status")))
                continue
            steps = (result.get("composer_execution") or {}).get("steps") or []
            out = str((steps[0].get("result") or {}).get("stdout") or "")
            if not out.split() or out.split()[0] != want:
                wrong.append((template, "reported %r, the file holds %s"
                              % (out.split()[:1], want)))
            self.assertEqual((ROOT / f).read_text(encoding="utf-8"),
                             "banana apple\ncherry plum\nfig grape\n",
                             "%s changed the file it only counted" % template)
        self.assertEqual(wrong, [], "a counting command did not report the real "
                                    "number: %r" % wrong)

    def test_a_literal_search_finds_the_line_and_changes_nothing(self):
        f = _fresh("banana apple\ncherry plum\nfig grape\n")
        result = _solve("Search the file %s for the exact text 'cherry plum'" % f)
        self.assertTrue(_verified(result),
                        "a literal search was not verified: %r" % result.get("status"))
        steps = (result.get("composer_execution") or {}).get("steps") or []
        out = str((steps[0].get("result") or {}).get("stdout") or "")
        self.assertEqual(out.strip(), "cherry plum",
                         "the literal search returned the wrong line: %r" % out)
        self.assertEqual((ROOT / f).read_text(encoding="utf-8"),
                         "banana apple\ncherry plum\nfig grape\n")

    def test_a_pattern_search_answers_with_the_lines_the_pattern_matches(self):
        """`egrep` end to end, and `grep` must not be silently substituted.

        Basic grep reads a pipe literally, so if egrep were not really bound the
        alternation would match nothing and exit 1 -- which is exactly why the
        assertion is on the returned lines and not on the status alone.
        """
        f = _fresh("banana apple\ncherry plum\nfig grape\n")
        result = _solve("Search the file %s for the regex 'plum|grape'" % f)
        self.assertTrue(_verified(result),
                        "a pattern search was not verified: %r" % result.get("status"))
        steps = (result.get("composer_execution") or {}).get("steps") or []
        out = str((steps[0].get("result") or {}).get("stdout") or "")
        self.assertEqual(sorted(out.splitlines()), ["cherry plum", "fig grape"],
                         "the alternation did not match both lines -- egrep was "
                         "not really the program that ran: %r" % out)
        self.assertEqual((ROOT / f).read_text(encoding="utf-8"),
                         "banana apple\ncherry plum\nfig grape\n")

    def test_a_byte_comparison_answers_with_the_code_the_world_agrees_with(self):
        """`cmp` end to end in both directions, and neither operand altered."""
        for same, want in ((True, 0), (False, 1)):
            a = _fresh("banana apple\ncherry plum\nfig grape\n")
            b = a.replace("a1.txt", "b2.txt")
            (ROOT / b).write_text(
                "banana apple\ncherry plum\nfig grape\n" if same
                else "banana apple\ncherry PLUM\nfig grape\n", encoding="utf-8")
            result = _solve("Compare the file %s and %s byte by byte" % (a, b))
            self.assertTrue(_verified(result),
                            "a byte comparison of %s files was not verified: %r"
                            % ("identical" if same else "differing",
                               result.get("status")))
            steps = (result.get("composer_execution") or {}).get("steps") or []
            got = (steps[0].get("result") or {}).get("returncode")
            self.assertEqual(got, want,
                             "identical=%s differing=%s: cmp reported %r, the world "
                             "says %r" % (same, not same, got, want))
            self.assertEqual((ROOT / a).read_text(encoding="utf-8"),
                             "banana apple\ncherry plum\nfig grape\n")
            self.assertEqual((ROOT / b).read_text(encoding="utf-8"),
                             ("banana apple\ncherry plum\nfig grape\n" if same
                              else "banana apple\ncherry PLUM\nfig grape\n"))

    def test_a_comparison_answers_with_the_code_the_world_agrees_with(self):
        """The hardest row in the file: the exit status is cross-checked, not trusted.

        `diff` reports its answer as an exit status, so the tempting check is
        ``returncode == 0`` -- which is the producer grading its own work, the
        exact shape PR #6118 showed to be worthless.  What actually happens is
        that the verifier re-runs the command and compares stdout, stderr AND the
        code, so a code the command did not really return is caught.

        Both directions are pinned, because a check that only ever saw identical
        files would pass on a machine that always reported 0, and a check that
        only ever saw differing ones would pass on a machine that always
        reported 1.
        """
        f = _fresh()
        same = "%s/same.txt" % SCRATCH
        other = "%s/other.txt" % SCRATCH
        (ROOT / same).write_text(UNSORTED, encoding="utf-8")
        (ROOT / other).write_text("cherry\nplum\n", encoding="utf-8")

        for target, expected_code in ((same, 0), (other, 1)):
            result = _solve("Diff the file %s against %s" % (f, target))
            self.assertTrue(_verified(result),
                            "a comparison against %s was not verified: %r"
                            % (target, result.get("status")))
            steps = (result.get("composer_execution") or {}).get("steps") or []
            self.assertTrue(steps, "no step ran")
            self.assertEqual(
                (steps[0].get("result") or {}).get("returncode"), expected_code,
                "diff against %s reported the wrong answer -- identical files "
                "must be 0 and differing files 1" % target)
            # Neither file is an operand the comparison may alter.
            self.assertEqual((ROOT / f).read_text(encoding="utf-8"), UNSORTED)

    def test_a_command_missing_an_operand_is_refused_not_completed(self):
        """The arity rule. cp with one path must not invent a destination."""
        self.assertIsNone(_argv("Copy the file %s/a1.txt" % SCRATCH),
                          "invented the second operand of cp")
        self.assertIsNone(_argv("Move the file %s/a1.txt" % SCRATCH),
                          "invented the second operand of mv")

    def test_a_sentence_that_states_no_command_binds_no_command(self):
        """The negative control that keeps a general runner out of reach."""
        for goal in ("Check the file %s/a1.txt" % SCRATCH,
                     "Run the archive manifest listing.",
                     "Run the python source audit ast.",
                     "Write the text hello world to the file %s/b2.txt" % SCRATCH):
            self.assertIsNone(_argv(goal), "invented a command line for %r" % goal)


class TestEveryProseRequestRunsAndIsChecked(unittest.TestCase):
    """Half two, end to end, with the effect read back from disk."""

    def tearDown(self):
        shutil.rmtree(ROOT / SCRATCH, ignore_errors=True)

    def _run(self, goal: str):
        return _solve(goal)

    def test_a_stated_copy_leaves_both_files(self):
        f = _fresh()
        g = "%s/b2.txt" % SCRATCH
        result = self._run("Copy the file %s to %s" % (f, g))
        self.assertTrue(_verified(result), "a stated copy was not verified: %r"
                        % result.get("status"))
        self.assertEqual((ROOT / g).read_text(encoding="utf-8"), UNSORTED)
        self.assertEqual((ROOT / f).read_text(encoding="utf-8"), UNSORTED)

    def test_a_stated_move_leaves_only_the_destination(self):
        f = _fresh()
        g = "%s/b2.txt" % SCRATCH
        result = self._run("Move the file %s to %s" % (f, g))
        self.assertTrue(_verified(result), "a stated move was not verified: %r"
                        % result.get("status"))
        self.assertFalse((ROOT / f).exists(), "the source survived a move")
        self.assertEqual((ROOT / g).read_text(encoding="utf-8"), UNSORTED)

    def test_a_stated_removal_really_removes(self):
        f = _fresh()
        result = self._run("Remove the file %s" % f)
        self.assertTrue(_verified(result), "a stated removal was not verified: %r"
                        % result.get("status"))
        self.assertFalse((ROOT / f).exists(), "the file survived its own removal")

    def test_a_stated_directory_is_a_real_directory(self):
        _fresh()
        d = "%s/d9" % SCRATCH
        result = self._run("Create the directory %s" % d)
        self.assertTrue(_verified(result), "a stated mkdir was not verified: %r"
                        % result.get("status"))
        self.assertTrue((ROOT / d).is_dir(), "mkdir was verified over no directory")

    def test_a_stated_empty_file_is_empty(self):
        _fresh()
        e = "%s/e9" % SCRATCH
        result = self._run("Create an empty file %s" % e)
        self.assertTrue(_verified(result), "a stated touch was not verified: %r"
                        % result.get("status"))
        self.assertTrue((ROOT / e).is_file())
        self.assertEqual((ROOT / e).read_text(encoding="utf-8"), "",
                         "the file the sentence called empty was not empty")

    def test_a_stated_read_leaves_the_file_alone(self):
        f = _fresh()
        result = self._run("Read the file %s" % f)
        self.assertTrue(_verified(result), "a stated read was not verified: %r"
                        % result.get("status"))
        self.assertEqual((ROOT / f).read_text(encoding="utf-8"), UNSORTED)

    def test_a_stated_line_count_reports_the_real_number(self):
        f = _fresh()
        result = self._run("Count the lines in the file %s" % f)
        self.assertTrue(_verified(result), "a stated wc -l was not verified: %r"
                        % result.get("status"))
        steps = (result.get("composer_execution") or {}).get("steps") or []
        self.assertTrue(steps, "no step ran")
        self.assertIn("3", str((steps[0].get("result") or {}).get("stdout") or ""),
                      "wc -l did not report three lines")

    def test_the_first_two_lines_are_the_first_two_lines(self):
        f = _fresh()
        result = self._run("Show the first 2 lines of the file %s" % f)
        self.assertTrue(_verified(result), "a stated head was not verified: %r"
                        % result.get("status"))
        steps = (result.get("composer_execution") or {}).get("steps") or []
        out = str((steps[0].get("result") or {}).get("stdout") or "")
        self.assertEqual(out.strip().splitlines(), ["banana", "apple"],
                         "head -n 2 did not return the first two lines: %r" % out)

    def test_a_stated_sort_to_stdout_leaves_the_file(self):
        f = _fresh()
        result = self._run("Sort the file %s" % f)
        self.assertTrue(_verified(result), "a stated sort was not verified: %r"
                        % result.get("status"))
        self.assertEqual((ROOT / f).read_text(encoding="utf-8"), UNSORTED,
                         "a sort to stdout rewrote its own input")

    def test_a_stated_checksum_runs(self):
        f = _fresh()
        result = self._run("Compute the sha256 of the file %s" % f)
        self.assertTrue(_verified(result), "a stated sha256sum was not verified: %r"
                        % result.get("status"))
        steps = (result.get("composer_execution") or {}).get("steps") or []
        out = str((steps[0].get("result") or {}).get("stdout") or "")
        self.assertEqual(len(out.split()[0]) if out.split() else 0, 64,
                         "sha256sum did not report a digest: %r" % out)
        self.assertEqual((ROOT / f).read_text(encoding="utf-8"), UNSORTED)

    def test_the_rest_of_the_verifiable_surface_runs_and_is_checked(self):
        """Every newly reachable command that CAN be checked, checked."""
        cases = (
            ("Compute the md5 of the file %s", 32),
            ("Show the unique lines of the file %s", None),
            ("Reverse the lines of the file %s", None),
            ("Number the lines of the file %s", None),
            ("Show the octal dump of the file %s", None),
            ("Find the lines in the file %s matching 'apple'", None),
        )
        unverified = []
        for template, digest_len in cases:
            f = _fresh()
            result = _solve(template % f)
            if not _verified(result):
                unverified.append((template, result.get("status")))
                continue
            if digest_len is not None:
                steps = (result.get("composer_execution") or {}).get("steps") or []
                out = str((steps[0].get("result") or {}).get("stdout") or "")
                self.assertEqual(len(out.split()[0]) if out.split() else 0, digest_len,
                                 "md5sum did not report a digest: %r" % out)
            # A reader must leave what it read alone.
            self.assertEqual((ROOT / f).read_text(encoding="utf-8"), UNSORTED,
                             "%s changed the file it only read" % template)
        self.assertEqual(unverified, [],
                         "a reachable command was not exactly verified: %r" % unverified)

    def test_a_stated_sort_into_a_file_writes_the_sorted_bytes_there(self):
        """The strongest row: the promise is recomputed, not trusted."""
        f = _fresh()
        g = "%s/b2.txt" % SCRATCH
        result = self._run("Sort the file %s into %s" % (f, g))
        self.assertTrue(_verified(result), "a stated sort -o was not verified: %r"
                        % result.get("status"))
        self.assertEqual((ROOT / g).read_text(encoding="utf-8"), SORTED,
                         "the destination is not the source in order")
        self.assertEqual((ROOT / f).read_text(encoding="utf-8"), UNSORTED,
                         "sorting into a file consumed the source")


class TestTheSortPostconditionIsAnOracleNotATrust(unittest.TestCase):
    """The half that makes ``sort -o`` safe: it is judged against the disk."""

    def tearDown(self):
        shutil.rmtree(ROOT / SCRATCH, ignore_errors=True)

    def _accept(self, argv):
        from canonical.runtime import raw_goal_trace_acceptance_v1 as A

        return A._inspect_shell_command_run({"argv": list(argv)}, {}, ROOT)

    def test_a_destination_that_is_not_the_source_in_order_is_refused(self):
        _fresh()
        (ROOT / ("%s/b2.txt" % SCRATCH)).write_text(UNSORTED, encoding="utf-8")
        ok, reason, _ = self._accept(
            ["sort", "-o", "%s/b2.txt" % SCRATCH, "%s/a1.txt" % SCRATCH])
        self.assertIs(ok, False, "certified a destination that is not sorted")
        self.assertEqual(reason, "COMMAND_SORT_DESTINATION_IS_NOT_THE_SOURCE_IN_ORDER")

    def test_a_sorted_destination_is_accepted(self):
        _fresh()
        (ROOT / ("%s/b2.txt" % SCRATCH)).write_text(SORTED, encoding="utf-8")
        ok, reason, _ = self._accept(
            ["sort", "-o", "%s/b2.txt" % SCRATCH, "%s/a1.txt" % SCRATCH])
        self.assertIs(ok, True, "refused a destination that is exactly sorted: %s" % reason)

    def test_an_absent_source_is_refused(self):
        _fresh()
        ok, reason, _ = self._accept(
            ["sort", "-o", "%s/b2.txt" % SCRATCH, "%s/absent.txt" % SCRATCH])
        self.assertIs(ok, False)
        self.assertEqual(reason, "COMMAND_SORT_SOURCE_ABSENT_FROM_DISK")

    def test_shapes_whose_promise_cannot_be_stated_are_refused(self):
        _fresh()
        # NOTE: ["sort", "<file>"] is deliberately absent. With no -o it writes
        # nothing, so it stays a reader and is checked by re-running it -- that
        # is row nine of the passing table above, not a shape to refuse.
        for argv in (["sort", "-o", "%s/b2.txt" % SCRATCH],
                     ["sort", "-o", "%s/b2.txt" % SCRATCH, "%s/a1.txt" % SCRATCH,
                      "%s/a1.txt" % SCRATCH]):
            ok, reason, _ = self._accept(argv)
            self.assertIs(ok, False, "certified an unstateable shape: %r" % argv)
            self.assertIn("UNSTATEABLE", reason,
                          "the refusal does not say why: %r for %r" % (reason, argv))

    def test_an_output_flag_with_no_postcondition_is_still_refused(self):
        """The guard on the widening: only sort gained a promise.

        ``grep -o`` means only-matching, not output-to-file, and there is no
        postcondition for it. It must be refused exactly as it was before the
        branch order changed, never re-run.
        """
        _fresh()
        ok, reason, _ = self._accept(
            ["grep", "-o", "apple", "%s/a1.txt" % SCRATCH])
        self.assertIs(ok, False, "re-ran a command whose -o is not an output flag")
        self.assertEqual(reason, "COMMAND_TAKES_AN_OUTPUT_FLAG")


class TestTheFallthroughIsScopedToWhatTheSentenceStates(unittest.TestCase):
    """The #6119 hazard the widened fallthrough must not reopen."""

    def tearDown(self):
        shutil.rmtree(ROOT / SCRATCH, ignore_errors=True)

    def test_a_sentence_stating_neither_payload_nor_command_still_fails_closed(self):
        """'Check the file X' states nothing to compose. It must not write."""
        f = _fresh("PRECIOUS ORIGINAL CONTENT\n")
        self.assertIsNone(_argv("Check the file %s" % f))
        result = _solve("Check the file %s" % f)
        self.assertEqual((ROOT / f).read_text(encoding="utf-8"),
                         "PRECIOUS ORIGINAL CONTENT\n",
                         "a request that stated nothing changed the file")
        self.assertIsNot(result.get("pass"), True,
                         "reported pass=True over a request that stated nothing")

    def test_a_search_that_finds_nothing_is_an_answer_not_a_crash(self):
        # grep exits 1 when no line matched.  That is the answer to a search that
        # finds nothing, not a failure of the command.  Measured on cb8534b: the
        # adapter raised RuntimeError:CLI_COMMAND_FAILED and the trace said
        # COMPOSED_STEP_RAISED_OUTCOME_UNKNOWN -- a crash report for a command
        # that ran correctly and answered truthfully.
        f = _fresh("apple\nbanana\napple\n")
        for pattern in ("apple", "zzzz"):
            out = _solve("Search the file %s for the exact text '%s'"
                         % (f, pattern))
            acc = out.get("raw_goal_acceptance") or {}
            self.assertTrue(
                _verified(out),
                "pattern %r was not verified: status=%r reason=%r "
                "unverified=%r" % (pattern, acc.get("status"), acc.get("reason"),
                                   acc.get("unverified_reason")))

    def test_a_search_on_a_file_it_cannot_read_still_fails(self):
        # The other side of the same coin, and the reason 2 is left out of the
        # answer table: grep exits 2 when the file is missing.  That IS trouble,
        # and accepting it would turn a broken command into a verified one.
        _fresh()
        out = _solve("Search the file %s/never.txt for the exact text 'apple'"
                     % SCRATCH)
        self.assertIsNot((out.get("raw_goal_acceptance") or {}).get("pass"), True,
                         "a search over a missing file was accepted: %r"
                         % (out.get("raw_goal_acceptance"),))

    def test_a_search_pattern_shaped_like_a_filename_is_not_the_output(self):
        # 'ap.le' and 'notes.md' are ordinary patterns and ordinary filenames.
        # extract_paths cannot tell them apart and PATH_OUTPUT takes the LAST
        # path in the sentence, so the pattern became the output and the adapter
        # failed CLI_EXPECTED_OUTPUT_MISSING over a promise nobody made.  'zzzz'
        # bound correctly, which is why this was invisible.
        from canonical.runtime import composer_route_v1 as _cr
        args = _cr.bind({"argv": "ARGV", "output_path": "PATH_OUTPUT"},
                        "Search the file a1.txt for the literal string 'ap.le'")
        self.assertEqual("a1.txt", args.get("output_path"))
        self.assertEqual(["fgrep", "ap.le", "a1.txt"], args.get("argv"))

        f = _fresh("apple\nbanana\n")
        out = _solve("Search the file %s for the literal string 'ap.le'" % f)
        acc = out.get("raw_goal_acceptance") or {}
        self.assertTrue(
            _verified(out),
            "status=%r reason=%r unverified=%r"
            % (acc.get("status"), acc.get("reason"), acc.get("unverified_reason")))


    def test_the_unit_wc_counts_may_come_either_side_of_the_counting_word(self):
        # "count the words", "how many words", "the number of words" and "the
        # word count" name the same unit.  The three wc rules used to require the
        # counting word FIRST, so "Show the word count of the file X" bound no
        # command and fell through to capability selection -- which measured as
        # docx.document.verify.intent_ooxml answering a request to count words.
        from canonical.runtime import composer_route_v1 as _cr
        f = _fresh("apple banana\ncherry\n")
        for goal, flag in (("Show the word count of the file %s" % f, "-w"),
                           ("Count the words in the file %s" % f, "-w"),
                           ("How many words are in the file %s" % f, "-w"),
                           ("Show the line count of the file %s" % f, "-l"),
                           ("Count the number of lines in the file %s" % f, "-l"),
                           ("Show the character count of the file %s" % f, "-c")):
            self.assertEqual(["wc", flag, f], _cr._prose_argv(goal), goal)
            self.assertTrue(_verified(_solve(goal)), goal)

    def test_the_algorithm_the_sentence_names_is_the_one_that_runs(self):
        # "Compute the md5 hash of X" must not return a sha256 digest: the
        # sentence named an algorithm.  md5sum is tried first for that reason,
        # and only now that sha256sum answers to the generic word "hash".
        from canonical.runtime import composer_route_v1 as _cr
        f = _fresh("apple\n")
        self.assertEqual(["md5sum", f],
                         _cr._prose_argv("Compute the md5 hash of the file %s" % f))
        self.assertEqual(["sha256sum", f],
                         _cr._prose_argv("Compute the hash of the file %s" % f))
        self.assertTrue(_verified(_solve("Compute the hash of the file %s" % f)))

    def test_removing_duplicate_lines_filters_a_file_it_does_not_delete(self):
        # "Remove the duplicate lines from the file X" is a filter over a file
        # that stays.  Measured, it matched `rm` first -- third in the table, and
        # the first pattern to match wins -- and `cp` matched "duplicate" before
        # that, found one operand instead of two, and abandoned the whole table.
        from canonical.runtime import composer_route_v1 as _cr
        # The duplicate is NOT adjacent, on purpose.  `uniq` removes adjacent
        # duplicates only, so on this file it answers all three lines -- the
        # duplicate still in it -- and that answer was certified as an exact
        # semantic acceptance, because acceptance checks reproducibility and
        # `uniq` is perfectly reproducible.  The distinct set is two lines.
        f = _fresh("apple\nbanana\napple\n")
        self.assertEqual(["sort", "-u", f],
                         _cr._prose_argv("Remove the duplicate lines from the file %s" % f))
        _r = _solve("Remove the duplicate lines from the file %s" % f)
        self.assertTrue(_verified(_r))
        self.assertEqual("apple\nbanana\n", _stdout(_r),
                         "the duplicate survived: the answer is not the distinct set")
        self.assertTrue(os.path.exists(os.path.join(ROOT, f)),
                        "the filter deleted the file it was asked to filter")
        self.assertEqual(["cp", "a.txt", "b.txt"],
                         _cr._prose_argv("Copy the file a.txt to b.txt"))

    def test_a_capability_that_cannot_run_a_command_does_not_answer_one(self):
        # The Word-document verifier's registry keywords include "word", so
        # "Show the word count of the file X" selected it and died inside a
        # sidecar check.  Its declared inputs can be FILLED from the sentence;
        # what it cannot do is run a command.
        from canonical.runtime import capability_composer_v1 as _comp
        from canonical.runtime import capability_selection_retrieval_v1 as _sel
        f = _fresh("apple\n")
        goal = "Show the word count of the file %s" % f
        reg = _comp.load_registry()
        verdict = _sel.admit(goal, "docx.document.verify.intent_ooxml",
                             reg.get("docx.document.verify.intent_ooxml"), ROOT)
        self.assertIs(verdict.get("admitted"), False, verdict)
        self.assertIn("NO_COMMAND_SLOT_FOR_THE_STATED_COMMAND",
                      str(verdict.get("reason")))
        # The capability that CAN run it is served by the composer, not by the
        # compiler's own binder -- shell.command.run is refused there with
        # argv:not_stated, which is exactly why the fallthrough exists.  So the
        # claim under test is the end-to-end one.
        self.assertTrue(_verified(_solve(goal)))

    def test_a_stated_command_is_routed_even_when_no_keyword_matches_it(self):
        # "folder" appears in no capability's keywords, so candidate_tokens
        # scored nothing and route() returned OPEN__COMPOSER_NO_REACHABLE_TOKEN
        # with tried=[] -- while extract_argv had already returned ['mkdir', X].
        # The identical sentence saying "directory" worked, because that one word
        # happened to be a keyword.  A request the machine can do must not depend
        # on that coincidence.
        from canonical.runtime import composer_route_v1 as _cr
        d = "%s/dqz" % SCRATCH
        goal = "Make a folder named %s" % d
        self.assertEqual(["mkdir", d], _cr.extract_argv(goal))
        self.assertTrue(_verified(_solve(goal)))
        self.assertTrue(os.path.isdir(os.path.join(ROOT, d)),
                        "the folder the sentence named was not created")

    def test_a_capability_that_merely_takes_an_argv_is_not_the_command_runner(self):
        # The regression pin for a mis-route measured while writing the rule
        # above: "declares an argv slot" matched auto.apt.zint, a barcode-package
        # installer, and route() returned it as a PASS.  A general command runner
        # takes the command line and a place for the result and nothing else.
        from canonical.runtime import composer_route_v1 as _cr
        d = "%s/dqz" % SCRATCH
        r = _cr.route("Make a folder named %s" % d)
        self.assertIs(r.get("pass"), True, r.get("status"))
        self.assertEqual(["shell.command.run"], r.get("chain"))
        for tried in (r.get("tried") or []):
            if tried.get("reachable"):
                self.assertNotIn("apt", str(tried.get("chain")), tried)


    def test_a_commands_result_can_be_written_where_the_sentence_says(self):
        # `output_path` was a promise to CHECK, never a place to write, so a
        # sentence asking for a result to be put somewhere had no mechanism at
        # all: "Join the files A and B into the file C" compiled, ran `cat A B`,
        # and was correctly refused with PROMISED_ARTIFACT_MISSING because
        # nothing ever wrote C.  The refusal was honest and the request ordinary.
        a = _fresh("apple\nbanana\napple\n")
        b = "%s/b1.txt" % SCRATCH
        (ROOT / b).write_text("grape\n", encoding="utf-8")
        c = "%s/c1.txt" % SCRATCH
        out = _solve("Join the files %s and %s into the file %s" % (a, b, c))
        self.assertTrue(_verified(out), out.get("status"))
        # the promise is read back from the bytes, not from a flag
        self.assertEqual("apple\nbanana\napple\ngrape\n",
                         (ROOT / c).read_text(encoding="utf-8"))

    def test_a_read_only_command_with_a_destination_is_not_refused_on_arity(self):
        # The program takes one file.  The sentence names two, and the second is
        # where the result goes -- so it was refused for want of arity, which read
        # as "you gave me too many files" for a request that stated exactly enough.
        from canonical.runtime import composer_route_v1 as _cr
        # The duplicate is NOT adjacent, on purpose.  This test used to say the
        # opposite -- that apple/banana/apple expecting two lines back was the
        # test being wrong about the program.  It was the program that was wrong:
        # "the unique lines" is the distinct set, and `uniq` on an unsorted file
        # leaves the duplicate in and was certified all the same.
        a = _fresh("apple\nbanana\napple\n")
        c = "%s/c1.txt" % SCRATCH
        goal = "Write the unique lines of the file %s to the file %s" % (a, c)
        self.assertEqual(["sort", "-u", a], _cr._prose_argv(goal))
        self.assertTrue(_verified(_solve(goal)))
        self.assertEqual("apple\nbanana\n", (ROOT / c).read_text(encoding="utf-8"))

    def test_a_destination_has_to_be_said_not_assumed(self):
        # The other side of the rule, and the reason it is scoped to the words
        # that introduce a destination: `cmp` and `diff` take two files and
        # write nothing, so the second path must stay an operand.
        from canonical.runtime import composer_route_v1 as _cr
        a = _fresh("apple\n")
        b = "%s/b1.txt" % SCRATCH
        (ROOT / b).write_text("grape\n", encoding="utf-8")
        # Measured, not assumed: "compare" reaches `diff`, and `cmp` answers only
        # to an explicit claim about bytes.  Both take two operands and write
        # nothing, which is the point under test.
        self.assertEqual(["diff", a, b], _cr._prose_argv("Compare the files %s and %s" % (a, b)))
        self.assertEqual(["cmp", "-s", a, b],
                         _cr._prose_argv("Check whether the files %s and %s have the same bytes" % (a, b)))
        self.assertEqual(["diff", a, b],
                         _cr._prose_argv("Show the difference between the file %s and the file %s" % (a, b)))
        self.assertTrue(_verified(_solve("Show the difference between the file %s and the file %s" % (a, b))))

    def test_a_command_that_consumes_its_operand_is_never_written_over(self):
        # For `rm A` the bound output is the file being deleted.  Writing stdout
        # there would resurrect it, so the declaration must not fire.
        from canonical.runtime import composer_route_v1 as _cr
        a = _fresh("apple\n")
        args = _cr.bind({"argv": "ARGV", "output_path": "PATH_OUTPUT"},
                        "Delete the file %s" % a)
        self.assertNotIn("write_stdout_to_output", args, args)
        self.assertTrue(_verified(_solve("Delete the file %s" % a)))
        self.assertFalse((ROOT / a).exists(), "the file was deleted and then written back")

    def test_a_stated_command_is_not_taken_by_a_keyword_match(self):
        # Measured while writing the rule: "Join the files A and B into the file
        # C" was routed to json.file.write on the single matched word "file", and
        # the chain then died OPEN__COMPOSER_SLOT_UNBOUND.  Trying the stated
        # command first is what fixed it, so the order is the thing under test.
        from canonical.runtime import composer_route_v1 as _cr
        a = _fresh("apple\n")
        b = "%s/b1.txt" % SCRATCH
        (ROOT / b).write_text("grape\n", encoding="utf-8")
        r = _cr.route("Join the files %s and %s into the file %s/c1.txt" % (a, b, SCRATCH))
        self.assertIs(r.get("pass"), True, r.get("status"))
        self.assertEqual(["shell.command.run"], r.get("chain"))

    def test_the_adapter_writes_stdout_only_when_the_sentence_asked_for_it(self):
        # The default must stay the default.  `output_path` has always meant
        # "check that this exists", and every route that worked before this
        # change runs through this adapter, so an unconditional write would be a
        # side effect no sentence asked for.
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "_cli_probe", ROOT / "canonical/runtime/bound_capabilities/cli_command.py")
        mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
        a = _fresh("apple\n")
        for flag, expect in ((None, False), ("true", True)):
            out = "%s/o%s.txt" % (SCRATCH, "1" if flag else "0")
            args = {"argv": ["cat", a], "output_path": out}
            if flag: args["write_stdout_to_output"] = flag
            try:
                mod.run(args, str(ROOT))
            except RuntimeError as exc:
                # Without the flag nothing is written, and a declared output
                # that is absent is exactly what the adapter reports -- that is
                # the documented behaviour, and the file must still not exist.
                self.assertIsNone(flag, "the flagged write raised: %s" % exc)
                self.assertEqual("CLI_EXPECTED_OUTPUT_MISSING", str(exc))
            self.assertIs((ROOT / out).exists(), expect,
                          "write_stdout_to_output=%r created a file: %r" % (flag, out))


    def test_a_sentence_can_ask_for_text_to_be_replaced_in_a_file(self):
        # The whole edit family measured 0 of 8 before this.  `sed` without -i
        # reads a file and writes nothing, so it is a reader whose transformed
        # text comes back on stdout -- and the adapter captures stdout in full
        # BEFORE it writes, which is the only reason writing back over the same
        # file is not a read-after-truncate race.
        a = _fresh("apple\nbanana\napple\n")
        out = _solve("Replace every 'apple' with 'pear' in the file %s" % a)
        self.assertTrue(_verified(out), out.get("status"))
        # read the promise back off the disk, and check the rest survived
        self.assertEqual("pear\nbanana\npear\n",
                         (ROOT / a).read_text(encoding="utf-8"))

    def test_a_substitution_whose_word_order_is_reversed_is_refused_not_guessed(self):
        # "Substitute 'pear' for 'apple'" puts the NEW value first.  Reading the
        # two quoted values in sentence order would rewrite the file exactly the
        # wrong way round, and an edit in the wrong direction destroys the text
        # it was asked to keep.  The phrasing is deliberately absent from the
        # table, so the request is refused and the file is left alone.
        a = _fresh("apple\nbanana\n")
        before = (ROOT / a).read_text(encoding="utf-8")
        out = _solve("Substitute 'pear' for 'apple' in the file %s" % a)
        self.assertIsNot(out.get("pass"), True, out.get("status"))
        self.assertEqual(before, (ROOT / a).read_text(encoding="utf-8"),
                         "a refused substitution edited the file anyway")

    def test_a_value_that_would_change_the_command_is_refused(self):
        # `|` is the substitution's delimiter and sed reads the left side as a
        # regular expression, so a value carrying either would make the command
        # mean something the sentence never said -- and it would mean it over
        # the caller's file.
        from canonical.runtime import composer_route_v1 as _cr
        a = _fresh("apple\n")
        self.assertIsNone(_cr._prose_argv("Replace 'a|b' with 'x' in the file %s" % a))
        self.assertIsNone(_cr._prose_argv("Replace 'a.b' with 'x' in the file %s" % a))

    def test_lines_can_be_filtered_out_by_what_they_do_not_contain(self):
        # `grep -v`, and the destination is a different file, so the source must
        # be left exactly as it was.
        a = _fresh("apple\nbanana\napple\ncherry\n")
        c = "%s/c1.txt" % SCRATCH
        out = _solve("Write the lines of the file %s that do not contain 'apple' "
                     "to the file %s" % (a, c))
        self.assertTrue(_verified(out), out.get("status"))
        self.assertEqual("banana\ncherry\n", (ROOT / c).read_text(encoding="utf-8"))
        self.assertEqual("apple\nbanana\napple\ncherry\n",
                         (ROOT / a).read_text(encoding="utf-8"))

    def test_empty_names_one_exact_pattern_and_not_a_loose_one(self):
        # "empty lines" is `^$` and nothing else.  It is a pattern the sentence
        # states by name, the way an ordinal states a column number -- not a
        # synonym the machine picked.
        from canonical.runtime import composer_route_v1 as _cr
        a = _fresh("apple\n\nbanana\n\n")
        self.assertEqual(["grep", "-v", "^$", a],
                         _cr._prose_argv("Remove the empty lines from the file %s" % a))
        c = "%s/c1.txt" % SCRATCH
        out = _solve("Remove the empty lines from the file %s and write the result "
                     "to the file %s" % (a, c))
        self.assertTrue(_verified(out), out.get("status"))
        self.assertEqual("apple\nbanana\n", (ROOT / c).read_text(encoding="utf-8"))

    def test_only_a_transform_may_write_back_over_the_file_it_read(self):
        # For `cat A` the bound output is A itself, and writing stdout there
        # would look harmless until a command that removes or truncates its
        # operand does the same thing.  The permission is a named table in the
        # acceptance layer, so this pins both sides of it.
        from canonical.runtime import composer_route_v1 as _cr
        a = _fresh("apple\n")
        yes = _cr.bind({"argv": "ARGV", "output_path": "PATH_OUTPUT"},
                       "Replace every 'apple' with 'pear' in the file %s" % a)
        self.assertEqual("true", yes.get("write_stdout_to_output"), yes)
        for sentence in ("Show the contents of the file %s" % a,
                         "Delete the file %s" % a,
                         "Search the file %s for the exact text 'apple'" % a):
            args = _cr.bind({"argv": "ARGV", "output_path": "PATH_OUTPUT"}, sentence)
            self.assertNotIn("write_stdout_to_output", args,
                             "%r was allowed to write over its own operand" % sentence)


    def _make_tree(self):
        a = _fresh("apple\nbanana\n")
        sub = os.path.join(SCRATCH, "sub")
        (ROOT / sub).mkdir(parents=True, exist_ok=True)
        (ROOT / sub / "deep.txt").write_text("fig\n", encoding="utf-8")
        return a

    def test_a_directory_can_be_copied_and_the_whole_tree_is_compared(self):
        # "Copy the directory A to the directory B" said "directory" twice, and
        # `cp` without -r refuses a directory -- so the report came back
        # COMPOSED_STEP_RAISED_OUTCOME_UNKNOWN, which claims not to know whether
        # anything happened.  The flag is not a guess: the sentence stated it.
        from canonical.runtime import composer_route_v1 as _cr
        # The source is a subdirectory and the destination a sibling: copying a
        # directory INTO itself is a different request and an error, and putting
        # the destination inside the source was this test's own first bug.
        self._make_tree()
        d = "%s/tree" % SCRATCH
        e = "%s/eq" % SCRATCH
        (ROOT / d).mkdir(parents=True, exist_ok=True)
        (ROOT / d / "aq.txt").write_text("apple\nbanana\n", encoding="utf-8")
        (ROOT / d / "sub").mkdir(exist_ok=True)
        (ROOT / d / "sub" / "deep.txt").write_text("fig\n", encoding="utf-8")
        goal = "Copy the directory %s to the directory %s" % (d, e)
        self.assertEqual(["cp", "-r", d, e], _cr._prose_argv(goal))
        self.assertTrue(_verified(_solve(goal)))
        self.assertEqual("apple\nbanana\n",
                         (ROOT / e / "aq.txt").read_text(encoding="utf-8"))
        self.assertEqual("fig\n", (ROOT / e / "sub" / "deep.txt").read_text(encoding="utf-8"))

    def test_a_tree_promise_without_the_recursive_flag_is_not_certified(self):
        # The other half.  `cp A B` on a directory is an error, so certifying a
        # copied tree there would be a green verdict over work that did not
        # happen -- the one direction a false report must never go.
        from canonical.runtime import raw_goal_trace_acceptance_v1 as _acc
        a = self._make_tree()
        (ROOT / SCRATCH / "tree").mkdir(parents=True, exist_ok=True)
        (ROOT / SCRATCH / "tree" / "aq.txt").write_text("apple\n", encoding="utf-8")
        ok, reason, _ = _acc._post_cp(["cp", "%s/tree" % SCRATCH,
                                       "%s/eq2" % SCRATCH], ROOT)
        self.assertFalse(ok)
        self.assertEqual("COMMAND_CP_TREE_PROMISE_NEEDS_A_RECURSIVE_FLAG", reason)
        # and the file shape that always worked still does
        b = "%s/b1.txt" % SCRATCH
        (ROOT / b).write_text((ROOT / a).read_text(encoding="utf-8"), encoding="utf-8")
        ok, reason, _ = _acc._post_cp(["cp", a, b], ROOT)
        self.assertTrue(ok, reason)

    def test_files_can_be_found_by_the_ending_the_sentence_spells_out(self):
        # `find` only reads the tree and prints what is there, so the inspector
        # re-runs it and compares stdout -- no new way to be trusted.  The dot is
        # load-bearing: stripping it turned ".txt" into the pattern `*txt`, which
        # is looser than the sentence said and would also select `notes_txt`.
        from canonical.runtime import composer_route_v1 as _cr
        self._make_tree()
        goal = "Find the files in the directory %s that end with .txt" % SCRATCH
        self.assertEqual(["find", SCRATCH, "-name", "*.txt"], _cr._prose_argv(goal))
        out = _solve(goal)
        self.assertTrue(_verified(out), out.get("status"))

    def test_a_search_of_a_directory_is_recursive_because_the_sentence_said_files(self):
        # `grep` on a directory without -r is an error, not an answer -- and the
        # sentence said "the files in the directory", which is a tree.  A search
        # of ONE file must stay non-recursive, or the flag is an invention.
        from canonical.runtime import composer_route_v1 as _cr
        a = self._make_tree()
        across = "Search the files in the directory %s for the exact text 'apple'" % SCRATCH
        self.assertEqual(["fgrep", "-r", "apple", SCRATCH], _cr._prose_argv(across))
        self.assertTrue(_verified(_solve(across)))
        single = "Search the file %s for the exact text 'apple'" % a
        self.assertEqual(["fgrep", "apple", a], _cr._prose_argv(single))
        self.assertTrue(_verified(_solve(single)))

    def test_a_capability_that_cannot_run_a_command_is_refused_at_the_live_gate(self):
        # The retrieval layer already refused evidence.claim_relation.generic_units
        # for this sentence, and the live gate -- which re-judges the compiler's
        # own pick -- admitted it anyway, so it ran and died while the composer
        # had the exact argv.  Both layers have to ask the same question.
        from canonical.runtime import live_brain_route_admission_v1 as _ra
        self._make_tree()
        goal = ("Search the files in the directory %s for the exact text 'apple'"
                % SCRATCH)
        verdict = _ra.route_admission(
            goal, {"selected_capability": "evidence.claim_relation.generic_units.stdlib",
                   "compiler_mode": "DETERMINISTIC_VERIFIED_CAPABILITY_MATCH"},
            _ra_compatible_registry())
        self.assertIs(verdict.get("admitted"), False, verdict)
        self.assertEqual("NO_COMMAND_SLOT_FOR_THE_STATED_COMMAND", verdict.get("rule"))

    def test_a_file_copy_still_binds_without_the_recursive_flag(self):
        # Regression pin: the flag comes from the word "directory", so a sentence
        # about files must be byte for byte what it was.
        from canonical.runtime import composer_route_v1 as _cr
        a = _fresh("apple\n")
        b = "%s/b1.txt" % SCRATCH
        goal = "Copy the file %s to the file %s" % (a, b)
        self.assertEqual(["cp", a, b], _cr._prose_argv(goal))
        self.assertTrue(_verified(_solve(goal)))
        self.assertEqual("apple\n", (ROOT / b).read_text(encoding="utf-8"))


    def test_a_file_can_be_converted_to_upper_case_in_place(self):
        # `tr` reads standard input, which the adapter never passes, so case
        # conversion looked blocked behind that wall.  It is not: `sed 's/.*/\U&/'`
        # reads the FILE and prints the converted text, so it is a reader like
        # cat, the inspector re-runs it, and the write mechanism already existed.
        from canonical.runtime import composer_route_v1 as _cr
        a = _fresh("apple\nBanana\n")
        goal = "Convert the file %s to upper case" % a
        self.assertEqual(["sed", "-e", "s/.*/\\U&/", a], _cr._prose_argv(goal))
        self.assertTrue(_verified(_solve(goal)))
        self.assertEqual("APPLE\nBANANA\n", (ROOT / a).read_text(encoding="utf-8"))

    def test_case_conversion_can_go_to_a_destination_and_leave_the_source_alone(self):
        a = _fresh("apple\nbanana\n")
        c = "%s/c1.txt" % SCRATCH
        goal = ("Convert the file %s to upper case and write it to the file %s"
                % (a, c))
        self.assertTrue(_verified(_solve(goal)))
        self.assertEqual("APPLE\nBANANA\n", (ROOT / c).read_text(encoding="utf-8"))
        self.assertEqual("apple\nbanana\n", (ROOT / a).read_text(encoding="utf-8"),
                         "the source was changed by a request that named a destination")

    def test_the_case_script_is_fixed_by_the_rule_and_not_taken_from_the_sentence(self):
        # The sed script comes from the rule, not from the sentence, so nothing
        # the caller writes can change what the command means -- and a quoted
        # value in the sentence must not end up inside the expression.
        from canonical.runtime import composer_route_v1 as _cr
        a = _fresh("apple\n")
        for goal in ("Convert the file %s to upper case" % a,
                     "Convert the file %s to upper case, replacing 'x' with 'y'" % a):
            argv = _cr._prose_argv(goal)
            self.assertIsNotNone(argv, goal)
            self.assertEqual("s/.*/\\U&/", argv[2], goal)

    def test_a_sentence_can_create_every_directory_it_names(self):
        # `mkdir` arity was one, so "create A and B" was refused for want of
        # arity -- a sentence that stated exactly enough operands, refused for
        # stating them.  The promise generalises honestly: every directory named
        # exists.
        from canonical.runtime import composer_route_v1 as _cr
        _fresh()
        p = "%s/p1" % SCRATCH
        q = "%s/q1" % SCRATCH
        goal = "Create the directory %s and the directory %s" % (p, q)
        self.assertEqual(["mkdir", p, q], _cr._prose_argv(goal))
        self.assertTrue(_verified(_solve(goal)))
        self.assertTrue((ROOT / p).is_dir() and (ROOT / q).is_dir())

    def test_a_directory_promise_covers_every_directory_not_just_the_first(self):
        # The whole reason a variadic shape is safe here: the postcondition asks
        # about all of them, so a mkdir that made one of two is refused.
        from canonical.runtime import raw_goal_trace_acceptance_v1 as _acc
        _fresh()
        p = "%s/p1" % SCRATCH
        (ROOT / p).mkdir(parents=True, exist_ok=True)
        ok, reason, _ = _acc._post_mkdir(["mkdir", p, "%s/absent1" % SCRATCH], ROOT)
        self.assertFalse(ok)
        self.assertEqual("COMMAND_MKDIR_DIRECTORY_ABSENT_FROM_DISK", reason)
        ok, reason, _ = _acc._post_mkdir(["mkdir", p], ROOT)
        self.assertTrue(ok, reason)

    def test_rm_was_not_given_the_same_freedom_as_mkdir(self):
        # The pin on the decision not to generalise.  Creating a directory the
        # sentence named is harmless; deleting a path the sentence happened to
        # mention is not.  So a deletion still names exactly one file, and a
        # sentence naming two is refused rather than executed.
        from canonical.runtime import composer_route_v1 as _cr
        a = _fresh("apple\n")
        b = "%s/b1.txt" % SCRATCH
        (ROOT / b).write_text("grape\n", encoding="utf-8")
        self.assertIsNone(_cr._prose_argv("Delete the file %s and the file %s" % (a, b)))
        self.assertTrue((ROOT / a).exists() and (ROOT / b).exists())
        self.assertEqual(["rm", a], _cr._prose_argv("Delete the file %s" % a))


    def _set_dir(self, names):
        # A directory holding exactly `names`, as SCRATCH-relative paths.
        d = "%s/ks" % SCRATCH
        full = ROOT / d
        for child in full.iterdir() if full.is_dir() else []:
            child.unlink() if child.is_file() else None
        full.mkdir(parents=True, exist_ok=True)
        for n in names:
            (full / n).write_text("apple\n", encoding="utf-8")
        return d

    def test_a_sentence_naming_a_set_of_files_deletes_exactly_that_set(self):
        # "all the .log files in the directory D" states one path and a shape.
        # The shape is expanded from the sentence's own words and the command
        # runs on exactly those names -- and the directory itself survives, so
        # the set was deleted and not its container.
        from canonical.runtime import composer_route_v1 as _cr
        _fresh()
        d = self._set_dir(["one.txt", "two.log", "three.txt", "four.log"])
        goal = "Delete all the .log files in the directory %s" % d
        argv = _cr._prose_argv(goal)
        self.assertEqual(sorted([d + "/four.log", d + "/two.log"]), sorted(argv[1:]))
        self.assertTrue(_verified(_solve(goal)))
        self.assertFalse((ROOT / d / "two.log").exists())
        self.assertFalse((ROOT / d / "four.log").exists())
        self.assertTrue((ROOT / d / "one.txt").exists())
        self.assertTrue((ROOT / d / "three.txt").exists())
        self.assertTrue((ROOT / d).is_dir(), "the container was deleted, not the set")

    def test_the_ending_the_sentence_spelled_out_is_not_widened(self):
        # ".log" names `*.log`.  A file called `notes_log` has no dot and is a
        # different name, so widening the pattern would delete a file the
        # sentence never described.
        _fresh()
        d = self._set_dir(["a.log", "notes_log", "b.txt"])
        self.assertTrue(_verified(_solve("Delete all the .log files in the directory %s" % d)))
        self.assertFalse((ROOT / d / "a.log").exists())
        self.assertTrue((ROOT / d / "notes_log").exists(),
                         "a file with no dot was deleted by a request for .log files")
        self.assertTrue((ROOT / d / "b.txt").exists())

    def test_a_set_operation_does_not_reach_into_subdirectories(self):
        # The sentence named one directory.  Deleting from a directory it did
        # not name would be work the sentence never asked for.
        _fresh()
        d = self._set_dir(["a.log"])
        (ROOT / d / "sub").mkdir(exist_ok=True)
        (ROOT / d / "sub" / "deep.log").write_text("x\n", encoding="utf-8")
        self.assertTrue(_verified(_solve("Delete all the .log files in the directory %s" % d)))
        self.assertFalse((ROOT / d / "a.log").exists())
        self.assertTrue((ROOT / d / "sub" / "deep.log").exists(),
                         "a subdirectory was searched by a request that named one level")

    def test_a_sentence_asking_for_a_recursive_deletion_is_refused_not_half_done(self):
        # The expansion is one level.  Running it on a sentence that said
        # "recursively" would report a deeper deletion than the one performed,
        # so the sentence gets no route instead.
        from canonical.runtime import composer_route_v1 as _cr
        _fresh()
        d = self._set_dir(["a.log"])
        self.assertIsNone(_cr._prose_argv(
            "Delete all the .log files in the directory %s recursively" % d))
        self.assertTrue((ROOT / d / "a.log").exists())

    def test_a_deletion_of_a_set_is_refused_if_any_one_file_survives(self):
        # The whole reason a multi-operand deletion is stateable: the promise
        # covers every operand.  Four gone and one left is a deletion that did
        # not happen, and flags are still refused as unstateable.
        from canonical.runtime import raw_goal_trace_acceptance_v1 as _acc
        _fresh()
        d = self._set_dir(["gone1.log", "still_here.log"])
        (ROOT / d / "gone1.log").unlink()
        ok, reason, _ = _acc._post_rm(["rm", "%s/gone1.log" % d, "%s/still_here.log" % d], ROOT)
        self.assertFalse(ok)
        self.assertEqual("COMMAND_RM_TARGET_STILL_PRESENT", reason)
        ok, reason, _ = _acc._post_rm(["rm", "%s/gone1.log" % d], ROOT)
        self.assertTrue(ok, reason)
        (ROOT / d / "still_here.log").unlink()
        ok, reason, _ = _acc._post_rm(
            ["rm", "%s/gone1.log" % d, "%s/still_here.log" % d], ROOT)
        self.assertTrue(ok, reason)
        _fresh()
        d2 = self._set_dir(["f.log"])
        ok, reason, _ = _acc._post_rm(["rm", "-f", "%s/f.log" % d2], ROOT)
        self.assertFalse(ok)
        self.assertEqual("COMMAND_RM_PROMISE_UNSTATEABLE_FOR_THIS_SHAPE", reason)

    def test_a_set_with_nothing_in_it_gets_no_route_rather_than_a_no_op(self):
        # An empty set cannot be handed to rm or wc.  Reporting a run that
        # touched nothing as the work the sentence described would be a lie, so
        # the sentence gets no route.
        from canonical.runtime import composer_route_v1 as _cr
        _fresh()
        d = self._set_dir(["only.txt"])
        self.assertIsNone(_cr._prose_argv("Delete all the .log files in the directory %s" % d))

    def test_a_sentence_that_just_says_all_the_files_is_not_a_set_operation(self):
        # The pin on the ordering.  "List all the files in the directory D"
        # says "all the files" and names a directory, so a block keyed on those
        # words alone steals it; it must fall through to `ls` untouched.
        from canonical.runtime import composer_route_v1 as _cr
        _fresh()
        d = self._set_dir(["one.txt", "two.log"])
        goal = "List all the files in the directory %s" % d
        self.assertEqual(["ls", d], _cr._prose_argv(goal))
        self.assertTrue(_verified(_solve(goal)))

    def test_counting_lines_over_a_set_runs_on_the_named_files(self):
        from canonical.runtime import composer_route_v1 as _cr
        _fresh()
        d = self._set_dir(["one.txt", "two.log", "three.txt"])
        goal = "Count the lines in all the files in the directory %s" % d
        argv = _cr._prose_argv(goal)
        self.assertEqual("wc", argv[0])
        self.assertEqual("-l", argv[1])
        self.assertEqual(3, len(argv) - 2)
        self.assertTrue(_verified(_solve(goal)))


    def test_a_request_to_append_does_not_replace_the_file(self):
        # The whole reason this test exists.  "Append the text 'hello' to the
        # file A" was served by a capability that writes a payload to a
        # destination, which TRUNCATES the file first.  Measured on the tree
        # before this change: A held 'apple\nbanana\n', afterwards it held
        # 'hello', and the run reported
        # PASS__RAW_GOAL_EXECUTED_AND_EXACT_SEMANTIC_ACCEPTANCE_VERIFIED.  The
        # content the sentence promised to keep was deleted and the deletion was
        # certified as the work asked for.  No capability in the registry writes
        # in append mode, so the honest outcome is a refusal with the file
        # untouched -- not a smaller lie.
        # Rewritten, not deleted, and stronger than it was.  It used to assert a
        # REFUSAL, because no capability in the registry wrote in append mode and
        # a refusal was the honest outcome.  sed's `a` command appends, so the
        # honest outcome is now the work itself -- and the promise this test was
        # written to protect is asserted directly: what was already there is
        # still there, in front of the line that was added.
        a = _fresh("apple\nbanana\n")
        result = _solve("Append the text 'hello' to the file %s" % a)
        self.assertTrue(_verified(result), result.get("status"))
        after = (ROOT / a).read_text(encoding="utf-8")
        self.assertEqual("apple\nbanana\nhello\n", after,
                         "a request to append changed what was already there")
        self.assertTrue(after.startswith("apple\nbanana\n"))

    def test_every_way_of_saying_append_keeps_what_was_there(self):
        # Scoped to the promise, not to one verb -- which is why it survived the
        # change that made append work.  Every phrasing below states the end of
        # the file or promises the content survives, so every one of them must
        # leave what was there in place and add the stated line after it.  Two
        # phrasings are asserted the OTHER way round below, because they name a
        # position this route cannot honour.
        for goal in ("Append the text 'hello' to the file %s",
                     "Add the text 'hello' to the end of the file %s",
                     "Add 'hello' to the end of the file %s",
                     "Write the text 'hello' at the end of the file %s",
                     "Put the text 'hello' at the end of the file %s",
                     "Append 'hello' to %s",
                     "Write the text 'hello' to the file %s without losing what is there"):
            a = _fresh("apple\nbanana\n")
            result = _solve(goal % a)
            self.assertTrue(_verified(result), (goal, result.get("status")))
            self.assertEqual("apple\nbanana\nhello\n",
                             (ROOT / a).read_text(encoding="utf-8"), goal)

    def test_a_position_the_route_cannot_honour_is_refused_not_guessed(self):
        # The other side of the rule above, and the reason `insert` and `prepend`
        # are not triggers.  Prepend means the beginning and insert does not say
        # where at all, so appending would put the line somewhere the sentence
        # never asked for -- in the one file the caller will not re-read.
        # Narrowed, not deleted, and for a measured reason: "prepend" and "at the
        # beginning" DO state a position, so they are served now and pinned in the
        # test above.  What stays refused is an insert that states none.
        # Only the unstated-position insert belongs here.  "Add the text 'hello'
        # to the file X" was A/B-checked against main and behaves identically
        # there -- the plain payload write the sentence describes, which truncates
        # and is certified -- so it is not this rule's case and is not asserted.
        for goal in ("Insert the text 'hello' into the file %s",):
            a = _fresh("apple\nbanana\n")
            result = _solve(goal % a)
            self.assertEqual("apple\nbanana\n", (ROOT / a).read_text(encoding="utf-8"),
                             goal)
            self.assertFalse(_verified(result), goal)
        a = _fresh("apple\nbanana\n")
        self.assertTrue(_verified(_solve("Prepend the text 'hello' to the file %s" % a)))
        self.assertEqual("hello\napple\nbanana\n", (ROOT / a).read_text(encoding="utf-8"))
        b = _fresh("apple\nbanana\n")
        self.assertTrue(_verified(_solve(
            "Insert the text 'hello' at the beginning of the file %s" % b)))
        self.assertEqual("hello\napple\nbanana\n", (ROOT / b).read_text(encoding="utf-8"))

    def test_a_plain_write_still_writes_when_the_sentence_asks_for_a_replacement(self):
        # The pin on the scope of the refusal.  A sentence that asks for the
        # file to HOLD some text is not a promise that anything survives, and
        # refusing it would trade one defect for a larger one.
        a = _fresh("apple\nbanana\n")
        self.assertTrue(_verified(_solve("Write the text 'hello' to the file %s" % a)))
        self.assertEqual("hello", (ROOT / a).read_text(encoding="utf-8"))

    def test_the_refusal_names_the_promise_the_sentence_made(self):
        # Pinned at the choke point that runs chains, and pinned on the reason:
        # the report must say which promise was broken, not merely that a
        # capability was declined -- and the file must be untouched, because the
        # refusal happens before the adapter is called, not after it truncated.
        from canonical.runtime import composer_route_v1 as _cr
        a = _fresh("apple\nbanana\n")
        verdict = _cr.execute_chain(
            ["text.file.write"], "Append the text 'hello' to the file %s" % a)
        self.assertFalse(verdict["pass"])
        self.assertEqual(
            "FAIL_CLOSED__WRITE_WOULD_DISCARD_CONTENT_THE_SENTENCE_PROMISED_TO_KEEP",
            verdict["status"])
        self.assertEqual([], verdict["steps"], "a step ran before the refusal")
        self.assertEqual("apple\nbanana\n", (ROOT / a).read_text(encoding="utf-8"))

    def test_compressing_a_file_replaces_it_with_an_archive_that_reads_back(self):
        # `gzip A` removes A and leaves A.gz.  The third fact is the one that
        # makes it a compression and not a renaming: the archive must read back
        # to the very bytes that were there, which also checks the stored CRC.
        import gzip as _gzip
        a = _fresh("apple\nbanana\n")
        goal = "Compress the file %s" % a
        from canonical.runtime import composer_route_v1 as _cr
        self.assertEqual(["gzip", a], _cr._prose_argv(goal))
        self.assertTrue(_verified(_solve(goal)))
        self.assertFalse((ROOT / a).exists(), "the source survived a compression")
        with _gzip.open(ROOT / (a + ".gz"), "rb") as handle:
            self.assertEqual(b"apple\nbanana\n", handle.read())

    def test_an_archive_that_does_not_read_back_is_not_a_compression(self):
        # A truncated or invented .gz satisfies "the source is gone and an
        # archive appeared" and still destroyed the file, so the postcondition
        # reads the whole stream rather than trusting the filename.
        import gzip as _gzip
        from canonical.runtime import raw_goal_trace_acceptance_v1 as _acc
        a = _fresh("apple\nbanana\n")
        good = (ROOT / a).read_bytes()
        (ROOT / a).unlink()
        (ROOT / (a + ".gz")).write_bytes(_gzip.compress(good))
        ok, reason, ev = _acc._post_gzip(["gzip", a], ROOT)
        self.assertTrue(ok, reason)
        self.assertEqual(len(good), ev["recoverable_bytes"])
        (ROOT / (a + ".gz")).write_bytes(_gzip.compress(good)[:9])
        ok, reason, _ev = _acc._post_gzip(["gzip", a], ROOT)
        self.assertFalse(ok)
        self.assertEqual("COMMAND_GZIP_ARCHIVE_NOT_A_COMPLETE_STREAM", reason)

    def test_a_compression_promise_covers_the_source_disappearing(self):
        from canonical.runtime import raw_goal_trace_acceptance_v1 as _acc
        a = _fresh("apple\nbanana\n")
        ok, reason, _ev = _acc._post_gzip(["gzip", a], ROOT)
        self.assertFalse(ok, "a compression was certified with the source still there")
        self.assertEqual("COMMAND_GZIP_SOURCE_STILL_PRESENT", reason)

    def test_a_compression_flag_is_unstateable(self):
        # `-k` keeps the source, so the promise above would be wrong; a flag
        # changes what survives and is refused rather than guessed at.
        from canonical.runtime import raw_goal_trace_acceptance_v1 as _acc
        a = _fresh("apple\nbanana\n")
        for argv in (["gzip", "-k", a], ["gzip", "-9", a]):
            ok, reason, _ev = _acc._post_gzip(argv, ROOT)
            self.assertFalse(ok, argv)
            self.assertEqual("COMMAND_GZIP_PROMISE_UNSTATEABLE_FOR_THIS_SHAPE", reason, argv)


    def _spaced(self):
        # The named file, plus a lookalike holding the name a reader that stops
        # at whitespace would see.  Without the trap, reading "my notes.txt" as
        # "notes.txt" would silently succeed on the wrong file.
        _fresh()
        base = ROOT / SCRATCH
        (base / "my notes.txt").write_text("apple\nbanana\n", encoding="utf-8")
        (base / "notes.txt").write_text("WRONG FILE\n", encoding="utf-8")
        return "%s/my notes.txt" % SCRATCH, "%s/notes.txt" % SCRATCH

    def test_a_filename_with_spaces_is_one_path_not_two(self):
        # Measured before this change: extract_paths read "my notes.txt" as the
        # tail `notes.txt` AND the head as a directory, so the sentence named one
        # file and the machine saw two things it was never told about.
        from canonical.runtime import composer_route_v1 as _cr
        named, trap = self._spaced()
        paths = _cr.extract_paths(
            "Copy the file %s to the file %s/backup.txt" % (named, SCRATCH))
        self.assertEqual([named, "%s/backup.txt" % SCRATCH], paths)
        self.assertNotIn(trap, paths, "the tail of the name was read as a file")
        self.assertFalse(any(p.endswith("/my") for p in paths),
                         "the head of the name was read as a directory")

    def test_a_greedy_read_does_not_span_two_destinations(self):
        # The pin on the lazy quantifier.  A greedy count measured this sentence
        # as ONE path stretching from the first name across "to the file" to the
        # second, which is a name no sentence ever stated.
        from canonical.runtime import composer_route_v1 as _cr
        named, _trap = self._spaced()
        paths = _cr.extract_paths(
            "Copy the file %s to the file %s/backup.txt" % (named, SCRATCH))
        self.assertEqual(2, len(paths), paths)

    def test_a_write_to_a_filename_with_spaces_does_not_invent_a_destination(self):
        # The whole reason this test exists.  Measured before this change: the
        # sentence named "my notes.txt", the machine took the last path it had
        # invented -- a file called `my` -- wrote there, left both real files
        # untouched, and reported
        # PASS__RAW_GOAL_EXECUTED_AND_EXACT_SEMANTIC_ACCEPTANCE_VERIFIED.
        named, trap = self._spaced()
        self.assertTrue(_verified(_solve("Write the text 'hello' to the file %s" % named)))
        self.assertEqual("hello", (ROOT / named).read_text(encoding="utf-8"))
        self.assertEqual("WRONG FILE\n", (ROOT / trap).read_text(encoding="utf-8"))
        self.assertFalse((ROOT / SCRATCH / "my").exists(),
                         "a destination was invented out of the first word of a filename")

    def test_a_copy_names_the_file_the_sentence_named_not_its_tail(self):
        named, trap = self._spaced()
        dest = "%s/backup.txt" % SCRATCH
        self.assertTrue(_verified(_solve(
            "Copy the file %s to the file %s" % (named, dest))))
        self.assertEqual("apple\nbanana\n", (ROOT / dest).read_text(encoding="utf-8"),
                         "the copy came from the lookalike file, not the named one")
        self.assertTrue((ROOT / trap).exists())

    def test_a_deletion_of_a_filename_with_spaces_leaves_the_lookalike_alone(self):
        named, trap = self._spaced()
        self.assertTrue(_verified(_solve("Delete the file %s" % named)))
        self.assertFalse((ROOT / named).exists())
        self.assertTrue((ROOT / trap).exists(),
                         "a file the sentence never named was deleted")

    def test_a_command_over_a_filename_with_spaces_reads_that_file(self):
        named, _trap = self._spaced()
        self.assertTrue(_verified(_solve("Convert the file %s to upper case" % named)))
        self.assertEqual("APPLE\nBANANA\n", (ROOT / named).read_text(encoding="utf-8"))

    def test_a_quoted_filename_is_an_operand_and_not_a_payload(self):
        # Quoting a name is the ordinary way to say it holds a space.  The value
        # is the only operand the sentence named, so masking it -- correct for a
        # quoted PATTERN -- leaves the command with nothing to run on.
        named, _trap = self._spaced()
        result = _solve("Count the lines in the file '%s'" % named)
        self.assertTrue(_verified(result))

    def test_a_quoted_pattern_is_still_not_a_path(self):
        # The pin on the other half of the distinction: a quoted value the
        # sentence introduced as a pattern must not become the destination.
        from canonical.runtime import composer_route_v1 as _cr
        a = _fresh("apple\n")
        goal = "Search the file %s for the exact text 'notes.md'" % a
        argv = _cr._prose_argv(goal)
        self.assertIsNotNone(argv, goal)
        self.assertEqual(a, argv[-1], "the search pattern became the operand")

    def test_a_preposition_after_the_introducer_is_not_part_of_a_name(self):
        # "which files in the directory D" must keep yielding D.  Without the
        # stopword guard the phrase "in the directory D" was read as one name.
        from canonical.runtime import composer_route_v1 as _cr
        _fresh()
        d = "%s/dq" % SCRATCH
        (ROOT / d).mkdir(parents=True, exist_ok=True)
        (ROOT / d / "one.txt").write_text("apple\n", encoding="utf-8")
        goal = "Show which files in the directory %s contain 'apple'" % d
        self.assertEqual([d], _cr.extract_paths(goal))
        self.assertTrue(_verified(_solve(goal)))


    def test_a_bare_name_with_spaces_is_read_from_the_world_not_guessed(self):
        # No word introduces the name here -- "sort my notes.txt" -- so the only
        # honest way to know where the name begins is that a name like that
        # really exists in a directory that really exists.  Measured before: 2 of
        # 8 such requests were served, and one that reported a pass had counted
        # the lines of the lookalike file instead.
        from canonical.runtime import composer_route_v1 as _cr
        named, trap = self._spaced()
        self.assertEqual([named], _cr.extract_paths("Sort %s" % named))
        self.assertNotIn(trap, _cr.extract_paths("Sort %s" % named))

    def test_a_bare_deletion_removes_the_named_file_and_not_its_tail(self):
        # The hardest shape for a rule that consults the disk: the acceptance
        # layer re-derives the command from the sentence AFTER the file is gone,
        # so a rule keyed on the file existing would read a different command the
        # second time.  The directory outlives the file, which is why the
        # discriminator is the parent and not the name.
        named, trap = self._spaced()
        self.assertTrue(_verified(_solve("Delete %s" % named)))
        self.assertFalse((ROOT / named).exists())
        self.assertTrue((ROOT / trap).exists(),
                         "a file the sentence never named was deleted")

    def test_a_bare_copy_reads_both_ends_of_the_sentence(self):
        named, _trap = self._spaced()
        dest = "%s/backup.txt" % SCRATCH
        self.assertTrue(_verified(_solve("Copy %s to %s" % (named, dest))))
        self.assertEqual("apple\nbanana\n", (ROOT / dest).read_text(encoding="utf-8"))

    def test_a_destination_with_spaces_that_does_not_exist_yet_is_read_whole(self):
        # A destination has not been written, so "does this name exist" cannot be
        # the question.  "Does this directory exist" can be, and it is the same
        # question for a source and for a destination.
        a = _fresh("apple\n")
        dest = "%s/my backup.txt" % SCRATCH
        self.assertTrue(_verified(_solve("Copy the file %s to %s" % (a, dest))))
        self.assertEqual("apple\n", (ROOT / dest).read_text(encoding="utf-8"))

    def test_a_name_in_a_directory_that_does_not_exist_is_not_invented(self):
        # The pin on the discriminator.  Reading any run of words as a name would
        # accept this, and the machine would then run a command on a path no
        # sentence ever stated and no disk ever held.
        from canonical.runtime import composer_route_v1 as _cr
        paths = _cr.extract_paths("Sort nosuchdir/my notes.txt")
        self.assertNotIn("nosuchdir/my notes.txt", paths)

    def test_a_phrase_that_is_not_a_name_is_still_not_a_path(self):
        from canonical.runtime import composer_route_v1 as _cr
        _fresh()
        d = "%s/dq" % SCRATCH
        (ROOT / d).mkdir(parents=True, exist_ok=True)
        (ROOT / d / "one.txt").write_text("apple\n", encoding="utf-8")
        goal = "Show which files in the directory %s contain 'apple'" % d
        self.assertEqual([d], _cr.extract_paths(goal))
        self.assertTrue(_verified(_solve(goal)))

    def test_reading_names_does_not_run_off_the_end_of_a_sentence(self):
        # Two spaced names in one sentence, the first starting at offset zero.
        # Shortening the sentence while walking it put the next offset past its
        # end, which is how this test earned its place.
        from canonical.runtime import composer_route_v1 as _cr
        named, _trap = self._spaced()
        other = "%s/other notes.txt" % SCRATCH
        (ROOT / other).write_text("fig\n", encoding="utf-8")
        self.assertEqual([named, other], _cr.extract_paths(
            "Compare the file %s and %s byte by byte" % (named, other)))
        self.assertEqual([named, other], _cr.extract_paths("%s %s" % (named, other)))


    def test_a_directory_is_not_read_out_of_a_path_that_was_already_read(self):
        # The core of the defect.  The prefix check that keeps a directory out of
        # the path list compares SPELLINGS, and for "/home/u/brain/x/a1.txt" the
        # directory token is "home/u/brain/x" -- not a prefix of the found path,
        # because the leading slash is missing.  The sentence was then read as
        # naming a file AND a folder, and a command needing one operand was
        # refused for want of arity.  The same happened to "./x/a1.txt".
        from canonical.runtime import composer_route_v1 as _cr
        a = _fresh("apple\nbanana\n")
        for stated in (str(ROOT / a), "./%s" % a):
            self.assertEqual([stated], _cr.extract_paths("Count the lines in %s" % stated),
                             stated)
            self.assertEqual(["wc", "-l", stated],
                             _cr._prose_argv("Count the lines in %s" % stated))

    def test_an_absolute_path_names_the_file_it_states(self):
        a = _fresh("apple\nbanana\n")
        result = _solve("Count the lines in %s" % (ROOT / a))
        self.assertTrue(_verified(result))

    def test_a_path_that_starts_with_dot_slash_names_the_same_file(self):
        a = _fresh("apple\nbanana\n")
        self.assertTrue(_verified(_solve("Count the lines in ./%s" % a)))

    def test_a_request_that_reports_success_is_a_request_that_was_checked(self):
        # The pin on the shape of the defect, and the one that generalises: the
        # absolute-path request reported pass True while raw_goal_acceptance was
        # absent entirely -- no answer, no acceptance, nothing checked.  A pass
        # that no verifier produced is not a pass, whatever else it is.
        a = _fresh("apple\nbanana\n")
        result = _solve("Count the lines in %s" % (ROOT / a))
        self.assertTrue(_verified(result))
        acceptance = result.get("raw_goal_acceptance") or {}
        self.assertIs(True, acceptance.get("pass"),
                      "a request reported success with no acceptance behind it")

    def test_an_absolute_deletion_removes_the_named_file(self):
        named, trap = self._spaced()
        self.assertTrue(_verified(_solve("Delete %s" % (ROOT / named))))
        self.assertFalse((ROOT / named).exists())
        self.assertTrue((ROOT / trap).exists())

    def test_an_extension_written_in_capitals_is_still_a_filename(self):
        _fresh()
        upper = "%s/A1.TXT" % SCRATCH
        (ROOT / upper).write_text("upper\next\n", encoding="utf-8")
        self.assertTrue(_verified(_solve("Count the lines in %s" % upper)))

    def test_a_path_outside_the_repository_is_refused_and_not_read(self):
        # Naming a file by an absolute path is now read correctly, so the
        # boundary has to be checked on the same shape: a path outside the
        # repository must be refused, its contents must not reach the report, and
        # a deletion must leave it alone.
        import tempfile, json as _json
        outside = pathlib.Path(tempfile.mkdtemp()) / "outside_probe.txt"
        outside.write_text("secret one\nsecret two\n", encoding="utf-8")
        try:
            read = _solve("Count the lines in %s" % outside)
            self.assertFalse(_verified(read))
            self.assertNotIn("secret", _json.dumps(read, default=str),
                             "the contents of a file outside the repository were reported")
            delete = _solve("Delete %s" % outside)
            self.assertFalse(_verified(delete))
            self.assertTrue(outside.exists(),
                            "a file outside the repository was deleted")
        finally:
            outside.unlink(missing_ok=True)
            outside.parent.rmdir()


    def _answer(self, result):
        import json as _json, re as _re
        text = _json.dumps(result, default=str)
        m = _re.search(r'"stdout"\s*:\s*"((?:[^"\\]|\\.)*)"', text)
        return m.group(1).encode().decode("unicode_escape") if m else None

    def test_a_request_to_be_shown_a_line_does_not_change_the_file(self):
        # The reason this test exists.  "Show the third line of the file X" set
        # the file as its own output, and because sed counts as an in-place
        # transform the adapter wrote the command's output over the source.
        # Measured: X went from four lines to one -- a request to be SHOWN
        # something destroyed the file it named.  The run was refused
        # afterwards, which is not the same as not doing it.
        a = _fresh("apple\nbanana\napple pie\ncherry\n")
        before = (ROOT / a).read_text(encoding="utf-8")
        result = _solve("Show the third line of the file %s" % a)
        self.assertTrue(_verified(result))
        self.assertEqual(before, (ROOT / a).read_text(encoding="utf-8"),
                         "a request to be shown a line changed the file")
        self.assertEqual("apple pie\n", self._answer(result))

    def test_a_reader_is_not_permitted_to_write_over_its_own_operand(self):
        # The distinction is in the script, not in the program: a sed script that
        # rewrites may write its result back, because that is the work the
        # sentence asked for; a sed script that only prints may not.
        from canonical.runtime import composer_route_v1 as _cr
        a = _fresh("apple\n")
        reader = {"argv": ["sed", "-n", "1p", a], "output_path": a}
        _cr._declare_a_written_output(reader, reader["argv"],
                                     "Show the first line of the file %s" % a)
        self.assertNotIn("write_stdout_to_output", reader,
                         "a reader was allowed to write over the file it read")
        writer = {"argv": ["sed", "-e", "s|apple|fig|", a], "output_path": a}
        _cr._declare_a_written_output(writer, writer["argv"],
                                     "Replace 'apple' with 'fig' in the file %s" % a)
        self.assertEqual("true", writer.get("write_stdout_to_output"))

    def test_a_count_of_the_lines_holding_a_text_is_not_the_line_count(self):
        # Measured: "How many lines in the file X contain 'apple'" bound `wc -l`
        # and answered 4, the number of lines in the file, when two of them hold
        # the text.  The answer was wrong and it was certified, because a whole
        # file is a perfectly reproducible answer to a question nobody asked.
        a = _fresh("apple\nbanana\napple pie\ncherry\n")
        result = _solve("How many lines in the file %s contain 'apple'?" % a)
        self.assertTrue(_verified(result))
        self.assertEqual("2\n", self._answer(result))

    def test_the_line_number_asked_for_is_reported(self):
        a = _fresh("apple\nbanana\napple pie\ncherry\n")
        result = _solve("Which line of the file %s contains 'cherry'?" % a)
        self.assertTrue(_verified(result))
        self.assertTrue(str(self._answer(result)).startswith("4:"),
                        self._answer(result))

    def test_a_transformation_still_writes_back_over_the_file_it_read(self):
        # The pin on the other half of the distinction.  Narrowing the write to a
        # rewriting script must not take away the in-place conversion, which is
        # the work that sentence asked for.
        a = _fresh("apple\nbanana\n")
        self.assertTrue(_verified(_solve("Convert the file %s to upper case" % a)))
        self.assertEqual("APPLE\nBANANA\n", (ROOT / a).read_text(encoding="utf-8"))

    def test_asking_for_several_lines_still_binds_the_command_that_means_it(self):
        # Singular "line" goes to the command that prints one; a stated COUNT of
        # lines must not, or "the first 3 lines" would return only the third.
        from canonical.runtime import composer_route_v1 as _cr
        a = _fresh("apple\nbanana\napple pie\ncherry\n")
        self.assertEqual(["head", "-n", "3", a],
                         _cr._prose_argv("Show the first 3 lines of the file %s" % a))
        result = _solve("Show the first 3 lines of the file %s" % a)
        self.assertTrue(_verified(result))
        self.assertEqual("apple\nbanana\napple pie\n", self._answer(result))


    def _status_answer(self, result):
        produced = ((result.get("composer_execution") or {}).get("produced") or {})
        return produced.get("returncode")

    def test_a_yes_answer_and_a_no_answer_are_not_the_same_answer(self):
        # The only test that matters here.  A yes-or-no question is answered by
        # the exit status, so an implementation that always reported the same
        # thing would still "pass" every row unless the two cases are asserted
        # against each other.  grep exits 0 when it finds the text and 1 when it
        # does not, and both are answers the acceptance layer enumerates.
        a = _fresh("apple\nbanana\n")
        yes = _solve("Does the file %s contain the text 'apple'?" % a)
        no = _solve("Does the file %s contain the text 'zebra'?" % a)
        self.assertTrue(_verified(yes))
        self.assertTrue(_verified(no))
        self.assertEqual(0, self._status_answer(yes))
        self.assertEqual(1, self._status_answer(no))
        self.assertNotEqual(self._status_answer(yes), self._status_answer(no),
                            "the same answer was given for both questions")

    def test_the_answer_to_a_yes_or_no_question_is_reproduced_by_running_it_again(self):
        # The answer is not asserted by the producer: the inspector re-runs the
        # command and the code it gets has to be the code that was recorded.
        a = _fresh("apple\nbanana\n")
        result = _solve("Does the file %s contain the text 'zebra'?" % a)
        self.assertTrue(_verified(result))
        ledger = ((result.get("raw_goal_acceptance") or {}).get("reinspection_ledger") or [])
        self.assertTrue(ledger, "nothing was re-inspected")
        reinspection = ledger[0].get("reinspection") or {}
        self.assertIs(True, reinspection.get("command_re_run"), "the answer was never re-run")
        self.assertEqual(int(self._status_answer(result)),
                         int(reinspection["returncode_reproduced"]))

    def test_a_yes_or_no_question_leaves_the_file_unchanged(self):
        # `grep -q` prints nothing, and an empty output written to the bound
        # destination would empty the file -- the same defect as a read that
        # truncates, one layer down.
        a = _fresh("apple\nbanana\n")
        before = (ROOT / a).read_text(encoding="utf-8")
        self.assertTrue(_verified(_solve("Does the file %s contain the text 'apple'?" % a)))
        self.assertEqual(before, (ROOT / a).read_text(encoding="utf-8"))

    def test_two_identical_files_and_two_different_files_are_distinguished(self):
        a = _fresh("apple\nbanana\n")
        same = "%s/same.txt" % SCRATCH
        other = "%s/other.txt" % SCRATCH
        (ROOT / same).write_text("apple\nbanana\n", encoding="utf-8")
        (ROOT / other).write_text("fig\n", encoding="utf-8")
        yes = _solve("Are the files %s and %s identical?" % (a, same))
        no = _solve("Are the files %s and %s identical?" % (a, other))
        self.assertTrue(_verified(yes))
        self.assertTrue(_verified(no))
        self.assertEqual(0, self._status_answer(yes))
        self.assertEqual(1, self._status_answer(no))

    def test_a_trouble_exit_status_is_never_reported_as_an_answer(self):
        # 2 means the command had trouble, not "no".  Folding it into the answer
        # would turn a broken search into a confident negative.
        from canonical.runtime import raw_goal_trace_acceptance_v1 as _acc
        for program in ("grep", "egrep", "fgrep", "cmp", "diff"):
            self.assertEqual({0, 1}, set(_acc._ANSWER_IS_THE_EXIT_STATUS[program]),
                             program)

    def test_a_question_about_a_tree_still_searches_the_tree(self):
        # The pin on the scope.  A yes-or-no rule keyed on the word "contain"
        # must not take a sentence that asks for a search of a whole directory:
        # answering it from one file would report a search that never happened.
        from canonical.runtime import composer_route_v1 as _cr
        _fresh()
        d = "%s/dq" % SCRATCH
        (ROOT / d).mkdir(parents=True, exist_ok=True)
        (ROOT / d / "one.txt").write_text("apple\n", encoding="utf-8")
        goal = "Search the files in the directory %s for the exact text 'apple'" % d
        argv = _cr._prose_argv(goal)
        self.assertIsNotNone(argv, goal)
        self.assertIn("-r", argv, "a search of a tree was answered from one file")
        self.assertEqual(d, argv[-1])

    # ------------------------------------------------------------------
    # A part of a file measured in a UNIT the sentence states.
    #
    # The table builds every argv as `flags(_prose_count(text))`, and both
    # `_head_flags` and `_tail_flags` answer in LINES -- the number is read out
    # of the sentence and the unit is thrown away.  Measured before this, all
    # four of these were CERTIFIED as exact semantic acceptance while answering
    # a different question:
    #   "Show lines 2 to 4 of X"              -> `cat`,      the whole file
    #   "Show the first 10 bytes of X"        -> `head -n 10`, ten LINES
    #   "Show the first 5 characters of X"    -> `head -n 5`,  five LINES
    #   "from line 3 to the end" of a 10-line file -> `tail -n 2`, the LAST two
    # Reproducibility cannot see any of this: ten lines are a perfectly
    # reproducible answer to a question nobody asked.  So every test here
    # asserts the ANSWER TEXT, and asserts it against the wrong answer.
    # ------------------------------------------------------------------
    PART = "apple\nbanana\napple pie\ncherry\n"

    def test_a_line_range_is_the_lines_asked_for_and_not_the_whole_file(self):
        a = _fresh(self.PART)
        whole = (ROOT / a).read_text(encoding="utf-8")
        result = _solve("Show lines 2 to 4 of the file %s" % a)
        self.assertTrue(_verified(result))
        self.assertEqual("banana\napple pie\ncherry\n", self._answer(result))
        # The assertion that actually carries the fix.  Before it, this sentence
        # bound `cat` and returned the whole file -- and passed.
        self.assertNotEqual(whole, self._answer(result),
                            "a range of lines was answered with the whole file")

    def test_a_range_of_both_ends_is_pinned_to_the_command_that_means_it(self):
        # argv, not just the answer: a regression to `cat` or to `head`/`tail`
        # has to fail even if the answer scraping above ever changes shape.
        from canonical.runtime import composer_route_v1 as _cr
        a = _fresh(self.PART)
        for word in ("to", "through"):
            self.assertEqual(["sed", "-n", "2,4p", a],
                             _cr._prose_argv("Show lines 2 %s 4 of the file %s" % (word, a)),
                             word)

    def test_a_range_that_names_one_line_twice_is_that_one_line(self):
        a = _fresh(self.PART)
        result = _solve("Show lines 3 to 3 of the file %s" % a)
        self.assertTrue(_verified(result))
        self.assertEqual("apple pie\n", self._answer(result))

    def test_bytes_are_counted_in_bytes_and_not_in_lines(self):
        a = _fresh(self.PART)
        result = _solve("Show the first 10 bytes of the file %s" % a)
        self.assertTrue(_verified(result))
        answer = self._answer(result)
        # Ten bytes of this file straddle a newline: `head -n 10` -- what this
        # sentence bound before -- returns all 30 bytes of the file instead.
        self.assertEqual(10, len(answer))
        self.assertEqual("apple\nbana", answer)

    def test_characters_are_counted_in_characters_and_not_in_lines(self):
        a = _fresh(self.PART)
        result = _solve("Show the first 5 characters of the file %s" % a)
        self.assertTrue(_verified(result))
        self.assertEqual("apple", self._answer(result))
        self.assertNotEqual(self.PART, self._answer(result),
                            "five characters was answered with the whole file")

    def test_the_last_of_a_quantity_in_bytes_is_read_from_the_end(self):
        # The unit rule is not a `first`-only rule.  Measured: `tail -c 10`.
        a = _fresh(self.PART)
        result = _solve("Show the last 10 bytes of the file %s" % a)
        self.assertTrue(_verified(result))
        self.assertEqual(10, len(self._answer(result)))
        self.assertEqual("ie\ncherry\n", self._answer(result))

    def test_a_range_starting_at_a_line_runs_to_the_end_of_the_file(self):
        # This is the test that kills `tail -n 3`.  The fixture is deliberately
        # LONG: on a four-line file `tail -n 2` answered "from line 3 to the
        # end" correctly by coincidence, and the rule looked right.  A rule that
        # is only right on the fixture it was measured against is a wrong rule,
        # so the fixture is ten lines and the answer has to be eight of them.
        lines = "".join("L%d\n" % i for i in range(1, 11))
        long_file = _fresh(lines)
        result = _solve("Show the lines from line 3 to the end of the file %s" % long_file)
        self.assertTrue(_verified(result))
        answer = self._answer(result)
        self.assertEqual(["L%d" % i for i in range(3, 11)], answer.splitlines())
        self.assertEqual(8, len(answer.splitlines()),
                         "a range with an open end was answered from the wrong end")

    def test_reading_a_part_of_a_file_leaves_every_byte_of_it_alone(self):
        # Earned the hard way: `sed -n 3p` with the file as its own output
        # truncated the file to one line, because sed counts as an in-place
        # transform.  Every new sed script here is a print, not a substitution,
        # and `head -c` / `tail -c` are reads -- but a read that destroys the
        # thing it read is worse than a refusal, so it is pinned for all four.
        for goal in ("Show lines 2 to 4 of the file %s",
                     "Show lines 3 to 3 of the file %s",
                     "Show the first 10 bytes of the file %s",
                     "Show the last 10 bytes of the file %s"):
            a = _fresh(self.PART)
            before = (ROOT / a).read_bytes()
            self.assertTrue(_verified(_solve(goal % a)), goal)
            self.assertEqual(before, (ROOT / a).read_bytes(), goal)

    def test_a_quantity_in_bytes_does_not_steal_a_count_of_characters(self):
        # The `_WC_QTY` scope.  "Count the characters in X" is `wc -c`'s
        # question; answering it with the first N bytes would report a count
        # that was never made.  Measured unchanged.
        from canonical.runtime import composer_route_v1 as _cr
        a = _fresh(self.PART)
        argv = _cr._prose_argv("Count the characters in the file %s" % a)
        self.assertEqual(["wc", "-c", a], argv)

    def test_a_quantity_measured_in_lines_is_still_measured_in_lines(self):
        # The other side of the same scope: no unit word means the documented
        # line default stands, so nothing that already worked moves.
        from canonical.runtime import composer_route_v1 as _cr
        a = _fresh(self.PART)
        self.assertEqual(["head", "-n", "3", a],
                         _cr._prose_argv("Show the first 3 lines of the file %s" % a))
        self.assertEqual(["tail", "-n", "2", a],
                         _cr._prose_argv("Show the last 2 lines of the file %s" % a))
        self.assertEqual(["sed", "-n", "3p", a],
                         _cr._prose_argv("Show the third line of the file %s" % a))

    def test_the_unit_rule_does_not_reach_into_a_directory(self):
        # The scope pin, the same way the tree question is pinned.  "Show the
        # first 2 files in the directory D" is not a quantity of one file's
        # bytes, and `head -c` over a directory would report a read of bytes
        # that are not there.  Measured: the block declines and no `-c` appears.
        from canonical.runtime import composer_route_v1 as _cr
        _fresh(self.PART)
        d = "%s/du" % SCRATCH
        (ROOT / d).mkdir(parents=True, exist_ok=True)
        (ROOT / d / "one.txt").write_text("apple\n", encoding="utf-8")
        argv = _cr._prose_argv("Show the first 2 files in the directory %s" % d) or []
        self.assertNotIn("-c", argv, "a directory request was read as a byte count")
        self.assertNotIn("+2", argv, "a directory request was read as a line range")


class TestAStatedOperationIsHonouredOrRefused(unittest.TestCase):
    """A qualifier the route cannot honour must not be silently dropped.

    Every defect here was measured CERTIFIED as an exact semantic answer while
    answering a different question.  Reproducibility cannot see any of it: the
    wrong output is just as reproducible as the right one.
    """

    def _answer(self, result):
        import json as _json, re as _re
        text = _json.dumps(result, default=str)
        m = _re.search(r'"stdout"\s*:\s*"((?:[^"\\]|\\.)*)"', text)
        return m.group(1).encode().decode("unicode_escape") if m else None

    def _set_of_two_files(self):
        a = _fresh("apple\nbanana\napple pie\ncherry\n")
        d = "%s/dset" % SCRATCH
        (ROOT / d).mkdir(parents=True, exist_ok=True)
        (ROOT / d / "one.txt").write_text("apple\nbanana\n", encoding="utf-8")
        (ROOT / d / "two.txt").write_text("fig\n", encoding="utf-8")
        return d

    def test_the_contents_of_a_set_of_files_are_not_their_names(self):
        # Measured: "Show the contents of every file in the directory D" bound
        # `ls D` -- its pattern is `(?:list|show) ... directory` -- and answered
        # "one.txt\ntwo.txt", which was certified as exact.
        d = self._set_of_two_files()
        result = _solve("Show the contents of every file in the directory %s" % d)
        self.assertTrue(_verified(result))
        self.assertEqual("apple\nbanana\nfig\n", self._answer(result))
        self.assertNotIn("one.txt", self._answer(result),
                         "a request for contents was answered with the names")

    def test_a_line_of_every_file_is_not_answered_with_a_line_count(self):
        # `_WC_LINES` is the pattern for the UNIT, and on its own it fires on any
        # sentence that says "line".  Measured: this sentence set `_counting`,
        # engaged the set expansion and returned `wc -l` over the set, answering
        # a request for the third line with "2, 1, 3 total".
        d = self._set_of_two_files()
        result = _solve("Show the third line of every file in the directory %s" % d)
        self.assertNotIn("total", self._answer(result) or "",
                         "a request for a line was answered with a line count")
        self.assertNotIn("total", str(result.get("status") or ""))

    def test_counting_the_lines_of_a_set_of_files_still_counts_them(self):
        # The scope pin on the other side: the word that says something is being
        # COUNTED is `_WC_QTY`, and a sentence that really counts keeps its route.
        from canonical.runtime import composer_route_v1 as _cr
        d = self._set_of_two_files()
        argv = _cr._prose_argv("Count the lines in every file in the directory %s" % d)
        self.assertIsNotNone(argv)
        self.assertEqual("wc", argv[0])
        self.assertEqual("-l", argv[1])
        self.assertEqual(2, len(argv) - 2, "the set was not expanded")

    def test_a_sentence_about_the_files_in_a_directory_is_not_a_listing_of_it(self):
        # The hazard this exposed.  Tightening `_counting` handed "Show lines 2 to
        # 4 of every file in the directory D" straight to the `ls` row, which
        # answered with the file NAMES and was certified.  A looser match further
        # down the table is not a fix for a loose match above it.
        from canonical.runtime import composer_route_v1 as _cr
        d = self._set_of_two_files()
        for goal in ("Show lines 2 to 4 of every file in the directory %s" % d,
                     "Show the first 10 bytes of every file in the directory %s" % d):
            argv = _cr._prose_argv(goal) or []
            self.assertNotEqual("ls", argv[:1], goal)

    def test_listing_a_directory_is_still_a_listing(self):
        # And a sentence that really asks for a listing keeps it.
        from canonical.runtime import composer_route_v1 as _cr
        d = self._set_of_two_files()
        for goal in ("List all the files in the directory %s" % d,
                     "Show the contents of the directory %s" % d):
            self.assertEqual(["ls", d], _cr._prose_argv(goal), goal)

    # ------------------------------------------------------------------
    # Silence is not an answer -- unless silence IS the answer.
    #
    # `sed -n 10p` over a four-line file exits 0 having printed nothing, and the
    # run was accepted: `output_path` was the file itself, so the fingerprint
    # that passed was a fingerprint of the FILE, and the answer was empty.
    # The re-inspection faithfully reproduced the emptiness, which proves the
    # nothing was real and proves nothing about whether it answers the sentence.
    # ------------------------------------------------------------------
    def test_a_line_the_file_does_not_have_is_not_an_answer(self):
        a = _fresh("apple\nbanana\napple pie\ncherry\n")
        result = _solve("Show the tenth line of the file %s" % a)
        self.assertFalse(_verified(result),
                         "a line that is not in the file was certified as an answer")
        import json as _json
        self.assertIn("COMMAND_PRINTED_NONE_OF_THE_LINES_THE_SENTENCE_NAMED",
                      _json.dumps(result, default=str))

    def test_a_range_the_file_does_not_reach_is_not_an_answer(self):
        a = _fresh("apple\nbanana\napple pie\ncherry\n")
        self.assertFalse(_verified(_solve("Show lines 8 to 9 of the file %s" % a)))

    def test_a_range_starting_past_the_end_is_not_an_answer(self):
        # `tail -n +99` is the same shape: success, and nothing printed.
        a = _fresh("apple\nbanana\napple pie\ncherry\n")
        result = _solve("Show the lines from line 99 to the end of the file %s" % a)
        self.assertFalse(_verified(result))

    def test_the_line_that_is_there_is_still_shown(self):
        a = _fresh("apple\nbanana\napple pie\ncherry\n")
        result = _solve("Show the third line of the file %s" % a)
        self.assertTrue(_verified(result))
        self.assertEqual("apple pie\n", self._answer(result))

    def test_silence_that_really_is_the_answer_is_still_an_answer(self):
        # THE COUNTER-TEST.  Without it, the rule above could be a blanket
        # "empty output is a failure" and still pass every other test here.
        # "Show the lines that do not contain X" over a file where EVERY line
        # contains X has the empty set as its answer, and `grep -v` says so by
        # exiting 1 -- the program itself reports "nothing matched".  The exit
        # code is the whole difference between that and a line that is not there.
        a = _fresh("apple\napple pie\napple sauce\n")
        result = _solve("Show the lines in the file %s that do not contain 'apple'" % a)
        self.assertTrue(_verified(result), "the empty set was refused as if it were a failure")
        self.assertEqual("", self._answer(result))
        self.assertEqual(1, int(((result.get("composer_execution") or {})
                                 .get("produced") or {}).get("returncode")))

    def test_an_empty_file_still_reads_as_empty(self):
        # The second counter-test, and the reason the rule names `sed` and `tail`
        # and not every reader: the contents of an empty file really are nothing,
        # and `cat` exits 0 saying so.
        a = _fresh("")
        result = _solve("Show the contents of the file %s" % a)
        self.assertTrue(_verified(result))
        self.assertEqual("", self._answer(result))


class TestAReadingDoesNotWriteAndAStatedTransformIsNotDropped(unittest.TestCase):
    """Two halves of one distinction: what the sentence ASKED FOR.

    A rewriting sed script was treated as sufficient licence to write its output
    back over the file it read.  It is not: "Show the file X in upper case" and
    "Convert the file X to upper case" bind the SAME script, and only the second
    asked for X to change.  Measured, the first turned 'apple\nbanana\n' into
    'APPLE\nBANANA\n' on disk and was certified as an exact semantic answer.

    And the case a sentence asked for was silently dropped when it also named a
    line, because no rule composed the two.  sed composes an address with a
    command inside one script, so no pipeline was ever needed -- the reason
    recorded for this being impossible was wrong.
    """

    def _answer(self, result):
        import json as _json, re as _re
        text = _json.dumps(result, default=str)
        m = _re.search(r'"stdout"\s*:\s*"((?:[^"\\]|\\.)*)"', text)
        return m.group(1).encode().decode("unicode_escape") if m else None

    TEXT = "apple\nbanana\napple pie\ncherry\n"

    def test_a_request_to_be_shown_a_file_in_upper_case_does_not_change_it(self):
        # The reason this class exists.  Measured before the fix: the file on
        # disk went from 'apple\nbanana\n...' to 'APPLE\nBANANA\n...' on a
        # request to be SHOWN something, and the run was certified.  A read that
        # destroys what it read is worse than a refusal.
        a = _fresh(self.TEXT)
        result = _solve("Show the file %s in upper case" % a)
        self.assertTrue(_verified(result))
        self.assertEqual("APPLE\nBANANA\nAPPLE PIE\nCHERRY\n", self._answer(result),
                         "the upper-cased text is the answer, and belongs on stdout")
        self.assertEqual(self.TEXT, (ROOT / a).read_text(encoding="utf-8"),
                         "a request to be shown something rewrote the file")

    def test_a_conversion_still_changes_the_file_it_was_asked_to_change(self):
        # The other half, pinned in the same place so the distinction cannot be
        # collapsed in either direction: an implementation that never wrote back
        # would pass the test above and fail this one.
        a = _fresh(self.TEXT)
        result = _solve("Convert the file %s to upper case" % a)
        self.assertTrue(_verified(result))
        self.assertEqual("APPLE\nBANANA\nAPPLE PIE\nCHERRY\n",
                         (ROOT / a).read_text(encoding="utf-8"))

    def test_the_same_script_is_a_read_or_a_write_by_the_verb_alone(self):
        # Both sentences bind the same rewriting script, so the script cannot be
        # what tells them apart.  Only the verb can, and this asserts that the
        # two outcomes really do differ.
        from canonical.runtime import composer_route_v1 as _cr
        a = _fresh(self.TEXT)
        show = _cr._prose_argv("Show the file %s in upper case" % a)
        convert = _cr._prose_argv("Convert the file %s to upper case" % a)
        self.assertEqual(show, convert, "expected both to bind the same script")
        one = _solve("Show the file %s in upper case" % a)
        self.assertEqual(self.TEXT, (ROOT / a).read_text(encoding="utf-8"))
        _solve("Convert the file %s to upper case" % a)
        self.assertNotEqual(self.TEXT, (ROOT / a).read_text(encoding="utf-8"))
        self.assertTrue(_verified(one))

    def test_a_line_asked_for_in_upper_case_is_that_line_in_upper_case(self):
        # sed composes the address with the transform in one script, so this is a
        # single command.  Measured before: it bound `sed -n 3p` and answered
        # 'apple pie' in lower case, certified, with the case dropped.
        a = _fresh(self.TEXT)
        result = _solve("Show the third line of the file %s in upper case" % a)
        self.assertTrue(_verified(result))
        self.assertEqual("APPLE PIE\n", self._answer(result))
        self.assertEqual(self.TEXT, (ROOT / a).read_text(encoding="utf-8"))

    def test_a_range_asked_for_in_upper_case_is_those_lines_in_upper_case(self):
        a = _fresh(self.TEXT)
        result = _solve("Show lines 2 to 4 of the file %s in upper case" % a)
        self.assertTrue(_verified(result))
        self.assertEqual("BANANA\nAPPLE PIE\nCHERRY\n", self._answer(result))
        self.assertEqual(self.TEXT, (ROOT / a).read_text(encoding="utf-8"))

    def test_a_line_asked_for_in_lower_case_is_that_line_in_lower_case(self):
        a = _fresh("APPLE\nBANANA\n")
        result = _solve("Show the second line of the file %s in lower case" % a)
        self.assertTrue(_verified(result))
        self.assertEqual("banana\n", self._answer(result))

    def test_the_composition_is_one_command_and_not_a_pipeline(self):
        # The argv, so a regression to two steps -- or to dropping the case --
        # fails even if the answer scraping above ever changes shape.
        from canonical.runtime import composer_route_v1 as _cr
        a = _fresh(self.TEXT)
        argv = _cr._prose_argv("Show the third line of the file %s in upper case" % a)
        self.assertEqual(["sed", "-n", "3s/.*/" + chr(92) + "U&/p", a], argv)
        self.assertEqual(4, len(argv), "a single command was asked for")

    def test_a_line_that_is_not_there_is_not_an_answer_even_in_upper_case(self):
        # The sibling pin.  `sed -n '10s/.*/\U&/p'` prints nothing and exits 0
        # when line 10 is absent, exactly like `sed -n 10p` -- and the silence
        # rule matches the script by shape, so composing a transform onto the
        # address must not slip past it.
        a = _fresh(self.TEXT)
        self.assertFalse(_verified(_solve("Show the tenth line of the file %s in upper case" % a)))
        self.assertFalse(_verified(_solve("Show lines 8 to 9 of the file %s in upper case" % a)))

    def test_a_plain_line_and_a_plain_range_are_untouched_by_the_composition(self):
        # No case word means no substitution in the script.
        from canonical.runtime import composer_route_v1 as _cr
        a = _fresh(self.TEXT)
        self.assertEqual(["sed", "-n", "3p", a],
                         _cr._prose_argv("Show the third line of the file %s" % a))
        self.assertEqual(["sed", "-n", "2,4p", a],
                         _cr._prose_argv("Show lines 2 to 4 of the file %s" % a))


class TestAFilterQuestionGetsTheLinesItAskedFor(unittest.TestCase):
    """The lines that hold a text, and the lines that are empty.

    `_FILTER_LINE` matched "Show the lines in X that contain 'apple'", one value
    was quoted, `_NEGATED_LINE` did not fire -- and then the branch ended, so the
    sentence fell all the way through to `cat` and was certified with the WHOLE
    FILE as the answer to a question about two of its four lines.  Measured over
    nine such sentences, including one quoting 'apple' itself: every one answered
    with the whole file.  The negative form of the very same sentence worked, so
    only half of it had ever been written.

    The same half-written shape hid in the blank-line rule, where `-v` was
    hard-coded: "show the empty lines" was answered with the lines that are NOT
    empty, because inverting is what "REMOVE the empty lines" means.
    """

    def _answer(self, result):
        import json as _json, re as _re
        text = _json.dumps(result, default=str)
        m = _re.search(r'"stdout"\s*:\s*"((?:[^"\\]|\\.)*)"', text)
        return m.group(1).encode().decode("unicode_escape") if m else None

    TEXT = "apple\nbanana\napple pie\ncherry\n"

    def test_the_lines_that_contain_a_text_are_those_lines_not_the_file(self):
        a = _fresh(self.TEXT)
        whole = (ROOT / a).read_text(encoding="utf-8")
        result = _solve("Show the lines in the file %s that contain 'apple'" % a)
        self.assertTrue(_verified(result))
        self.assertEqual("apple\napple pie\n", self._answer(result))
        self.assertNotEqual(whole, self._answer(result),
                            "a question about two lines was answered with the whole file")
        self.assertEqual(self.TEXT, (ROOT / a).read_text(encoding="utf-8"))

    def test_the_positive_and_negative_forms_are_not_the_same_answer(self):
        # The assertion that carries the fix.  Before it, the positive form
        # returned the whole file and the negative form returned two lines, and
        # both were certified -- so an implementation that ignored the negation
        # entirely would still have passed a one-sided test.
        a = _fresh(self.TEXT)
        yes = _solve("Show the lines in the file %s that contain 'apple'" % a)
        no = _solve("Show the lines in the file %s that do not contain 'apple'" % a)
        self.assertTrue(_verified(yes))
        self.assertTrue(_verified(no))
        self.assertEqual("apple\napple pie\n", self._answer(yes))
        self.assertEqual("banana\ncherry\n", self._answer(no))
        self.assertNotEqual(self._answer(yes), self._answer(no))

    def test_a_value_nothing_matches_is_an_answer_and_not_the_whole_file(self):
        # The counter-test.  `grep` exits 1 when nothing matches, and that is the
        # answer "nothing matched" -- not a failure and not a licence to fall
        # through to `cat`, which is what used to happen.
        a = _fresh(self.TEXT)
        result = _solve("Show the lines in the file %s that contain 'zebra'" % a)
        self.assertTrue(_verified(result))
        self.assertEqual("", self._answer(result))

    def test_a_metacharacter_in_the_stated_value_is_a_literal_not_a_shell_word(self):
        # The value reaches the command as one argv element, so nothing in it is
        # interpreted.  Were a shell involved, `$(echo apple)` would become
        # 'apple' and match two lines; measured, it matches none.
        a = _fresh(self.TEXT)
        for value in ("a;b", "a|b", "$(echo apple)", "`echo apple`", 'a"b', "a*b", "a\\b"):
            result = _solve("Show the lines in the file %s that contain '%s'" % (a, value))
            self.assertTrue(_verified(result), value)
            self.assertEqual("", self._answer(result), value)

    def test_a_value_that_is_literal_text_is_not_read_as_a_regular_expression(self):
        # "Contain" is literal language, so `a*b` means those three characters --
        # and no line holds them.  Measured with `grep`, which treats the value as
        # a regex, this answered 'banana', because `a*b` matches it.
        a = _fresh(self.TEXT)
        result = _solve("Show the lines in the file %s that contain 'a*b'" % a)
        self.assertTrue(_verified(result))
        self.assertEqual("", self._answer(result))
        self.assertEqual("apple\napple pie\n",
                         self._answer(_solve(
                             "Show the lines in the file %s that contain 'apple'" % a)),
                         "the literal matcher must still find ordinary text")

    def test_a_value_the_sentence_never_delimited_is_not_guessed(self):
        # "contain 'a'b'" has three quote marks, so what was quoted is not
        # recoverable.  The recoverable fragment is `a`, and searching for that
        # matches three of the four lines -- a confident answer to a question the
        # sentence did not manage to ask.
        a = _fresh(self.TEXT)
        result = _solve("Show the lines in the file %s that contain 'a'b'" % a)
        self.assertFalse(_verified(result),
                         "an unbalanced quotation was answered by guessing the value")

    def test_a_quoted_payload_is_not_read_as_a_quoted_pattern(self):
        # Shape cannot tell a payload from a pattern, and neither can the word
        # "line": this sentence satisfies `_FILTER_LINE` and quotes exactly one
        # value.  Taking it as a filter bound `grep` over the file the sentence
        # was asking to be WRITTEN, and the promised artifact was then correctly
        # reported missing.  Caught by an existing test, and pinned here too.
        out = "%s/payload1.txt" % SCRATCH
        _fresh(self.TEXT)
        result = _solve("Write the line 'PROJECT BRAIN' to the file %s." % out)
        self.assertTrue(_verified(result))
        self.assertEqual("PROJECT BRAIN", (ROOT / out).read_text(encoding="utf-8"))

    def test_the_empty_lines_asked_for_are_the_empty_ones(self):
        # Both word orders, and the answer is the empty line -- not the two lines
        # that are not empty, which is what hard-coding `-v` returned.
        blank = _fresh("apple\n\ncherry\n")
        for goal in ("Show the empty lines in the file %s" % blank,
                     "Show the lines in the file %s that are empty" % blank):
            result = _solve(goal)
            self.assertTrue(_verified(result), goal)
            self.assertEqual("\n", self._answer(result), goal)

    def test_removing_the_empty_lines_still_keeps_the_ones_that_are_not(self):
        # The other half of the inversion, pinned so the fix cannot be a blanket
        # removal of `-v`.
        blank = _fresh("apple\n\ncherry\n")
        result = _solve("Remove the empty lines from the file %s" % blank)
        self.assertTrue(_verified(result))
        self.assertEqual("apple\ncherry\n", self._answer(result))

    def test_a_file_named_for_the_word_does_not_make_the_sentence_about_it(self):
        # The fixture is literally called blank.txt.  Measured without masking
        # the paths out first, the file's own NAME satisfied the blank-line
        # pattern, so a question about which of its lines contain 'apple' became
        # a question about its empty lines.
        blank = _fresh("apple\n\ncherry\n")
        self.assertTrue(blank.endswith("a1.txt"))
        named = "%s/blank.txt" % SCRATCH
        (ROOT / named).write_text("apple\n\ncherry\n", encoding="utf-8")
        result = _solve("Show the lines in the file %s that contain 'apple'" % named)
        self.assertTrue(_verified(result))
        self.assertEqual("apple\n", self._answer(result),
                         "the file's name was read as the sentence's subject")

    def test_a_second_operation_beside_the_filter_is_refused_not_half_served(self):
        # "The SORTED lines that contain 'apple'" needs two commands.  Serving the
        # filter alone would drop the sort and certify it, which is the defect;
        # so this refuses.  Pinned so the refusal is not later traded for a
        # half-answer that looks like progress.
        from canonical.runtime import composer_route_v1 as _cr
        a = _fresh(self.TEXT)
        goal = "Show the sorted lines in the file %s that contain 'apple'" % a
        self.assertIsNone(_cr._prose_argv(goal))
        self.assertFalse(_verified(_solve(goal)))


class TestThePlainestWayToAskEachQuestionIsAnswered(unittest.TestCase):
    """Every operation, asked in its plainest English.

    The corpora this file grew out of were written from the phrasings the binder
    already understood, which is how a family gets measured as closed while its
    most ordinary sentence is wrong.  Measured from the OPERATIONS instead, over
    eighteen plainest-phrasing questions: six were answered wrongly and all six
    were certified as exact semantic answers.

      "Show me the last line of X"            -> the last TWO lines
      "Where does 'apple' appear in X?"       -> refused
      "the lines in X with 'apple'"           -> the whole file
      "the lines in X without 'apple'"        -> the whole file
      "the lines of X in reverse order"       -> the whole file, unreversed
      "What is different between A and B?"    -> refused

    The cause is one thing: each pattern was written for a single word order and
    a single word form.  "difference" matched and "different" did not; "reverse
    the lines" matched and "the lines ... in reverse order" did not.  And the
    table was matched against the sentence WITH ITS PATH IN IT, so a path stood
    between words the pattern expected to be neighbours -- and a file called
    `blank.txt` satisfied the blank-line pattern by its own name.

    The expectations below are computed by RUNNING the command that means each
    question, never by writing down what the answer should be.
    """

    def _answer(self, result):
        import json as _json, re as _re
        text = _json.dumps(result, default=str)
        m = _re.search(r'"stdout"\s*:\s*"((?:[^"\\]|\\.)*)"', text)
        return m.group(1).encode().decode("unicode_escape") if m else None

    def _status(self, result):
        return ((result.get("composer_execution") or {}).get("produced") or {}).get("returncode")

    TEXT = "apple\nbanana\napple pie\ncherry\n"
    OTHER = "apple\nbanana\nfig\n"

    def _truth(self, argv):
        """The answer to the question, from the command that means it."""
        import subprocess as _sp
        proc = _sp.run(argv, cwd=str(ROOT), capture_output=True)
        return proc.returncode, proc.stdout.decode("utf-8")

    def test_each_question_matches_the_command_that_means_it(self):
        a = _fresh(self.TEXT)
        b = "%s/other1.txt" % SCRATCH
        (ROOT / b).write_text(self.OTHER, encoding="utf-8")
        cases = [
            ("Show me the contents of the file %s" % a, ["cat", a], False),
            ("Show me the first line of the file %s" % a, ["head", "-n", "1", a], False),
            ("Show me the last line of the file %s" % a, ["tail", "-n", "1", a], False),
            ("Show the final line of the file %s" % a, ["tail", "-n", "1", a], False),
            ("Print the last line of the file %s" % a, ["tail", "-n", "1", a], False),
            ("Show me the last 3 lines of the file %s" % a, ["tail", "-n", "3", a], False),
            ("How many lines are in the file %s?" % a, ["wc", "-l", a], False),
            ("How many words are in the file %s?" % a, ["wc", "-w", a], False),
            ("Where does 'apple' appear in the file %s?" % a, ["grep", "-n", "apple", a], False),
            ("Which lines in the file %s contain 'apple'?" % a, ["grep", "-n", "apple", a], False),
            ("How many lines in the file %s contain 'apple'?" % a, ["grep", "-c", "apple", a], False),
            ("Show me the lines in the file %s with 'apple'" % a, ["fgrep", "apple", a], False),
            ("Show the lines in the file %s that contain 'apple'" % a,
             ["fgrep", "apple", a], False),
            ("Show me the lines in the file %s without 'apple'" % a,
             ["fgrep", "-v", "apple", a], False),
            ("Sort the lines of the file %s" % a, ["sort", a], False),
            ("Show me the lines of the file %s in reverse order" % a, ["tac", a], False),
            ("Reverse the lines of the file %s" % a, ["tac", a], False),
            ("Show the file %s in upper case" % a, ["sed", "-e", "s/.*/" + chr(92) + "U&/", a], False),
            ("What is different between the files %s and %s?" % (a, b), ["diff", a, b], True),
            ("Show the differences between the files %s and %s" % (a, b), ["diff", a, b], True),
            ("Are the files %s and %s the same?" % (a, a), ["cmp", "-s", a, a], True),
        ]
        for goal, argv, exit_is_the_answer in cases:
            _fresh(self.TEXT)
            (ROOT / b).write_text(self.OTHER, encoding="utf-8")
            code, out = self._truth(argv)
            result = _solve(goal)
            self.assertTrue(_verified(result), goal)
            if exit_is_the_answer:
                self.assertEqual(code, self._status(result), goal)
            else:
                self.assertEqual(out, self._answer(result), goal)
            self.assertEqual(self.TEXT, (ROOT / a).read_text(encoding="utf-8"),
                             "a reading rewrote the file: " + goal)

    def test_the_last_line_of_a_file_is_one_line_and_not_the_default_two(self):
        # `_prose_count` documents a default of 2, which is right for "the last
        # lines" and wrong for "the last line".  Measured: the last line of a
        # four-line file was answered with its last two.
        a = _fresh(self.TEXT)
        for goal in ("Show me the last line of the file %s" % a,
                     "Show the final line of the file %s" % a):
            result = _solve(goal)
            self.assertTrue(_verified(result), goal)
            self.assertEqual("cherry\n", self._answer(result), goal)

    def test_a_count_the_sentence_states_still_stands(self):
        # The other side of the singular rule: a stated number is not overridden.
        a = _fresh(self.TEXT)
        result = _solve("Show me the last 3 lines of the file %s" % a)
        self.assertTrue(_verified(result))
        self.assertEqual("banana\napple pie\ncherry\n", self._answer(result))

    def test_the_lines_in_reverse_order_are_reversed_from_either_word_order(self):
        a = _fresh(self.TEXT)
        for goal in ("Show me the lines of the file %s in reverse order" % a,
                     "Reverse the lines of the file %s" % a):
            result = _solve(goal)
            self.assertTrue(_verified(result), goal)
            self.assertEqual("cherry\napple pie\nbanana\napple\n", self._answer(result), goal)

    def test_the_lines_with_a_text_and_the_lines_without_it_are_not_the_same(self):
        # "With" and "without" introduce a quoted value directly, with no verb of
        # containing at all.  Measured, both fell through to `cat` and were
        # certified with the whole file -- so both gave the SAME answer, and only
        # asking both can show that.
        a = _fresh(self.TEXT)
        yes = _solve("Show me the lines in the file %s with 'apple'" % a)
        no = _solve("Show me the lines in the file %s without 'apple'" % a)
        self.assertTrue(_verified(yes))
        self.assertTrue(_verified(no))
        self.assertEqual("apple\napple pie\n", self._answer(yes))
        self.assertEqual("banana\ncherry\n", self._answer(no))
        self.assertNotEqual(self._answer(yes), self._answer(no))

    def test_a_verb_of_appearing_is_a_verb_of_containing(self):
        a = _fresh(self.TEXT)
        result = _solve("Where does 'apple' appear in the file %s?" % a)
        self.assertTrue(_verified(result))
        self.assertEqual("1:apple\n3:apple pie\n", self._answer(result))

    def test_a_difference_question_is_answered_whatever_word_carries_it(self):
        a = _fresh(self.TEXT)
        b = "%s/other2.txt" % SCRATCH
        (ROOT / b).write_text(self.OTHER, encoding="utf-8")
        for goal in ("What is different between the files %s and %s?" % (a, b),
                     "Show the differences between the files %s and %s" % (a, b),
                     "Compare the files %s and %s" % (a, b)):
            result = _solve(goal)
            self.assertTrue(_verified(result), goal)
            self.assertEqual(1, self._status(result), goal)

    def test_a_path_is_not_read_as_prose(self):
        # The fixture is deliberately named for a word a pattern looks for.  The
        # table is matched with every path masked out, so the name cannot satisfy
        # a pattern and the words on either side of the path stay neighbours.
        named = "%s/reverse.txt" % SCRATCH
        _fresh(self.TEXT)
        (ROOT / named).write_text(self.TEXT, encoding="utf-8")
        result = _solve("Show me the lines of the file %s in reverse order" % named)
        self.assertTrue(_verified(result))
        self.assertEqual("cherry\napple pie\nbanana\napple\n", self._answer(result))
        result = _solve("Show me the last line of the file %s" % named)
        self.assertTrue(_verified(result))
        self.assertEqual("cherry\n", self._answer(result))



class TestAQuestionNeedsNoVerbAndAUniqueSetIsReallyUnique(unittest.TestCase):
    """Two defects found by asking merged main, not by reasoning about the code.

    Both were measured on main AFTER the plainest-phrasing class was reported
    closed, which is the point: the census that closed it carried a verb in every
    filter row -- "Show me the lines in X with 'apple'" -- so the plainest form of
    all, the noun phrase on its own, was never asked.

      "the lines in X with 'apple'"        -> REFUSED, while the same question
                                              with "Show me" in front was answered
      "the lines in X that contain 'apple'"-> REFUSED
      "the lines in X matching 'apple'"    -> REFUSED
      "the lines in X without 'apple'"     -> REFUSED
      "the lines in X that do not contain" -> REFUSED
      "Show the unique lines of the file X"-> on apple/banana/apple/cherry the
                                              answer held `apple` TWICE, and was
                                              certified as an exact semantic
                                              acceptance, because acceptance
                                              checks reproducibility and `uniq`
                                              is perfectly reproducible.

    The first is a refusal, so nothing wrong was believed.  The second is a
    certified wrong answer, and it had been in main since the row was added:
    the test pinned the ARGV (`uniq`) and never looked at what it returned.
    """

    def _truth(self, argv):
        """What the command that MEANS the question really returns."""
        import subprocess
        return subprocess.run(argv, capture_output=True, text=True,
                              cwd=str(ROOT)).stdout

    def test_the_plainest_form_of_a_filter_question_needs_no_verb(self):
        f = _fresh("apple\nbanana\nappe pie\ncherry\n")
        before = (ROOT / f).read_bytes()
        cases = (
            ("the lines in the file %s with 'apple'" % f, ["fgrep", "apple", f]),
            ("the lines in the file %s that contain 'apple'" % f,
             ["fgrep", "apple", f]),
            ("the lines in the file %s which include 'apple'" % f,
             ["fgrep", "apple", f]),
            ("the lines in the file %s without 'apple'" % f,
             ["fgrep", "-v", "apple", f]),
            ("the lines in the file %s that do not contain 'apple'" % f,
             ["fgrep", "-v", "apple", f]),
        )
        for goal, argv in cases:
            result = _solve(goal)
            self.assertTrue(_verified(result), goal)
            self.assertEqual(self._truth(argv), _stdout(result), goal)
        self.assertEqual(before, (ROOT / f).read_bytes(),
                         "a question about lines rewrote the file it named")

    def test_a_count_and_a_line_number_question_are_not_answered_with_lines(self):
        # The nearest legitimate cases to the rule this class widens, and the
        # reason the new arm is scoped away from them.  Both mention lines, a
        # quoted value and a word of containing -- exactly what the new arm
        # matches -- and neither is asking for the lines themselves.
        f = _fresh("apple\nbanana\nappe pie\ncherry\n")
        for goal, argv in (
                ("How many lines in the file %s contain 'apple'?" % f,
                 ["grep", "-c", "apple", f]),
                ("Which lines in the file %s contain 'apple'?" % f,
                 ["grep", "-n", "apple", f])):
            result = _solve(goal)
            self.assertTrue(_verified(result), goal)
            self.assertEqual(self._truth(argv), _stdout(result), goal)

    def test_the_unique_lines_are_the_distinct_set_when_the_file_is_unsorted(self):
        # The duplicate is not adjacent, which is the whole test.  `uniq` removes
        # adjacent duplicates only, so on this file it returns all four lines --
        # the duplicate still in it -- and that answer was certified.
        f = _fresh("apple\nbanana\napple\ncherry\n")
        result = _solve("Show the unique lines of the file %s" % f)
        self.assertTrue(_verified(result))
        self.assertEqual("apple\nbanana\ncherry\n", _stdout(result))
        self.assertEqual(self._truth(["sort", "-u", f]), _stdout(result))
        self.assertNotEqual(self._truth(["uniq", f]), _stdout(result),
                            "the answer is what the adjacent-only program gives")

    def test_a_pattern_search_is_still_handed_to_the_pattern_matcher(self):
        # Rewritten harder, not deleted.  This used to assert that the VERBLESS
        # form was refused, because the filter block sent a quoted value to the
        # literal matcher and `fgrep 'ap.le'` matches nothing in a file that holds
        # "apple" -- a refusal was better than that.  The block now has a branch
        # for a stated pattern that binds `grep`, so both forms are served and the
        # real assertion is the one that matters: a pattern is never handed to the
        # literal matcher, in either form.
        from canonical.runtime import composer_route_v1 as _cr
        f = _fresh("apple\nbanana\n")
        for goal in ("Find the lines in the file %s matching 'ap.le'" % f,
                     "the lines in the file %s matching 'ap.le'" % f):
            argv = _cr._prose_argv(goal)
            self.assertIsNotNone(argv, "a pattern search was refused: %r" % goal)
            self.assertEqual("grep", argv[0], goal)

    def test_a_pattern_question_is_answered_as_a_pattern_in_both_forms(self):
        # The distinction the branch above exists to keep, asserted on the answer
        # and not on the argv.  `ap.le` matches "apple" as a regular expression and
        # matches nothing at all as literal text, so the two matchers give
        # different answers to the same quoted value -- and "contain" is literal
        # language while "matching" is pattern language.
        f = _fresh("apple\nbanana\napple\ncherry\n")
        self.assertEqual("apple\napple\n",
                         _stdout(_solve("the lines in the file %s matching 'ap.le'" % f)))
        self.assertEqual("apple\napple\n",
                         _stdout(_solve("Find the lines in the file %s matching 'ap.le'" % f)))
        # the same value asked for literally matches nothing, and says so
        self.assertEqual("", _stdout(_solve(
            "the lines in the file %s that contain 'ap.le'" % f)))
        # and negating a pattern inverts the pattern, not the empty literal match.
        # Measured before the branch was ordered first: `fgrep -v 'ap.le'` matched
        # nothing, inverting that returned the WHOLE FILE, and it was certified.
        self.assertEqual("banana\ncherry\n",
                         _stdout(_solve("the lines in the file %s not matching 'ap.le'" % f)))

    def test_a_question_about_the_empty_lines_needs_no_verb_either(self):
        f = _fresh("apple\nbanana\n\ncherry\n\n")
        for goal in ("the empty lines in the file %s" % f,
                     "Show me the empty lines in the file %s" % f):
            self.assertEqual("\n\n", _stdout(_solve(goal)), goal)
        self.assertEqual("apple\nbanana\n\ncherry\n\n",
                         (ROOT / f).read_text(encoding="utf-8"),
                         "a question about a file changed it")


class TestANounPhraseIsAnsweredAndAChainThatRanNothingIsNotAPass(unittest.TestCase):
    """Asking with no verb at all, and the false pass that hid behind it.

    Measured on main 5126acf, a census of eighteen ordinary requests asked as
    bare noun phrases -- the plainest form there is -- scored ten of eighteen.
    The eight failures were three different defects, and the worst was not a
    refusal:

      "the first 3 lines of X"   -> pass=True, status PASS__COMPOSED_CAPABILITY_CHAIN,
                                    NO raw_goal_acceptance, chain=[], produced={}
      "the lines of X numbered"  -> the same
      "the contents of the file X" -> routed to a JSON file WRITER for a read
      "the first/last/third line of X" -> FAIL__RAW_GOAL_COMPILATION_GAP
      "the files in the directory D"   -> refused

    The first two are the reason this class exists.  `route` returned
    PASS__SYNTHESISED_PROGRAM with an empty chain, `execute_chain([])` ran its
    loop zero times and returned pass=True with the status
    PASS__COMPOSER_CHAIN_EXECUTED, and the front door reported the goal DONE.  A
    request that ran no step and left no bytes was reported as finished.

    Two more were found while measuring the fix, both pre-existing and both
    certified: "X in upper case" -- a phrase that states no verb either way --
    wrote the upper-cased text back over X, and "the third line of X in upper
    case" was answered with the WHOLE FILE upper-cased.

    Every expectation below is computed by RUNNING the command that means the
    question.
    """

    TEXT = "apple\nbanana\napple pie\ncherry\n"

    def _truth(self, argv):
        import subprocess
        return subprocess.run(argv, capture_output=True, text=True,
                              cwd=str(ROOT)).stdout

    def _fixtures(self):
        f = _fresh(self.TEXT)
        (ROOT / SCRATCH / "b1.txt").write_text("apple\nbanana\nfig\n", encoding="utf-8")
        (ROOT / SCRATCH / "dup.txt").write_text("apple\nbanana\nappe\ncherry\n",
                                               encoding="utf-8")
        d = "%s/dset" % SCRATCH
        (ROOT / d).mkdir(parents=True, exist_ok=True)
        (ROOT / d / "one.txt").write_text("apple\nbanana\n", encoding="utf-8")
        (ROOT / d / "two.log").write_text("fig\n", encoding="utf-8")
        return f, "%s/b1.txt" % SCRATCH, "%s/dup.txt" % SCRATCH, d

    def test_a_noun_phrase_gets_the_answer_the_verbed_form_gets(self):
        f, other, dup, d = self._fixtures()
        touched = [f, other, dup, "%s/one.txt" % d, "%s/two.log" % d]
        before = {p: (ROOT / p).read_bytes() for p in touched}
        cases = (
            ("the contents of the file %s" % f, ["cat", f]),
            ("the first line of %s" % f, ["sed", "-n", "1p", f]),
            ("the last line of %s" % f, ["tail", "-n", "1", f]),
            ("the third line of %s" % f, ["sed", "-n", "3p", f]),
            ("the first 3 lines of %s" % f, ["head", "-n", "3", f]),
            ("the last 2 lines of %s" % f, ["tail", "-n", "2", f]),
            ("the lines 2 to 4 of %s" % f, ["sed", "-n", "2,4p", f]),
            ("the number of lines in %s" % f, ["wc", "-l", f]),
            ("the sorted lines of %s" % f, ["sort", f]),
            ("the unique lines of the file %s" % dup, ["sort", "-u", dup]),
            ("the lines of %s in reverse order" % f, ["tac", f]),
            ("the lines of %s numbered" % f, ["nl", f]),
            ("the lines in the file %s with 'apple'" % f, ["fgrep", "apple", f]),
            ("the lines in the file %s without 'apple'" % f, ["fgrep", "-v", "apple", f]),
            ("the files in the directory %s" % d, ["ls", d]),
            ("the difference between %s and %s" % (f, other), ["diff", f, other]),
        )
        for goal, argv in cases:
            result = _solve(goal)
            self.assertTrue(_verified(result), goal)
            self.assertEqual(self._truth(argv), _stdout(result), goal)
        self.assertEqual(before, {p: (ROOT / p).read_bytes() for p in touched},
                         "a noun phrase that asked to be shown something changed a file")

    def test_a_chain_that_ran_no_step_is_not_reported_as_executed(self):
        from canonical.runtime import composer_route_v1 as _cr
        out = _cr.execute_chain([], "the first 3 lines of a1.txt")
        self.assertIs(False, out.get("pass"))
        self.assertEqual([], out.get("steps"))
        self.assertEqual("FAIL__COMPOSER_CHAIN_RAN_NO_STEP", out.get("status"))

    def test_no_goal_is_reported_done_without_an_acceptance_verdict(self):
        # The invariant the two false passes broke, stated generally rather than
        # per sentence: nothing may report pass=True while carrying no acceptance
        # verdict at all.  Measured on 5126acf, two noun phrases did exactly that.
        f, _other, _dup, d = self._fixtures()
        hollow = []
        for goal in ("the first 3 lines of %s" % f,
                     "the last 2 lines of %s" % f,
                     "the lines of %s numbered" % f,
                     "the contents of the file %s" % f,
                     "the files in the directory %s" % d,
                     "the third line of %s" % f,
                     "the lines 2 to 4 of %s" % f):
            result = _solve(goal)
            if result.get("pass") is True and result.get("raw_goal_acceptance") is None:
                hollow.append((goal, result.get("status")))
        self.assertEqual([], hollow, "a goal was reported done with no verdict")

    def test_a_noun_phrase_names_a_reader_and_not_a_writer(self):
        # "the contents of the file X" measured as routing to `json.file.write`
        # -- a capability that truncates what it is given, chosen for a request
        # to be shown something.
        from canonical.runtime import composer_route_v1 as _cr
        f, _o, _d, _e = self._fixtures()
        self.assertEqual(["cat", f], _cr._prose_argv("the contents of the file %s" % f))

    def test_an_ambiguous_transform_answers_without_destroying_the_file(self):
        # The phrase states no verb, so it does not say whether the file should
        # change.  The answer is on stdout either way, so the file stays.
        a = _fresh(self.TEXT)
        result = _solve("%s in upper case" % a)
        self.assertTrue(_verified(result))
        self.assertEqual("APPLE\nBANANA\nAPPLE PIE\nCHERRY\n", _stdout(result))
        self.assertEqual(self.TEXT.encode(), (ROOT / a).read_bytes(),
                         "an ambiguous phrase rewrote the file it named")

    def test_a_stated_conversion_still_writes_the_file(self):
        # The other side of the rule above, pinned so narrowing the write path
        # cannot pass by simply never writing.  Both of these wrote before and
        # must write now.
        from canonical.runtime import composer_route_v1 as _cr
        a = _fresh(self.TEXT)
        result = _solve("Convert the file %s to upper case" % a)
        self.assertTrue(_verified(result))
        self.assertEqual("APPLE\nBANANA\nAPPLE PIE\nCHERRY\n",
                         (ROOT / a).read_text(encoding="utf-8"))
        for sentence in ("Replace every 'apple' with 'pear' in the file %s" % a,
                         "Replace 'apple' with 'fig' in the file %s" % a):
            args = _cr.bind({"argv": "ARGV", "output_path": "PATH_OUTPUT"}, sentence)
            self.assertEqual("true", args.get("write_stdout_to_output"), sentence)

    def test_a_noun_phrase_that_states_a_transform_is_composed_not_dropped(self):
        # Both of these were answered with the WHOLE FILE, upper-cased, and
        # certified.  The address and the case are one sed script, so the line
        # the sentence named is the line that comes back.
        for goal, want in (("the third line of %s in upper case", "APPLE PIE\n"),
                           ("the lines 2 to 4 of %s in upper case",
                            "BANANA\nAPPLE PIE\nCHERRY\n")):
            a = _fresh(self.TEXT)
            result = _solve(goal % a)
            self.assertTrue(_verified(result), goal)
            self.assertEqual(want, _stdout(result), goal)
            self.assertEqual(self.TEXT.encode(), (ROOT / a).read_bytes(), goal)


class TestAnAppendIsServedAndADirectoryIsNamedByTheSentence(unittest.TestCase):
    """The mutating requests that were measured as refused, now served.

    A census of fourteen ordinary mutating requests, judged by comparing the
    world the binder left with the world the real command left in a parallel
    directory, scored five of fourteen on main 263ad2f.  None of the nine was a
    wrong answer or a deletion -- every one was fail-closed -- but they were
    ordinary requests going unserved, and two of them were served wrongly in a
    way that only the world could show:

      "Append the line 'date' to the file X"        -> refused, three phrasings
      "Move the file X into the directory D"        -> COMMAND_MV_DESTINATION_ABSENT
                                                       over a move that HAD happened
      "Delete the directory D"                      -> `rm D`, failed on a non-empty
                                                       directory, reported
                                                       COMPOSED_STEP_RAISED_OUTCOME_UNKNOWN
      "Write ... without losing what is there"      -> refused, though the code
                                                       already knew the promise

    The last one is the sharpest: `_KEEPS_EXISTING_CONTENT` recognised the
    promise and `_PLAIN_PAYLOAD_WRITES` knew the writer would break it, so the
    system could tell the sentence wanted the content kept and had no program
    that kept it.
    """

    def _world(self):
        f = _fresh("apple\nbanana\ncherry\n")
        d = "%s/dset" % SCRATCH
        (ROOT / d).mkdir(parents=True, exist_ok=True)
        (ROOT / d / "one.log").write_text("fig\n", encoding="utf-8")
        return f, d

    def test_an_append_adds_the_line_and_keeps_what_was_there(self):
        # `_fresh` wipes the whole scratch directory, so the fixture is written
        # by hand here: the test needs a second file to survive beside the one
        # being appended to, and a helper that deletes the tree cannot provide it.
        for index, goal in enumerate((
                "Append the line 'date' to the file %s",
                "Add the line 'date' to the end of the file %s",
                "Write the line 'date' at the end of the file %s",
                "Append 'date' to %s")):
            root = ROOT / SCRATCH
            root.mkdir(parents=True, exist_ok=True)
            a = "%s/ap%d.txt" % (SCRATCH, index)
            neighbour = "%s/nb%d.txt" % (SCRATCH, index)
            (ROOT / a).write_text("apple\nbanana\ncherry\n", encoding="utf-8")
            (ROOT / neighbour).write_text("fig\n", encoding="utf-8")
            result = _solve(goal % a)
            self.assertTrue(_verified(result), (goal, result.get("status")))
            self.assertEqual("apple\nbanana\ncherry\ndate\n",
                             (ROOT / a).read_text(encoding="utf-8"), goal)
            # A file the sentence never named is untouched: the append is scoped
            # to the one operand, not to the directory it happens to sit in.
            self.assertEqual("fig\n", (ROOT / neighbour).read_text(encoding="utf-8"),
                             goal)

    def test_a_command_that_writes_the_file_itself_is_not_also_handed_its_stdout(self):
        # The hazard this closes, measured before the guard: `sed -i` writes the
        # file itself and puts nothing on stdout, so writing that stdout over the
        # declared output would truncate a file the command had just rewritten.
        from canonical.runtime import composer_route_v1 as _cr
        a = _fresh("apple\n")
        for argv in (["sed", "-i", "$a date", a], ["sort", "-o", a, a]):
            args = {}
            _cr._declare_a_written_output(
                args, argv, "Append the line 'date' to the file %s" % a)
            self.assertNotIn("write_stdout_to_output", args, argv)

    def test_the_append_postcondition_can_fail(self):
        # Pinned from both sides so it cannot pass by trusting the flag.  The
        # promise is asked of the disk: the last line is the line that was added.
        from canonical.runtime import raw_goal_trace_acceptance_v1 as _accept
        a = _fresh("apple\nbanana\n")
        ok, reason, _ev = _accept._post_sed(["sed", "-i", "$a date", a], ROOT)
        self.assertFalse(ok, "a file with no appended line was certified")
        self.assertEqual("COMMAND_SED_LAST_LINE_IS_NOT_THE_APPENDED_TEXT", reason)
        (ROOT / a).write_text("apple\nbanana\ndate\n", encoding="utf-8")
        ok, _reason, _ev = _accept._post_sed(["sed", "-i", "$a date", a], ROOT)
        self.assertTrue(ok)
        # A substitution has no promise about the last line and stays refused.
        ok, reason, _ev = _accept._post_sed(["sed", "-i", "s|a|b|g", a], ROOT)
        self.assertFalse(ok)
        self.assertEqual("COMMAND_SED_PROMISE_UNSTATEABLE_FOR_THIS_SHAPE", reason)

    def test_moving_a_file_into_a_directory_is_proven_by_the_world(self):
        f, d = self._world()
        result = _solve("Move the file %s into the directory %s" % (f, d))
        self.assertTrue(_verified(result), result.get("status"))
        self.assertTrue((ROOT / d / "a1.txt").is_file(),
                        "the file is not inside the directory it was moved into")
        self.assertFalse((ROOT / f).exists(), "the source is still there")

    def test_deleting_a_directory_the_sentence_named_deletes_it(self):
        _f, d = self._world()
        result = _solve("Delete the directory %s" % d)
        self.assertTrue(_verified(result), result.get("status"))
        self.assertFalse((ROOT / d).exists(), "the directory survived its own deletion")

    def test_a_file_deletion_still_binds_no_flag_at_all(self):
        # The pin on the scope of the rule above: `rm -r` is bound only when the
        # sentence says "directory".  A sentence about a file gets plain `rm`,
        # which fails loudly on a directory instead of removing a tree.
        from canonical.runtime import composer_route_v1 as _cr
        f, _d = self._world()
        self.assertEqual(["rm", f], _cr._prose_argv("Delete the file %s" % f))


class TestRemovingSomethingInsideAFileIsNotDeletingTheFile(unittest.TestCase):
    """Eight ordinary sentences deleted the file they named and were certified.

    Measured on main d3e9a3a, before this change:

        Remove the executable permission from the file X   -> `rm X`  DELETED, verified
        Remove the read permission from the file X         -> `rm X`  DELETED, verified
        Remove the first line from the file X              -> `rm X`  DELETED, verified
        Remove the last line from the file X               -> `rm X`  DELETED, verified
        Remove the word 'apple' from the file X            -> `rm X`  DELETED, verified
        Remove the header from the file X                  -> `rm X`  DELETED, verified
        Remove the trailing spaces from the file X         -> `rm X`  DELETED, verified
        Remove the comments from the file X                -> `rm X`  DELETED, verified

    Every one reported PASS__RAW_GOAL_EXECUTED_AND_EXACT_SEMANTIC_ACCEPTANCE_VERIFIED.
    "Remove X from the file Y" is an edit of Y; the sentence names Y as the
    SOURCE, and the `rm` row matched on the verb alone.

    Scoping `rm` alone was not enough and is measured below: the same sentences
    then fell through to a READER and were still certified -- `head -n 1` printed
    the line it had been asked to delete.  A certified wrong answer is not a
    smaller failure than a deletion, so the fall-through is refused too.
    """

    EDITS = ("Remove the executable permission from the file %s",
             "Remove the read permission from the file %s",
             "Remove the first line from the file %s",
             "Remove the last line from the file %s",
             "Remove the word 'apple' from the file %s",
             "Remove the header from the file %s",
             "Remove the trailing spaces from the file %s",
             "Remove the comments from the file %s")

    def test_no_removal_of_something_inside_a_file_deletes_the_file(self):
        # This invariant is unchanged and now covers eight sentences that are
        # served as well as the ones still refused: an edit of a file's contents
        # must never remove the file.
        for goal in self.EDITS:
            a = _fresh("apple\nbanana\ncherry\n")
            _solve(goal % a)
            self.assertTrue((ROOT / a).exists(),
                            "the file was deleted by %r" % (goal,))

    def test_an_edit_nothing_can_prove_is_refused_and_leaves_the_file_alone(self):
        # Four of the eight are served now and four are not, and the split is not
        # arbitrary: a deletion by POSITION leaves nothing checkable behind,
        # because the line removed is gone and was never in the argv, while a
        # deletion by PATTERN keeps the pattern in the argv and so keeps a promise
        # the disk can answer.  The unprovable ones are refused with the file
        # byte-identical -- not served and certified on a promise no one can check.
        for goal in ("Remove the first line from the file %s",
                     "Remove the last line from the file %s",
                     "Remove the header from the file %s"):
            a = _fresh("apple\nbanana\ncherry\n")
            self.assertFalse(_verified(_solve(goal % a)), goal)
            self.assertEqual("apple\nbanana\ncherry\n",
                             (ROOT / a).read_text(encoding="utf-8"), goal)

    def test_the_edits_that_can_be_proven_are_proven_by_the_world_afterwards(self):
        # The other side of the split.  Each of these is certified only because a
        # postcondition asked the disk the question the argv can answer, so each is
        # asserted on the bytes it left and on the mode bit it left.
        a = _fresh("apple\nbanana\napple\ncherry\n")
        self.assertTrue(_verified(_solve("Remove the word 'apple' from the file %s" % a)))
        self.assertEqual("\nbanana\n\ncherry\n", (ROOT / a).read_text(encoding="utf-8"))

        b = _fresh("apple  \nbanana\ncherry   \n")
        self.assertTrue(_verified(_solve("Remove the trailing spaces from the file %s" % b)))
        self.assertEqual("apple\nbanana\ncherry\n", (ROOT / b).read_text(encoding="utf-8"))

        c = _fresh("apple\n# a comment\nbanana\n")
        self.assertTrue(_verified(_solve("Remove the comments from the file %s" % c)))
        self.assertEqual("apple\nbanana\n", (ROOT / c).read_text(encoding="utf-8"))

        d = _fresh("apple\n")
        self.assertTrue(_verified(_solve("Make the file %s executable" % d)))
        self.assertTrue((ROOT / d).stat().st_mode & 0o100)
        self.assertTrue(_verified(_solve("Remove the executable permission from the file %s" % d)))
        self.assertFalse((ROOT / d).stat().st_mode & 0o100)
        self.assertEqual("apple\n", (ROOT / d).read_text(encoding="utf-8"))

        e = _fresh("apple\nbanana\n")
        self.assertTrue(_verified(_solve("Empty the file %s" % e)))
        self.assertEqual("", (ROOT / e).read_text(encoding="utf-8"))

    def test_a_real_deletion_still_deletes(self):
        # The pin on the scope of both rules above: they are scoped to the OBJECT
        # of the verb, not to the verb, so naming the file itself still deletes it.
        for goal in ("Remove the file %s", "Delete the file %s"):
            a = _fresh("apple\nbanana\ncherry\n")
            self.assertTrue(_verified(_solve(goal % a)), goal)
            self.assertFalse((ROOT / a).exists(), goal)

    def test_a_directory_the_sentence_named_is_still_deleted_whole(self):
        root = ROOT / SCRATCH
        root.mkdir(parents=True, exist_ok=True)
        d = "%s/treerm" % SCRATCH
        (ROOT / d).mkdir(parents=True, exist_ok=True)
        (ROOT / d / "one.log").write_text("fig\n", encoding="utf-8")
        result = _solve("Delete the directory %s" % d)
        self.assertTrue(_verified(result), result.get("status"))
        self.assertFalse((ROOT / d).exists())

    def test_deleting_files_inside_a_directory_does_not_delete_the_directory(self):
        # Regression pin on a defect introduced and merged by the change that
        # taught `rm -r` to read the word "directory": that rule matched on the
        # word alone and paths[0] was the DIRECTORY, so a sentence naming files
        # inside it bound `rm -r` on the tree and deleted every file in it,
        # certifying the deletion of files the sentence never named.  Refusing is
        # the honest outcome until the pattern is expanded to real names.
        root = ROOT / SCRATCH
        root.mkdir(parents=True, exist_ok=True)
        d = "%s/treerm2" % SCRATCH
        (ROOT / d).mkdir(parents=True, exist_ok=True)
        for name in ("one.log", "two.txt"):
            (ROOT / d / name).write_text("fig\n", encoding="utf-8")
        result = _solve("Delete the files named '*.log' in the directory %s" % d)
        self.assertFalse(_verified(result), result.get("status"))
        self.assertTrue((ROOT / d).exists(), "the directory itself was deleted")
        self.assertTrue((ROOT / d / "two.txt").exists(),
                        "a file the sentence never named was deleted")

    def test_the_removals_that_are_owned_still_do_their_work(self):
        # The nearest legitimate cases to the refusal above.  A rule that refuses
        # too much is a defect too, and these four really perform the removal.
        a = _fresh("apple\nbanana\napple\ncherry\n\n")
        self.assertEqual("apple\nbanana\ncherry\n",
                         _stdout(_solve("Remove the duplicate lines from the file %s" % a)).lstrip("\n"))
        self.assertEqual("apple\nbanana\ncherry\n",
                         _stdout(_solve("Remove the repeated lines from the file %s" % a)).lstrip("\n"))
        b = _fresh("apple\nbanana\napple\ncherry\n\n")
        self.assertEqual("apple\nbanana\napple\ncherry\n",
                         _stdout(_solve("Remove the empty lines from the file %s" % b)))
        c = _fresh("apple\nbanana\napple\ncherry\n\n")
        self.assertEqual("apple\nbanana\napple\ncherry\n",
                         _stdout(_solve("Remove the blank lines from the file %s" % c)))

    def test_reading_a_line_is_untouched_by_the_refusal(self):
        # The refusal keys on a removal verb, so asking for a line still answers.
        a = _fresh("apple\nbanana\ncherry\n")
        self.assertEqual("apple\n", _stdout(_solve("Show the first line of the file %s" % a)))
        self.assertEqual("cherry\n", _stdout(_solve("Show the last line of the file %s" % a)))
        self.assertEqual("apple\nbanana\ncherry\n",
                         (ROOT / a).read_text(encoding="utf-8"))


class TestATwoFileRequestAndATreeQuestionGetTheOperationTheyStated(unittest.TestCase):
    """A census of two-file and directory requests, judged against the real command.

    Measured on main 4cd4af4, sixteen rows scored eight.  Five of the failures
    were certified WRONG answers rather than refusals, and one of them destroyed
    data:

        "Append the contents of the file A to the file B"
            -> `cat A` with B declared as the output, which TRUNCATED B and wrote
               A's bytes over it.  B held 'cherry\\ndate\\n'; afterwards it held
               'apple\\nbanana\\n'.  A copy, certified as an append, with the
               content B already held destroyed.

        "the files named '*.log' in the directory D"
            -> `ls D`, every entry in the directory, for a question about one file
        "the files in the directory D and its subdirectories"
            -> `ls D`, one level, for a question about a tree
        "How many files are in the directory D?"
            -> `ls D`, a list of names as the answer to a question that asked
               for a number

    The first two of those were the plainest form of a question the binder already
    answered correctly with a verb in front of it: "Find the files named '*.log'
    in the directory D" bound `find`.  A question is not a different question for
    dropping its verb.
    """

    def _half(self, name):
        d = "%s/%s" % (SCRATCH, name)
        (ROOT / d).mkdir(parents=True, exist_ok=True)
        (ROOT / d / "a.txt").write_text("apple\nbanana\n", encoding="utf-8")
        (ROOT / d / "b.txt").write_text("cherry\ndate\n", encoding="utf-8")
        (ROOT / d / "sub").mkdir(exist_ok=True)
        (ROOT / d / "sub" / "one.log").write_text("fig\n", encoding="utf-8")
        return d

    def test_appending_one_file_to_another_keeps_what_the_destination_held(self):
        # The defect this exists for.  A copy certified as an append is the worst
        # shape there is: the answer looks right, the file it destroyed is the one
        # the sentence named as the destination, and nothing is missing from the
        # report.  sed's `r` command is the operation the sentence stated, and the
        # source survives it, which is what makes the result provable afterwards.
        d = self._half("apdst")
        result = _solve("Append the contents of the file %s/a.txt to the file %s/b.txt" % (d, d))
        self.assertTrue(_verified(result), result.get("status"))
        self.assertEqual("cherry\ndate\napple\nbanana\n",
                         (ROOT / d / "b.txt").read_text(encoding="utf-8"),
                         "what the destination held was not kept")
        self.assertEqual("apple\nbanana\n",
                         (ROOT / d / "a.txt").read_text(encoding="utf-8"),
                         "the source was consumed by an append")

    def test_the_append_postcondition_is_recomputed_from_a_source_that_survives(self):
        # Pinned able to fail, from both sides.  Unlike every other in-place shape
        # this one has a real oracle: `r` reads the source and does not consume it,
        # so the promised tail is recomputed from a file still on disk.
        from canonical.runtime import raw_goal_trace_acceptance_v1 as _accept
        d = self._half("appost")
        argv = ["sed", "-i", "$r %s/a.txt" % d, "%s/b.txt" % d]
        (ROOT / d / "b.txt").write_text("cherry\ndate\napple\nbanana\n", encoding="utf-8")
        self.assertTrue(_accept._post_sed(argv, ROOT)[0])
        (ROOT / d / "b.txt").write_text("cherry\ndate\nWRONG\n", encoding="utf-8")
        ok, reason, _ev = _accept._post_sed(argv, ROOT)
        self.assertFalse(ok, "a destination that does not end with the source was certified")
        self.assertEqual("COMMAND_SED_FILE_DOES_NOT_END_WITH_THE_APPENDED_CONTENTS", reason)
        ok, reason, _ev = _accept._post_sed(
            ["sed", "-i", "$r /etc/passwd", "%s/b.txt" % d], ROOT)
        self.assertFalse(ok)
        self.assertEqual("COMMAND_SED_SOURCE_PATH_OUTSIDE_REPOSITORY", reason)

    def test_a_question_about_a_tree_is_not_answered_with_one_level_of_it(self):
        d = self._half("treeq")
        want = "%s/sub/one.log" % d          # find prints the path as it was given
        got = _stdout(_solve("the files named '*.log' in the directory %s" % d))
        self.assertEqual(want, got.strip(),
                         "a question about one file was answered with the directory")
        got = _stdout(_solve("the files in the directory %s and its subdirectories" % d))
        self.assertIn("one.log", got, "a tree question was answered with its top level")
        # and the verb form of the same two questions still answers the same way
        self.assertEqual(want, _stdout(_solve(
            "Find the files named '*.log' in the directory %s" % d)).strip())

    def test_a_listing_of_a_directory_is_not_a_count_of_it(self):
        # Asked how many, answered with names, certified.  Counting needs a
        # pipeline and no single program here does it, so the honest outcome is a
        # refusal -- and the count `wc` really performs is untouched.
        d = self._half("countq")
        self.assertFalse(_verified(_solve("How many files are in the directory %s?" % d)))
        a = _fresh("apple\nbanana\ncherry\n")
        self.assertEqual("3", _stdout(_solve("How many lines are in the file %s?" % a)).split()[0])

    def test_naming_a_tree_does_not_hijack_a_mutation_or_a_creation(self):
        # The pin on the scope of the widening above, and the two regressions it
        # was measured causing.  "named" appears in a deletion and in a creation
        # as well as in a search, and both were answered with a listing.
        from canonical.runtime import composer_route_v1 as _cr
        d = self._half("hijack")
        result = _solve("Delete the files named '*.log' in the directory %s" % d)
        self.assertFalse(_verified(result), "a deletion was answered with a listing")
        self.assertTrue((ROOT / d / "sub" / "one.log").exists(),
                        "a file the sentence named was removed by a route that only reads")
        new = "%s/made" % SCRATCH
        self.assertEqual(["mkdir", new], _cr.extract_argv("Make a folder named %s" % new))
        self.assertTrue(_verified(_solve("Make a folder named %s" % new)))
        self.assertTrue((ROOT / new).is_dir())

    def test_a_plain_listing_of_a_directory_is_still_a_listing(self):
        # The nearest legitimate case to every refusal and widening above.
        d = self._half("plainls")
        got = sorted((_stdout(_solve("the files in the directory %s" % d)) or "").split())
        self.assertEqual(["a.txt", "b.txt", "sub"], got)


if __name__ == "__main__":
    unittest.main()


class TestASecondOperandIsTheSameQuestionAskedTwice(unittest.TestCase):
    """One program, two operands.  These were all recorded as needing a pipeline.

    They do not.  Every sentence here is a single program given a second operand,
    and the arity gate refused all of them because the prose rows state exactly
    one.  "The first line of the files A and B" is the same question the binder
    already answered, asked twice.

    The permission is an allowlist and not a blanket one, because for three
    programs a second operand means something else, and one of them is a
    destruction wearing the face of a read:

        `uniq A B`  does not read B.  B is the OUTPUT FILE.  Measured: A held
                    'apple\\nbanana\\n', B held 'cherry\\ndate\\n', and after
                    `uniq A B` the command printed nothing and B held
                    'apple\\nbanana\\n' -- the content B already had was replaced,
                    rc 0, no diagnostic.
        `tac A B`   reverses the concatenation, so A's first line ends up last.
        `nl A B`    numbers straight through both, so B's first line is not 1.

    Allowing two operands for a program where the second means something else
    would have answered each of those with the wrong output and one with a
    destroyed file.  So the allowlist is pinned from both sides.
    """

    def _pair(self, name):
        d = "%s/%s" % (SCRATCH, name)
        (ROOT / d).mkdir(parents=True, exist_ok=True)
        (ROOT / d / "a.txt").write_text("apple\nbanana\ncherry\n", encoding="utf-8")
        (ROOT / d / "b.txt").write_text("banana\ndate\napple\n", encoding="utf-8")
        return d

    def _both_intact(self, d):
        self.assertEqual("apple\nbanana\ncherry\n",
                         (ROOT / d / "a.txt").read_text(encoding="utf-8"))
        self.assertEqual("banana\ndate\napple\n",
                         (ROOT / d / "b.txt").read_text(encoding="utf-8"))

    def test_the_first_line_of_two_files_is_asked_of_each_file(self):
        d = self._pair("mohead")
        result = _solve("Show the first line of the files %s/a.txt and %s/b.txt" % (d, d))
        self.assertTrue(_verified(result), result.get("status"))
        out = _stdout(result)
        # head names the file it is answering for, so the answer carries both the
        # lines and which file each came from.
        for want in ("apple", "banana"):
            self.assertIn(want, out.split("\n"))
        self.assertNotIn("cherry", out.split("\n"))
        self.assertNotIn("date", out.split("\n"))
        self._both_intact(d)

    def test_the_line_count_of_two_files_reports_each_one_and_the_total(self):
        d = self._pair("mowc")
        result = _solve("How many lines are in the files %s/a.txt and %s/b.txt?" % (d, d))
        self.assertTrue(_verified(result), result.get("status"))
        fields = _stdout(result).split()
        # three lines in each file and six across both -- the total is what a
        # count over two files means, and it is the number a single count cannot
        # give.  A listing of names here would be a certified wrong answer.
        self.assertIn("6", fields)
        self.assertIn("total", fields)
        self.assertEqual(2, fields.count("3"))
        self._both_intact(d)

    def test_sorting_two_files_merges_their_lines(self):
        d = self._pair("mosort")
        result = _solve("Sort the lines of the files %s/a.txt and %s/b.txt" % (d, d))
        self.assertTrue(_verified(result), result.get("status"))
        self.assertEqual(["apple", "apple", "banana", "banana", "cherry", "date"],
                         [x for x in _stdout(result).split("\n") if x])
        self._both_intact(d)

    def test_the_lines_two_files_share_are_taken_from_the_other_file(self):
        # Not a pipeline and not an intersection computed in Python: grep reads one
        # file as its pattern list and prints the lines of the other that match
        # whole-line.  The oracle is the set the two files actually share.
        d = self._pair("moboth")
        a = set((ROOT / d / "a.txt").read_text(encoding="utf-8").split("\n")) - {""}
        b = set((ROOT / d / "b.txt").read_text(encoding="utf-8").split("\n")) - {""}
        result = _solve("the lines that are in both the file %s/a.txt and the file %s/b.txt"
                        % (d, d))
        self.assertTrue(_verified(result), result.get("status"))
        self.assertEqual(sorted(a & b),
                         sorted(x for x in _stdout(result).split("\n") if x))
        self.assertEqual(["apple", "banana"],
                         sorted(x for x in _stdout(result).split("\n") if x))
        self._both_intact(d)

    def test_the_lines_only_one_file_has_are_the_complement_of_the_shared_ones(self):
        # The order of the two files IS the question.  -f takes the pattern file,
        # so "the lines in A that are not in B" must be `grep -xvf B A`.  Swapped,
        # it answers the opposite question with exactly as much confidence, and
        # both answers are plausible-looking lists of lines.
        d = self._pair("moonly")
        result = _solve("the lines in the file %s/a.txt that are not in the file %s/b.txt"
                        % (d, d))
        self.assertTrue(_verified(result), result.get("status"))
        self.assertEqual(["cherry"], [x for x in _stdout(result).split("\n") if x])
        # Asserted against its opposite: the same two files with the roles swapped
        # must give a different answer, or the binder is not reading the order.
        flipped = _solve("the lines in the file %s/b.txt that are not in the file %s/a.txt"
                         % (d, d))
        self.assertTrue(_verified(flipped), flipped.get("status"))
        self.assertEqual(["date"], [x for x in _stdout(flipped).split("\n") if x])
        self._both_intact(d)

    def test_a_second_operand_never_reaches_a_program_that_writes_to_it(self):
        # The reason the permission is an allowlist and not a blanket one.
        # `uniq A B` does not dedupe two files -- B is where it WRITES.  Measured
        # on this sandbox: it printed nothing, returned 0, and replaced B's
        # 'cherry\ndate\n' with A's 'apple\nbanana\n'.  A blank answer and a
        # destroyed destination, from a sentence that asked to remove duplicates.
        # `uniq` is not a prose row at all, so the shape is unreachable; the
        # sentences that ask for it are answered by `sort -u`, which reads both
        # operands and writes neither.  Pinned on the bytes, not on the argv: if
        # uniq ever becomes a row, this goes red before B is destroyed silently.
        d = self._pair("mouniq")
        before_a = (ROOT / d / "a.txt").read_text(encoding="utf-8")
        before_b = (ROOT / d / "b.txt").read_text(encoding="utf-8")
        result = _solve("Remove the duplicate lines from the files %s/a.txt and %s/b.txt"
                        % (d, d))
        self.assertTrue(_verified(result), result.get("status"))
        self.assertEqual(["apple", "banana", "cherry", "date"],
                         [x for x in _stdout(result).split("\n") if x])
        self.assertEqual(before_a, (ROOT / d / "a.txt").read_text(encoding="utf-8"))
        self.assertEqual(before_b, (ROOT / d / "b.txt").read_text(encoding="utf-8"),
                         "the second operand of uniq is its output file; B must survive")

    def test_a_program_whose_second_operand_changes_the_meaning_still_refuses(self):
        # `tac A B` reverses the concatenation and `nl A B` numbers through both,
        # so neither answers "do this to each file".  Refusing is right; guessing
        # which of the two readings was meant is not.
        d = self._pair("motac")
        for goal in ("Reverse the files %s/a.txt and %s/b.txt" % (d, d),
                     "the lines of the files %s/a.txt and %s/b.txt numbered" % (d, d)):
            result = _solve(goal)
            self.assertFalse(_verified(result), "%s -> %s" % (goal, _stdout(result)))
        self._both_intact(d)

    def test_the_single_file_forms_are_not_disturbed_by_the_second_operand(self):
        # A pin: the widening is for MORE operands than a row states, never fewer
        # and never a change to the one-operand answer that already worked.
        d = self._pair("moone")
        first = _solve("Show the first line of the file %s/a.txt" % d)
        self.assertTrue(_verified(first), first.get("status"))
        self.assertEqual("apple\n", _stdout(first))
        count = _solve("How many lines are in the file %s/a.txt?" % d)
        self.assertTrue(_verified(count), count.get("status"))
        self.assertIn("3", _stdout(count).split())
        self._both_intact(d)


class TestTheLinesThatRepeatAreNotAnsweredWithTheLinesThatDoNot(unittest.TestCase):
    """`sort -u` answers "the unique lines".  It does not answer "the duplicate lines".

    Both questions used to reach the same row, because that row matched the bare
    words `duplicate` or `repeated` next to `lines`, and so the two OPPOSITE
    questions shared one answer.  Measured on main d39c9db, on a file holding
    apple/banana/apple/cherry/banana/apple:

        "Show the duplicate lines of the file X"
            -> `sort -u`, certified, returning 'apple\\nbanana\\ncherry\\n'.
               The duplicate lines are 'apple\\nbanana\\n'.  `cherry` appears
               exactly once and is not a duplicate, so the answer named a line
               that is the opposite of what was asked for -- and it is a
               plausible list of lines from the right file, which is what makes
               it hard to notice.

        "How many duplicate lines are in the file X?"
            -> `wc -l`, certified, returning 6.  The answer is 2.
        "How many unique lines are in the file X?"
            -> `wc -l`, certified, returning 6.  The answer is 3.
               Both are the total line count wearing the shape of an answer.

        "Are all the lines of the file X unique?"
            -> `sort -u`, certified, returning the distinct set -- a listing as
               the answer to a yes/no question.

    The repeats themselves are `sort X | uniq -d`, which is two programs, and this
    binder emits one argv.  `uniq -d` alone sees ADJACENT repeats only and
    measured empty on this file.  So those are refusals now: a refusal states
    what it cannot do, whereas the old answer reported the wrong lines as the
    work that was asked for.
    """

    DUPES = "apple\nbanana\napple\ncherry\nbanana\napple\n"

    def _file(self, name):
        d = "%s/%s" % (SCRATCH, name)
        (ROOT / d).mkdir(parents=True, exist_ok=True)
        (ROOT / d / "a.txt").write_text(self.DUPES, encoding="utf-8")
        return d + "/a.txt"

    def test_the_duplicate_lines_are_not_answered_with_the_distinct_set(self):
        f = self._file("dl1")
        result = _solve("Show the duplicate lines of the file %s" % f)
        self.assertFalse(_verified(result),
                         "the distinct set is not the set of lines that repeat: %r"
                         % _stdout(result))
        # The old answer was the distinct set, and the distinct set contains a
        # line that appears exactly once.  Assert that directly, so the reason
        # this must fail is written down and not just the verdict.
        distinct = sorted(set(self.DUPES.split("\n")) - {""})
        self.assertIn("cherry", distinct)
        self.assertEqual(1, self.DUPES.split("\n").count("cherry"),
                         "cherry appears once, so it is not a duplicate line")
        self.assertEqual(self.DUPES, (ROOT / f).read_text(encoding="utf-8"))

    def test_the_verbless_form_of_the_same_question_is_refused_too(self):
        # A phrasing variant is a defect class.  The plainest form is the noun
        # phrase with no verb in front of it at all.
        f = self._file("dl2")
        for goal in ("the duplicate lines of the file %s" % f,
                     "the repeated lines of the file %s" % f,
                     "the lines that appear more than once in the file %s" % f):
            result = _solve(goal)
            self.assertFalse(_verified(result), "%s -> %r" % (goal, _stdout(result)))
            self.assertEqual(self.DUPES, (ROOT / f).read_text(encoding="utf-8"),
                             "a refusal must leave the file alone")

    def test_a_count_of_a_filtered_set_is_not_the_total_line_count(self):
        # 6 is how many lines the file holds.  It is not how many of them repeat,
        # and it is not how many are distinct.  Both were certified.
        f = self._file("dl3")
        self.assertEqual(6, len(self.DUPES.split("\n")) - 1)
        self.assertEqual(2, len({x for x in self.DUPES.split("\n")
                                 if self.DUPES.split("\n").count(x) > 1}))
        self.assertEqual(3, len(set(self.DUPES.split("\n")) - {""}))
        for goal in ("How many duplicate lines are in the file %s?" % f,
                     "How many unique lines are in the file %s?" % f):
            result = _solve(goal)
            self.assertFalse(_verified(result), "%s -> %r" % (goal, _stdout(result)))
        # The nearest legitimate case that must still pass: the count a file
        # really has is what `wc -l` measures, and it stays served.
        plain = _solve("How many lines are in the file %s?" % f)
        self.assertTrue(_verified(plain), plain.get("status"))
        self.assertIn("6", _stdout(plain).split())

    def test_a_yes_no_question_is_not_answered_with_a_listing(self):
        f = self._file("dl4")
        result = _solve("Are all the lines of the file %s unique?" % f)
        self.assertFalse(_verified(result),
                         "a listing is not an answer to a yes/no question: %r"
                         % _stdout(result))
        self.assertEqual(self.DUPES, (ROOT / f).read_text(encoding="utf-8"))

    def test_the_distinct_set_is_served_under_both_of_its_names(self):
        # "unique" and "distinct" both mean the distinct set here -- that reading
        # was chosen deliberately over `uniq`, which leaves duplicates in an
        # unsorted file.  "distinct" measured as binding nothing at all.
        f = self._file("dl5")
        want = "apple\nbanana\ncherry\n"
        for goal in ("Show the unique lines of the file %s" % f,
                     "the distinct lines of the file %s" % f):
            result = _solve(goal)
            self.assertTrue(_verified(result), "%s -> %s" % (goal, result.get("status")))
            self.assertEqual(want, _stdout(result))

    def test_removing_the_duplicates_still_yields_the_distinct_set(self):
        # The neighbour that shares the word.  "Remove the duplicate lines" asks
        # for what is LEFT, which is the distinct set, and it is pinned elsewhere.
        # Scoping the question about the repeats must not have taken this with it.
        f = self._file("dl6")
        result = _solve("Remove the duplicate lines from the file %s" % f)
        self.assertTrue(_verified(result), result.get("status"))
        self.assertEqual("apple\nbanana\ncherry\n", _stdout(result))

    def test_the_removals_that_are_owned_are_untouched_by_the_new_refusals(self):
        # Every one of these contains a word a new refusal could have swallowed.
        # They are FILTERS in this repository, not in-place edits -- that is
        # pinned elsewhere for the duplicate form -- so the kept lines come back
        # on stdout and the file is left exactly as it was.
        d = "%s/dl7" % SCRATCH
        (ROOT / d).mkdir(parents=True, exist_ok=True)
        f = d + "/b.txt"
        want = "apple\nbanana\n# note\n"
        for goal in ("Remove the empty lines from the file %s" % f,
                     "Remove the blank lines from the file %s" % f):
            (ROOT / f).write_text("apple\n\nbanana\n# note\n\n", encoding="utf-8")
            result = _solve(goal)
            self.assertTrue(_verified(result), "%s -> %s" % (goal, result.get("status")))
            self.assertEqual(want, _stdout(result), goal)
            self.assertEqual("apple\n\nbanana\n# note\n\n",
                             (ROOT / f).read_text(encoding="utf-8"),
                             "%s is a filter; the file must be untouched" % goal)


class TestAQuotedValueDoesNotEatThePathItIsQuotedBeside(unittest.TestCase):
    """Masking a quoted value must remove the QUOTED SPAN, not those characters.

    The `grep -c` / `grep -n` branch masked its value with a blind
    `re.sub(re.escape(value), " ", sentence)`, which eats those characters
    wherever they occur -- including inside the file's own path.  Measured on a
    file at canonical/astra_runtime/tmp/m3v7x/zz/u.txt, the pattern 'an' turned
    the operand into "c onical/astra_runtime/tmp/m3v7x/zz/u.txt" and grep failed
    with "No such file or directory".  13 of 15 two- and three-character patterns
    corrupted the path the same way, including 'tm', 'mp' and 'ru', because the
    path is built out of ordinary letters.

    `_mask_a_quoted_value` already existed for exactly this defect and its
    docstring already described it.  It was called from one branch and not from
    this one.  A fix applied to one call site is not applied to its siblings.
    """

    def _f(self, name):
        d = "%s/%s" % (SCRATCH, name)
        (ROOT / d).mkdir(parents=True, exist_ok=True)
        (ROOT / d / "u.txt").write_text("apple\nbanana\ncherry\n", encoding="utf-8")
        return d + "/u.txt"

    def test_a_pattern_found_inside_the_path_does_not_break_the_path(self):
        f = self._f("mv1")
        # Every one of these occurs inside the path this repository runs in.  If
        # the value is masked blindly the operand arrives with a space in it and
        # the command fails on a file that does not exist.
        for pat in ("an", "ca", "ni", "ic", "al", "ru", "nt", "tm", "mp"):
            result = _solve("How many lines in the file %s contain '%s'?" % (f, pat))
            self.assertTrue(
                _verified(result),
                "the pattern %r was masked out of the path itself: %s"
                % (pat, result.get("status")))
        # And the count is the real one, not merely a successful run.  On
        # apple/banana/cherry: 'an' is in "banana" alone, so 1; 'a' is in "apple"
        # and "banana" but NOT in "cherry", so 2 -- a number that is merely
        # plausible would be 3, the count of lines in the file.
        self.assertEqual("1\n", _stdout(_solve(
            "How many lines in the file %s contain 'an'?" % f)))
        self.assertEqual("2\n", _stdout(_solve(
            "How many lines in the file %s contain 'a'?" % f)))

    def test_the_value_is_still_masked_where_it_was_quoted(self):
        # The other half: masking exists so a quoted value is not read as a
        # second file.  Removing it entirely would pass the test above and fail
        # this one.
        f = self._f("mv2")
        result = _solve("the lines in the file %s that contain 'u.txt'" % f)
        self.assertTrue(_verified(result), result.get("status"))
        self.assertEqual("", _stdout(result))


class TestAColumnThatIsNotThereAndANumberThatWasAskedFor(unittest.TestCase):
    """Two certified wrong answers, each the whole answer to a different question.

    "The second column of the file X" on a file with no tab in it was certified
    returning the ENTIRE FILE, because `cut -f 2` prints a line that has no
    delimiter unchanged.  Every line looked like its own second column.

    "The line numbers in the file X containing 'an'" was certified returning
    'banana' -- the matching line, with no number on it.  The number was the
    whole question.
    """

    def _file(self, name, content):
        d = "%s/%s" % (SCRATCH, name)
        (ROOT / d).mkdir(parents=True, exist_ok=True)
        (ROOT / d / "a.txt").write_text(content, encoding="utf-8")
        return d + "/a.txt"

    def test_a_file_with_no_such_column_does_not_return_its_whole_lines(self):
        f = self._file("cw1", "apple banana cherry\ndate fig grape\n")
        result = _solve("Show the second column of the file %s" % f)
        self.assertTrue(_verified(result), result.get("status"))
        # `-s` suppresses a line with no delimiter, so a file that has no columns
        # yields nothing rather than pretending every line is one.
        self.assertEqual("", _stdout(result),
                         "a file with no tab has no second column; returning its "
                         "lines invents one")
        self.assertEqual("apple banana cherry\ndate fig grape\n",
                         (ROOT / f).read_text(encoding="utf-8"))

    def test_a_real_column_still_comes_back_unchanged(self):
        # The nearest legitimate case: `-s` must not cost the ordinary answer.
        f = self._file("cw2", "name\tage\tcity\nann\t30\toslo\nbob\t25\trome\n")
        self.assertEqual("age\n30\n25\n",
                         _stdout(_solve("Show the second column of the file %s" % f)))
        self.assertEqual("name\nann\nbob\n",
                         _stdout(_solve("Show the first column of the file %s" % f)))
        self.assertEqual("city\noslo\nrome\n",
                         _stdout(_solve("Cut field 3 from the file %s" % f)))

    def test_a_line_number_question_carries_the_number(self):
        f = self._file("cw3", "apple\nbanana\ncherry\n")
        result = _solve("the line numbers in the file %s containing 'an'" % f)
        self.assertTrue(_verified(result), result.get("status"))
        self.assertEqual("2:banana\n", _stdout(result))

    def test_the_plain_filter_is_untouched_by_the_number_flag(self):
        # The pin on the other side: a sentence that asks for the LINES must not
        # grow line numbers it did not ask for.
        f = self._file("cw4", "apple\nbanana\ncherry\n")
        self.assertEqual("banana\n", _stdout(_solve(
            "the lines in the file %s that contain 'an'" % f)))
        self.assertEqual("apple\ncherry\n", _stdout(_solve(
            "the lines in the file %s that do not contain 'an'" % f)))


class TestAShapeIsAWayToAskForASetOfFiles(unittest.TestCase):
    """Stating which files you want is a question about a set, not a request for a listing.

    A ten-row census of set-of-files requests, judged against the real `find` run
    in a parallel directory, scored TWO of ten on main 17993e0.  Eight were
    certified wrong answers and none of them destroyed anything, which is what
    let them survive: the answer is always a plausible list of real names from
    the right directory.

        "the files in the directory D ending with '.log'"   -> `ls D`, every entry
        "the files in the directory D starting with 'one'"  -> `ls D`, every entry
        "the .log files in the directory D"                 -> `ls D`, every entry
            Each returned keep.txt and a SUBDIRECTORY alongside the two files
            that were asked about.

        "Find the files in the directory D that end with '.log'"
            -> `find D -name '.log'`, a pattern matching a file literally named
               ".log", returning NOTHING -- certified, in a directory holding two
               .log files.  The same sentence WITHOUT quotes around .log was
               correct, which is what kept it hidden: the defect was in the
               quoting, not in the question.

        "the files in the directory D and its subdirectories ending with '.log'"
            -> nothing, for the same reason.

    There were two causes.  The set block could only be entered by the verb
    "find" or by the word "named"; a sentence that states a SHAPE instead never
    reached it and fell through to the `ls` row, which matches anything holding
    both "files" and "directory".  And inside the block, the quoted branch used
    the value raw while the unquoted branch built `*` + value, so quoting the
    value turned a suffix pattern into a literal name.
    """

    def _dir(self, name):
        d = "%s/%s" % (SCRATCH, name)
        (ROOT / d / "sub").mkdir(parents=True, exist_ok=True)
        (ROOT / d / "one.log").write_text("x\n", encoding="utf-8")
        (ROOT / d / "two.log").write_text("y\n", encoding="utf-8")
        (ROOT / d / "keep.txt").write_text("z\n", encoding="utf-8")
        (ROOT / d / "sub" / "deep.log").write_text("w\n", encoding="utf-8")
        return d

    @staticmethod
    def _names(result):
        return sorted(x.rsplit("/", 1)[-1] for x in _stdout(result).split())

    def test_an_ending_selects_a_set_and_not_the_whole_directory(self):
        d = self._dir("sf1")
        result = _solve("the files in the directory %s ending with '.log'" % d)
        self.assertTrue(_verified(result), result.get("status"))
        self.assertEqual(["deep.log", "one.log", "two.log"], self._names(result))
        # The two things a listing adds and a set must not: a file that does not
        # match, and a directory, which is not a file at all.
        self.assertNotIn("keep.txt", self._names(result))
        self.assertNotIn("sub", self._names(result))

    def test_the_quoted_form_is_not_read_as_a_literal_filename(self):
        # The defect that returned nothing: `-name '.log'` matches a file called
        # ".log" and there is no such file, so the answer was empty and certified.
        d = self._dir("sf2")
        for goal in ("Find the files in the directory %s that end with '.log'" % d,
                     "the files in the directory %s that end with '.log'" % d,
                     "the files in the directory %s ending with .log" % d):
            result = _solve(goal)
            self.assertTrue(_verified(result), "%s -> %s" % (goal, result.get("status")))
            self.assertEqual(["deep.log", "one.log", "two.log"], self._names(result),
                             "the quoted and unquoted forms of the same shape must "
                             "give the same set: %s" % goal)

    def test_an_extension_in_front_of_the_word_files_names_the_set(self):
        d = self._dir("sf3")
        want = ["deep.log", "one.log", "two.log"]
        for goal in ("the .log files in the directory %s" % d,
                     "all the .log files in the directory %s" % d):
            result = _solve(goal)
            self.assertTrue(_verified(result), "%s -> %s" % (goal, result.get("status")))
            self.assertEqual(want, self._names(result), goal)

    def test_a_prefix_shape_selects_by_prefix(self):
        d = self._dir("sf4")
        result = _solve("the files in the directory %s starting with 'one'" % d)
        self.assertTrue(_verified(result), result.get("status"))
        self.assertEqual(["one.log"], self._names(result))

    def test_a_shape_asked_for_over_a_tree_walks_the_tree(self):
        # The explicit tree form and the plain form must agree: both are a walk,
        # and a question is not a different question for saying "subdirectories".
        d = self._dir("sf5")
        want = ["deep.log", "one.log", "two.log"]
        self.assertEqual(want, self._names(_solve(
            "the files in the directory %s and its subdirectories ending with '.log'" % d)))

    def test_the_plain_listing_is_still_a_listing(self):
        # The pin on the other side of the widening.  A sentence that states no
        # shape at all asks for everything in the directory, and it must keep
        # getting everything -- including the subdirectory, which `ls` reports.
        d = self._dir("sf6")
        result = _solve("the files in the directory %s" % d)
        self.assertTrue(_verified(result), result.get("status"))
        self.assertEqual(["keep.txt", "one.log", "sub", "two.log"], self._names(result))

    def test_a_shape_does_not_turn_a_deletion_or_a_creation_into_a_listing(self):
        # Both of these were measured regressions the last time this entry
        # condition was widened, and both are pinned.  A set search reads; a
        # deletion and a creation are not readings, and answering either with a
        # list of names is a certified answer to a different question.
        d = self._dir("sf7")
        for goal in ("Delete the .log files in the directory %s" % d,
                     "Delete the files in the directory %s ending with '.log'" % d):
            result = _solve(goal)
            self.assertFalse(_verified(result), "%s was answered with a listing: %s"
                             % (goal, _stdout(result)))
        self.assertTrue((ROOT / d / "one.log").exists(), "a refusal must not delete")
        self.assertTrue((ROOT / d / "keep.txt").exists())
        made = _solve("Make a folder named %s/brandnew" % d)
        self.assertTrue((ROOT / d / "brandnew").is_dir(),
                        "a creation answered with a listing creates nothing: %s"
                        % made.get("status"))


class TestAChangeTheSentenceScopedIsNotWidenedAndItsMirrorIsNotLost(unittest.TestCase):
    """Four defects in the edit class, three of them certified wrong answers.

    A seventeen-row census of mutating requests, judged by running the real
    command in a parallel directory and comparing the resulting bytes and modes,
    scored thirteen of seventeen on main c8fe19b:

        "Replace the FIRST 'hello' with 'goodbye' in the file X"
            -> `sed -e s|hello|goodbye|g`, which replaced BOTH.  Measured,
               'hello world\\nhello again\\n' became 'goodbye world\\ngoodbye
               again\\n' and was certified, for a sentence that said first.

        "Remove the lines containing 'again' from the file X"
            -> plain `fgrep again`, which PRINTS the matching lines and changes
               nothing.  The answer was 'hello again\\n' -- the very line the
               sentence asked to have gone -- and the file still held it.

        "Add the text 'top' to the beginning of the file X"  -> refused
        "Add the text 'top' at the start of the file X"      -> refused
            while the mirror sentence "Add the text 'end' to the END of the file
            X" was served.  The prepend branch had always accepted these verbs
            and these positions; the gate in front of it listed `append` and
            `prepend` but not `add`, and the append rule has its own separate
            trigger, so one pair of opposites had two gates and only one was open.
    """

    TWO_HELLOS = "hello world\nhello again\n"

    def _f(self, name):
        d = "%s/%s" % (SCRATCH, name)
        (ROOT / d).mkdir(parents=True, exist_ok=True)
        (ROOT / d / "a.txt").write_text(self.TWO_HELLOS, encoding="utf-8")
        return d + "/a.txt"

    def test_replacing_the_first_occurrence_does_not_replace_all_of_them(self):
        f = self._f("ed1")
        result = _solve("Replace the first 'hello' with 'goodbye' in the file %s" % f)
        # Refused, and the reason is not caution for its own sake.  The bytes the
        # sentence asks for are producible -- `0,/hello/s|hello|goodbye|` gives
        # exactly 'goodbye world\\nhello again\\n' -- but nothing can certify
        # them: written back, the re-run finds the NEXT hello and cannot
        # reproduce the answer; not written back, the file still holds both while
        # the report says it was done; with -i, the file that would confirm the
        # promise is the one the command consumed.  This is the same shape as the
        # deletion-by-position refusal.  What is asserted here is the direction:
        # a refusal leaves the file exactly as it was.
        self.assertFalse(_verified(result),
                         "certified a replacement nothing can check: %r" % _stdout(result))
        self.assertEqual(self.TWO_HELLOS, (ROOT / f).read_text(encoding="utf-8"))
        # And the specific wrong answer this prevents: the global form, which is
        # what main bound, replaces both.
        self.assertEqual(2, self.TWO_HELLOS.count("hello"))

    def test_removing_the_lines_that_contain_a_value_keeps_the_other_lines(self):
        f = self._f("ed2")
        result = _solve("Remove the lines containing 'again' from the file %s" % f)
        self.assertTrue(_verified(result), result.get("status"))
        # A line removal is a filter here -- the kept lines come back and the file
        # is left alone, the convention pinned for the duplicate form.
        self.assertEqual("hello world\n", _stdout(result))
        self.assertEqual(self.TWO_HELLOS, (ROOT / f).read_text(encoding="utf-8"),
                         "a filter must not rewrite the file")

    def test_the_same_sentence_without_the_removal_verb_still_selects(self):
        # The pin on the other side of the inversion: a question about the lines
        # that CONTAIN a value must not grow a -v it did not ask for.
        f = self._f("ed3")
        self.assertEqual("hello again\n", _stdout(_solve(
            "the lines in the file %s that contain 'again'" % f)))
        self.assertEqual("hello world\n", _stdout(_solve(
            "the lines in the file %s that do not contain 'again'" % f)))

    def test_adding_to_the_beginning_is_the_mirror_of_adding_to_the_end(self):
        # One pair of opposites.  Only one half was served, and the difference was
        # a preposition: the append trigger has always been "(to|at) the end"
        # while the prepend gate admitted neither the verb "add" nor "to the
        # beginning".
        for name, goal, want in (
                ("ed4a", "Add the text 'top' to the beginning of the file %s",
                 "top\n" + "hello world\nhello again\n"),
                ("ed4b", "Add the text 'top' at the start of the file %s",
                 "top\n" + "hello world\nhello again\n"),
                ("ed4c", "Add the text 'top' to the top of the file %s",
                 "top\n" + "hello world\nhello again\n"),
                ("ed4d", "Add the text 'end' to the end of the file %s",
                 "hello world\nhello again\n" + "end\n")):
            f = self._f(name)
            result = _solve(goal % f)
            self.assertTrue(_verified(result), "%s -> %s" % (goal, result.get("status")))
            self.assertEqual(want, (ROOT / f).read_text(encoding="utf-8"), goal)

    def test_replacing_every_occurrence_still_rewrites_the_file(self):
        # The sibling that already worked, pinned so narrowing "first" did not
        # take the global form with it.
        f = self._f("ed5")
        result = _solve("Replace every 'hello' with 'goodbye' in the file %s" % f)
        self.assertTrue(_verified(result), result.get("status"))
        self.assertEqual("goodbye world\ngoodbye again\n",
                         (ROOT / f).read_text(encoding="utf-8"))

    def test_an_insert_that_states_no_position_is_still_refused(self):
        # Pinned before this change and pinned again: `insert` does not say where,
        # so serving it as a prepend would put the line somewhere the sentence
        # never named.  Widening the gate to `add|put|place` must not reopen it.
        f = self._f("ed6")
        result = _solve("Insert the text 'hello' into the file %s" % f)
        self.assertFalse(_verified(result), _stdout(result))
        self.assertEqual(self.TWO_HELLOS, (ROOT / f).read_text(encoding="utf-8"))

    def test_a_reading_of_the_file_still_does_not_write_to_it(self):
        # The write-back is gated on the sentence asking for a change.  A request
        # to be SHOWN something must leave the file alone even when the script it
        # binds would rewrite it.
        f = self._f("ed7")
        result = _solve("Show the contents of the file %s in upper case" % f)
        self.assertTrue(_verified(result), result.get("status"))
        self.assertEqual("HELLO WORLD\nHELLO AGAIN\n", _stdout(result))
        self.assertEqual(self.TWO_HELLOS, (ROOT / f).read_text(encoding="utf-8"))


class TestThePlainestWordForAConceptIsInTheSameListAsItsSynonyms(unittest.TestCase):
    """A certified wrong answer that survived a fix written for the same defect.

    This repository already found and fixed this lie once.  The comment sitting
    above the rule reads:

        `wc -l` counts every line the file holds, so "How many unique lines are
        in the file X" was certified with 6 on a file whose distinct set is 3,
        and "How many duplicate lines" with 6 where the answer is 2.

    The rule it introduced guards the words `unique|distinct|duplicate|repeated`.
    The plainest English word for the same idea -- "different" -- is in none of
    the three lists that name the concept, so on main e62d1f3:

        "how many DIFFERENT lines are in the file X"
            -> `wc -l`, certified
               PASS__RAW_GOAL_EXECUTED_AND_EXACT_SEMANTIC_ACCEPTANCE_VERIFIED,
               printed '5 ...' on a file whose distinct set is 3.

        "the DIFFERENT lines in the file X"
            -> refused, while "the unique lines" and "the distinct lines" were
               both served by the very rule that would have served it.

    A list of words is a list of phrasings, not a list of questions.
    """

    FIVE_LINES_THREE_DISTINCT = "apple\nbanana\napple\ncherry\nbanana\n"

    def _f(self, name, second=None):
        d = "%s/%s" % (SCRATCH, name)
        (ROOT / d).mkdir(parents=True, exist_ok=True)
        (ROOT / d / "a.txt").write_text(self.FIVE_LINES_THREE_DISTINCT,
                                        encoding="utf-8")
        if second is not None:
            (ROOT / d / "b.txt").write_text(second, encoding="utf-8")
        return d

    def test_a_count_of_the_distinct_set_is_not_the_total_line_count(self):
        # The lie.  Five lines, three distinct.  The word "different" used to
        # fall through to `wc -l` and be certified as the answer.
        d = self._f("df1")
        result = _solve("how many different lines are in the file %s/a.txt" % d)
        self.assertFalse(_verified(result),
                         "certified a total line count as a count of the distinct "
                         "set: %r" % _stdout(result))
        out = _stdout(result) or ""
        self.assertNotIn("5", out.split()[:1],
                         "the total line count was handed back as the answer")

    def test_the_three_synonyms_of_one_question_bind_one_operation(self):
        # One question, three ways of writing it.  Before the fix only two were
        # served and the third was refused, so the plainest form was the worst
        # served of the three.
        seen = []
        for name, word in (("df2a", "unique"), ("df2b", "distinct"),
                           ("df2c", "different")):
            d = self._f(name)
            result = _solve("the %s lines in the file %s/a.txt" % (word, d))
            self.assertTrue(_verified(result), "%s -> %s" % (word, result.get("status")))
            seen.append(_stdout(result))
        self.assertEqual(["apple\nbanana\ncherry\n"] * 3, seen)
        # And the opposite is asserted too: this is the DISTINCT set, not the file.
        self.assertNotEqual(self.FIVE_LINES_THREE_DISTINCT, seen[0])

    def test_the_plain_count_a_file_has_is_still_served(self):
        # `wc -l` really does measure this.  Narrowing the distinct-set count must
        # not take the honest count with it.
        d = self._f("df3")
        result = _solve("how many lines are in the file %s/a.txt" % d)
        self.assertTrue(_verified(result), result.get("status"))
        self.assertEqual("5", (_stdout(result) or "").split()[0])

    def test_removal_of_the_repeats_is_still_served(self):
        # The pinned sibling: asking for what is left once the repeats are gone IS
        # the distinct set, and it is a filter.
        d = self._f("df4")
        result = _solve("Remove the duplicate lines from the file %s/a.txt" % d)
        self.assertTrue(_verified(result), result.get("status"))
        self.assertEqual("apple\nbanana\ncherry\n", _stdout(result))
        self.assertEqual(self.FIVE_LINES_THREE_DISTINCT,
                         (ROOT / d / "a.txt").read_text(encoding="utf-8"))

    def test_different_as_an_adjective_keeps_its_own_answer(self):
        # "different" is an ordinary adjective.  Widening on the bare word would
        # hijack four sentences that were already correct; the arm is anchored to
        # "lines" AFTER the word, and each of these puts the noun before it.
        d = self._f("df5", second="apple\nfig\n")
        a, b = "%s/a.txt" % d, "%s/b.txt" % d
        for goal in ("Write the unique lines of the file %s to a different file %s/c.txt"
                     % (a, d),
                     "Are the lines in the file %s different from the file %s" % (a, b),
                     "Show the lines in the file %s that are different from the file %s" % (a, b),
                     "Copy the file %s to a different name %s/c.txt" % (a, d)):
            self.assertTrue(_verified(_solve(goal)), "hijacked: %s" % goal)
        # And the two-file comparison still compares, rather than deduplicating.
        cmp_result = _solve("Are the lines in the file %s different from the file %s"
                            % (a, b))
        self.assertNotEqual("apple\nbanana\ncherry\n", _stdout(cmp_result),
                            "the two-file question was answered with a deduplicated set")


class TestANegationAndALongFilenameAreNotSilentlyDropped(unittest.TestCase):
    """Two certified wrong answers, found by a 28-row census of everyday requests.

    Both were certified with the strongest verdict the system has, and neither
    destroyed anything -- which is why they survived.

    (1) "the lines in the file X that are NOT BLANK" bound `grep '^$'` with no
        `-v` and returned the two blank lines: the exact opposite of the
        question.  So did "the NON-BLANK lines".  Four phrasings of two opposite
        questions bound one command, because the blank arm inverted for a REMOVAL
        verb and for nothing else.

    (2) "Make the file X all upper case" printed the upper-cased text, left the
        file lower case, and was certified.  The rule that decides whether to
        write the file back is `make ... upper` with TWENTY CHARACTERS allowed
        between the words -- and a path sits between them.  Measured: with the
        name `a.txt` it wrote the file; with `notes.txt` it did not.  The same
        question, answered by how long the filename is.
    """

    NOTED = "# Title\n\nbody line\n\nlast\n"      # 5 lines: 3 non-blank, 2 blank
    LOWER = "apple\nbanana\n"

    def _f(self, name, content):
        d = "%s/%s" % (SCRATCH, name)
        (ROOT / d).mkdir(parents=True, exist_ok=True)
        (ROOT / d / "notes.md").write_text(content, encoding="utf-8")
        return d + "/notes.md"

    def test_the_lines_that_are_not_blank_are_not_the_blank_lines(self):
        for word in ("that are not blank", "that are not empty"):
            f = self._f("nb1", self.NOTED)
            result = _solve("the lines in the file %s %s" % (f, word))
            self.assertTrue(_verified(result), "%s -> %s" % (word, result.get("status")))
            self.assertEqual("# Title\nbody line\nlast\n", _stdout(result), word)
        # And the hyphenated form, which is one word and not a window at all.
        f = self._f("nb2", self.NOTED)
        self.assertEqual("# Title\nbody line\nlast\n",
                         _stdout(_solve("the non-blank lines in the file %s" % f)))

    def test_the_blank_lines_are_still_the_blank_lines(self):
        # The pin on the other side of the inversion: asking FOR the blank lines
        # must not grow a -v it did not ask for.
        for word in ("blank", "empty"):
            f = self._f("nb3", self.NOTED)
            result = _solve("the %s lines in the file %s" % (word, f))
            self.assertTrue(_verified(result), result.get("status"))
            self.assertEqual("\n\n", _stdout(result), word)

    def test_removing_the_blank_lines_is_still_a_filter(self):
        f = self._f("nb4", self.NOTED)
        result = _solve("Remove the blank lines from the file %s" % f)
        self.assertTrue(_verified(result), result.get("status"))
        self.assertEqual("# Title\nbody line\nlast\n", _stdout(result))
        self.assertEqual(self.NOTED, (ROOT / f).read_text(encoding="utf-8"),
                         "a filter must not rewrite the file")

    def test_making_a_file_upper_case_changes_the_file(self):
        f = self._f("up1", self.LOWER)
        result = _solve("Make the file %s all upper case" % f)
        self.assertTrue(_verified(result), result.get("status"))
        self.assertEqual("APPLE\nBANANA\n", (ROOT / f).read_text(encoding="utf-8"),
                         "the sentence said MAKE THE FILE, and the file did not change")

    def test_a_short_name_and_a_long_name_get_the_same_answer(self):
        # The defect in one assertion.  The old rule allowed twenty characters
        # between "make" and "upper", so the answer depended on the filename.
        short = "a.txt"
        long_ = "a-filename-long-enough-to-break-the-window.txt"
        for name in (short, long_):
            d = "%s/up2" % SCRATCH
            (ROOT / d).mkdir(parents=True, exist_ok=True)
            (ROOT / d / name).write_text(self.LOWER, encoding="utf-8")
            result = _solve("Make the file %s/%s all upper case" % (d, name))
            self.assertTrue(_verified(result), "%s -> %s" % (name, result.get("status")))
            self.assertEqual("APPLE\nBANANA\n",
                             (ROOT / d / name).read_text(encoding="utf-8"),
                             "the filename decided the answer: %s" % name)

    def test_showing_a_file_in_upper_case_still_does_not_write(self):
        # The pin that must not move.  A request to be SHOWN something puts its
        # answer on stdout and leaves the file alone, even though the script it
        # binds would rewrite it.
        f = self._f("up3", self.LOWER)
        result = _solve("Show the contents of the file %s in upper case" % f)
        self.assertTrue(_verified(result), result.get("status"))
        self.assertEqual("APPLE\nBANANA\n", _stdout(result))
        self.assertEqual(self.LOWER, (ROOT / f).read_text(encoding="utf-8"))

    def test_a_file_named_after_a_verb_is_not_a_request_to_change_it(self):
        # Masking the path before reading the verbs cuts both ways: a file called
        # `convert.md` is an operand, and its name must not turn a reading into a
        # rewrite.
        d = "%s/up4" % SCRATCH
        (ROOT / d).mkdir(parents=True, exist_ok=True)
        (ROOT / d / "convert.md").write_text(self.LOWER, encoding="utf-8")
        result = _solve("Show the contents of the file %s/convert.md" % d)
        self.assertTrue(_verified(result), result.get("status"))
        self.assertEqual(self.LOWER, (ROOT / d / "convert.md").read_text(encoding="utf-8"),
                         "the filename made a reading into a rewrite")


class TestTheOrderARequestNamesIsNotTheDefaultOrder(unittest.TestCase):
    """Three requests said WHICH order.  All three were certified without it.

    "Sort the file X in reverse order" returned the forward order.
    "Sort the file X numerically" returned the lexicographic one, 100 ahead of 2.
    "Sort the file X and remove duplicates" fell past the `-u` rule to the `rm`
    rule and DELETED THE FILE -- certified as an exact semantic answer.

    The word that names the order, and the thing the verb acts on, are both part
    of the request.  A default that ignores them is a wrong answer, and a wrong
    answer that destroys the input is the worst kind: there is nothing left to
    ask again.
    """

    LINES = "apple\nbanana\napple\ncherry\nbanana\n"
    NUMS = "10\n9\n100\n2\n33\n"

    def _file(self, content, name="a1.txt"):
        root = ROOT / SCRATCH
        shutil.rmtree(root, ignore_errors=True)
        root.mkdir(parents=True, exist_ok=True)
        rel = "%s/%s" % (SCRATCH, name)
        (ROOT / rel).write_text(content, encoding="utf-8")
        return rel

    def test_reverse_order_is_the_reverse_order(self):
        f = self._file(self.LINES)
        r = _solve("Sort the file %s in reverse order" % f)
        self.assertTrue(_verified(r))
        self.assertEqual(_stdout(r), "cherry\nbanana\nbanana\napple\napple\n")

    def test_numeric_order_puts_two_before_one_hundred(self):
        f = self._file(self.NUMS, "n.txt")
        r = _solve("Sort the file %s numerically" % f)
        self.assertTrue(_verified(r))
        self.assertEqual(_stdout(r), "2\n9\n10\n33\n100\n")

    def test_removing_duplicates_does_not_remove_the_file(self):
        f = self._file(self.LINES)
        r = _solve("Sort the file %s and remove duplicates" % f)
        self.assertTrue(_verified(r))
        self.assertEqual(_stdout(r), "apple\nbanana\ncherry\n")
        self.assertTrue((ROOT / f).exists(),
                        "the request was to remove DUPLICATES, not the file")
        self.assertEqual((ROOT / f).read_text(encoding="utf-8"), self.LINES)

    # --- and the neighbours that must not move to make those three true.
    def test_a_file_actually_named_duplicates_is_still_removed(self):
        f = self._file("keep me\n", "duplicates.txt")
        r = _solve("Remove the file %s" % f)
        self.assertFalse((ROOT / f).exists(),
                         "a file NAMED duplicates.txt is the object, not a set")

    def test_reversing_the_lines_is_still_tac_not_a_sorted_reverse(self):
        f = self._file(self.LINES)
        r = _solve("Reverse the lines of the file %s" % f)
        self.assertTrue(_verified(r))
        self.assertEqual(_stdout(r), "banana\ncherry\napple\nbanana\napple\n")

    def test_the_unique_lines_still_bind_sort_dash_u(self):
        f = self._file(self.LINES)
        r = _solve("Show the unique lines of the file %s" % f)
        self.assertTrue(_verified(r))
        self.assertEqual(_stdout(r), "apple\nbanana\ncherry\n")

    def test_a_plain_sort_still_carries_no_ordering_flag(self):
        f = self._file(self.LINES)
        r = _solve("Sort the file %s" % f)
        self.assertTrue(_verified(r))
        self.assertEqual(_stdout(r), "apple\napple\nbanana\nbanana\ncherry\n")


class TestAnUnquotedValueIsTheSameValueAsAQuotedOne(unittest.TestCase):
    """Punctuation is not part of the question.

    "the lines containing apple" bound `cat` and returned the WHOLE FILE for a
    question about two of its lines, certified.  The quoted form of the same
    sentence bound `fgrep apple` and returned the two.  "How many lines contain
    apple" bound `wc -l` and answered 5 where two lines hold the word.

    Both arms already did the whole job once they held one value; both read it
    from `_quoted_values`, so a sentence that stated its value bare arrived
    holding none.
    """

    LINES = "apple pie\nbanana split\napple tart\n\ncherry\n"

    def _file(self, content, name="a1.txt"):
        root = ROOT / SCRATCH
        shutil.rmtree(root, ignore_errors=True)
        root.mkdir(parents=True, exist_ok=True)
        rel = "%s/%s" % (SCRATCH, name)
        (ROOT / rel).write_text(content, encoding="utf-8")
        return rel

    def test_the_lines_containing_an_unquoted_value(self):
        f = self._file(self.LINES)
        r = _solve("Show the lines containing apple in the file %s" % f)
        self.assertTrue(_verified(r))
        self.assertEqual(_stdout(r), "apple pie\napple tart\n")

    def test_the_lines_that_contain_an_unquoted_value(self):
        f = self._file(self.LINES)
        r = _solve("Show the lines in the file %s that contain apple" % f)
        self.assertTrue(_verified(r))
        self.assertEqual(_stdout(r), "apple pie\napple tart\n")

    def test_how_many_lines_contain_an_unquoted_value(self):
        f = self._file(self.LINES)
        r = _solve("How many lines contain apple in the file %s" % f)
        self.assertTrue(_verified(r))
        self.assertEqual(_stdout(r).split()[0], "2")

    def test_how_many_empty_lines_counts_the_empty_ones(self):
        f = self._file(self.LINES)
        r = _solve("How many empty lines are in the file %s" % f)
        self.assertTrue(_verified(r))
        self.assertEqual(_stdout(r).split()[0], "1")

    # --- pins: the quoted forms, and the sentences that must not be hijacked.
    def test_the_quoted_form_still_answers_the_same(self):
        f = self._file(self.LINES)
        r = _solve("Show the lines containing 'apple' in the file %s" % f)
        self.assertTrue(_verified(r))
        self.assertEqual(_stdout(r), "apple pie\napple tart\n")

    def test_a_file_whose_name_is_the_value_keeps_its_path(self):
        f = self._file(self.LINES, "apple.txt")
        r = _solve("Show the lines containing apple in the file %s" % f)
        self.assertTrue(_verified(r))
        self.assertEqual(_stdout(r), "apple pie\napple tart\n")

    def test_a_plain_line_count_is_still_a_plain_line_count(self):
        f = self._file(self.LINES)
        r = _solve("How many lines are in the file %s" % f)
        self.assertTrue(_verified(r))
        self.assertEqual(_stdout(r).split()[0], "5")

    def test_a_file_named_blank_is_not_asked_how_many_lines_are_empty(self):
        f = self._file("apple\n\n\npear\n", "blank.txt")
        r = _solve("How many lines are in the file %s" % f)
        self.assertTrue(_verified(r))
        self.assertEqual(_stdout(r).split()[0], "4")

    def test_the_blank_lines_themselves_are_still_returned(self):
        f = self._file(self.LINES)
        r = _solve("Show the blank lines in the file %s" % f)
        self.assertTrue(_verified(r))
        self.assertEqual(_stdout(r), "\n")

    def test_a_regex_pattern_is_still_not_a_literal(self):
        f = self._file(self.LINES)
        r = _solve("Show the lines in the file %s matching 'ap.le'" % f)
        self.assertTrue(_verified(r))
        self.assertEqual(_stdout(r), "apple pie\napple tart\n")


class TestAWordThatQualifiesAFilterMustReachTheFlags(unittest.TestCase):
    """A word that says HOW to match is part of the question.

    "the lines containing APPLE ... ignoring case" bound `fgrep APPLE`, matched
    nothing in a file that holds "apple pie", and was CERTIFIED returning an
    empty answer.  The words were read, decided nothing, and were dropped.

    And a filter whose value cannot be recovered must be refused.  "the lines
    containing text" states "text" as often as an ordinary noun as a value, so
    refusing to guess it is right -- but the sentence then fell to the leftover
    `cat` row and was certified with the WHOLE FILE, an answer to a question no
    line of that file asks.
    """

    LINES = "apple pie\nbanana split\napple tart\n\ncherry\n"

    def _file(self, content, name="a1.txt"):
        root = ROOT / SCRATCH
        shutil.rmtree(root, ignore_errors=True)
        root.mkdir(parents=True, exist_ok=True)
        rel = "%s/%s" % (SCRATCH, name)
        (ROOT / rel).write_text(content, encoding="utf-8")
        return rel

    def test_ignoring_case_reaches_the_command(self):
        f = self._file(self.LINES)
        r = _solve("Show the lines containing APPLE in the file %s ignoring case" % f)
        self.assertTrue(_verified(r))
        self.assertEqual(_stdout(r), "apple pie\napple tart\n")

    def test_case_insensitive_is_the_same_request(self):
        f = self._file(self.LINES)
        r = _solve("Show the lines containing APPLE in the file %s case-insensitive" % f)
        self.assertTrue(_verified(r))
        self.assertEqual(_stdout(r), "apple pie\napple tart\n")

    def test_case_is_still_significant_when_nothing_says_otherwise(self):
        f = self._file(self.LINES)
        r = _solve("Show the lines containing APPLE in the file %s" % f)
        self.assertTrue(_verified(r))
        self.assertEqual(_stdout(r), "")

    def test_a_value_that_cannot_be_recovered_is_refused_not_the_whole_file(self):
        f = self._file(self.LINES)
        r = _solve("Show the lines containing text in the file %s" % f)
        self.assertNotEqual(_stdout(r), self.LINES,
                            "the whole file is not an answer to 'which lines hold text'")

    # --- pins: the sentences the narrower `cat` row must keep serving.
    def test_reading_a_file_still_reads_it(self):
        f = self._file(self.LINES)
        r = _solve("Read the file %s" % f)
        self.assertTrue(_verified(r))
        self.assertEqual(_stdout(r), self.LINES)

    def test_the_contents_of_a_file_still_reads_it(self):
        f = self._file(self.LINES)
        r = _solve("Show the contents of the file %s" % f)
        self.assertTrue(_verified(r))
        self.assertEqual(_stdout(r), self.LINES)

    def test_a_file_whose_name_says_containing_still_reads_it(self):
        f = self._file("the report\n", "report.txt")
        r = _solve("Show the contents of the file %s containing the report" % f)
        self.assertTrue(_verified(r))
        self.assertEqual(_stdout(r), "the report\n")

    def test_showing_the_lines_of_a_file_still_reads_it(self):
        f = self._file(self.LINES)
        r = _solve("Show the lines of the file %s" % f)
        self.assertTrue(_verified(r))
        self.assertEqual(_stdout(r), self.LINES)

    def test_a_bare_value_still_matches_without_the_case_flag(self):
        f = self._file(self.LINES)
        r = _solve("Show the lines containing apple in the file %s" % f)
        self.assertTrue(_verified(r))
        self.assertEqual(_stdout(r), "apple pie\napple tart\n")

    def test_line_numbers_still_carry_their_numbers(self):
        f = self._file(self.LINES)
        r = _solve("Show the line numbers in the file %s containing apple" % f)
        self.assertTrue(_verified(r))
        self.assertEqual(_stdout(r), "1:apple pie\n3:apple tart\n")


class TestAListWrittenTwiceIsAListEditedOnce(unittest.TestCase):
    """The nouns that name something inside a file were written twice.

    Both copies were byte-identical across 37 nouns, which is exactly how a list
    comes to be edited in one place only.  `duplicate` was in NEITHER copy, so
    the fix to the `rm` row's own duplicates clause left its sibling deleting:

        "Remove the duplicates from every file in the directory D"
          -> `rm one.txt two.txt`   THE DIRECTORY CAME BACK EMPTY.  CERTIFIED.

    A set expansion turns one wrong deletion into a whole directory of them,
    which is the reason the guard exists at all.
    """

    CONTENT = "apple\nbanana\napple\n"

    def _set(self):
        root = ROOT / SCRATCH
        shutil.rmtree(root, ignore_errors=True)
        (root / "set").mkdir(parents=True, exist_ok=True)
        for n in ("one.txt", "two.txt"):
            (root / "set" / n).write_text(self.CONTENT, encoding="utf-8")
        (root / "a.txt").write_text(self.CONTENT, encoding="utf-8")
        (root / "duplicates.txt").write_text(self.CONTENT, encoding="utf-8")
        return "%s/set" % SCRATCH, "%s/a.txt" % SCRATCH

    def _argv(self, result):
        m = re.findall(r'"argv"\s*:\s*(\[[^\]]*\])', json.dumps(result, default=str))
        return " ".join(json.loads(m[0])) if m else "NONE"

    def test_removing_duplicates_from_a_set_does_not_delete_the_set(self):
        d, _ = self._set()
        r = _solve("Remove the duplicates from every file in the directory %s" % d)
        self.assertEqual(sorted(p.name for p in (ROOT / d).iterdir()),
                         ["one.txt", "two.txt"],
                         "the request was to remove DUPLICATES, not every file")
        self.assertNotIn("rm ", self._argv(r))

    def test_removing_repeats_from_a_set_does_not_delete_the_set(self):
        d, _ = self._set()
        r = _solve("Remove the repeats from every file in the directory %s" % d)
        self.assertEqual(sorted(p.name for p in (ROOT / d).iterdir()),
                         ["one.txt", "two.txt"])
        self.assertNotIn("rm ", self._argv(r))

    def test_the_noun_list_is_written_once(self):
        src = (ROOT / "canonical/runtime/composer_route_v1.py").read_text(encoding="utf-8")
        self.assertEqual(src.count("permission|permissions|bit|bits"), 1,
                         "the list is duplicated again; the two copies will drift")
        self.assertIn("duplicate", _binder._INSIDE_THE_FILE_NOUNS)

    # --- pins: the deletions and refusals that must not move.
    def test_sorting_and_removing_duplicates_still_sorts(self):
        _, f = self._set()
        r = _solve("Sort the file %s and remove duplicates" % f)
        self.assertTrue(_verified(r))
        self.assertEqual(_stdout(r), "apple\nbanana\n")
        self.assertTrue((ROOT / f).exists())

    def test_a_file_named_duplicates_is_still_removed(self):
        _, _f = self._set()
        target = "%s/duplicates.txt" % SCRATCH
        _solve("Remove the file %s" % target)
        self.assertFalse((ROOT / target).exists())

    def test_removing_the_duplicate_lines_still_sorts(self):
        _, f = self._set()
        r = _solve("Remove the duplicate lines from the file %s" % f)
        self.assertTrue(_verified(r))
        self.assertEqual(_stdout(r), "apple\nbanana\n")

    def test_removing_the_first_line_is_still_refused(self):
        _, f = self._set()
        _solve("Remove the first line from the file %s" % f)
        self.assertEqual((ROOT / f).read_text(encoding="utf-8"), self.CONTENT)

    def test_removing_the_read_permission_is_still_refused(self):
        _, f = self._set()
        _solve("Remove the read permission from the file %s" % f)
        self.assertEqual((ROOT / f).read_text(encoding="utf-8"), self.CONTENT)

    def test_deleting_a_whole_directory_still_deletes_it(self):
        d, _ = self._set()
        _solve("Delete the directory %s" % d)
        self.assertFalse((ROOT / d).exists())


class TestTwoValuesJoinedByOrAreOnePattern(unittest.TestCase):
    """An alternation stated in English is an alternation.

    All four phrasings of one question were wrong.  "the lines containing apple
    or banana" bound `fgrep apple` and dropped every banana line, certified.
    The quoted form quoted two values, so the arm that requires exactly one
    refused it.  And "matching 'apple|banana'" bound `grep` -- BRE, where `|` is
    a LITERAL character -- matched nothing in a file holding both words, and was
    certified with an empty answer.

    `egrep` was already a rule in this module and its exit status was already
    declared an answer.  This is wiring, not new policy.
    """

    LINES = "apple pie\nbanana split\napple tart\n\ncherry\n"
    BOTH = "apple pie\nbanana split\napple tart\n"

    def _file(self, content=None, name="a1.txt"):
        root = ROOT / SCRATCH
        shutil.rmtree(root, ignore_errors=True)
        root.mkdir(parents=True, exist_ok=True)
        rel = "%s/%s" % (SCRATCH, name)
        (ROOT / rel).write_text(content or self.LINES, encoding="utf-8")
        return rel

    def test_two_values_joined_by_or_are_one_pattern(self):
        f = self._file()
        r = _solve("Show the lines containing apple or banana in the file %s" % f)
        self.assertTrue(_verified(r))
        self.assertEqual(_stdout(r), self.BOTH)

    def test_the_quoted_form_of_the_same_alternative(self):
        f = self._file()
        r = _solve("Show the lines containing 'apple' or 'banana' in the file %s" % f)
        self.assertTrue(_verified(r))
        self.assertEqual(_stdout(r), self.BOTH)

    def test_an_alternative_the_sentence_calls_a_regex_reaches_egrep(self):
        # The module's design is three-way and pinned elsewhere: `fgrep` when the
        # sentence calls the text literal, `grep` when it says "matching", `egrep`
        # when it says regex.  So the supported way to state an alternation is to
        # call it a regex -- and that is asserted here, because it is the phrasing
        # a caller must use once "or" is the only English form the filter arm
        # builds an alternation from.  "matching 'apple|banana'" stays BRE by
        # design and is recorded as open, not silently re-dialected.
        f = self._file()
        r = _solve("Search the file %s for the regex 'apple|banana'" % f)
        self.assertTrue(_verified(r))
        self.assertEqual(_stdout(r), self.BOTH)

    def test_a_pattern_the_sentence_only_calls_matching_stays_bre(self):
        f = self._file()
        r = _solve("Show the lines in the file %s matching 'ap.le'" % f)
        self.assertTrue(_verified(r))
        self.assertEqual(_stdout(r), "apple pie\napple tart\n")

    # --- pins: the dialect change must be inert where a dot is all there is.
    def test_a_regex_with_only_a_dot_is_unchanged(self):
        f = self._file()
        r = _solve("Show the lines in the file %s matching 'ap.le'" % f)
        self.assertTrue(_verified(r))
        self.assertEqual(_stdout(r), "apple pie\napple tart\n")

    def test_a_negated_regex_still_inverts(self):
        f = self._file()
        r = _solve("Show the lines in the file %s not matching 'ap.le'" % f)
        self.assertTrue(_verified(r))
        self.assertEqual(_stdout(r), "banana split\n\ncherry\n")

    def test_a_single_value_is_still_a_literal_match(self):
        f = self._file()
        r = _solve("Show the lines containing apple in the file %s" % f)
        self.assertTrue(_verified(r))
        self.assertEqual(_stdout(r), "apple pie\napple tart\n")

    def test_a_single_quoted_value_is_still_a_literal_match(self):
        f = self._file()
        r = _solve("Show the lines containing 'apple' in the file %s" % f)
        self.assertTrue(_verified(r))
        self.assertEqual(_stdout(r), "apple pie\napple tart\n")

    def test_ignoring_case_still_reaches_the_command(self):
        f = self._file()
        r = _solve("Show the lines containing APPLE in the file %s ignoring case" % f)
        self.assertTrue(_verified(r))
        self.assertEqual(_stdout(r), "apple pie\napple tart\n")

    def test_a_count_is_still_a_count(self):
        f = self._file()
        r = _solve("How many lines contain apple in the file %s" % f)
        self.assertTrue(_verified(r))
        self.assertEqual(_stdout(r).split()[0], "2")

    def test_the_blank_lines_still_come_back(self):
        f = self._file()
        r = _solve("Show the blank lines in the file %s" % f)
        self.assertTrue(_verified(r))
        self.assertEqual(_stdout(r), "\n")

    def test_a_value_that_cannot_be_recovered_is_still_refused(self):
        f = self._file()
        r = _solve("Show the lines containing text in the file %s" % f)
        self.assertNotEqual(_stdout(r), self.LINES)
