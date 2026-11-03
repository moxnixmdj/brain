# First principles, second pass — three ideas tested, three refuted

**2026-11-04.** The owner asked again whether this is the smartest approach, from the deepest layer.
The honest answer requires saying what I did wrong, not proposing a better plan. So this document is
mostly refutations: three things I believed at the start of this turn, and the measurement that ended
each one. The one recommendation at the end is small and mechanical, which is the point.

Authority **NONE**. Spend $0. `truth.achieved` false.

---

## 0. The error at the root, named precisely

Last turn I fixed the diet and reported it honestly. But I still described the creature as *learning*,
and the measurements never supported that word. Three separate refutations this turn all point at one
structural fact:

> There is a **conservation law** in this tree: blocked tasks → stored suggestions → accepted → closed,
> or blocked → refused, but **nothing converts into capability**.

Concretely: `_extract_capability_feature_flags` is a pure function of the host and the registry. It
returns 33 READY at t0. Measured after six sessions — 18 capabilities successfully onboarded, 18
inspectors persisted, `closed` reaching 18 — the count of READY capabilities is **33, at birth and at
death, every single session**. The repertoire never grew. Only the beliefs about a fixed repertoire
moved, and (last turn) they moved in the wrong direction until fed honest features.

So the right question was never "how do we make its self-model better". It is:

> **What would it take for a session to end with a capability that could not be executed at the start?**

Every candidate answer I tested this turn failed. That is the finding.

---

## 1. Refuted idea A — "it is ignorant of slot types it could infer"

**The idea.** 50 of 155 capabilities are refused for `unknown_slot_type_on_surface`, across 89 distinct
slot names. The adapters demonstrably coerce these values (`str(args.get("python_executable") or
sys.executable)`), so the type is derivable from the adapter's own source. Infer the type → the
capability becomes attemptable. This looked like the single biggest lever in the tree.

**The measurement.** Induce the type from the adapter AST/regex, validate on slots whose type
`type_of` already knows, then count coverage.

Instrumentation matters here, so the path to the number is recorded: my first version read all 80
adapters as one concatenated corpus and got **25.9%** agreement; per-adapter and specificity-ordered
it was **31.0%**; the failure was `PATH → STR`, because `str(base / args["path"])` is a *join*, not a
coercion. Detecting path-context evidence (`base / X`, `.resolve()`, `.read_text()`, `open()`) instead
of `str()` wrappers gave:

| coarse kind | agreement | n |
|---|---|---|
| NUM | 100% | 31/31 |
| PATH | 85% | 74/87 |
| STR | n/a (only 1 test case) | 0/1 |
| **overall** | **88.2%** | 105/119 |

**It works.** And it is worthless: applied to the 50 blocked capabilities it **fully resolves 3**, and
partially resolves 8. 39 stay blocked on something else entirely. Even a perfect inducer here moves
READY from 33 to at most 36 (+9%), because the other 47 capabilities have a *second* precondition
behind the unknown slot.

**And on the 3 it does resolve, the block was not the slot type.** With the types hand-supplied, two
still return `PRECONDITION_UNMET` — one flips to `upstream_coupled_artifact_required`, the other to a
*new* slot-level refusal that was hidden behind the first: a capability blocked on two grounds reports
only one, and clearing one reveals the next. The third reached onboarding and honestly failed:
`NO_GENUINELY_PASSING_RUNS`.

So: 88%-accurate inference buys 3 capabilities, 2 of which turn out to be blocked on something else.
**Refuted.**

---

## 2. Refuted idea B — "its onboarding replaces a verifier with a learned one"

**The idea.** If `verified_hits` growing while reach is frozen means the applied rule was already in
the store and the verifier was redundant, then onboarding *should* be able to generalize a verifier
from demonstrations and thereby make blocked capabilities attemptable.

