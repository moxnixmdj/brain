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

---

## Execution log — shape ceiling (Step 4, cheapest item): landed, and it contained a real bug

The plan's Step 4.1 said "admit a tail-expression form of the pattern. Small edit." It was a
small edit, and it turned up a defect that had been silently generating garbage:

**`operator_generalization_v1._occurrences` searched for an operator's characters without
asking whether it had found a whole token.** Taught `<= → <` and offered

    fn within(x: i64, hi: i64) -> bool { x <= hi }

it produced **two** candidates — the correct rewrite, and `->= bool`, because the `>` of the
arrow looked like a comparison. `-` is generalizable too, so `x -> y` could become `x +> y`,
and `>>` could become `>>=`. The caller's mandatory verifier rejected all of it, so nothing
wrong was ever applied — but a generator emitting syntactically impossible candidates spends
the caller's oracle budget on proposals that cannot succeed, and the candidate count it reports
becomes a number about noise.

Fixed with a maximal-token guard (`_is_standalone`). Three tests fail on the old matcher.

**Then the bridge was wired to it.** `recall_across_languages` asked only the narrow question —
"does the stored skeleton unify?" — so a rule taught inside a `return` could only fire inside a
`return`. It now offers the operator-swap form second, still through `parses_in` and still
through the caller's mandatory verifier. It can propose more; it still cannot accept anything.

| | before | after |
|---|---|---|
| C++ | CROSSED, executed 3/3 | CROSSED, executed 3/3 |
| Go, TypeScript, Java | CROSSED, text-only | CROSSED, text-only |
| **Rust** | **refused** (`RULE_PATTERN_ABSENT`) | **CROSSED** |
| carried | 4/5 | **5/5** |

An existing test asserted `hit is None` for Rust *"because the pattern needs a token Rust does
not have."* That was true of the stored skeleton and false of the lesson, so the test now
asserts the crossing **and** a new test holds the refusal side: the same lesson against a
verifier that says no must still return nothing. Widening what may be proposed is not widening
what may be accepted.

## Routing, measured (Step 3) — the denominator, not the guess

Fresh count of the registry, replacing the stale "443 rows / 11 reached":

| | |
|---|---|
| capabilities | **141** |
| distinct declared effects | **259** |
| effects claimed by exactly one capability | 247 |
| effects claimed by more than one | 12 |
| capabilities declaring no effect | 0 |

What is still **not** measured is *reach*: how many of those 259 effects a real sentence can
actually bind. That is the next measurement, and it is the one that sizes Step 3. Measuring it
requires driving the live binder with a corpus and recording which rows fire — not counting
rows. Until then any reach figure is a guess, and the honest statement is 259 declared, reach
unknown.

## What is left, ranked, with the reason each is where it is

1. **Routing reach census.** 259 effects, reach unmeasured. A lesson lives inside a row, so
   this is a hard ceiling on everything below it. Mechanical work, high multiplier, no research.
2. **The governance blocker.** The drift guard refuses an internal default for want of
   external-supplier evidence. This is now the cheapest unblock in the tree and it needs an
   owner decision, not another agent's workaround.
3. **Cross-project carry.** Learning is contained to one repository because
   `RetainedRepairSession` refuses outside paths. Loosening that is a safety boundary, not a
   configuration, and it was deliberately not loosened to improve a number.
4. **Screen → state.** The only genuine research gap left in "anything on a computer."
5. **`pyautogui` on a real OS.** 90 modules rest on one unproven sentence.

## The shape of the plan now, in one line

**The learner is on, the shape ceiling is higher, and the two things left are a counting
exercise (routing) and a permissions decision (cross-project carry) — plus one research gap
that no amount of engineering around it will close.**

---

## Execution log — Step 3 (routing reach): measured, and the instrument's own limit was the finding

I set out to produce the reach denominator that replaced the stale "443 rows, 11 reached".
What I produced is a **diagnostic**, and the reason is the most useful thing in this section.

### What the census measured

`canonical/tools/route_reach_census_v1.py`, reproducible, 40 s, artifact at
`canonical/verification/ROUTE_REACH_CENSUS_V1.json`:

| | |
|---|---|
| capabilities | 141 |
| distinct declared effects | 259 |
| self-reached by declared vocabulary | **48** |
| routed to a different capability | **55** |
| unreached by every templated address | **38** |
| — of which `GOAL_INPUT_BINDING_REQUIRED` | **35** |

That last row is the actionable one. Those capabilities declare templates demanding
role-shaped inputs (`op`, `repo_root`, `rev`, `staged`, …) that no prose sentence names —
`git.repository.operate.v1` declares nine. This is the same defect class an earlier fix removed
from the test-scaffold row ("unbindable for five inputs no sentence states"), and it is a
declaration bug, not a phrasing artefact.

### Why the number is NOT a reach figure, and why I am not quoting it as one

Three successive addresses were needed to find this out, and each one falsified the previous:

1. A keyword bag was assumed to be the most generous address. **Wrong in both directions:**
   `python.source.symbols.index.ast` was unreached by it and is reached by one ordinary English
   sentence; `python.refactor.rename_symbol` is the reverse.
2. A natural template was added. It produced `GOAL_INPUT_BINDING_REQUIRED` for 133 of 141 —
   which reads as catastrophic and is mostly an artefact of the template, not the tree.
3. The template plus a real path produced **exactly the same counts**, proving the blocker is
   role-shaped inputs rather than a missing path.

The limit is now asserted *in the code and in the artifact*, not just in prose: every report
carries `reach_denominator_claim: TEMPLATED_ADDRESSES_ONLY__NOT_A_REACH_DENOMINATOR__UNREACHED_DOES_NOT_MEAN_UNREACHABLE`,
and a test pins that a capability recorded UNREACHED is reachable in ordinary English — so the
counts cannot be quoted as a fraction of anything a user experiences.

**What would actually settle reach:** a corpus of real user sentences, run through the same
compiler. That is a corpus-construction job, and it is the honest next step rather than a
figure this tool can manufacture.

### Regression

7 new tests, all passing. Nothing in the routing path was changed — this adds a measurement and
a limit, and modifies no behaviour.

---

## Execution log — the real reach number, from real sentences

The previous section said a corpus of real user sentences was the only thing that would turn
reach into a number. The repository already has one: **49 hand-written advanced
software-engineering requests** in `execution_guard/swe_advanced_probe_v1.py`, spanning
polyglot, build, CI, performance, concurrency, test authoring, debugging, refactoring, git and
design. `route_reach_census_v1.py --real` routes them and reports reach.

### Measured 2026-11-02, routing only, nothing executed

| | |
|---|---|
| sentences | 49 |
| routed somewhere | **32** |
| capabilities reached | **12 / 141** (8.5%) |
| declared effects reached | **43 / 259** (16.6%) |
| unrouted | **17** |

This is the figure that was quoted for months as *"443 rows, 11 reached"* — an unverified
number from a superseded document that did not even match the current tree's row count. It is
now **12 of 141 at a named commit, reproducible in five seconds**, and the old figure's shape
turns out to have been right while its denominator was wrong.

### Where the 17 go, and why it is not one problem

| cause | count |
|---|---|
| `GOAL_COMPILATION_NO_VERIFIED_CAPABILITY_MATCH` | 14 |
| `GOAL_INPUT_BINDING_REQUIRED` | 3 |

The 14 are **declaration gaps**: the door has no row whose declared effect matches the request.
The 3 are **template defects**: a row exists but demands inputs the sentence never states.

### The concrete gap this exposed

`Add a target lint to .../Makefile`, `Fix the failing CI job in .../ci.yml`, and
`Make the CI workflow ... run the tests on Python 3.11 and 3.12` all route nowhere. The tree
contains `canonical/swe_kernel/polyglot_build_ci_engine_v1.py`, which is written, tested and
referenced by four action intents — and **has no registry row at all**. A working build/CI
capability exists and no sentence can reach it.

That is the same shape as the two defects already fixed this session (a learner nobody enabled,
a status that over-claimed), and it is now **named and measured** rather than inferred. It is
also deliberately **not** half-built here: registering a capability requires adapter wiring,
declared effects, and verification on held-out requests, and the honest state is that the gap
is diagnosed and the fix is scoped.

### Concentration is the routing story

Three rows absorb most of the routed traffic — one row takes **11 of the 32** routed sentences
on its own, another 6. That is why "reach" and "capability count" are different numbers, and
why adding a 142nd row would move neither.

---

## Execution log 6 — the loop closes its own defects (2026-11-04, `2bbd14ad`)

Four landings corrected strings, defaults and one measurement instrument. Every defect they
fixed was found by an agent and pointed at, so the improvement rate was proportional to how
many sessions a human ran. **Unaided closure rate was 0.**

`canonical/tools/self_maintenance_loop_v1.py` is the first thing in this repository that
finds, repairs and proves a defect with nobody pointing:

```
PERCEIVE -> MODEL -> SELECT -> ACT -> VERIFY -> LEARN
3 defect classes, deterministic, deterministic, zero model spend, no new authority
```

### What it measured, live, unattended

An ordinary edit to a receipted test file, then the loop, no instruction given to it:

| | value |
|---|---|
| defects found | 2 (`STALE_ACTION_INTENT_RECEIPT:…:9`, `:12` — same file, two receipts) |
| repairs prepared and independently verified on disk | 2 |
| certified by the drift guard at the ref | 2 (`--certify`, after the commit) |
| unaided closure rate | **100%** on this class, 2/2 |

The drift guard's verdict moved from
`V22_COUNTEREXAMPLE_RECEIPT_BLOB_STALE_OR_MISMATCH:9` + `:12` to **absent**, leaving only the
known `LIVE_CHALLENGER_FRONTIER_EXEMPTION_NOT_ALLOWED_FOR_ACTION_KIND` objection that needs
an owner decision.

