# Verified skills do not compose just because each one verified

**2026-11-12.** Branch `arena/3778edad-brain`. Authority **NONE**. `truth.achieved` = `false`.

## What was measured

Two rules taught the ordinary way. Both are accepted:

```
teach A:  `x <= 10` -> `x < 10`      crystallized: True
teach B:  `x < 10`  -> `x <= 10`     crystallized: True

step 1: 'return x <= 10' -> 'return x < 10'
step 2: 'return x < 10'  -> 'return x <= 10'
started : 'return x <= 10'
ended   : 'return x <= 10'
NET CHANGE: none -- the second skill undid the first
```

**Both applications are individually correct. The sequence is a no-op.**

And `recall_and_apply_verified` cannot catch this. It verifies each candidate at each step,
and every step passes. The check is local; a local check cannot see a global revert.

This is the concrete reason a store of N verified skills says nothing about a sequence of 2 —
which is what "the most advanced coding agent" actually is: a sequence, not a single edit.

## What was added

`canonical/swe_kernel/skill_sequence_verify_v1.py`

`verify_sequence(source, rules)` applies the rules in order and reports per step whether it
changed anything, and whether it returned to a state the text had already been in:

| verdict | meaning |
|---|---|
| `PASS` | every step changed the text, and no step returned to an earlier state |
| `FAIL` | a step reverted to an earlier state — the sequence undoes itself |
| `NO_CHANGE` | a step did nothing, so a rule was counted that had no effect |
| `UNDEFINED` | empty sequence, or a rule that is not a rule |

`verify_all_pairs` checks every ordered pair and reports **interference witnesses** — the
smallest unit at which composition breaks. Measured on the pair above:

```
verdict: FAIL | reason: STEP_REVERTED_EARLIER_STATE:step2
  step 1: CHANGED
  step 2: REVERTED  (to_state_of_step: 0)
```

Exit 1 when a sequence fails or any pair interferes.

**A no-op is not a pass, and a revert is not a pass.** Those two sentences are the whole
module; without them the store reports "2 verified skills" for a rule that cancels itself.

## Tests — 9, green

The first asserts the revert is **named**, not merely detected (`reverted_to_step == 0`).
Also covered: a single rule passes; a genuine chain passes; a doubled rule is `NO_CHANGE`;
an empty sequence is `UNDEFINED` not `PASS`; a raising rule is `FAIL` and located by step;
the pair scan finds the witness and is clean for one rule; CLI exit codes carry the verdict.

## One more thing measured, not fixed

`whole_task_correctness_proved` is written **15 times** and **read zero times** — it is
hardcoded `False` everywhere and nothing consults it. That is honest labelling, and it is
also a field that cannot fail. Changing what it gates is a policy change, not a bug fix, so
it is recorded here rather than altered.

## Why this is the right next increment

`skill_recheck_v1` (previous PR) makes a single stored rule falsifiable. This makes the
*combination* falsifiable. The two together are the minimum needed before "give it more
skills" can mean "it can do more": otherwise every added skill is an unaudited interaction
with every existing one, and the store grows while the guarantee stays at one edit.

Sequence verification is deliberately **weaker** than whole-task correctness and says so; it
proves the rules do not cancel each other, not that the result is right.
