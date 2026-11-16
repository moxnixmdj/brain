# The judge was the missing part

*Project Brain — 2026-11-16 — receipt `canonical/verification/INSTRUCTION_CONTRACT_20261116_V1.json`*

## The claim under test

"Show the model an action once and it is permanent, therefore all computer use is solved."

The previous rounds removed two candidate excuses: the action prior is inert (it says nothing
useful about what to do next) and the value of a step is not recoverable from the state alone. Both
were measured dead, honestly, and both are recorded. What remained was the thing every source from
this round points at: **the verifier**.

The tree's whole record is built on an oracle it does not have in deployment — the page's own
reward, the repository's own tests. Every "the machine learned this" claim so far was really "the
machine found a plan and the page confirmed it". That is a measurement apparatus, not a capability.

So the question this round answers with numbers is narrower and harder:

> **When the reward is taken away, how often does the machine's own contract agree with the
> verdict the environment would have given?**

## What was built

`canonical/runtime/instruction_contract_v1.py` compiles an instruction, together with the observation
in front of it, into a conjunction of checkable clauses — or into a **named refusal**. Ten operators:

| operator | what it decides | why state alone could not |
|---|---|---|
| `CLICK_NAMED` | the named control was pressed, and what the instruction required **first** was true | pressing Submit on a wrong selection is a different trace with the same end state |
| `CLICK_LABELLED` | a control the page labels with the instruction's own words was pressed | the label lives in the page, not the instruction |
| `CLICK_ORDINAL` | the n-th control **of a kind** was pressed | — |
| `ORDINAL_PRESS` | the n-th pressable thing of that kind, **as visible when pressed** | "the 3rd result" only exists after the search runs |
| `PRESS_SEQUENCE` | controls were pressed **in the stated order** | ONE→TWO and TWO→ONE end on the same page |
| `SELECT_SET` | the named things are checked, found through label→input in both directions | the state is on a different element from the name |
| `TYPE_VALUE` | the field holds the named value | — |
| `TYPE_MATCHING` | the value satisfies "starts with / ends with / contains" | the instruction gave a predicate, not a literal |
| `SET_CONTROL` | slider/spinner/select ends holding the named value | the value is in the observation; geometry is not needed |
| `FOCUS` | the field took the focus, witnessed by state **or** by the press | `focus-text.html` rewards *inside* its focus handler and blurs in the same statement, so the post-success observation can never show it |
| `LABEL_ON_TRACE` | a control the instruction says to **find** surfaces and is then pressed | it is not in the opening observation, and the instruction says so |

Every clause carries its `provenance` — the words that produced it — so a wrong contract can be
argued with rather than merely obeyed. The module's own scope is a constant in the record:

```
verifies = "THAT_THE_INSTRUCTION_HAPPENED_NOT_THAT_THE_ANSWER_WAS_RIGHT"
```

That is the honest boundary. `enter-date` compiles to "the field holds `08/13/2018`", never to "that
date is the right one". `simple-arithmetic` would compile to "`7` was typed", never to "7 is
correct". The contract removes the environment as the judge of *whether the instruction happened*.
It does not, and cannot, become the judge of *whether the answer is right*. **That residual is
exactly the asymmetry the task names**, and it is now a measured boundary instead of a caveat.

## The measurement

Two arms per page, so a label is earned twice:

* **A** — the plan the machine found (the page scored it a success)
* **B** — the same plan with **one action replaced** (same length, same shape). If the page also
  scores B a success, that is a genuinely equivalent plan and not an error.

The contract is compiled **from the opening observation only** and never sees the reward: a test
scans its source text for `raw_reward`/`done`/`reward` subscripts and fails the build if one appears.

```
PAGES WITH A PLAN        18
JUDGED ATTEMPTS          32
AGREEMENT               32/32  (1.0)
FALSE ACCEPT             0
FALSE REJECT             0
UNCHECKABLE              4   (2 pages: the page never names the control)
```

Per operator, every clause was exercised in both directions (13 disagreements with the page's
verdict, of which the contract was right every time).

## Falsifiability: the defence against an always-pass grader

Coverage is cheap and worthless. A contract that accepts **doing nothing at all** can never reject
a wrong trace, no matter how many clauses it prints. So the census asks that question of every page,
on the real page, and counts the answer separately:

```
COMPILED                 70/140   (0.50 of the instruction corpus)
FALSIFIABLE              70/70
ACCEPTS DOING NOTHING     0
```