### Four defects in the loop itself, all found before landing

1. **841 defects was fiction.** The finder scanned the whole intent archive; the drift guard
   loads only intents in the change set. An archived receipt pointing at a file that has
   since changed is the archive working. Scope is now the change set — pinned by two tests
   that must fail together: the scope test, and the test that proves the archive really does
   hold stale receipts (without which the scope test measures nothing).
2. **A measure-only run wrote 2,436 lines into the real ledger.** Measure is not act; a dry
   run now gets a throwaway copy. The first version of that test passed *against the bug*
   because its fixture found nothing and recorded nothing. Mutation testing caught the vacuous
   test; review did not.
3. **The measurement class compared tuples in memory to lists on disk**, so every run
   "found" a stale artifact and every repair rewrote it — a fix that fires forever is churn
   wearing the costume of a fix.
4. **It reported 2/2 closed (100%) while `enforce_goal_hierarchy.py` still failed.** The
   guard resolves receipts at `ref:path`; the repair only becomes true when a commit exists.
   A number that disagrees with the enforcer is the number that is wrong. Closure is now
   credited on *certification*, and `--certify <result.json>` re-asks the ref afterwards.

Each of the four is pinned by a test that was confirmed to fail in the world where the
property breaks (five mutants: no canonicalisation, trust-the-fixer, scan-the-archive,
dry-run-writes, credit-on-verification — each killed exactly one test).

### What this does not mean

The closed class is bookkeeping. No capability, no routing, no reach changed. The honest
limit, stated in the module: **unattended repair is confined to facts derivable from the
artifact itself** — a blob sha, a derived key, a recomputation. Capability ids, routing
bindings and semantic choices are not derivable, and no class here touches them. That
boundary is the next thing to widen, and widening it is where unaided closure rate stops
being a bookkeeping number.

---

## Execution log 7 — the system infers its own checking predicates (2026-11-04)

The loop in log 6 was still mine in the way that matters: I wrote its three defect classes. The
system executed them and reordered them; it did not work out *what to check*. So the ceiling
was my enumeration.

`canonical/tools/derivation_inference_v1.py` removes that ceiling for one kind of question:
**which numbers in this repository are pure functions of the tree, and of which function?**

The hypothesis space (8 candidate derivations) is supplied by a person. The attribution is
not. From 368,460 recorded values in 9,550 documents:

| measurement | result |
|---|---|
| fields whose meaning was inferred (`ATTRIBUTED`, ≥90% agreement) | **66** |
| fields declared ambiguous (`UNDERDETERMINED`) | 5 |
| fields it cannot explain (`UNEXPLAINED`) | 920 |
| fields with too little evidence to say | 37,876 |
| mean agreement on attributed fields | **99.26%** |
| held-out records of the same field | **8,617 / 8,716 = 98.86%** |
| contexts withheld whole, rule learned only from others | **772 / 773 = 99.87%** over 17 |
| anomalies inside fields it *does* understand | 227 |
| model size written to disk | 991 fields, 218 KB |

The learned model is persisted (`canonical/verification/DERIVATION_MODEL_V1.json`) and consumed
by `self_maintenance_loop_v1` as a fourth defect class, `DERIVED_VALUE_DISAGREES`. Live proof,
unattended, on a document the system had never seen with a field nobody named:

```
found 1  closed 1  certified 1   (bytes: 1 -> 59,476, the real size of the file it names)
```

### A hypothesis of mine, falsified by the system

`git_blob_sha` binds at only **85.4%** against the current blob. I proposed that receipts record
the file *as it was when the receipt was written*, and implemented `git_blob_at_record_commit`.
It binds at **76.7%** of the records it can compute — **worse than the hypothesis it was meant
to replace**. The records do not say that. Kept in the space, reported as beaten.

### And a headline of mine, retracted

Before that: 40 of 40 sampled disagreements under `git_blob_sha` were shas that "never existed"
— 2,864 disagreements, apparently systematic fabrication. **It was the sandbox.** The clone was
depth-1 (8 commits). After `git fetch --unshallow` (21,236 commits), a 60-record sample gives
**43 HISTORICAL_BLOB, 17 REAL_OBJECT_OTHER_PATH, 0 NEVER_AN_OBJECT**. Every single "fabrication"
was a real blob from history I had not fetched.

The instrument now refuses to make that claim in a shallow clone: it emits
`UNVERIFIABLE_IN_SHALLOW_CLONE` and marks the conclusion `PROVISIONAL`. Pinned by a test, and
by a mutant that removes the guard.

### Four errors in this module, all found before landing

1. **Shape granularity.** Keying on the exact sibling-key set produced 477 shapes with 1 record
   each and everything `INSUFFICIENT_SUPPORT` — a measurement of my key, not the repository.
   Split into FIELD (what is asserted) and CONTEXT (where it appears): inference at field,
   transfer measured at context.
2. **Booleans as sites.** 100,893 policy decisions were counted as unexplained "derivations".
   A `true` in a governance document is a choice, not a computation over bytes. Excluded.
3. **Name-only model.** It could never say anything about a field it had not seen. Added a role
   tier (value class × names-a-path) that *can*, and kept it separate: an analogy at ≥80% is
   reported as a suspicion and is **never allowed to rewrite a document**. Pinned by a mutant.
4. **A 70%-explained field marked `ATTRIBUTED`.** A stale `.pyc` from a mutation run made this
   look like a threshold problem; clearing caches showed the threshold was real and the test
   that caught it is now permanent — a threshold nobody pins is a threshold that drifts.

Mutation results: ignore shallow blindness → 1 test fails; let an analogy repair → 1 fails;
lower the binding threshold → 1 fails.

### The honest limit, stated as the next target

The hypothesis space is still supplied. The system picks among eight derivations a person
imagined; it does not invent a ninth. `widen()` exists and composes candidates from primitives,
but on this corpus nearly every unexplained field is a count, a score or an index that no
function of the tree produces — so it accepts few and says so. **The next real widening is not
more candidates; it is a hypothesis space that grows from the falsifications.** Log 6's classes
were mine; log 7's predicates are inferred; log 8 has to make the *space* learned.

No capability credit. Knowing that a recorded number equals a function of the tree is not
being capable, and neither is repairing the document that quoted it.

---

## Execution log 8 — the hypothesis space itself, and a correction to log 7 (2026-11-04)

Log 7 said the honest limit was that "the hypothesis space is still supplied by a person". This
removes that limit for one class of question, and in doing so found that last log's headline
number was inflated.

### The space is now generated, not listed

`canonical/tools/derivation_grammar_v1.py` replaces eight hand-written `Candidate(...)` lines
with a grammar and searches its cross product:

```
recipe = transform( arrange( elements ) )
elements   5   file bytes | committed bytes | path text | the record's path list | value list
arrange    4   raw | sorted-newline | sorted-comma | deduplicated-sorted-newline
transform  4   length | sha1 | sha256 | git blob
```

| | |
|---|---|
| naive cross product | 80 |
| duplicates of the identity that a naive cross product generates | 36 |
| **semantically distinct recipes** | **44** (+4 structural counts = 48) |
| previous layer could express | 8 |
| coverage of the previous layer | **6 of 8** — the grammar cannot select "the commit that last wrote this record" |

Measured on the full corpus (368,658 records, 9,553 documents, 38,911 fields):

| | |
|---|---|
| fields the previous layer explained | 34 |
| additional fields learned from the generated space | **2** (1 of them needs a recipe the old list could not express) |
| recipes tried searching **337** unexplained fields | 3,107 |
| values that refuse a content derivation, with evidence | **139** |
| not found in the generated space (our limit, labelled as ours) | 196 |
| accounting | 38,911 of 38,911 fields, `closes=True` |

The 139 are split into three facts about the data, kept separate from the one fact about the
instrument:

```
INPUTS_NOT_RECORDED             15   identical recorded inputs, different values
UNDECIDABLE_FROM_CORPUS        120   constant across every record
EVIDENCE_OF_WRITE_TIME_CHOICE    4   tracks position or order
NOT_FOUND_IN_GENERATED_SPACE   196   FACT_ABOUT_INSTRUMENT, never counted as non-derivability
```

### The correction: 32 of 66 was measured on a subset

`derivation_inference_v1` counted agreement only where the candidate produced a value **at all**.
A derivation that computed for 3% of a field and was right about all of it scored 100%. The
audit: **32 of the 66 "attributed" fields had their winning derivation computing on under 90% of
their records**, the worst at 2.5% (`git_blob_at_record_commit`, 160 records, one of which it
could answer).

With `COVERAGE_MIN = 0.90` as a precondition:

| | log 7 claimed | corrected |
|---|---|---|
| fields attributed | 66 | **34** |
| attribution agreement | 99.26% | 99.60% (higher, on a smaller and honest set) |
| attribution coverage | not measured | **99.17%** |
| held-out accuracy | 98.86% (8,617/8,716) | **98.93%** (3,408/3,445) |
| live predicates the loop may act on | 66 | **34** |

Half the model was asserting more than its evidence covered. The loop now repairs on 34
predicates instead of 66, and the 32 dropped ones were exactly the ones that would have rewritten
documents on the strength of a corner.

The same bug was in the new module in a worse form: `countdistinct|pathlist|raw` "bound" a
396-record field at 100% by computing on **47** records and being silently skipped on the other
349. Coverage is now a precondition in both layers, and where it fails the state is `LOW_COVERAGE`,
not `ATTRIBUTED`.

### Two more errors, and one that was mine to be embarrassed by

