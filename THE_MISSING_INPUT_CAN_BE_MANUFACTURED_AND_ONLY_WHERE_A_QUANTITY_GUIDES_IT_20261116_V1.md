# The missing input can be manufactured — and only where a quantity guides it

Round 17. Branch `arena/4a06d20c-brain`, from `cabbc10b`.

## What round 16 left, and the name the field uses for it

Round 16 closed the assertion half of the question by measurement: **0 of 8** unpinned behavioural parts of real
fixes could be pinned from the tests' own inputs, because a suite that passes is precisely the set of
observations already made. The missing thing is therefore not an assertion. It is an **input that reaches the
changed line**.

The tree had three organs near this and none of them generates a reaching input:
`distinguishing_projection_v1` chooses *what to observe*, `whitebox_introspector_and_trace_synthesizer_v1`
harvests obligations that *already exist*, `interventional_goal_v1` derives goals from interventions. Searching
the web under the correct name found the answer immediately: **directed greybox fuzzing**. WAFLGO (USENIX'24)
directs generation at the *change sites of a commit*; AFLGo and ColorGo score seeds by distance to a target
site; Driller and QSYM pair mutation with concolic solving when mutation stalls. Their shared conclusion is the
one that governs this round: undirected iteration is hopeless, and **distance to the target is what makes the
search converge**.

So the honest minimal faithful scale is: seeds from the human's own tests, a mutation grammar, execution
feedback from the target file, retention by distance, then a fix-versus-mutant comparison, and an assertion only
if it is green on the fix and red on the revert.

## Three bugs in my own instrument, found before any number was believed

This is the part that matters, because each of the three would have produced a *plausible* false number.

1. **I aimed at the `if` header instead of the guarded body.** `if len(text) > 12:` executes on *every* call, so
   every input "reached" the target and the instrument reported `REACHED_NO_DIFFERENCE` for a guard it had never
   triggered. The target must be the deepest statement the condition guards — the last added line.
2. **I measured distance between line numbers.** In a six-line function every call is one line from the target,
   so the distance never improved, the corpus froze on the seed, and the doubling chain that would have produced
   a 13-character string never started. The gradient must be over *inputs*. The only one available without
   semantics is the quantity the changed block compares against, read off the artifact: `12` becomes
   `|len(text) - 12|`, and longer strings are retained.
3. **The receipt stored the last line of the assertion, not the assertion.** The claim "green on the fix, red on
   the revert" was therefore not checkable from the receipt at all — the `pytest.raises(..., match=...)` wrapper
   was missing. My own first independent reproduction failed because of it, and the pins looked weaker than they
   are.

A fourth correction is a scope refusal rather than a bug: a part that only **removes** code adds no line, so
there is no line to reach. Those are reported `REFUSED__PART_REMOVES_CODE`, never as a failed search. They are
6 of 78 behavioural parts across the corpus, so refusing them costs little and keeps the denominator honest.

## The fire proof, and the honesty proof

The claim of this round is *generation, not recovery*, so the fixture must be one whose changed line is
reachable only by an input no test supplies. A guard `if len(text) > 12: raise ValueError("too long")` with a
suite that asserts only the exception's type is green on the revert; the search finds `len > 12` from the
artifact's own quantity and the synthesised assertion is green on the fix and red on the revert.

The honesty proof is the mirror image: a guard that triggers on a string containing characters the tests and
the pre-fix module never mention must come back **`NOT_REACHED`** with its executions spent and its closest
distance — a search that fails reports a failed search, never an absence of behaviour. Both are in
`canonical/tests/test_reach_the_changed_site_v1.py` (7 tests).

## What the real corpus says

17 real fixes prepared from the committed manifest (1 `REFUSED__CONTROL_BROKEN`), **8** unpinned behavioural
parts — the same denominator round 16 measured at 0 of 8 — in **693** executions:

| state | parts |
|---|---|
| reached by generated input **and pinned and verified** | **2** |
| reached, no observable difference | 0 |
| searched, never reached | 4 |
| refused: the test file makes no literal call | 1 |
| refused: the part removes code | 1 |

Certified share of round 15's 42 behavioural parts: **0.714 → 0.762**. Of the 6 parts that could be searched,
2 were won: **one third**.

The two pins are both error-message differences in `tomli` at `31c85a18` — the class round 16 proved is
pinnable but that no test asserted:

```python
with pytest.raises(_exc('TOMLDecodeError'), match=re.escape('Expected "\'" (at end of document)')):
    _m.loads("\n'")

with pytest.raises(_exc('TOMLDecodeError'), match=re.escape("Illegal character '\n' (at line 2, column 3)")):
    _m.loads('\n"#\n"#')
```

Neither input appears in the human's tests, and neither is derived from the fix's message. Both were generated
by mutation from the tests' own literal arguments. Verified independently in freshly built trees, with the
assertion text copied from the receipt and plain `pytest` judging: **fixed → 2 passed, defective → 2 failed.**
Notably neither pin had a numeric hint: the gradient was empty and the mutation grammar alone found them,
because a malformed string lands on the error path.

## Why the other four were not reached — the answer to the standing question

The four failures are not random. Their conditions compare against **structure**, not quantity:

```
elif isinstance(state, dict) and state.keys() >= set(self.__slots__):
suffix_location(state, "End of line or end of document not found after a statement" ...
```

No integer, no length, no magnitude appears in the changed block; there is nothing in the artifact to build a
distance from. The published field solves exactly this by having a language model propose the trigger condition
(PBFuzz, CCS 2026; GapForge, Aug 2026 — both make the LLM's one pass load-bearing). That is the dependency this
project refuses, and without it execution feedback alone closes the loop only when the changed site sits near an
error the mutation grammar can stumble into.

So the answer to *"does instant learning solve all computer use?"* sharpens rather than changes. Three rounds
have now measured three different answers to "what is missing": not the action (rounds 15: 0.714 of the change
is already pinned by the human's suite), not the assertion (round 16: 0 of 8 recoverable), and not the input
*unconditionally* (round 17: 2 of 8, and both from the error-path class). What remains is the decision **which
input could reach which line** — reachability reasoning. An agent that has seen the most advanced coding action
once can copy the action; it still cannot say which input makes the new behaviour observable, and a suite it
writes without that decision asserts nothing new.

That is the single bottleneck: **reachability reasoning**, not parameter supply, not action supply, not the
verifier's strength. It is the one place where the field's state of the art is an inference over semantics, and
it is therefore the one place where "show it once" cannot help, because what has to be learned is not a
behaviour but a *consequence*.

## What this round does not claim

It does not claim the unpinned parts are pinnable. Four were not reached, two could not be searched at all, and
the certified share is 0.762, not 1. It does not claim the search is complete: the budget is 120 executions per
part, the corpus keeps 8 seeds, and the alphabet is the tests' and the pre-fix module's vocabulary only. It does
not claim independent verification: the two pins were re-checked in fresh trees with plain `pytest`, which is
reproduction, not an outside authority. Model calls 0, network calls 0, spend $0.

## Next

The four failures name the next organ precisely: a **reachability hypothesis** — a statement of the form "this
line executes only when this predicate over the input holds", proposed without a language model, checked by
execution, and rejected when execution contradicts it. The only honest source for such a hypothesis in this
tree's vocabulary is the *data-flow* from the test's literal through the changed block's comparisons, which is
static analysis over the artifact, not semantics over the world. Until that exists, the number stays at 2 of 8.