Refusals keep their own column, because a machine that declines to guess has not failed:

| refusal | count | what it means |
|---|---|---|
| `MULTI_APP_STATE_OUTSIDE_OBSERVATION` | 15 | the state lives in an app the observation does not contain |
| `SPATIAL_NEEDS_GEOMETRY` | 20 | drag/draw/angle/colour — needs pixels |
| `NO_CLAUSE_UNDERSTOOD` | 11 | the words name no decidable predicate here |
| `LABEL_NOT_ON_THE_PAGE` | 5 | the instruction names a control the page shows nowhere |
| `STYLE_NOT_IN_OBSERVATION` | 3 | underlined/bold/italic |
| `VISUAL_QUANTITY_NEEDS_PIXELS` | 3 | "how many" |
| `FUZZY_NO_DECIDABLE_PREDICATE` | 2 | "best describes", "similar to" |
| `CONTINUOUS_NO_END_STATE` | 1 | the reward is a process, not an end state |
| `ERROR` (bridge) | 8 | the page itself would not load |

`LABEL_NOT_ON_THE_PAGE` is the refusal this round is proudest of. `"Close the dialog box by clicking
the "x""` — the x is drawn by CSS. The string `x` **does** occur inside the class
`ui-icon-closethick`, and accepting that would have been a contract that passed the decoy for the
wrong reason: it recognised a symbol convention it had guessed. It refuses instead.

## The six defects this measurement found in my own verifier

Every one of these was caught by the page disagreeing with the contract, not by reasoning:

1. **Number words blacklisted as labels.** "Click button ONE" fell back to "press any button", which
   the decoy satisfied → **false accept**. Numbers are labels when the page shows them as labels.
2. **A kind-only fallback clause.** "press any button" is satisfied by every trace. Deleted; the
   fallback is now a refusal.
3. **`SELECT_SET` read only the final observation.** Pressing Submit ends the episode and the page
   replaces itself, so the checked state was gone → **false reject**. Every observation is inspected.
4. **The checked state was looked for sideways only.** MiniWoB++ puts the name on `<label>` and the
   state on its **child** `<input>` → **false reject**. The association now runs both directions.
5. **A press clause that ignored its own instruction.** "Select ULZC and click Submit" compiled to
   just the press, so pressing Submit with nothing chosen passed → **false accept**. A press now
   carries what the instruction required before it.
6. **An unquoted literal was not read as a value.** "Enter 08/13/2018 as the date" compiled to just
   the press, so typing garbage passed → **false accept**.

Defects 2, 4 and 6 are the same disease in three costumes: **a clause that is cheap to satisfy**.
That is the failure mode generated verifiers have in the literature, and the census now measures it
directly rather than trusting that it is absent.

## What this changes about the standing claim

* **Instant learning in a new environment is not solved — but the blocker is not the action model.**
  On 18 pages the contract agrees with the environment 32 times out of 32 without ever seeing the
  reward. The machine can now tell whether it did what it was told.
* **Half of computer use is not yet expressible.** 70/140 instructions compile. The 70 that do not
  are refused for a named reason, and the largest single block is honest: **geometry (20) and other
  apps' state (15)** are not in the observation. Those are observation problems, not learning
  problems, and calling them learning problems is what has kept this field busy.
* **The verifier is worth more than the policy.** Nothing about the policy changed this round. Only
  the judge did — and that turned 40% of the corpus from "unjudgeable" into "decided".
* **The asymmetry is real and now bounded.** The contract verifies that the instruction happened. It
  never verifies that the answer was right. Any claim of "solved" that crosses that line is false,
  and this record is where the line is.

## Reproduce

```
python3 canonical/tests/test_instruction_contract_v1.py            # 22 tests, offline, 0 failures
python3 canonical/tools/instruction_contract_measure_v1.py \
    --html-dir <miniwob/html> --node-modules-dir <node_modules> --census
python3 canonical/tools/instruction_contract_measure_v1.py \
    --html-dir ... --node-modules-dir ... --budget 400 --out /tmp/m.jsonl
python3 canonical/tools/instruction_contract_measure_v1.py --consolidate /tmp/m.jsonl \
    --receipt canonical/verification/INSTRUCTION_CONTRACT_20261116_V1.json
```

`AUTHORITY NONE — SANDBOX MEASUREMENT, NOT INDEPENDENT VERIFICATION.`
Producer-cognition model dependency count: **0**. Incremental spend: **$0**.