1. **`git_blob_sha` was "proven nondeterministic"** — a field that demonstrably *is* a blob id.
   Adding the writing commit to the input signature did not fix it, so I looked at a collision
   instead of simplifying: five action intents quoting the same path's blob at five different
   commits, **none of which the receipt names**. The verdict is now `INPUTS_NOT_RECORDED`, which
   says what is true — the record is under-specified — instead of claiming a proof.
2. **36 of 80 generated recipes were duplicates.** Sorting, splitting or deduplicating a *single*
   element is the identity, so `len|file|sortnl` and `len|file|raw` are the same hypothesis. Worse
   than wasted search: a duplicate could win a field and be credited in the yield table under a
   name that learned nothing.
3. **A constant-output recipe can match by coincidence.** `count|pathlist|raw` returns 1 for every
   one-file record. Rejected now by `_is_constant_predictor` — a derivation that yields the same
   value for every record explains nothing about any of them.

### What is learned now, and what that changes next run

Each primitive carries a yield (`confirmed` count), persisted to
`canonical/verification/DERIVATION_YIELDS_V1.json`. Search order is by yield, so a confirmed
recipe is tried first next time. Current leaders: `pre:raw`, `transform:countdistinct`,
`elements:pathlist`. That is learning that changes behaviour across runs, and its unit is
**recipes tried** (3,107 this run), never a solve rate.

Mutation results — each mutant must kill a test:
drop the coverage precondition → fails; allow constant predictors → fails (only after the fixture
was rebuilt: the first version let `UNDECIDABLE_FROM_CORPUS` fire first, so the test passed for
the wrong reason); ignore the holdout → fails; relabel under-specification as our own limit → fails.

### The remaining honest limit

The **primitives** are still supplied. The system composes them, searches them, proves some fields
are not functions of anything it can read, and learns which primitives pay off — but it has not
invented an element type or a transform. 196 fields are `NOT_FOUND_IN_GENERATED_SPACE`, and that
number is a statement about the grammar, not about the repository. The next widening is a grammar
that grows a production from repeated failure, not more primitives typed by hand.

No capability credit. Reproducing a number from the tree is not being capable.

---

## Execution log 9 — the system models itself, and the answer is that it cannot yet (2026-11-04)

Three landings taught the system to explain numbers the repository recorded. All three were
general, verifiable, and none of them made the system able to be **wrong about itself**. That is
the line between a measurement system and a creature: a measuring system always reports what it
did; only a predicting one can be surprised.

So this landing does something none of the previous ones did. It asks the system to predict its
own next action and scores the prediction against what it actually does.

### The number that matters

Using only what the registry already declares about itself, the system predicts which capability
the front door will pick **9 of 32 times — 28.1%**. On the same untouched tree:

```
Fix the off-by-one bug in main.cpp        -> python.source.test_adequacy.v1   (declares python)
Add a function to lib.rs                  -> ...semantic_behavior.compile     (go, python)
Rename the exported function in app.ts    -> ...semantic_behavior.compile     (go, python)
Add a NOT NULL constraint in schema.sql   -> decision.synthesis.typed.stdlib (python)
Repair the C++ source so it compiles      -> source.candidates.enumerate     (go, python)
```

Five of 32 routed requests are answered by a capability that declares a **different ecosystem**
than the request names. Every previous layer checked the tree. None checked the system.

### The experiment, and its honest result

| | |
|---|---|
| model built from the registry's own declaration (holdout) | **33.3%** (5/15) |
| model learned from the system's own observed behaviour (holdout) | **33.3%** (5/15) |
| model learned from 240 **manufactured** experiences, tested on the 49 real requests | **12.5%** (4/32) |

Learning from its own past does not beat its own documentation; learning from manufactured
experience is **worse than the documentation**. Both are reported because both are results.

### The gate failed, and it is pinned as a failure

A trust gate ("distrust unless both models endorse the router's choice") catches **4 of 5**
real defects — and destroys **21 correct answers**. With manufactured experience it catches
**5 of 5** and preserves **0**: it distrusts everything, which is the classic way to look
perfect. Precision against the mechanical label: **0.16**.

A test now fails if a future change makes the gate look better without re-measuring, and fails
if `correct_lost` or `correct_preserved` is dropped from the report.

### The fix I attempted, measured, and reverted

The compiler's own docstring forbids reporting a substitution as a success. A language mismatch
*is* a substitution. So the self-model's five findings were turned into a fail-closed refusal in
`goal_front_compiler_v1.py`, and measured on identical file sets:

| | failing tests |
|---|---|
| without the change | **53** |
| with the change | **62** |

**Nine regressions for five fixes.** Reverted. Reach went 32 → 27 routed, which is the metric
getting *more* honest (it had been counting wrong-ecosystem answers), but a tree that regains
nine failing tests to fix five routes is worse than one that never fixed five. A test now pins
that the law is **not** wired in, and names the numbers that would have to change to re-open it.

### What the system refused to learn from

The only large "behaviour corpus" in the tree — 423 `(sentence, selected)` records in
`ROUTE_REACH_CENSUS_V1.json` — is a templated echo of the registry's own keywords
("archive tar gz bundle manifest package create from"). Training on it would predict my generator
and teach the system nothing about itself. Refused by name, in the report and in a test.

### The deepest finding

**The system has almost no life.** 368,660 records exist about *files*; 49 exist about *its own
behaviour*. A model of self needs experience, and this one has 49 events, one contaminated corpus
it must refuse, and 240 manufactured sentences that make it worse than its own documentation.

The ceiling is not inference. Three layers of inference over a closed book cannot become a
creature, because a closed book never says no. What is missing is a life: situations the system
did not choose, outcomes it did not predict, in a world that refuses.

Next, and it is not another inference layer: give it experience with consequences —
prediction about *executed actions* (does the declared effect hold when the capability actually
runs?), where refusal costs something and the oracle is the result, not the declaration.

No capability credit. A model of oneself is not capability.

---

## Execution log 10 — the oracle leaves the book (2026-11-04)

Log 9 ended with the diagnosis that every previous layer judged the system by a book the system
holds. A closed book never says no.

`canonical/tools/executed_effect_oracle_v1.py` opens it. It takes a capability the registry ships,
builds a world around it, lets it **run**, and asks the only question whose answer the system does
not control:

> did the artifact do what this capability's own declaration promised?

The declaration is `action_template.expect` plus the recomputable part of
`verification.observed_effect` — a *prediction* written down in advance. The verdict never reads
it as evidence; it reads the filesystem.

### The first defect found by execution, in two years of a passing suite

`archive.tar_gz.create_from_manifest` archives the paths a manifest lists and reports
`output_verified: true`. Given ordinary repository files:

```
asked for : ['notes.txt', 'report.md']
archive   : ['m.json']                        <- only the manifest itself
reported  : output_verified = True, member_count = 1
```

`_manifest_paths` silently dropped every path that did not start with `canonical/`, then reported
success over a bundle containing nothing the caller asked for. **No test in the tree caught it
because every test passes `canonical/`-prefixed paths.**

Same defect in `archive_verify_gnu_tar.py`, same filter.

### Reproducible before/after, not a memory of one

`--regress <rev>` replays every situation against the adapter source at that commit and against
the tree, and recomputes both verdicts. On `ec230a32e4`:

| situation | before | after |
|---|---|---|
| `archive_of_plain_repository_files` | **INPUTS_IGNORED_SILENTLY**, artifact `['m.json']` | **EFFECT_HELD**, artifact `['m.json','notes.txt','report.md']` |
| `archive_of_prefixed_paths` | EFFECT_HELD | EFFECT_HELD |
| `archive_of_a_path_that_does_not_exist` | REFUSED_AS_DECLARED | REFUSED_AS_DECLARED |
| `verify_an_archive_that_was_just_created` | EFFECT_HELD | EFFECT_HELD |

**One verdict changed.** Regression check on the archive, compiler, capability-type and unified-
model suites: **the same 4 failures before and after** — all pre-existing, none caused by the fix.

Credit where it is due and nowhere else: **the detection and the verdict came from the oracle
reading the artifact. The repair was authored by the agent.** A test pins that sentence in the
artifact so it cannot drift into a claim the system earned it.

### Two verdicts that will never be merged

```
REFUSED_AS_DECLARED      ARCHIVE_MEMBER_SOURCE_MISSING:canonical/absent.txt
                         The system saying no to a world that does not fit its contract.
                         A good outcome, not a failure to be scored against.
INPUTS_IGNORED_SILENTLY  success claimed over an artifact missing what was asked for.
                         The only verdict here that is a lie about the world.
```

### Learning that changes behaviour

A contradiction demotes the capability: `distrust` is persisted, and from then on the system may
not accept that capability's `expect` field as evidence — it must recompute. Restoring the word
takes **two** independent confirmations, not one, because a single pass can be the same input that
already failed. Mutation-checked: restoring after one pass fails a test.

### The honest denominator

**2 of 141 capabilities could be situated.** 139 could not: no fixture builder exists, and several
need libraries this sandbox does not have (`tree_sitter`, `docx`, `PIL`) or live network and
credentials. The oracle says so in its own output rather than reporting 141.

And what it cannot see, stated in every run: it checks that the artifact reflects the supplied
inputs. A bundle with the right files in the wrong order passes. That is `INDEPENDENT_CHECK_KIND`,
recorded per verdict so nobody has to guess what was established.

### What this does and does not change

It changes one thing that nine logs could not: **the system now has a source of truth it cannot
edit.** That is the precondition for a creature — not its existence. Two situated capabilities is
not a life; it is the first breath, and the honest count is two.

The next widening is the fixture surface: 139 capabilities with no world built for them. Every one
built is a place the system can be wrong in a way it cannot talk its way out of.

No capability credit.

