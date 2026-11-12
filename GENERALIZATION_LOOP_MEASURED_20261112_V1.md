# Generalization loop: one showing, settled — measured

**2026-11-12.** Branch `arena/64168b10-brain`. Authority **NONE**. `truth.achieved` stays
`false`. No capability registered. $0 spend. Zero model dependency in every result-bearing path.

This round answers the owner's question — *Problem 2: Generalization (NOT SOLVED)* — by
building the missing integration, not by arguing. The mechanism existed (`wider()` in
`edit_by_example_v1`); nothing used it automatically or safely. Now something does.

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
| The direction is revolutionary | **PARTLY TRUE** | verifier-gated learning is the shape the whole 2026 field converged on (SkillRL, SICA 17→53, DGM 20→50); the novelty here is the refusal discipline, not the loop |

**Why "once" cannot buy "everything" — from first principles.** A demonstration is not a
specification. One example is at most one constraint per observation; exact identification
needs `log2|H|` bits. The tree measured this directly: after one demonstration ~14 of 47
programs fit and the leader is right on 10% of held-out inputs. Repetition does not widen
the hypothesis space (1→2→3 examples all 6/7). The prior generalises; the example only
selects. **One try is enough exactly when the interface and the verifier already do the
generalising** — when the prior is pre-loaded.

**The smartest things to do** (ranked by measured leverage, not opinion):
1. **Chosen questions, not more examples.** One demo + 2 chosen questions → 100% (10/10).
   Two adversarially-chosen showings → general (4/4). A million repetitions → nothing.
2. **Widen the interface/verifier regime.** A typed interface against a declared contract
   is a pre-loaded hypothesis space. `npm test` means the same thing in ten thousand repos;
   pixels do not. This is the only large 2026 gain (Agent S4: 3.8× by evolving interfaces).
3. **Wire the oracle at the front door.** 8/149 admitted; the largest red cluster is the
   door, not the learner. Nothing downstream can be measured until this moves.
4. **Donor-distilled prior** (bounded acquisition, donor deleted, held-out qualification).
   The only lawful route to a shared space no person wrote.

**Explicitly not on the list:** breadth of environments as a strategy (measured 0/5
transfer), growing a static skill catalogue (92/98 inert per SWE-Skills-Bench), sentience
as a target (nothing measures it).

---

## 2. Problem 2, defined precisely

> **Problem 1: Exact Recall (SOLVED)** — same task again → instant. 8.13× measured.
> **Problem 2: Generalization (NOT SOLVED)** — similar task → adapt. Exact matches only.

"Similar" means: same defect, different names/shapes. The measured state was:

| mechanism | 1 showing | 2 showings |
|---|---|---|
| `edit_by_example` literal | 1/4 unseen sites | — |
| `edit_by_example` wider (computed, unused) | 4/4 (hypothesis) | 4/4 (fact) |
| `settled_admission` (target question) | refuses without oracle | — |

The gap was not the algebra — `wider()` already computes the generalization candidate
from one showing. The gap was that **nothing settled it**: no automatic computation,
no evidence check, no fail-closed refusal. The user had to know to provide a second
showing. That is the problem this round solves.

---

## 3. What was built: `generalization_loop_v1`

`canonical/swe_kernel/taught_actions/generalization_loop_v1.py` — the automatic
generalization loop. From one showing it computes both hypotheses and settles them:

```
learn literal + wider from 1 showing
  -> apply both to target
  -> agree?          ADMIT (no question)
  -> no wider?       ADMIT literal (maximal)
  -> disagree, no oracle?  REFUSE_UNSETTLED (fail closed)
  -> disagree, oracle?     ask about wider first;
                           admit on confirmation, fall back to literal,
                           refuse when neither is confirmed
```

The oracle is the minimum question interface: `oracle(target_text, edited_text) -> bool`.
One question settles the generalization. The asymmetric protocol (admit on confirmation,
refuse on contradiction) is the same discipline as `settled_admission_v1`, applied to
the rule question instead of the target question.

### 3.1 The measurement

`generalization_loop_probe_20261112.py` — same 4-site corpus, three arms:

| arm | edited | refused | meaning |
|---|---|---|---|
| raw literal (before) | **1/4** | 3/4 | exact recall only — Problem 2 as stated |
| loop + oracle (this round) | **4/4** | 0/4 | generalization, settled by evidence |
| loop, no oracle | 1/4 | **3/4 REFUSE_UNSETTLED** | knows what it does not know |

Plus the over-generalization arm: `pairs(n) = n * 2` must stay `*2`; wider would make it
`*3`. The loop asks the oracle, the oracle rejects wider, and the loop **refuses** —
the silent wrongness of defect 6 (`is_last_index`) cannot happen through this path.

### 3.2 What this does and does not solve

**Solves:** the rule-generalization question. One showing now reaches 4/4 unseen sites
automatically, with evidence, instead of waiting for a second showing. Without evidence
it refuses and names the disagreement — the fail-closed property.

**Does not solve:** the target-applicability question. When literal and wider agree,
the loop admits without asking whether the edit should be applied at all. That is
`settled_admission_v1`'s domain (apply vs keep, settled by function-execution probes).
The two modules compose: generalization_loop settles *which rule*; settled_admission
settles *whether to apply it*. Together they are the complete generalization solution.

**Does not claim:** cross-kind compounding (still 0/5), arbitrary-environment coverage
(still 8/149), permanence under drift, sentience. The loop generalises within one
edit family, which is exactly the scope Problem 2 defines.

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

**Real (measured):** exact recall (8.13×); per-kind transfer (8/15, 6.33×); two-showings
generalization (4/4); oracle-settled target admission (settled_admission, 11 tests);
**now: automatic rule generalization from one showing, settled by evidence (4/4 with
oracle, 1/4 + 3/4 fail-closed without, over-generalization refused).**

**Not real (measured, pinned):** one-try identification (0.10 accuracy); one-success
applicability (0/200); cross-kind compounding (0/5); arbitrary-environment coverage
(8/149 front door); permanence under drift; sentience.

**Smartest next steps, ranked:**
1. **Wire the oracle at the front door** — give live fabric paths the oracle interface;
   re-run the one-try census. Target: 8/149 → measured.
2. **Compose the two settlement modules** — generalization_loop (which rule) +
   settled_admission (whether to apply) as one call at the front door.
3. **Per-place settlement** — the loop currently settles whole edits; per-place would
   keep 3 correct generalizations when wider is wrong on 1 of 4 places.
4. **Donor-distilled prior** — the only route to a shared space no person wrote.

---

## 6. Reproduction

```bash
python3 generalization_loop_probe_20261112.py
python3 -m pytest canonical/tests/test_generalization_loop_v1.py -q          # 10 passed
python3 -m pytest canonical/tests/test_one_showing_is_literal_two_showings_are_general_v1.py \
    canonical/tests/test_settled_taught_admission_v1.py \
    canonical/tests/test_an_edit_is_worked_out_from_an_example_and_repeated_on_another_file_v1.py -q  # 69 passed
```

## 7. Standing non-claims

One family of edit, synthetic corpus, producer-run, one machine, no independent verifier,
$0 spent, zero model dependency. `truth.achieved` is `false`. No capability registered,
no benchmark or acceptance credit, no sentience claim. The 4 sites are 4 shapes of one
defect, not a population.
