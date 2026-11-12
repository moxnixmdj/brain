# A capability that cannot know this machine cannot run it

**2026-11-12.** Base `2540a6ed`. Branch `arena/89828447-brain`. Round 6 of the owner's question.

Two things happened this round, and one of them is in the owner's favour.

**The positive result.** Rounds 3–5 refuted parts of the plan. This round ran the plan
itself — *experience a job once, keep it, reuse it* — end to end on the real runtime, with no
simulation:

```
TRIAL 1   count functions in macro_v1.py  then audit it     → 2/2 VERIFIED, macro recorded
TRIAL 2   same job on world_probe_v1.py (different file)    → used_macro: TRUE, 2/2 verified
TRIAL 3   back on macro_v1.py                               → used_macro: TRUE, succ 3
```

**The one-try loop works.** One demonstration, a different file, correct reuse, verified at every
step. The owner is right that this mechanism exists in the tree and functions.

**The refutation, and it is narrow and exact.** The loop works on this machine. It cannot work
across machines that differ, because 56 of 145 capabilities declare no preconditions at all — so
the front door cannot tell `this box lacks qrencode` from `qrencode is here and the job is fine`.
A "try" in a new environment is therefore not an experiment on those rows: it is an unlabelled
execution.

Authority **NONE**. One machine, no independent verifier, $0, zero model dependency.
`truth.achieved` stays `false`; no capability registered; no family flipped.

---

## 1. The positive result, stated precisely

`chain_v1.run` decomposed a two-clause sentence, selected a capability for each clause, executed
and verified both, and recorded the plan. On the next, *different* file the same plan was retrieved
and applied, and every step was verified again by the normal path.

That is the owner's loop and it is real. Two caveats, both measured, both narrower than round 3's:

- Reuse is by **shape** — verbs and file kinds. It generalises across files of the same kind, not
  across kinds.
- It carries the plan, not the reason. `proved_where` was null on every stored macro (round 5's
  repair is available but no caller passes an address yet), so a *precondition failure* is the
  only thing that can discipline a plan, and it is the thing §2 shows is missing.

## 2. Where the plan breaks: 56 rows that cannot fail

The front door's gate is `world_probe_v1.probe_effect`. It is a good sensor. Measured on this
machine, where `qrencode`, `zbarimg`, `sqlite3` and the `docx`/`xlsx` python libraries are all
genuinely absent:

| Capability | declares `requires` | what the sensor says about the missing fact |
|---|---|---|
| `image.qr.generate.qrencode` | `[]` | `qrencode.runtime.available` → **`executable_absent`** |
| `image.code.decode.zbarimg` | `[]` | `zbarimg.runtime.available` → **`executable_absent`** |
| `sqlite.table.create_from_json_records` | `[]` | `sqlite3.runtime.available` → **`executable_absent`** |
| `sqlite.table.verify_against_json_records` | `[]` | `sqlite3.runtime.available` → **`executable_absent`** |

**The sensor was never broken. Nobody asked it.** `_decide_runtime` does `shutil.which` and returns
`executable_absent` correctly; it is reached only if the effect string appears in the row's
`requires`, and for these rows the list is empty. This is a data omission, not a capability gap —
the cheapest kind of defect there is.

### The counterfactual, measured by injection

The registry is a protected path, so the file was not touched. A copy was handed to `act` (which
accepts a `registry` argument) with exactly one added precondition:

```
BEFORE   "generate a qr code for https://example.com"
         → this row is a live candidate (no rejection), then ACTION_FAILED
           Blocker:BOUND_APT_METADATA_NOT_FOUND
AFTER    same sentence, one added precondition
         → this row rejected: PRECONDITION_NOT_TRUE_OF_WORLD
```

The machine stops *at the gate* instead of *after an attempt that could never work*. All four rows
behave the same way: **4/4 the sensor decides the fact, 4/4 the injection changes the outcome.**

And it is not a blanket ban: with the injector reporting `qrencode` present, the same row returns to
being a candidate. The row stays usable on a machine that has the tool.

## 3. What this means for "give it a try in every new environment"

A trial is informative only if its outcome can be attributed. On these 56 rows it cannot:

| | this machine | a machine with the tool |
|---|---|---|
| row declares `requires: []` | attempts, fails | attempts, succeeds |