## Execution log 11 — the first thing in this repository that acts without being told (2026-11-04)

Logs 7, 8, 9 and 10 were each a better tool, and each was rejected for the same reason: a tool is
not a creature. Every instrument in the tree ran because a person typed its name. The system had
368,660 records about files in its control and 49 records about its own behaviour, and **zero
processes that decided what to do next**. This log is about that number.

### What was built

`canonical/runtime/organism_v1.py` — a long-lived process with its own tick clock. Not a script:
it loads its previous life from `canonical/astra_runtime/state/ORGANISM_V1.json`, keeps an
identity across restarts, and on every tick does the loop the whole plan has been circling:

```
choose a target  ->  write a falsifiable prediction  ->  act  ->  observe  ->  compare  ->  change what it does next
```

The chooser scores **targets**, not organs, with an upper-confidence bound over each target's own
record: a target never attended is infinitely attractive, so every target is seen before any is
revisited. Settled targets retire after two confirmations; the whole set re-opens after 25 ticks.
Its organs are existing authority — the executed-effect oracle and four self-maintenance defect
classes — and the process **may not widen its own organ set** (`PROTECTED_ACTIONS`, and a test).

### The four things it did that nothing here has done

| property | before | measured |
|---|---|---|
| processes deciding what to do next | 0 | 1 |
| defects found and repaired with nobody pointing | — | **2/2** |
| identity across process death | — | `d3f450f0ea72`, `restarts: 1`, ticks 18 → 24 |
| prediction written before the action | — | 32 PREDICTION / 32 OUTCOME, ordered |

One defect was planted while the process was awake and repaired on the first tick it looked: a
size lie in a verification file, `recorded 22726 == actual 22726` afterwards. The second was
planted **while the process was dead**; the restart resumed the same life, noticed it, and
repaired `26838 == 26838`.

### The three failures that mattered more than the successes

**1. It was a scheduler, not a chooser.** The first run scored organs. All targets inside an organ
share a score, an alphabetical tie-break picked the same one, and it took **14 identical ticks on
one target, 0 predictions, 0 surprises**. A chooser whose arms are not the thing being chosen is a
freeze. Fix: score targets; unattended means infinite.

**2. Predictions were looked up under a key that never existed.** `predict()` received the whole
state and indexed `targets[target_id]` where the map is keyed `organ::target`. Every tick was
therefore unpredicted — and an unpredicted tick is counted as *unpredicted*, never as correct,
which is the only reason the bug showed up as a number instead of as a success.

**3. Rest had become permanent ignorance.** A healthy world taught it to retire everything, and
`live()` stopped after six idle ticks. I then broke the archive adapter underneath it — asked for
two files, archived one — and the process **slept through the breakage**, reporting nothing worth
doing, forever. It would have slept while the world was demolished. Fix (`_still_asleep`): a
target resting on a timer is not a target that is gone, so the clock keeps running until it comes
back. Rest is legitimate; sleeping through a changed world is not.

### The measurement this log exists for

A deterministic world cannot teach, so every clean run reports `surprises 0` and proves nothing.
`canonical/tools/organism_hostile_world_v1.py` therefore moves the world **under one continuous
life** and counts:

```
phase 1  healthy world
phase 2  the world silently changes  (the adapter regains the filter that drops plain paths)
phase 3  the changed world, untouched  -> a learner must stop being surprised
phase 4  world restored              -> the old world is news again
```

Three runs, same experiment:

| run | one change costs | restoration costs | surprises while the world held still |
|---|---|---|---|
| before waking | never noticed (`0`, `0` actions) | — | — |
| waking + lifetime modal verdict | **3** | **4** | 0 |
| recency-weighted expectation | **1** | **1** | **0** |

The middle row is the important one. It predicted `EFFECT_HELD` at t35, t38 and t39 because the
*modal verdict of the target's whole life* was `EFFECT_HELD`: a world that had been healthy for
eight ticks outvoted a world that had just broken. A lifetime average is a memory of a dead world.
Expectations now come from the last three encounters, each step back in time halving its vote, so
one new fact beats an old majority. Pinned by
`test_a_long_happy_history_does_not_outvote_a_fresh_breakage`, which fails on the flat window and
on the lifetime average.

### What is real and what is not

| claim | verdict | evidence |
|---|---|---|
| A process here now acts on its own clock, uninvoked | **TRUE** | 136 ticks, 32 actions, no human call inside the run |
| It predicts each action before taking it | **TRUE** | 32/32 outcomes preceded by their prediction |
| It is surprised when the world disagrees | **TRUE** | 2 surprises, both at genuine world changes |
| Surprise changes what it does next | **TRUE** | 3 → 1 surprises per change after recency; it stops repeating the mistake |
| It repairs real defects unattended | **TRUE, N=2** | one planted alive, one planted dead; both verified by file size afterwards |
| It survives process death as the same life | **TRUE** | identity + tick continuity + `RESUME` journal entry |
| It is learning in general | **FALSE** | its world is one adapter and five organs. Nothing here generalises |
| `surprise_early → surprise_late` improves with time | **FALSE, honestly** | `0.0714 → 0.0714`. Surprise does not decay with age, and should not: it decays *per change*, which is the number above |
| Any of this is sentience | **FALSE** | four preconditions, no claim. `SURPRISE_IS_A_BOOLEAN_ABOUT_ITS_OWN_ACCURACY_NOT_A_FEELING` |

### Tests, and the worlds in which they must fail

17 tests in `canonical/tests/test_organism_v1.py`. **14 mutants, 14 killed**, each in a world where
its claim is false: prediction written after the outcome; never retiring; never surprised; a
restart beginning a new life; no first-visit priority; flat curiosity; unpredicted counted as
correct; state not saved; a loop organ predicting from hope instead of history; grinding a retired
target; flat curiosity after learning; lifetime average instead of recency; flat window count;
ignoring recent history.

One mutant **survived the first pass** and was the most useful result of the day: `unpredicted`
being journaled as `surprise: false` instead of `None`. The summary did not notice, because
`unpredicted` is derived from counts and never reads the field — but anyone replaying the journal
would have read that tick as a prediction that held. The test now pins the journal, not the
summary.

### One thing this log found in its own past

Committing this work surfaced a violation in **log 9**: `test_capability_self_model_v1.py:179`
ended with `assert ... or True`. That is not a test. It cannot fail, it was reported as passing,
and it was counted in log 9's "62 with" figure. The repo integrity guard flagged it as
`TAUTOLOGICAL_ASSERTION` and is now clean (17 rules, 0 violations).

What the assertion was reaching for is also false: it claimed the reverted language law survives
as a measurable instrument while staying out of the compiler, and after the revert the mechanism
is in **neither** file. Only the safety property — the compiler must not silently regain a
nine-test regression — is pinned now. The rest is a comment saying so, because a claim about where
a reverted mechanism lives would encode a *limitation*, and a limitation may not block a widening.

### What this does not fix

The unaided closure rate is still **0** for classes that matter. What exists is a loop that closes
defects it is handed, on its own clock, and remembers the encounter. It cannot *find* a class of
defect nobody has written a detector for; it has four detectors and one oracle situation set, and
widening either is still a person's job. That is the next thing, and it is the thing that
separates a maintenance daemon from a creature that grows.

Drift guard unchanged: red on `LIVE_CHALLENGER_FRONTIER_EXEMPTION_NOT_ALLOWED_FOR_ACTION_KIND`,
awaiting an owner decision. No capability credit.

## Execution log 12 — it has a model now, and the model says the world is too thin (2026-11-04)

Log 11 was rejected for the fifth time, correctly. The organism acted, predicted, was surprised and
survived a restart, but its prediction machinery was a **lookup table**: `effect::archive_of_plain_
repository_files` learned a verdict at t35 and that knowledge was bound to a string. Given a second
capability that silently drops inputs, it would have been surprised again, from zero. A system that
can only remember cannot get better at anything it has not already done.

### What was built

**`canonical/runtime/belief_v1.py`** — a model of the world, not a table of the past.

* It predicts from **senses**: numeric signals readable before acting.
* It **grows its own distinctions**. It starts as one leaf with the base rate and adds a split only
  when the split earns it. The candidate space is generated mechanically from every signal and
  every observed threshold; nothing is enumerated by hand.
* Acceptance requires all of: **improvement on average, improvement in every group, p < 0.01/rank
  against a shuffled-verdict null, and survival under a second, independent grouping.**
* It **abstains** when it knows nothing, and abstention is never scored as a correct answer.

**`canonical/tools/capability_world_v1.py`** — a world for every capability the registry declares.

| before | after |
|---|---|
| 4 situations, all hand-written, one adapter | **77 capabilities × 6 worlds = 462 observed outcomes** |
| a person chose each input | every declared input synthesised from its own name, in a fresh directory, in its own process, under a timeout |
| 2 of 141 capabilities situated | 77 of 141, with the 64 excluded for stated reasons (61 reach a subprocess/network/browser, 3 have no adapter on disk) |

Verdict distribution over 462 worlds: 270 CRASHED, 137 REFUSED_NAMED, 30 CLAIM_CHECKED,
13 CLAIM_FALSE, 6 CLAIM_FIELD_ABSENT, 6 NO_OUTPUT.

### The measurement this log exists for

Can it predict what a capability will do **before running it**, for a capability it has never run?
Split **by capability**, so no held-out capability appears in training in any world.

| number | value |
|---|---|
| holdout accuracy | **0.4839** |
| majority baseline | **0.4839** |
| lift | **0.0 (0 examples)** |
| log 11's identity table | **0.0** — it answers nothing for a capability it has never met |
| in-sample accuracy | 0.5637 (memory, not learning) |
| distinctions accepted | **0** |

