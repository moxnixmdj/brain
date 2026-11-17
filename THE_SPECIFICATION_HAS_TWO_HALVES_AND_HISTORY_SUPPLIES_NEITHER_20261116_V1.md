# The specification has two halves, and history supplies neither

*Round 4. 2026-11-16. Branch `arena/adb89925-brain`, base `fd43dc31`.*

## What round 3 left on the table

Round 3 measured three routes by which the artifact — the code, the tests, the commit — might be made to
supply its own specification. All three came back zero, and the cause was named: **real work extends a
specification instead of violating a property.** A change that adds `riscv64` to packaging does not break
anything; it makes something true that was not true. Property checkers can only see violations, so the
whole class of work that *matters* is invisible to them.

The named next organ was therefore the **intent compiler**: turn the instruction into the checkable pair,
then hand that pair to the exact verifier and the aimed-edit space that already solve eight of eight when
such a pair exists.

## The organ already existed — for the other domain

Research first, as always. `canonical/runtime/instruction_contract_v1.py` already compiles a sentence into
a contract: *"Click on the 'No' button"* becomes `CLICK_NAMED`, an ordinal click becomes `CLICK_ORDINAL`, a
set selection becomes `SELECT_SET`, and every instruction it cannot compile is **refused by name** —
`REFUSED__VISUAL_QUANTITY`, `REFUSED__SPATIAL`, `REFUSED__STYLE_NOT_OBSERVABLE`, `REFUSED__FUZZY`,
`REFUSED__MULTI_APP`. It ran on 130 real instructions and its receipt is committed.

That is the pattern. It had **no coding counterpart**. What round 4 builds is not a new idea — it is the
missing domain, with the same discipline and no model.

## The language

A sentence is compiled against the environment, never against itself:

```
value the sentence names  ×  direction its verb states  ×  grounding in a callable the module defines
```

- values: quoted strings first (a quote is the author pointing), then value-shaped tokens;
- directions: `WIDENING` (*add, support, allow, accept*), `NARROWING` (*remove, reject, drop, ban*),
  `REPAIR` (*fix, correct, handle*) — and direction is read on the sentence **with its own named values
  removed**, because "Support --disable-gil builds" widens even though the flag contains *disable*;
- grounding: one candidate site per callable that contains the value, one per parameter position. *Which*
  site and *which* parameter is not decided by names — "riscv64" shares no run with either `archs` or
  `executable` — it is decided by executing both states and keeping the site that discriminates.

Clauses: `ACCEPTS_NAMED`, `REJECTS_NAMED`, `NAMED_IN_OUTCOME`, and `STILL_RUNS` — the last only ever
beside a grounded clause, because a `STILL_RUNS`-alone contract is a refusal wearing a verdict.

Refusals, named one at a time: `REFUSED__NO_VALUE_IN_THE_INSTRUCTION`,
`REFUSED__THE_NAMED_VALUE_IS_NOT_IN_THE_ENVIRONMENT`, `REFUSED__THE_NAMED_VALUE_IS_NOT_IN_A_CALLABLE`,
`REFUSED__NO_DIRECTION_IN_THE_INSTRUCTION`. Verdicts: `DISCRIMINATING` (holds at the fixed state, fails at
its parent), `VACUOUS` (holds at both), `WRONG_AT_FIXED` (fails where it must hold — the compilation is
wrong, and that is reported).

## The measurement, and the three bugs that stood between me and it

Forty real commits, each handed its own message as the stated instruction:

| | |
|---|---|
| commits | 40 (21 ship a test, 19 do not) |
| **compiled** | **2** |
| **refused by name** | **38** |
| `NO_DIRECTION_IN_THE_INSTRUCTION` | 19 |
| `THE_NAMED_VALUE_IS_NOT_IN_THE_ENVIRONMENT` | 15 |
| `NO_VALUE_IN_THE_INSTRUCTION` | 6 |
| `THE_NAMED_VALUE_IS_NOT_IN_A_CALLABLE` | 3 |
| discriminating | **0** |
| wrong at the fixed state | **2** |

Getting to those numbers required distrusting three earlier versions of them, and every one of the three
bugs flattered the instrument:

1. **Refusals were double-counted.** Forty commits read as seventy-eight refusals, because the refusal was
   incremented on two paths, and because refusals are counted per (commit × module) row. A denominator can
   lie before a numerator does.
2. **The direction was read inside the value.** "Support --disable-gil builds" was parsed as `NARROWING`,
   because the flag's name contains *disable*. The sentence's own values must be removed before its verb is
   read. This bug is what produced the only `DISCRIMINATING` I ever saw this round — and it was false.
3. **A `False` return was counted as acceptance.** `supports_arch("riscv64") -> False` satisfied
   `ACCEPTS_NAMED`, because "returned" was treated as "accepted". That is the always-pass grader this tree
   already refused, one layer down. Acceptance now requires a truthy return; `False`, `None`, `[]`, `{}`,
   `0` are the environment saying no.

Each fix moved the number *down*. That is the direction a fix should move it.

## Why both compiled rows are wrong

The instrument is not blind — one test builds a real two-state repository where the parent raises and the
fixed state accepts the value, and the compiler returns `DISCRIMINATING` with the expected outcomes; the
same file pins `VACUOUS` and `WRONG_AT_FIXED`. So the corpus zero is a statement about history, not about a
grader that cannot pass.

Both compiled rows fail for the *same* reason, and it is the interesting one:

- **`4d853406` — "Add riscv64 as a supported manylinux architecture."** The value is a build target. The
  callable whose text contains it is the ABI-compatibility test, which returns `False` in both states. What
  changed is the generator that lists supported architectures — *elsewhere in the same module.* The value
  sits in the module; the mechanism that decides it does not sit where the value sits.
- **`7e4f258892` — "Support --disable-gil builds (PEP 703)."** The "value" is a build flag named in prose,
  not an argument to anything. The site returns `False`. A human shipped a test for this change; the
  model-free compiler could not locate the mechanism even though it could read the words.

## The answer

**The specification has two halves — the value and the site — and a sentence supplies only the first.**
Textual occurrence of a value in a callable is not evidence that the callable decides the value's fate:
2 out of 2 times, here, it did not. That is why every November-2026 system that compiles instructions
(ContextCov, RefineAct, AgentGuardUtil, Compiled AI) spends a model in the compile phase — the model is
doing **site selection**, which is the genuinely hard half, and which no surface heuristic recovered. I
tried two: longest-shared-run parameter affinity (mine, this round) and occurrence-first (inherited). Both
failed the same way.

And 95% of the corpus never gets that far: a commit message states no value, or no direction, or names a
value the environment has never heard of. That is `INSUFFICIENCY_CERTIFICATE_20261113_V1` arriving in the
coding domain — *the causal observable is absent, so repetition cannot separate success from failure* — and
no amount of experience manufactures it. Experience supplies actions. The instruction supplies the value.
The environment supplies the site **only under an intervention**, which is precisely what an agent does
when it runs the thing it just changed and watches.

So the honest ledger for the user's question, four rounds in:

| round | route | result |
|---|---|---|
| 1 | experience → actions | cost law, not coverage; `p_correct` 0.2978 |
| 2 | differential pins from real diffs | 13 drivable, **0 pins**, memorisable 4.814% |
| 3 | structure → laws | 40 commits, 188 laws, **0 kills** |
| 4 | instruction → contract | 40 commits, 2 compiled, **0 discriminating**, 2 wrong sites |

Four instruments, four zeros, one cause, now sharpened: **the bottleneck is the specification, and the
specification's missing half is the site.** The next lever is not another textual reading of the message. It
is an **interventional** one: change one thing, run it, and let the difference name the site — the same move
that made the computer-use contract work, where the page supplies observables that a commit message does
not.

The organ is real, it runs with `K3 = 0`, `$0`, no network, no parameters, and it will compile any
instruction that names a value and a site at once. What history cannot do is be that instruction.

*Reproduce:* `.venv/bin/python canonical/swe_kernel/instruction_contract_for_code_v1.py --corpus --limit 40
--json canonical/verification/INSTRUCTION_CONTRACT_FOR_CODE_20261116_V1.json`
