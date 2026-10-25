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
import os

import shutil
import sys
import time
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
        ("Show the unique lines of the file {f}", ["uniq", "{f}"]),
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
        ("Show the first field of the file {f}", ["cut", "-f", "1", "{f}"]),
        ("Show the second column of the file {f}", ["cut", "-f", "2", "{f}"]),
        ("Cut field 3 from the file {f}", ["cut", "-f", "3", "{f}"]),
        ("Search the file {f} for the exact text 'a.c'", ["fgrep", "a.c", "{f}"]),
        # --- a byte comparison and a pattern search, each reached only by a
        #     sentence that SAYS which question it is asking.
        ("Compare the file {f} and {f} byte by byte", ["cmp", "{f}", "{f}"]),
        ("Compare the file {f} and {f} byte-for-byte", ["cmp", "{f}", "{f}"]),
        ("Check whether the file {f} and {f} are identical bytes", ["cmp", "{f}", "{f}"]),
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
        self.assertEqual(argv, ["cut", "-f", "2", path],
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
        """grep needs a pattern; a sentence that states none binds nothing."""
        self.assertIsNone(_argv("Search the file %s/a1.txt" % SCRATCH),
                          "invented a search pattern")
        self.assertIsNone(_argv("Find the lines in %s/a1.txt matching 'a' or 'b'"
                                % SCRATCH),
                          "guessed between two stated patterns")

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
        f = _fresh("apple\nbanana\napple\n")
        self.assertEqual(["uniq", f],
                         _cr._prose_argv("Remove the duplicate lines from the file %s" % f))
        self.assertTrue(_verified(_solve("Remove the duplicate lines from the file %s" % f)))
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
        # `uniq` takes one file.  The sentence names two, and the second is where
        # the result goes -- so it was refused for want of arity, which read as
        # "you gave me too many files" for a request that stated exactly enough.
        from canonical.runtime import composer_route_v1 as _cr
        # Adjacent duplicates, because that is all `uniq` removes -- writing the
        # fixture as apple/banana/apple and expecting two lines back was this
        # test being wrong about the program, not the program being wrong.
        a = _fresh("apple\napple\nbanana\n")
        c = "%s/c1.txt" % SCRATCH
        goal = "Write the unique lines of the file %s to the file %s" % (a, c)
        self.assertEqual(["uniq", a], _cr._prose_argv(goal))
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
        self.assertEqual(["cmp", a, b],
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



if __name__ == "__main__":
    unittest.main()