**The model learned nothing on this world, and it was right not to.** A permissive tree with all
guards removed reaches **CV 0.637 against 0.584** — a real +5.3 points, while scoring **0.861
in-sample**. So the senses carry a little signal, the optimism gap is large, and my gate at
n=77 capabilities is too strict to separate +5.3 from luck. Reported as such: not earned.

The most tempting number in this log was a hand rule that scored **0.729** against a 0.542 baseline
on one holdout split. It was an artifact: on that split the base rate happened to be REFUSED while
the full world's base rate is CRASHED, and the rule's two buckets both have CRASHED as their
majority. A rule that agrees with the base rate is not a discovery.

### Six real bugs, all found by the measurement, none by reading the code

1. **Information gain with the sign reversed.** It preferred the split that explained the *least*
   about the verdict, and chose a noise signal over the informative one.
2. **Growing from an empty leaf.** The baseline scored 0.000, so every candidate looked like a huge
   improvement. A model always has a prior; the question is whether a distinction beats it.
3. **A permutation test that failed open.** A cursor ran past the end of a shuffled list, emptied a
   bucket by the third fold, and returned p=1.0 for a perfect distinction. It fails closed now.
4. **Fold deltas with the sign reversed**, so a +0.69 improvement on every fold was recorded as
   −0.69 of harm and a perfectly learnable world was rejected as noise.
5. **Single-slice validation.** Eight validation capabilities were so unrepresentative that an
   undifferentiated leaf scored 0.903 there and 0.484 on the real holdout. Selection is now by
   folds over groups.
6. **A gate that was too loose.** A 2% margin accepted 27 splits in 20 pure-noise worlds. Now:
   **1 in 20**, with the true rule still detected (1.000 against a 0.515 baseline, and 19 of 20
   noise worlds refused).

### Wired into the creature, not beside it

`organism_v1.tick` now asks the model first and falls back to the target's own record only when the
model abstains (below 3 observations or 0.75 confidence). Every experience teaches the model, and a
**surprise is the only event that re-grows it** — because a distinction is only worth adding when
the current one was wrong. The model lives in the organism's persisted state, so it survives
restarts the same way its life does. The journal records `from_model` and `first_visit` per
prediction, so the transfer claim is auditable rather than asserted.

Live, 24 ticks, fresh state: 14 actions, 10 predicted, 2 surprises, **2 predictions from the model**,
**0 of them on a first visit**, 2 re-grows. The creature speaks through its model; it does not yet
speak about anything it has never seen.

### What is real and what is not

| claim | verdict | evidence |
|---|---|---|
| It has a falsifiable model rather than a lookup table | **TRUE** | 9 tests; a distinction must beat a shuffled null, every group, and a second grouping |
| Its idea space grows without a person enumerating it | **TRUE** | candidates generated from all senses × all thresholds; 5/5 mutants killed |
| It refuses structure in a world that has none | **TRUE** | 1 accepted split in 20 noise worlds |
| It learns a rule it can see, out of group | **TRUE** | 1.000 holdout vs 0.515 baseline |
| It predicts an unrun capability better than the base rate | **FALSE** | 0.4839 vs 0.4839, 0 examples; ceiling +5.3 not separable at this n |
| The world grew from 2 situations to 77 | **TRUE** | 462 worlds, 64 exclusions each with a stated reason |
| A bigger world means better senses | **FALSE** | more worlds, same thin senses; the ceiling moved 5 points, not 25 |

### What this says about the approach

The binding constraint is no longer the model, the loop, or the agenda. It is **what the body can
see**. Six worlds per capability and a static read of its source text predict almost nothing about
whether it will refuse, crash, or lie — the optimistic in-sample number (0.861) and the honest
cross-validated one (0.637 against 0.584) are the whole gap between a system that looks smart and
one that is.

The next widening is therefore sensory, not structural: a capability's outcome depends on what it
does with a *malformed* thing, and the only way to know that is to have seen it handle one. That is
a claim to test, not a conclusion to assert. No capability credit; unaided closure for classes that
matter is still 0. Drift guard unchanged.

## Execution log 13 — the world is built by the capability's own refusal (2026-11-04)

Log 12 ended with a bad number and an honest reading of it: on 462 mechanical worlds the model
learned **nothing**, and a permissive tree could only reach +5.3 points over the base rate. The
reason was visible in the verdict list and I had not looked at it.

**270 of 462 worlds ended in CRASHED.** Of those, 127 were `FileNotFoundError` on a path my own
fixture invented, 23 were a JSON file I wrote as garbage on purpose, 70 were a package this machine
does not have. That world was mostly a measurement of *me*. A world that is mostly an artifact of
its builder cannot teach anything, and no model improvement was ever going to fix it.

### What was actually in the failures

29 of the crashes were the capability **naming the world it wanted**:

    RuntimeError: SACCR_INPUT_SHAPE_REJECTED:need {"trades": [non-empty]}
    ValueError:    RELEVANCE_INPUT_NOT_JSON:JSONDecodeError
    FileNotFoundError: [Errno 2] No such file or directory: '<the path it actually wanted>'

That is a specification written in a refusal. So the world does not have to be guessed, and it does
not have to be enumerated by a person: **start with the smallest world, run, read the refusal,
change one thing, run again.**

`canonical/tools/world_forge_v1.py` does that. Seventy lines of operators, each keyed on an
exception class or on the shape of a message — never on a capability id, which a test checks
against all 141 registry entries and all 130 adapter names.

### Measured

| | before | after |
|---|---|---|
| capabilities that reach a verdict of their own | **31** of 58 | **36** of 58 |
| gained | — | **5** |
| rounds needed, when it worked | — | 1, 1, 2, 3 (33 needed none) |

The five gained: `decision.synthesis.verify.stdlib`, `evidence.claim_relation.generic_units.stdlib`,
`plain_goal.bound_capability.grounding.verify.stdlib`, `source.objective_relevance.rank.bm25`,
`test.slice.never_miss.v1`. Four of them reached **CLAIM_FALSE** — in the world they themselves
specified, their own declared claim did not hold. That is a verdict about the capability in a
synthesised world, not proof it is broken, and it is stated that way in the artifact.

Stopped by: 12 `UNREPAIRABLE_MISSING_PACKAGE` (PIL, openpyxl, sympy, pypdf,
source_candidate_provenance_verify — installing one is spending, forbidden in a credited path),
6 `UNREPAIRABLE_NOT_UNDERSTOOD`, 3 loop-with-no-progress, 1 rounds exhausted.

### The first version repaired nothing at all

0 gained on the first run. Both causes were real and both were mine:

1. The shape parser demanded JSON, and `{"trades": [non-empty]}` is not JSON. Now `[non-empty]`
   is read as *one element*, which is what it means, and the world it asks for gets built.
2. Every path was resolved against **the repository**, so a path inside the temporary world was
   reported as unreachable, and the only repair that could have worked was refused for being
   impossible.

Five capabilities became drivable when those two were fixed. Neither was findable by reading the
code; both were findable by reading the refusals.

### A finding that is not a fixture problem

An adapter that resolves a path against the working directory instead of the `root` it was handed
is a capability **escaping its own world**. The forge refuses to patch it — writing the file it
wants, wherever it wants it, is the fixture covering for the capability — and names it
`UNREPAIRABLE_ADAPTER_ESCAPES_ROOT`. There are adapters in this registry that do it. That is a
defect class nobody has a detector for, and it belongs to the oracle, not to the forge.

### It is a faculty, not a tool

`ForgeOrgan` lives inside the organism. Its targets are the capabilities it cannot drive (10, after
the missing-package ones are excluded as unfixable); its action is one repair round; its
observation is whether the capability now speaks for itself. It is attended to on the organism's
own clock, like every other organ, and it is subject to the same rule: a prediction before the
action, surprise when the world disagrees. First tick, live: predicted `DECLARED`, observed
`STILL_CRASHING:UNREPAIRABLE_NOT_UNDERSTOOD`, surprise — and the model learned from it.

### What is real and what is not

| claim | verdict | evidence |
|---|---|---|
| The system builds worlds from its own failures | **TRUE** | 5 capabilities gained, each with the repair trail recorded |
| The repairs are generic, not per-capability | **TRUE** | a test searches the operator source for all 141 ids and 130 module names; none appear |
| A missing package is never pretended away | **TRUE** | 12 counted unreachable, named, unpatched |
| It can drive a majority of the registry | **FALSE** | 36 of 58 sandboxable; 12 blocked by spend, 6 unexplained, plus 63 not sandboxable at all |
| This makes the model predictive | **UNKNOWN, and not claimed** | the +5.3 ceiling from log 12 has not been re-measured on the repaired worlds |
| Unaided closure for classes that matter | **STILL 0** | the forge closes *fixture* gaps, not capability gaps |

### The next honest step

Re-measure the transfer number on the forged worlds. If the ceiling moves because the worlds are
now meaningful rather than because the model changed, that is the signal that log 12's bottleneck
was the world all along. If it does not move, then the senses really are the limit and the answer is
different. Either way it is a measurement, not a claim — and it is cheaper than anything else on the
list.

No capability credit. Drift guard unchanged.

### Correction, same day: the faculty almost widened the organ set

Adding `ForgeOrgan` conditionally — *if it has targets, add it* — broke
`test_the_organism_cannot_widen_its_own_organ_set`, and the test was right. An organ whose
existence depends on a file on disk is a faculty that grants itself faculties the moment someone
writes that file. The set is now a closed literal, `ORGAN_NAMES`, used by both the module and the
test, and membership is asserted identical across two builds. **Targets may depend on the world;
organs may not.** 35 tests pass with the correction in place.

## Execution log 14 — curiosity, and the 962 findings that were all mine (2026-11-04)

