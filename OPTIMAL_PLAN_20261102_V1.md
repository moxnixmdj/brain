# The optimal plan

**2026-11-02.** Ordered by measured leverage, not by what is interesting. Every number below
came from running a file in this checkout; the stale ones are marked stale and not used.

---

## The one fact the whole plan turns on

I ran the live repair comparison (`canonical/tools/live_scoped_transfer_benchmark_v1.py`),
three arms, same constructed boundary lesson, fresh interpreter per case:

| case | cold | statement rule | **+ generalization** |
|---|---|---|---|
| renamed | PASS | PASS / hit | **PASS / hit** |
| compound | PASS | PASS | **PASS / hit** |
| if_statement | PASS | PASS | **PASS / hit** |
| flipped | PASS | PASS | **PASS / hit** |
| negated | PASS | PASS | **PASS / hit** |
| disjunction | PASS | PASS | **PASS / hit** |
| negative_inclusive (control) | PASS | PASS | PASS |
| **solved** | 7/7 | 7/7 | **7/7** |
| **retained hits** | 0 | 1 | **6** |
| **search invocations** | 6 | 5 | **0** |

Two readable facts:

1. **The learning chain, fully switched on, removes all search.** 6 search invocations → **0**.
   Every real repair becomes a recalled plan. That is instant learning working exactly as
   designed, in the live repair path, end to end.
2. **It does not raise the solve rate. 7/7 → 7/7 → 7/7.** Cold search already solves these.
   Learning buys **cost**, never capability, in this family.

Fact 2 is why the plan below is not "learn more". Fact 1 is why it is "switch on what exists".

---

## Step 1 — Turn the chain on in production. It is off by default.

**`python_repair_apply_verified_v1.py:149` defaults `retained_learning` to `{"enabled": False}`.**
The capability that dominates this entire family is dormant unless a caller explicitly opts in,
and only a benchmark tool does. Production repairs search cold every time.

The measured prize for flipping it: **search 6 → 0, retained hits 1 → 6**.

### Why this is sound and not a safety risk — the insight that unblocks it

Recall requires a caller-declared `contract` with `scope_id` and `verification_kind:
TEST_SUITE`. That looks like the unsolvable scope-induction problem, and it is why nobody
enabled it. But it is **not**, because of one property already in the code:

> `recall_and_apply_verified` takes a mandatory verifier, and `RetainedRepairSession` wires it
> to `ProjectTestOracle` — the project's **real test suite** — which runs on **every** recall.

So the scope is a **cost filter, not a safety filter**. The oracle is the safety filter. A scope
derived too widely costs a failed oracle call and a fallback to search. A scope derived too
narrowly costs the search we already pay today. **Neither can produce a wrong patch that the
test suite would have caught.**

That reframes the work from "induce the correct hypothesis space" (hard, unsolved, the real
frontier) to "derive a scope key that is *good enough often enough*" (small, sound, measurable).

### The work, concretely

1. Derive the scope from what the project already declares: test paths + `verification_kind`,
   keyed deterministically. `environment_fit_v1` already reads a project's own commands from its
   CI file — reuse that, invent nothing.
2. Default `retained_learning.enabled` to **true** when a TEST_SUITE contract can be derived;
   false otherwise, with a named reason. Fail closed, never guess.
3. Default `allow_operator_generalization` to **true** in that path — it is already gated on
   `TEST_SUITE` + `scope_id` + `python`.
4. **Re-measure on held-out real repositories**, not constructed ones.

### The honest limit of step 1

The benchmark above is *"known constructed boundary variants, non-blind"* — its own docstring
says so. 6/6 hits on **constructed neighbours** is not 6/6 on arbitrary repositories. Step 1 is
not done when the flag is flipped; it is done when a held-out repo shows the same search
collapse. That is the acceptance test, and it must be written before the flip.

**Stop condition:** on a repository the store has never seen, the second repair of the same kind
spends 0 search invocations and the first spends what it always did, with the full suite green
both times.

---

## Step 2 — Change the metric. Stop reporting solve rate for this family.

7/7 → 7/7 → 7/7 is not a failure of learning; it is learning being measured against the wrong
number. The instrument that shows the gain is **search invocations, wall clock, and trial
count** — which is exactly what the transfer probe already prints (32 → 1, 64 → 1, 16 → 1).

