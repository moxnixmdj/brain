# Generalization loop: one showing, settled — measured

**2026-11-12.** Branch `arena/64168b10-brain`. Authority **NONE**. `truth.achieved` stays
`false`. No capability registered. $0 spend. Zero model dependency in every result-bearing path.

This round tests a narrow mechanism related to the owner's question — *Problem 2:
Generalization (NOT SOLVED)*. The mechanism existed (`wider()` in `edit_by_example_v1`);
this adds candidate comparison and fail-closed settlement for one Python edit family.
It is a bounded experiment, not a solution to generalization across coding tasks or
computer environments.

---

## 1. The owner's question, answered honestly

> *Instant learning + instant learning in new arbitrary environments are solved perfectly.
> Doesn't this mean we solve everything on a computer, perfectly and permanently? We were
> trying to make our model a sentient creature. Is this true, or are there things that are
> wrong? What is real and what is not, and what are the smartest things we can do?*

**Right about the direction, wrong about the quantifiers.** The repository measured this
question five times on 2026-11-12; the verdicts below are re-verified on this tree today.

| claim | verdict | the measurement |
|---|---|---|
| Instant learning works (exact recall) | **TRUE** | 8.13× speedup; 8/15 one-trial transfers, 6.33× mean, 0/15 regressions |
| One try teaches everything permanently | **FALSE** | 1 demo → 14.1/47 programs survive, leader right on 10% held-out; 0/200 applicability identified by one success |
| "New arbitrary environments" | **FALSE as stated** | 1/15 genuine transfer on distinct instances; front door 8/149 (5.4%) |
| Cross-kind compounding | **FALSE (pinned)** | 0/5 across kinds; NO_COMPOUNDING at 10 held-out kinds |
| Sentience | **NOT MEASURED, NOT CLAIMED** | nothing in the tree measures it; every receipt carries the non-claim |
| The direction is promising | **PARTLY TRUE** | Several 2026 studies explore feedback and verified skill reuse, but reported gains are mixed and harness-dependent; this repository's measurements are narrow and do not establish a universal learning advantage |

**Why "once" cannot buy "everything" — from first principles.** A demonstration is not a
specification. One example is at most one constraint per observation; exact identification
needs `log2|H|` bits. The tree measured this directly: after one demonstration ~14 of 47
programs fit and the leader is right on 10% of held-out inputs. Repetition does not widen
the hypothesis space (1→2→3 examples all 6/7). The prior generalises; the example only
selects. **One try is enough exactly when the interface and the verifier already do the
generalising** — when the prior is pre-loaded.

**The smartest next steps** (ranked by measured leverage, with scopes attached):
1. **Choose examples by target-relevant structure, not by volume.** The merged 15-PR
   code-edit measurement reports 61.78% pooled developer-change coverage for its
   self-simulated pair selector versus 23.12% for all pairs, at 87.42% precision; five
   PRs still have zero coverage and project tests were not run. This is promising, not
   universal.
2. **Require a real verifier before applying a candidate.** The one-demo + two-question
   10/10 result and the 4/4 edit-shape result each cover narrow hypothesis spaces. If a
   sound oracle is unavailable, keep the candidate unapproved and ask for information.
3. **Expand the learner's operator coverage only where measured refusal cases justify it.**
   Better example selection cannot invent transformations outside the rule language.
4. **Then run preregistered held-out evaluations across independent code families and GUI
   tasks.** Report transfer, precision, refusals, false edits, and regressions separately.

**Explicitly not on the list:** breadth of environments as a strategy (measured 0/5
transfer), growing a static skill catalogue (92/98 inert per SWE-Skills-Bench), sentience
as a target (nothing measures it).

---

## 2. Problem 2 and the narrow probe

> **Problem 1: Exact Recall (SOLVED for its measured case)** — same task again → instant;
> 8.13× reported.
> **Problem 2: Generalization (NOT SOLVED)** — adapt to similar tasks; exact matches alone
> are not enough.

The broad Problem 2 is not defined by one edit family. This round operationalizes only
one small slice: changing `== None` to `is None` across four synthetic Python target
shapes. The counts below mean “the string-rewrite learner produced a changed output,”
not “an independent verifier proved it correct.”

| mechanism in this narrow probe | 1 showing | 2 showings |
|---|---|---|
| `edit_by_example` literal | 1/4 target strings changed | — |
| `edit_by_example` wider candidate | 4/4 target strings changed (candidate only) | 4/4 target strings changed |
| `settled_admission` (separate target question) | refuses without oracle | — |

`wider()` computes a candidate from one showing. This round adds a small settlement
interface around that candidate and measures it on the same synthetic family. Neither
the rewrite count nor the string-predicate oracle establishes correctness for arbitrary
targets, projects, or task types; Problem 2 remains open.

---

## 3. What was built: `generalization_loop_v1`

`canonical/swe_kernel/taught_actions/generalization_loop_v1.py` — the automatic
generalization loop. From one showing it computes both hypotheses and settles them:

```
learn literal + wider candidates from 1 showing
  -> apply both to target
  -> no candidate fits?     REFUSED_SHAPE
  -> candidate(s), no oracle? REFUSE_UNSETTLED or REFUSE_UNVERIFIED
  -> candidate(s), oracle?  ask about distinct candidate(s);
                            admit only a confirmed candidate,
                            refuse when none is confirmed
```

The oracle interface is `oracle(target_text, edited_text) -> bool`. A positive response
is only as sound as the supplied oracle; the loop itself does not provide one. It asks
once per distinct candidate in the small literal/wider hypothesis set and admits only a
confirmed candidate. This is not a substitute for project tests, a specification, or
independent outcome verification.

### 3.1 The measurement