The question asked again was the right one. So I measured the thing I had never measured:

```
every target the organism can ever attend to   14
of those, typed by a person                    14
```

Thirteen logs produced initiative, surprise, persistence, a generalising model and a world-forge.
**It had an agenda and no curiosity.** Its entire universe was the list I wrote, in a repository
holding roughly twenty thousand checkable claims. That is what "static code" means, and no amount
of machinery around a fourteen-item list changes it.

### The first principle

**Every check is a test of a claim.** A detector has to be enumerated by somebody. A claim is
already written down. Counted here on 2026-11-04:

| source | checkable claims |
|---|---|
| registry (`result_fields`, `requires`, `limitations`, `provides`) | 1,916 |
| verification artifacts (hash, size, path, count fields) | 17,121 |
| behaviour-asserting docstring sentences | 340 |
| assert statements | 14,662 |

`canonical/tools/claim_miner_v1.py` mines them and tests them. **20,946 hypotheses, 0 enumerated by
a person.** The hypothesis space grows whenever anybody writes anything.

### The part that matters more than the mining

The first run reported **962 contradictions**. Almost none were real: prose sentences matched as
paths, the fraction `9/10` matched as a path, a capability id matched as a file, `payload_sha256`
compared against an unrelated file in the same row, and a recorded count compared against the
present. **A miner that reports everything is indistinguishable from a working one until somebody
checks**, which is exactly the trap this repository exists to avoid.

Six rules now stand between the corpus and a finding, each one written because it was violated:

| rule | what it stopped |
|---|---|
| a value is a path only if it is *shaped* like one | prose, `9/10`, capability ids |
| a hash pairs only with a **same-stem** path in the same row | `payload_sha256` vs another file |
| two quantities sharing one stem are **unpaired** | one file, two subjects, two false findings |
| a recorded **count** describes a moment | history reported as a fault |
| the named thing must have **ever existed here** (git decides) | claims about *other* repositories |
| the subject must not have **changed since** the document (git decides) | stale-by-design hashes; all 5 survivors were this |
| a field missing on a **degraded** path is not a false claim | 10 of 11 behavioural contradictions |

Result:

| verdict | count |
|---|---|
| HOLDS | **5,608** |
| HISTORICAL (true when written) | 11,058 |
| UNPAIRED (cannot be tested) | 2,881 |
| UNTESTABLE | 1,393 |
| **CONTRADICTED** | **6** |

Verified by hand: five of the six are still my mispairings. **One is real.**

### The one real finding

`python.software.request.semantic_behavior.compile.v1` declares 20 `result_fields`, including
`acceptance_program_sha256`. Its adapter:

```python
result = compile_request(task_text)
if result.get("coverage_complete") is True:
    program = render_test(result)
    result = {**result, "acceptance_program_sha256": _sha(program.encode("utf-8"))}
...
    return {**result, ..., "output_verified": True}
```

When coverage is incomplete the hash is never computed — and the capability **still returns
`output_verified: True`**. A declared output absent from a run that reports success. Same shape as
log 10's finding, in a capability I had never looked at, found by testing a claim nobody asked me
to test.

It is a lead, not a proven defect: whether that path *should* be verified is a judgement. It is
recorded as such.

### The structural change

`DoubtOrgan` is inside the organism. Its targets are claims, mined at runtime. The creature's
universe went from **14 targets I typed to 1,130 it found**: 1,106 behavioural claims plus the
forge's 10 plus the 14 that were already there. Live, 14 ticks: all on doubt targets, 14 predicted,
**11 predictions came from its own model**, 3 surprises.

And there is an honest problem in that run: 860 of the 1,106 behavioural claims are UNTESTABLE
because the forge cannot yet drive their capabilities. The creature now mostly doubts things it
cannot settle. Widening the world is what makes curiosity pay — the two systems are one system.

### What is real and what is not

| claim | verdict | evidence |
|---|---|---|
| The system generates hypotheses without a person listing them | **TRUE** | 20,946 mined, 0 enumerated; a test fails if that number is ever above zero |
| Its target set now grows with the corpus | **TRUE** | 14 → 1,130; targets are mined, organs are still closed |
| It found a real defect nobody pointed at | **TRUE, N=1** | declared field absent on a success path, code cited |
| Precision is good enough to trust the volume | **PARTLY** | 962 → 6, and 5 of those 6 are still mine |
| Most claims can be settled | **FALSE** | 5,608 hold, but 2,881 unpaired and 1,393 untestable |
| Unaided closure rate for classes that matter | **STILL 0** | one lead is not a fixed and proven defect |

### What the deepest layer says

The thing that was static was never the loop, the model or the agenda. It was **where the
questions come from**. A creature that is handed its doubts is a maintenance daemon no matter how
good its clock is. A creature that reads what the world says about itself and asks whether it is
true has a universe the size of everything written down.

The next widening is not more claims and not more organs. It is making the 860 unsettleable claims
settleable — because a doubt you can never resolve is not curiosity, it is noise with a schedule.

No capability credit. Drift guard unchanged.

### Same-commit note on the closed set

Adding `doubt` moved the organ-set pin, deliberately and in this commit, with the test updated
beside it. The property being protected is not "the set never changes" — it is "the set never
changes *at runtime*, because of something on disk". A closed set with an explicit, reviewed edit
is the mechanism working; a set that grows because a file appeared is the bug.

## Execution log 15 — the world got wider, and the gap that is left is not code (2026-11-04)

Log 14 ended with a number that made the next step obvious: the creature doubted 1,106 claims and
could settle **245**. A doubt you cannot resolve is not curiosity. So this log is only about
widening the world, and about reporting honestly where widening stops working.

### Three lies the harness was telling

Each of these made a capability look worse than it is, and each was found by measuring rather than
by reading.

**1. A caption is not a capability.** The unsafe check was `if "subprocess" in source`. The word
appears in docstrings and in `"required": ...` keys. **Eleven capabilities — 122 claims — had never
been testable because of prose.** An AST answers the question the substring was trying to ask:
what does this code import, and what does it call. 61 exclusions became 50, and the 50 are real.

**2. A refusal that exits was recorded as silence.** One adapter printed its error as JSON and
called `sys.exit()`, which killed my worker before it could report. Six capabilities were filed as
`NO_OUTPUT` — *the harness's problem, described as the capability's silence.* The worker now catches
`SystemExit` and reports it as a refusal, and it extracts the adapter's own `"reason"` so the forge
can read the world specification instead of my placeholder.

**3. The last line of stdout is not necessarily mine.** The forge parsed `lines[-1]` as its verdict.
An adapter that prints JSON owns that line. Results are now written behind a sentinel; a result that
cannot be told apart from the world's chatter is not a result.

### Two goals, not one

A refusal is a **good** outcome for a capability and a **dead end** for a claim about what it
returns. The forge had a single notion of "finished", so 24 capabilities refused cleanly and settled
none of their 222 claims. There are now two goals — `DECLARED` (it spoke) and `OUTPUT` (it did the
thing) — and the claim miner asks for `OUTPUT`.

### What widened

| | log 14 | now |
|---|---|---|
| capabilities attempted | 58 | **88** |
| reaching a verdict of their own | 31 | **61** |
| producing output (settleable) | 12 | **37** |
| **behavioural claims settled** | **245** of 1,106 | **286** of 1,106 |
| claims contradicted | 1 | 1 (the same one) |

### The boundary: satisfied, not removed

**50 capabilities import `subprocess`, `socket` or a browser, and 413 claims live behind them.**
The refusal to run them is a safety property — an adapter that shells out can edit the tree it is
standing in, and one already did in log 12.

So the boundary is satisfied instead of moved: the capability runs inside a **throwaway
`git archive HEAD` copy**, and — the detail that makes it real — it is **imported from the copy**,
so every path it derives from `__file__` points inside the copy. Then the copy is destroyed, and the
real tree is checked before and after.

Measured over all 50:

| | |
|---|---|
| capabilities behind the boundary | 50 |
| produced output in a sandbox | **4** |
| claims now settleable | **35** |
| **real tree changed by any run** | **False** |

That is a small yield, and it is the finding, not a failure of the sandbox.

### Why widening stopped paying

Every remaining refusal is a **domain** requirement, not a fixture error:

```
MODULE_MUST_BE_PY            ANCHOR_NOT_DIRECTORY        MEASURED_TREE_BYTE_LIMIT
PYTHON_LIBRARY_CONTRACT_INCOMPLETE   PYTHON_CODEC_CONTRACT_INCOMPLETE
```

and the rest need tools this machine does not have: `PIL`, `openpyxl`, `sympy`, `pypdf`,
`tesseract`, `zbarimg`, `pandoc`, plus npm and apt packages. No generic operator can invent a
tesseract binary. **The remaining ~800 claims cannot be settled by better code. They need either
spend or an environment that has the tools.**

I did add the two operators that *are* still generic — a named argument must end in `.py`, a named
argument must be a directory — because those are about shape, not domain. They moved four
capabilities. The rest I refused to add, because an operator per capability is a person's work
wearing a machine's clothes, which is the exact thing the no-names test exists to stop.

### One idea I measured and rejected

Static testing: "does the declared field appear anywhere in the adapter's source?" It would cover
all 141 capabilities without executing anything. Calibrated against the 12 capabilities where I have
execution ground truth: **99% precision** on the "present" direction (97 of 98 claim-instances) —
genuinely good.

Then I looked at where it would actually fire: **31 claims**, and the ones I inspected are all
*delegation* — the keys are built by an imported module, so the adapter's source legitimately does
not contain them. Static absence would have been a false-positive generator. **Rejected, not
built.** The measurement is in the log rather than in the code because a weaker oracle that mostly
fires wrongly is worse than no oracle.