**The measurement.** After six sessions: **18 capabilities onboarded**, all host-READY, inspectors
persisted to `onboarded_inspectors.json`. Meanwhile **91 capabilities remain both blocked and unowned**.
The set onboarded and the set blocked are disjoint by construction — `sovereign_perform` refuses to
attempt anything whose preconditions are unmet, so onboarding can only ever touch what was already
reachable.

**Refuted, and by construction rather than by degree.** Onboarding re-labels the reachable set; it
cannot extend it. That is why the creature can look busy for six sessions and never grow.

---

## 3. Refuted idea C — "fitted self-correction would make the loop adaptive"

**The idea.** Fit the map from belief to observed outcome instead of returning the belief.

**The measurement** (last turn, repeated here because it is the same lesson). A least-squares shrink
toward the base rate, fitted on settled receipts only, landed at α = 0.334 — reproducing my offline
prediction of 0.330 exactly. Against the two protocols:

| arm | 26-cycle skill | 6×12 skill |
|---|---|---|
| truthful diet, no fit | **+0.246** | −0.179 |
| truthful diet + fitted α | +0.098 | −0.084 |

It gained 0.01 where it was blocked and lost 0.15 where it already worked. Deleted, not shipped.

**Refuted.** An adaptive-looking organ that lowers the measured number is not an improvement, and
"it is more principled" is not evidence.

---

## 4. What survives: one mechanical defect worth a day

Of 155 capabilities, **122 are blocked**. The largest single block is
`writes_fixed_repo_tmp_under_ro_input` — **19 capabilities**, and the cause is exactly 19 distinct
hardcoded literals in 19 adapters:

```
canonical/tmp_amplify_report.json
canonical/tmp_contract_issue_fusion.json
canonical/tmp_fault_patch_supercomposer.json
... 16 more, one per adapter
```

Each adapter writes its intermediate to a fixed path inside the repository. Under a read-only input
mount that is both a correctness bug (two concurrent runs collide) and the reason the capability is
refused. This is not epistemic and not one of the 89 unknown concepts: it is a mechanical rewrite to a
per-run temporary directory, verifiable by the capability actually passing.

That is a **+16%** shift in the reachable set, in one class of change, with an executable pass/fail
oracle. It is the only candidate I found this turn whose payoff is not speculative.

**What it is not.** It is not sentient, not adaptive, and it does not close any of the four loops in
`FIRST_PRINCIPLES_FOUR_LOOPS_20261103_V1.md`. It makes the *world* bigger for the creature. That is
the precondition for the loops mattering at all, not a substitute for them.

---

## 5. The thing I am now unwilling to claim

Three turns ago I was asked whether this is a sentient-like creature. The honest answer after this
turn's measurements:

- **Real:** it runs unattended, keeps identity and standing across restarts, predicts before it acts,
  is settled by an outside verdict, owes nothing to a model, spends nothing, and its refusals are
  honest and specific.
- **Not real:** it does not acquire capability. No session in any measurement has produced a capability
  that was not executable before it started. The repertoire is a constant 33 of 155. Its "learning" is
  confined to beliefs about a fixed menu, and the one loop that could change the menu — acquiring a new
  executable skill — is not wired to the thing that blocks it.

A system whose reach is constant and whose self-model is the only moving part is not a creature. It is
an instrument that reports on itself accurately. That is worth having and it is a real achievement of
this tree — but it is the thing I should have said three turns ago instead of reaching for the word.

---

## 6. Recommendation, in order, and why each is falsifiable

1. **Fix the 19 fixed-path adapters** → +19 capabilities, all at once, verified by each capability
   onboarding. Falsifier: run the 19 after the change; any that still refuse reports why.
2. **Only then re-measure the four loops.** Every loop measurement to date was taken on a repertoire of
   33 with a 79% block rate, which is not a fair test of whether the loops work.
3. **Then** the sign error across families (§3 of the previous document) with n large enough to split
   by family.

What I will not do: propose another organ, another plan document, or another fitted parameter before
something in this table moves a capability from impossible to possible.