This matters because the opposite is a live risk in this repo: a *solve-rate* framing pressures
the next agent to widen a scope until a number moves, which is how a false success gets built.
Report `B_exec` separately from capability, as `RESOURCE_BOUNDED_CAPABILITY_BYTES_LAW_V1`
already requires.

**Stop condition:** no document in the tree claims a solve-rate gain from learning unless a
matched-arm comparison shows one. (The one that did — 6/9 vs 6/9 — says "no advantage".)

---

## Step 3 — Routing is the bigger multiplier, and it is mechanical work

Current registry, counted today: **141 rows, 259 distinct declared effects.** The "443 rows, 11
reached" figure quoted in older documents is **stale — do not cite it.**

A lesson lives *inside a row*. If the door does not route the sentence to that row, the lesson
is never consulted, no matter how many times it was taught. Measured in this tree: a rule was
taught and recalled `MATCHED`, and the door still refused because selection declined first.

So reach is a **hard ceiling on everything in Steps 1 and 4**. A perfect learner behind a door
that reaches 3% of its own capabilities returns 3% of the gain.

The work is enumeration, not invention: take the 259 declared effects, measure which are reachable
by a sentence, and extend the declaration table for the unreached ones. Cheaper per unit of real
gain than any new abstraction, and it compounds with every step above.

**Stop condition:** a fresh row-reach census, reproducible, replacing the stale figure.

---

## Step 4 — Widen the representable shape, one measured step at a time

The generalized arm's 6/6 is bounded by what `operator_generalization_v1` can *represent*:
one-operator differences, plus the boundary disjunction form. That ceiling is the real frontier,
and it is a **hypothesis-space** problem, not a learning problem — more training data cannot
move it, which is why 1, 2 and 3 examples all gave 6/7.

Order, cheapest first:

1. **Tail-expression forms.** The Rust miss is diagnosed, not mysterious: the stored pattern is
   `return ?id0 <= ?id1`, so it never matches `x <= hi` as a tail expression. This is the same
   Wall-1 defect inside the one module built to defeat it. Small edit, turns 4/5 into 5/5.
2. **Two-operator and negated shapes** — the shapes the 1/7 ladder missed, each added only when
   a probe proves it.
3. **Let the machine author the scope**, not the shape. `rule_scope_learning_v1` +
   `finite_capability_diagnosis.select_probe` already narrow a scope by measurement (2 of 3
   probes, and they refuse to guess when underdetermined). They are called only from tests.
   Wiring them is integration, and it is the honest version of "the machine decides how general
   its lesson is".

**Stop condition:** the shape ladder moves above 1/7 on shapes that were not hand-authored as
the reason to move it. Never widen the tolerance to pass — `NEVER_WIDEN_THE_TOLERANCE`.

---

## Step 5 — "Anything on a computer" needs the last honest sentence, then a layer

The GUI loop already closes end to end against a virtual 1920×1080 desktop: pixels → correct
pixel → world changes → next screenshot differs, 12/12. Only `VirtualDesktop` is a double.

1. **Buy the one missing sentence:** `pyautogui` drives a real operating system. Run the existing
   loop against a real X display. That is evidence, not mechanism, and 90 modules currently
   rest on it.
2. **Then build the screen→state recipe layer.** This is the only genuine research gap left in
   "any computer": a CLI state is a filename and an exit code; a GUI state is pixels, and
   "learn the transition function in one trial" on pixels is a tabulation nobody can afford.
   Until a screen becomes a comparable state, instant learning applies to the terminal and not
   to the desktop.

**Stop condition:** a GUI task the machine has never seen, solved at a trial count that is
lower than the second time it does it — the same invariant Step 1 satisfies on the CLI.

---

## What the optimal plan explicitly does NOT do

- **Do not run it in N new environments to "learn all of those".** Measured dead: 1, 2 and 3
  examples all gave **6/7**. The failure is representational, not statistical. Trying costs
  linear time and returns sublinear gain.
- **Do not chase solve rate with learning.** 7/7 vs 7/7. It is a cost technology.
- **Do not build a new learner.** The learner is not the bottleneck. Four working mechanisms sit
  disconnected from the production path; the cheapest capability in the tree is a **default
  value**.