### What is real and what is not

| claim | verdict | evidence |
|---|---|---|
| The harness no longer reports its own failures as the capability's silence | **TRUE** | 6 mutants around sentinel / SystemExit / goal all killed |
| The unsafe check now means what it says | **TRUE** | 122 claims freed from comments; `os.system` still blocked (mutant killed) |
| Subprocess capabilities can be run without touching this tree | **TRUE** | 50 runs, `real_tree_changed: False` |
| That unlocked their claims | **FALSE** | 4 of 50, 35 of 413 claims |
| Most claims can be settled | **FALSE** | 286 of 1,106 = 26% |
| The remaining gap is a code problem | **FALSE** | it is missing binaries and domain worlds |
| Unaided closure for classes that matter | **STILL 0** | one lead, still unfixed |

### What the deepest layer says now

Three logs have widened the world and the settled-claim number has gone 245 → 286. The curve is
flat because the constraint was never the world-builder — it is that **most of what this repository
claims about itself cannot be checked without tools it does not have.** That is an authority
question (may I install things?) and a scope question (which capabilities matter at all), not an
engineering one.

I will not spend money to find out, because that is a stated law. So the honest next move is not
another widening: it is to **fix the one real defect this machinery found** and prove the fix with
the same oracle that found it — closing the loop from "doubt" to "settled", which is the first time
in fifteen logs that the system would have found, fixed and verified something with nobody pointing.

No capability credit. Drift guard unchanged.

---

## Log 16 — It grew a word for something nobody told it about

Log 15 widened the world; this one attacks the layer underneath it. Every belief this system has
grown, in fifteen logs, has grown **inside a vocabulary I chose.** `belief_v1` picks thresholds on
columns that already exist. Add a column, it gets smarter. It cannot add the column. That is static
code wearing a model's clothes: knowledge that grows, in a language that does not.

So the axis is **the vocabulary**, and the question is brutal: can this thing invent a distinction
that nothing in its senses expresses, decide for itself that the distinction is worth keeping, and
then think in it?

### What was built

`canonical/runtime/vocabulary_v1.py`. A fixed algebra (abs, log1p, sign; add, sub, mul, div,
mindiff, maxdiff, ratio_gap), expressions as tuples, `discover` gated on held-out groups, on
fold-internal thresholds, on helping in *every* fold, and on a permutation null. Then `dedupe`,
`augment`, `check_still_earning`.

Wired into `organism_v1.tick`: every sense passes through the creature's own vocabulary before the
model sees it, so an invented dimension is a dimension it thinks in from then on. Nobody calls it.
No session loop was widened, no tool was handed to a human.

### What it does, measured

Offline — discovered from the training split, then handed to the belief tree, scored on a holdout:

| world | fixed vocabulary | invented vocabulary | what it invented |
|---|---|---|---|
| product | 0.850 | **0.983** | `mul(a, b)`, `add(a, b)` |
| sum | 0.817 | **1.000** | `add(a, b)`, `mul(a, b)` |
| xor | 0.583 | **0.867** | `maxdiff(a, b)`, `mindiff(a, b)`, `sub(a, b)`, `div(a, b)` |
| ratio | 0.617 | 0.617 | `sub(a, b)`, `div(a, b)` — solves nothing |
| noise, 8 worlds | — | **0 invented** | — |

Live — the real `tick` loop, 30 seeds × 160 ticks, same world and seed, the only difference being
whether the creature may invent:

| | frozen | growing |
|---|---|---|
| mean prediction accuracy | 0.447 | **0.684** |
| predictions made | 295 | 1,573 |
| worlds that invented a distinction | 0 | **16 of 30** |
| structureless worlds that invented one anyway | — | **1 of 30** |

Artifact: `canonical/verification/VOCABULARY_V1.json`, regenerated by
`canonical/tools/vocabulary_probe_v1.py --write`. Person-enumerated distinctions: **0**.

### The three things measurement killed in me

**1. A human-chosen number I had not tested.** I gave each signal "three shots" at a threshold and
wrote a paragraph explaining why three was right. Measured: 1, 3 and 6 shots gave the identical
total, 3.483, on four worlds. It is back to one, because one is what the evidence supports.

**2. A trigger that can never fire.** I gated vocabulary growth on *surprise*. Over 140 ticks of a
world built on a product, `vocabulary_checks: 0` — nothing predicted, so nothing could be wrong, so
the creature was never surprised. A system that only re-examines its vocabulary when it is caught
being wrong stays blind exactly while it is confidently ignorant. The trigger is now **inadequacy**:
the model cannot beat the base rate on its own experience.

**3. A held-out test that could not fail.** Inside the loop every target is its own group, so
grouping by target hands back one-example test sets. The creature invented three distinctions on a
world with no structure in it. Folds are now **time blocks** — what it concluded about the past must
survive the present. Live false inventions fell 4 of 30 → **1 of 30**.

And one guard that only muscle closed: a feature can pass its own held-out gate and still make the
learner worse. Inventing on `ratio` took it 0.883 → 0.533. So admission is now decided **by the
model**, on the creature's own held-out experience — if the vocabulary does not beat what it
replaced by more than 0.02, it is set aside and the retirement is recorded.

### Mutation

16 tests in `test_vocabulary_v1.py`, 12 mutants. **10 killed:**

leak threshold from all data · no dedupe · never retire · augment returns its input · admit on
average only · admit on noise (dropped per-fold rule) · unbounded cuts per signal · global top-k
crowding · no pay-for-itself guard · invented senses not actually used · growth never triggers.

**2 survived, and both are reported rather than tuned away:**

| surviving mutant | why it survives | what that means |
|---|---|---|
| drop the permutation p-gate | in 52 measured offline worlds that gate **never fired** — the per-fold rule rejects first | it is a backstop I cannot justify by evidence; kept, labelled, not credited |
| replace time folds with target folds | the pay-for-itself guard rejects what the weak folds would admit | two guards, one job; the second is not independently proven |

### What is real and what is not

| claim | verdict | evidence |
|---|---|---|
| It invents distinctions no given sense can express | **TRUE** | `mul(a,b)` from a product world; 0 person-enumerated |
| Inventing improves held-out prediction | **TRUE (offline)** | 0.850→0.983, 0.817→1.000, 0.583→0.867 |
| It happens in a live loop, not on invocation | **TRUE** | 16 of 30 seeds, 1,573 predictions vs 295 frozen |
| It mostly does not invent on nothing | **TRUE, not clean** | 0 of 8 offline; **1 of 30 live** |
| The `ratio` world is solved | **FALSE** | 0.617 → 0.617 |
| The 0.883 baseline regression is explained | **FALSE** | not reproducible after the quota change; not attributed |
| Distinctions transfer across scale | **FALSE** (log 15, unchanged) | a feature is a threshold with a scale attached |
| Unaided closure for classes that matter | **STILL 0** | bookkeeping 100% (N=2); the real lead, N=1, unfixed |

### What the deepest layer says now

Three logs of widening and the invented vocabulary is the first thing in sixteen that **made the
creature better at something rather than making the world bigger**. But look at what still had to be
true for it to work: I supplied the algebra. `add`, `mul`, `mindiff`, `ratio_gap` — that list is a
person's idea of what combinations are thinkable. The system chose *which* to keep; it did not
choose *what could be built*. The next vocabulary is the one where the operators themselves are
learned, and I will not pretend this log is that.

Authority: **NONE**. Terminal truth: `false`. No capability credit.

---

## Log 17 — The model could not learn a conjunction, and I had not measured it

Log 16 ended by naming its own next layer: the algebra was mine, so invent the operators. I tried
that first, measured it, and it failed. What the failed experiment exposed was worse and more
useful: **the learner underneath could not represent a rule that is not one cut at a time.**

The measurement, on a world whose rule is `a > 0.5 AND b > 0.5`:

```
splits_accepted: 0     accuracy 0.700     majority baseline 0.750
```

It refused to split and predicted the majority class. Worse than a one-line rule. Seventeen logs,
and no log had measured whether this thing can learn anything but an additive boundary.

### Why: a conjunction pays nothing cut by cut

Cut on `a`: above 0.5 the world is still half and half. Accuracy does not move. The gate judges each
cut against the prior, so it rejects, and the pair that *would* work is never built.

### What I tried that failed, because I measured it

| attempt | result | why it was thrown away |
|---|---|---|
| judge the best PAIR before refusing a cut | and 1.000, or 1.000, product 0.883 | **6–7 of 20 structureless worlds admitted a split**, against 0–1 for the gate alone |
| judge by log loss instead of accuracy | — | **57 accepted splits across 10 noise worlds**; more capacity, no control |
| a search-matched permutation null on pairs | noise 6 → 2 of 20 | correct in principle, still not zero, 3× slower |

Every one of those is in the log rather than in the tree, because each is a place I tuned a number
against noise and called it progress.

### What shipped

Judge **the whole small tree**, not its cuts:

- the tree is chosen on one grouping and must then pay on **two more independent groupings**;
- every leaf must hold at least 5 examples (10%), and that is checked on the *combination*, not the
  cut, because combinations strand small leaves;
- the tree must beat its own prior in **every** fold, not on average;
- and it must beat a permutation null of shuffled verdicts (0 of 24 shuffles — coarse, but it is a
  null of the statistic that is actually used);
- the single-cut gate still runs first and keeps its own null. The whole-tree path is used only for
  the case that gate is structurally blind to, because letting it propose lone cuts admitted three
  of twenty structureless worlds.

### Measured, out of group, 6 worlds each