The failure carries no information the machine can use, because the thing that caused it was never
in the model. Round 5 established that a success must be *addressed* to its environment; this round
establishes the prior requirement — **the failure must first be distinguishable from a bad plan.**

So the owner's ordering is inverted by measurement. Trying more environments does not teach more,
because on 56 rows the environment is not represented anywhere the learner can read it. Declaring
what a row needs is upstream of every demonstration, and it is what makes a demonstration a datum.

## 4. What I did not do, on purpose

`canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json` is owner-protected (CODEOWNERS). There is an
unprotected mirror — `BOUND_CAPABILITY_REGISTRY_SNAPSHOT_V1.json` — that `load_registry` merges
*over* the registry, so the same change could have shipped without touching the protected file.

I did not use it. AGENTS.md is explicit: *"Say so in the PR description and stop. Do not work around
it."* Using the mirror to edit protected rows is the workaround that sentence forbids, whether or not
the guard would catch it. The audit measures the change and stops. **This is the thing I need from
you** — it is a four-row, four-line change to a file only you can land:

```json
"image.qr.generate.qrencode"            : "requires": ["qrencode.runtime.available"]
"image.code.decode.zbarimg"             : "requires": ["zbarimg.runtime.available"]
"sqlite.table.create_from_json_records" : "requires": ["sqlite3.runtime.available"]
"sqlite.table.verify_against_json_records": "requires": ["sqlite3.runtime.available"]
```

Widening further is available and I did not do it: a dozen `python.*` rows name a python runtime.
That would need a `python.runtime.available` probe plus an argument about which rows really need it.
Four rows you can check by eye beat twenty you would have to trust.

## 5. What 2026 says

The same gap is named, from different directions, throughout the field:

- **SkillHarness** (arXiv 2606.20636): skills learned from successful trajectories *"often fail to
  capture the conditions under which they remain valid"*; the fix is a per-skill boundary plus
  failure-derived lessons.
- **SkillApt** (arXiv 2609.26863): *"environment validity should be a hard precondition for
  applicability… when the precondition cannot be reproduced through the agent's actual tool path,
  the system should retire or quarantine the skill."*
- **OSExpert** (arXiv 2603.07978): exploration cost is the binding constraint, which is exactly why
  attempts that cannot be attributed are expensive rather than merely useless.
- **SkillsVote** (arXiv 2605.18401) and **2605.23899**: experience reuse transfers *negatively*
  without conditions that decide when to apply it.

## 6. Answering the owner, plainly

**"Give it a try in a new environment and it learns permanently."**
On this machine, for a job it can actually run: **yes, measured, it works** — one trial, then correct
reuse on a different file. Across machines that differ: **no**, because 56 rows cannot represent the
difference. The loop is real; its evidence is not yet addressed or even attributable.

**"Instant learning in new arbitrary environments is solved perfectly."**
Solved for *speed on a compatible interface*. Not solved for *knowing whether the environment is
compatible*, which is the part "new arbitrary" refers to.

**"Give it the smartest actions."**
Still right, and now with a second condition: an action is reusable across environments only if it
declares what it needs. 59 of 145 are invocable with no learning at all; of those that are not, the
cheapest real unlock is four data lines, not a learner.

**"Sentient creature."**
Not measured here and not the objective. The relevant observation is only this: the machine now
records where a thing was proved, and can be told what a machine lacks. Knowledge that survives
being moved is a precondition for anything one would call a creature; the reverse is not implied.

## 7. Receipts and non-claims

- `a_capability_that_cannot_know_this_machine_cannot_run_it_20261112.py` — the audit.
- `canonical/tests/test_a_capability_that_cannot_know_this_machine_cannot_run_it_v1.py` — **7/7**,
  including a test that the audit **cannot write** the registry it reads.
- The full-run numbers: 145 capabilities, **56** declaring no preconditions, **4** naming a runtime
  the sensor can decide, **4/4** decided, **4/4** changed by the injection.

**Not claimed:** that these four rows are the only gap (they are the only *decidable* ones by this
derivation); that the fix makes the machine able to run qrencode; that reuse is safe — it remains
attributable at best, with the `prefer`→`survivor` gate and per-step verification as the safety net.
No GUI was driven. The "new environments" here are two different files and one absent binary, not
provisioned machines.