- **Do not aim at the word "sentient".** Keep the measurable half — `ignorance_ledger_v1` ranks
  what the machine does not know by expected value and improves by being wrong. That is real.
  A claim with no instrument endangers every number above.
- **Do not treat "know all the data / fastest way" as satisfiable.** Report a lower bound plus a
  named coverage residual. The unknown space cannot be enumerated; only the owner can adopt that
  reading.

---

## Sequencing and dependency

```
Step 1 (switch on)  ──> highest measured leverage, smallest change, needs a held-out repo test
      │
      ├─> Step 2 (metric)   : must land with or before Step 1, or the gain will be misreported
      │
      └─> Step 3 (routing)  : ceiling on Steps 1 and 4; parallel, mechanical
                  │
                  └─> Step 4 (shape) ──> Step 5 (GUI)
```

1 and 2 land together: turning the chain on while still reporting solve rate would produce a
green number that is flat, which is the worst possible outcome for the next agent's judgement.

---

## The one-line version

**The learner is finished and switched off. The optimal plan is to switch it on where the
oracle already makes it safe, measure cost instead of solve rate, then spend the remaining
effort on the two things that are genuinely unsolved — what a lesson's scope is, and how to
turn a screen into a state.**

---

## Execution log — 2026-11-02

### Step 1 + Step 2: landed

**`canonical/swe_kernel/retained_scope_derivation_v1.py`** (new) derives the two inputs the
session was always waiting for, from facts the tree already states:

| input | derived from | decline reason when underivable |
|---|---|---|
| `scope_id` | sha256 of the sorted repository-relative test corpus | `DECLINED:NO_TEST_CORPUS_TO_SCOPE_AGAINST` |
| `target_path` | the single non-test module, when there is exactly one | `DECLINED:MULTIPLE_SOURCE_FILES_TARGET_AMBIGUOUS` |
| `db_path` | `.brain/retained_repair_skills.sqlite`, contained, reported | — |
| `allow_operator_generalization` | on, only under the store's own TEST_SUITE + scope + python precondition | — |

**`python_repair_apply_verified_v1.py`** calls it whenever the caller states no configuration,
and reports it in every run. A stated configuration is kept verbatim, including
`{"enabled": False}`.

### Measured, end to end, through the live capability

| run | derivation | search invocations | retained | suite |
|---|---|---|---|---|
| first, unseen project | ON, scope `python/tests/a25b1cc7c8c0ec43/v1` | **1** | taught | green |
| second, same breakage | ON, same scope | **0** | recalled | green |

### Tests

`canonical/tests/test_the_second_repair_is_cheaper_v1.py` — **10 tests. Six fail on the base
commit; all ten pass here.** They pin the invariant the improvement actually claims (a cost
saving on the second encounter) and not a solve-rate change, because measurement says none
exists: the cold arm solved the same cases. Three refusals are pinned as hard as the acceptance:
a stated `enabled: False` is never overridden, two source files decline with a named reason,
and a project whose correct answer differs from the stored lesson is still repaired correctly.

Regression: 58 passing across the repair capability's own suite, 37 across this change and the
transfer work. Three failures in `test_a_stated_defect_is_a_request_to_repair_v1` and
`test_a_repair_sentence_that_names_no_test_still_repairs_the_source_v1` are **pre-existing and
identical on the base commit** — measured, not assumed.

### One thing this deliberately did not do

**The memory is per-repository, because `RetainedRepairSession` refuses any database path
outside the repository.** So learning compounds *within* a project and does not carry to a
different one. Loosening that containment is a safety-boundary change, not a configuration one,
and it was not made to make a number look better. Cross-project carry is Step 4 territory and
is named as a limit here rather than papered over.

### The governance objection is unchanged, and it is now on the critical path

`LIVE_CHALLENGER_FRONTIER_EXEMPTION_NOT_ALLOWED_FOR_ACTION_KIND` is still the only red. The
guard demands external-supplier challenger evidence for an internal default. Two intents also
landed as one PR; rather than drop the earlier record, the first intent is carried verbatim
inside the second under `supersedes`.

The pressure this creates is now concrete rather than hypothetical: **the highest-leverage
action in the tree — turning on a measured 6 → 0 — is blocked by a schema for a question it
does not ask.** That is the owner's call.