| world | model | majority baseline | worlds with structure |
|---|---|---|---|
| `a > 0.5 AND b > 0.5` | **0.981** | 0.758 | 6 of 6 |
| `a > 0.5 OR b > 0.5` | **0.986** | 0.769 | 6 of 6 |
| `a * b > 0.25` | **0.908** | 0.647 | 6 of 6 |
| `XOR` | 0.506 | 0.544 | **0 of 6** |

Noise, same probe: **0 distinctions invented in 20 worlds at 60 examples, 0 in 20 at 90, 2 in 20 at
140.** Those two come from the older single-cut gate and are stated rather than smoothed.

Artifact: `canonical/verification/LEARNER_V1.json`, from `canonical/tools/learner_probe_v1.py`.

### The thing I set out to do, and what it was worth

Operator invention: let an admitted feature become a new sense and run the algebra over it.
Measured against the falsification that mattered — a plain deeper enumeration of the same fixed
algebra at the same budget — it **did not win once**:

| world | grow (operator invention) | brute-force deeper search |
|---|---|---|
| circle | 0.683 (nothing admitted) | 0.711 |
| and | 0.700 | 0.944 |
| noise | 0.500 | 0.601 (ungated) |

And carrying invented operators between worlds so a new world would be cheaper: **identical accuracy
(0.832 → 0.832) at higher cost (75 → 134 candidate evaluations)**. Inventing is already cheap per
world, so a vocabulary that persists buys nothing. The module was deleted rather than kept as
decoration, and the negative stands.

The attempt did leave one real finding behind: the generator never composed a signal with itself, so
`a * a` could not be built and any world with a squared term was unreachable. That is fixed.

### A side effect I did not plan and will report anyway

The `ratio` world log 16 recorded as unsolved and unchanged (0.617 → 0.617) is **now solved:
0.833 → 1.000**. The cause is the better learner, not the vocabulary. I did not tune for it; the
vocabulary probe was re-run after the learner change and the number moved.

### A bug in my own harness, again

Every "depth-2 world" measurement in the first half of this session was taken on the wrong worlds:
my generator built a dict literal with `r.choice(...)` inside it for the noise branch, and Python
evaluates every value, so the noise draw advanced the RNG and every subsequent `a, b` differed. The
worlds were not the worlds I named. This is the third harness-lie in three logs — the pattern is
that I trust a fixture I have not printed.

### Mutation

9 mutants on the new gate, **9 killed**: no whole-tree path · no second grouping · no third grouping
· no leaf-size check · no combination leaf-size check · accepts without gain · ignores a hurt fold ·
always rejects · record hides the accepted tree.

### What is real and what is not

| claim | verdict | evidence |
|---|---|---|
| It learns a conjunction | **TRUE** | 0.981 against 0.758 baseline, 6 of 6 worlds |
| It learns a disjunction, gain in the low branch | **TRUE** | 0.986 against 0.769 |
| The widening cost nothing that worked | **TRUE** | product 0.908 vs 0.647 |
| It refuses structure in noise (60, 90 examples) | **TRUE** | 0 of 40 worlds |
| It refuses structure in noise at 140 examples | **FALSE** | 2 of 20; stated, not fixed |
| It learns `xor` | **FALSE** | 0 of 6 worlds; a two-cut tree applies the same cuts everywhere |
| Operator invention beats deeper enumeration | **FALSE** | it did not win once; module deleted |
| Accumulated operators make a new world cheaper | **FALSE** | same accuracy, 79% more evaluations |
| Unaided closure for classes that matter | **STILL 0** | bookkeeping 100% (N=2); the real lead, N=1, unfixed |

### What the deepest layer says now

The creature can now learn a rule it could not express before this log — that is the second time in
seventeen logs that a change made it better at something instead of making the world bigger. But
notice the shape of what it can learn: **two cuts, one shape.** `xor` needs a different cut in each
branch and it fails completely. So the next layer is not more vocabulary and not a bigger search; it
is a representation where the branch decides what is asked next. I will not pretend this log is that.

Authority: **NONE**. Terminal truth: `false`. No capability credit.

---

## Log 18 — The method was the one thing I never let it choose

Seventeen logs. The beliefs grew; the vocabulary grew; the tree shape grew. The **learning
procedure** did not move once, and every number in it was mine: depth, width, minimum gain, minimum
leaf, and the choice of an axis-aligned greedy tree at all.

That last one is not an implementation detail. It is the thing that decides what the creature is
capable of. `xor` failed in logs 9, 16 and 17 — not because xor is hard, but because every cut of
it has zero information gain and the only hypothesis space available was one that chose cuts by
information gain. The failure was mine, wearing the world's clothes.

So the method became an object of measurement: a space of methods is generated, each is fitted and
scored out-of-fold on the creature's own experience, and it adopts the one that measurably predicts
better — or keeps what it has.

### The space is a product, not a list

`{tree(depth 1..3), nearest(k 1, 5, 11), stump} × {raw senses, invented features}` plus the
incumbent. One combination — **nearest neighbours over invented features** — is nowhere in this
repository written down, and the creature picked it for xor. That is what crossing a space buys that
enumerating one does not.

### Measured, chosen on its own experience, scored on worlds it never saw

| world | creature's method choice | held out | majority baseline | adopted |
|---|---|---|---|---|
| `xor` | nearest(k=1/5/11) | **0.931** | 0.517 | 3 of 4 |
| `circles` | nearest(k=1, k=5) | **0.947** | 0.711 | 3 of 4 |
| `product` | stump over invented feature | **0.978** | 0.625 | 3 of 4 |
| `sum` | stump over invented feature | **0.975** | 0.525 | 4 of 4 |
| `and` | tree(depth=2) or incumbent | 0.981 | 0.769 | 0 of 4 |
| `or` | tree(depth=2) or incumbent | 0.975 | 0.758 | 0 of 4 |
| `stripe` | incumbent | 0.994 | 0.625 | 1 of 4 |
| noise, 10 worlds | — | 0.470 | 0.498 | **0 of 10** |

For comparison, log 17 measured xor at 0.506 (base rate) and circles at 0.800. Those were not
limitations of the worlds. They were limitations of one hypothesis family.

Two rows matter as much as the top: on `and`/`or`/`stripe` the creature **declines** to change,
because its incumbent already wins. A system that always adopts the winner would be replacing a
working method to satisfy a search.

### Alive, not invoked

The real `organism_v1.tick` loop, 200 ticks, same world and seed, the only difference being whether
the creature may use the method it adopted:

| live world | incumbent only | with method choice | method picked |
|---|---|---|---|
| xor | 0.600 (n=10 predictions) | **0.886** (n=166) | nearest(k=5)[invented] |
| noise | 0.500 (n=2) | 0.524 (n=42) | nearest(k=5)[invented] |

Artifact: `canonical/verification/METHOD_V1.json` from `canonical/tools/method_probe_v1.py`.

### The bug that made me distrust the first table

The winner's permutation null was broken and it looked conservative: it scored the *original*
verdicts thirty times, because `score()` reads its data from the folds, and I passed the real folds
into a null built for shuffled labels. Every world failed it, including learnable ones. It was found
by asserting the **passing** case.

And before that: `circles` measured 0.476 and I nearly wrote it up as a method failure. It had never
been measured — the probe imported another probe's generator, which had no `circles` branch and fell
through to noise, still returning a number. That is the fourth fixture bug in four logs, so the
cause was removed rather than the instance: **one generator**, `canonical/tools/worlds_v1.py`, with
`check()` asserting every named world actually has the labels its name claims, and an unknown name
raising instead of falling through.

### Mutation

12 mutants across the method gate; **8 killed**. Survivors, reported:

| survivor | why | what it means |
|---|---|---|
| delete the winner null | the regroup checks and the incumbent comparison catch the same worlds | the null is a backstop here, as the split-level p-gate was in log 16 |
| delete the selection-time incumbent test | subsumed by the like-for-like regroup comparison | **removed from the code**, not kept as decoration |

One more honest negative: a greedy axis-aligned tree still cannot learn xor — 0.625 on its own
training data, because greedy gain never proposes a cut at 0.5. I expected per-branch recursion to
fix that and it did not. What fixed it was a different **family**. That is the argument for choosing
methods over tuning one, and it is a stronger argument than the one I set out to make.

### What is real and what is not

| claim | verdict | evidence |
|---|---|---|
| The creature chooses its learning method by measurement | **TRUE** | 7 worlds, method picked varies by world, declines where incumbent wins |
| That choice reaches worlds the incumbent cannot | **TRUE** | xor 0.931 vs 0.517; circles 0.947 vs 0.711 |
| It happens in a live loop, not on invocation | **TRUE** | xor 0.886 against 0.600 incumbent-only, 166 predictions |
| It does not manufacture methods on noise | **TRUE, not clean** | 0 of 10 offline; **1 in 40 offline** and 1 live, both measured harmless out of sample |
| The method primitives are no longer mine | **FALSE** | tree and nearest neighbour are still a person's idea of a hypothesis |
| A deeper axis-aligned tree learns xor | **FALSE** | 0.625; a different family learned it |
| Unaided closure for classes that matter | **STILL 0** | bookkeeping 100% (N=2); the real lead, N=1, unfixed |

### What the deepest layer says now

Three layers have come off: the beliefs (log 9), the vocabulary they are stated in (log 16), and now
the procedure that learns them (log 18). What remains is the layer underneath all three: **the
primitives**. A tree, a distance, a threshold — those are a person's idea of what a hypothesis is.
The creature now composes and chooses among hypotheses; it does not invent the kind.

That is the next static thing, and I can see two honest ways at it: search a space in which the
*representation itself* is a program the system writes, or let it build representations from the
data's own invariances rather than from operators I named. Neither is a token change, and saying
this log removed them would be false.

Authority: **NONE**. Terminal truth: `false`. No capability credit.