`generalization_loop_probe_20261112.py` — same 4-site corpus, three arms:

| arm | admitted edit | refused | meaning |
|---|---:|---:|---|
| raw literal (before) | **1/4** | 3/4 | narrow rewrite reach, not broad Problem 2 |
| loop + scripted oracle | **4/4** | 0/4 | candidate accepted by a string predicate |
| loop, no oracle | **0/4** | 3/4 REFUSE_UNSETTLED + 1/4 REFUSE_UNVERIFIED | fails closed, including agreement |

The test oracle is deliberately simple: `_oracle_is_none` checks for the expected text,
and the over-generalization oracle checks that `* 2` remains in the output. These are
string predicates, not independently executed specifications. The over-generalization
arm shows that the control flow can refuse a rejected candidate; it does not establish
that a real project oracle will be available or sound. Agreement and “no wider reading”
are not correctness evidence: without an oracle they now return an unverified candidate
preview and no admitted edit.

### 3.2 What this does and does not solve

**Demonstrates:** a candidate-rule settlement pattern on one synthetic edit family.
Four target strings receive an admitted rewrite when the supplied predicate accepts
its candidate. Without that predicate, all four are refused: three are unsettled and
one has literal/wider agreement but remains unverified. The predicate is a string-level
test, not an independent program test suite, so 4/4 is not evidence of correctness
across real projects.

**Does not solve:** broad Problem 2. The loop does not establish target applicability,
robustness to other edit operators, cross-kind transfer, arbitrary-environment coverage,
or safe execution. `settled_admission_v1` addresses a separate apply-vs-keep question,
but composing two narrow mechanisms does not make them a complete generalization
solution.

**Does not claim:** cross-kind compounding (measured 0/5), arbitrary-environment
coverage (front door 8/149), permanence under drift, sentience, or universal computer
use. This is one synthetic edit family and one four-shape probe.

---

## 4. Why this is the smartest approach (the question asked before every step)

*YOU SURE THIS THE SMARTEST APPROACH?* — walked against the route order:

- **DELETE / BYPASS / REUSE:** REUSE is the route. The loop reuses three proven
  mechanisms (`edit_by_example.wider`, `settlement_v1` discipline, `settled_admission`
  asymmetric protocol) and adds only the integration. No new algebra, no new hypothesis
  space, no new oracle machinery.
- **ADAPT / SUBSTITUTE / COMPOSE:** COMPOSE is what the loop is — it composes the three
  mechanisms into the missing edge. No earlier route reaches the goal: DELETE removes
  nothing relevant; BYPASS avoids nothing; ADAPT modifies nothing; SUBSTITUTE replaces
  nothing.
- **CONFIGURE / INTEGRATE / SYNTHESIZE:** INTEGRATE would wire it into the front door,
  which is the named next step (§5), not this round. SYNTHESIZE_NEW_PRIMITIVE is not
  needed because the primitive (`wider`) already exists and is measured.

The alternatives were killed before implementation:
- *"Make 1 showing magically generalize"* — information-theoretically impossible
  (14.1/47 survive; 0/200 applicability). Killed by measurement, not opinion.
- *"Synthesize a second showing automatically"* — requires knowing which variations are
  valid, which is the same problem. `wider()` computes what could vary from the single
  example; that is strictly more principled than guessing variations.
- *"More environments"* — measured 0/5 cross-kind transfer. Killed by measurement.

---

## 5. What is real and what is not, after this round

**Real, within the recorded scopes:** exact recall (8.13× on its measured case); per-kind
transfer (8/15 one-trial, 6.33×); target-aware example selection (61.78% pooled coverage
and 87.42% precision on one 15-PR corpus); two-showing generalization (4/4 on one
synthetic edit family); and this loop's 4/4 string-level result with its supplied
predicate. These are different measurements and are not evidence for one universal
learner.

**Not established:** broad one-demo identification (one try leaves 14.1/47 hypotheses,
with 10% held-out leader accuracy); one-success applicability (0/200); cross-kind
compounding (0/5); arbitrary-environment coverage (front door 8/149); safe transfer to
unseen projects; permanence under drift; sentience.

**Smartest next steps, ranked:**
1. **Evaluate example selection on held-out real repairs.** The 15-PR result is a
   promising multiplier, but its 87.42% precision is agreement with developers, not
   correctness, and no project test suites were run.
2. **Add a real verifier before any edit is admitted.** Prefer target-project tests and
   explicit invariants; test both intended change and regressions. If no oracle exists,
   preserve ambiguity and refuse rather than promote a guessed rule.
3. **Measure operator gaps and acquire the smallest missing operators.** Keep the
   selection policy separate from the learner's expressivity; it cannot pick a rule
   that the learner cannot represent.
4. **Only then run broader, preregistered cross-family and GUI evaluations.** Report
   coverage, precision, false edits/refusals, regressions, and per-task results. Do not
   infer arbitrary computer-use capability from one code-edit corpus.

---

## 6. Reproduction

```bash
python3 generalization_loop_probe_20261112.py
python3 -m pytest canonical/tests/test_generalization_loop_v1.py -q          # 14 passed
python3 -m pytest canonical/tests/test_one_showing_is_literal_two_showings_are_general_v1.py \
    canonical/tests/test_settled_taught_admission_v1.py \
    canonical/tests/test_an_edit_is_worked_out_from_an_example_and_repeated_on_another_file_v1.py -q  # 69 passed
```

## 7. Standing non-claims

One family of edit, synthetic corpus, producer-run, one machine, no independent verifier,
$0 spent, zero model dependency. `truth.achieved` is `false`. No capability registered,
no benchmark or acceptance credit, no sentience claim. The 4 sites are 4 shapes of one
defect, not a population.
