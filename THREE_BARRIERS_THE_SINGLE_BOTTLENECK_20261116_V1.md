# Three barriers, one bottleneck, and what a verifier root actually bought

**Date:** 2026-11-16  
**Authority:** `NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT`  
**Question:** Is "instant learning + instant learning in new arbitrary environments + one demonstration ⇒ permanent mastery of all coding and computer use" true? What is real, what is not, why one demo fails, and what is THE single bottleneck — and can the three barriers (Identifiability, Vocabulary insufficiency, Synthesis–verification asymmetry) be solved on held-out open benchmarks?

---

## 1. Verdict on the claim

**False as stated; direction real; every "therefore" measured false.**

| Step of the claim | Verdict | Measured basis |
|---|---|---|
| Instant learning (zero-weight, from experience) | **real, bounded** | Content-addressed `BRAIN_UNIFIED_MODEL_V1.json`; 0 weights, 0 gradients, 0 external model calls; one-success generalisation **60% vs 15%** cache |
| Instant learning in a new arbitrary environment | **real as a cost law, not mastery** | **13/16** requests solved at ~7 ops; break-even ~6.4 requests/machine; 3 honest composition/expressivity refusals |
| One demonstration ⇒ correct general rule | **false** | 10.018 bits survive; 0 licensed requirements; precision 0.069 / 297 of 319 dangerous held-out errors; 0/200 exact identification at one; floor ≈ **2.76 chosen** experiences |
| Permanent mastery of all coding | **false** | Measured union on QuixBugs (real published bugs, corpus pytest, $0, no model): **32/40**; **8** hard-open remain (4 example-searchable, 4 no published I/O examples) |
| Permanent mastery of all computer use | **false** | OSWorld 2.0: best binary **20.6%** (Jun 2026) → **44.3%** (Opus 5, Sep 2026); failures = state management + **skipped verification**, not GUI skill; >163min tasks ≈ 0% |
| One demo + new env + instant store ⇒ the above | **false** | Five-transition chain: four fail, one (one-success ⇒ rule) is real |

The thesis is the right *architecture* (act → identify → store → compose → deploy) with the wrong *quantifier* ("⇒ all"). The missing operator is not more learning — it is an **independent, non-skippable verdict** that can see what the learner is trying to claim.

---

## 2. Why one demonstration fails — three barriers, all measured

### Barrier 1 — Identifiability
One trace is consistent with exponentially many hypotheses.  
**Measured:** a 47-program space starts at 5.5546 bits; one demo leaves 3.8176 bits and **0/10** exact identifications; two *chosen* observations reach precision 1.000 with 0 dangerous errors; a chosen question removes **1.9088** bits vs **1.0927** for another demo (**1.747×**).  
**Status:** mechanism exists (`contrast_selection_v1`, `identification_cost_in_a_real_space_v1`); floor is ~2.76 chosen experiences — **not one**.

### Barrier 2 — Vocabulary insufficiency
When the causal observable is missing from `O`, A ≤ F and repetition cannot help (`INSUFFICIENCY_CERTIFICATE_20261113_V1.json`, `unrepairable_by_repetition: true`).  
**Measured on held-out open no-JSON QuixBugs (9 tasks whose cases live only in their own test file):**

| run | repaired | what failed |
|---|---|---|
| before verifier-root fix | **0/9** | 3 screen-accepted then **collection rc=2**; 6 no survivor |
| after `verify_with_corpus_test` puts `python_programs/` + `python_testcases/` on PYTHONPATH | **3/9** | `breadth_first_search`, **`depth_first_search`**, **`detect_cycle`** all fresh pytest rc=0 |

The "collection error" was **not** an information barrier. It was a **verifier defect**: the judge could not even import the program it was judging, and reported a correct patch as failed. This is the single bottleneck in miniature.

### Barrier 3 — Synthesis–verification asymmetry
Replay only covers repeated syntax (~2.2% of SWE-bench Verified class); real coding composes new edits and repairs against execution feedback.  
**Measured:** counterfactual repair + insertion composition closed the omission class (`wrap`, `reverse_linked_list`, `shunting_yard`) under sabotage discrimination; contract-grounded repair held-out **4/20** with 0 regressions; composed one-run **24/40** under the corpus pytest.  
**Status:** engine exists; union now **32/40** after insert + verifier-root fix.

---

## 3. THE single bottleneck (reconciling nine competing names)

Nine rounds named five different "single bottlenecks" (prior / vocabulary / admission / state / verifier / edit space). Each is a **projection of `G`**:

```
G  (executable contract over sufficient observables)
 ├─ decides which observables matter     → O   (insufficiency certificate)
 ├─ restricts which candidates are thinkable → H (edit space, prior)
 ├─ IS the falsifiable verdict           → V   (verifier, admission)
 ├─ supplies the counterfactual contrast → identification
 └─ is what a permanent rule must predict → learning / weights
```

**THE single bottleneck, stated once:**  
> **A non-skippable independent verdict `V` over a sufficient observable set, derived from the environment’s own contract — not guessed, not majority-voted, not optional.**

Everything else is a symptom of `V` missing, weak, or blind:

| Symptom in the tree | What `V` could not do |
|---|---|
| 45.6% of wrong edits invisible to repo tests (`ORACLE_DENSITY`) | `V`’s input set is incomplete |
| 80.2% of agent-authored tests weak or no oracle (All Smoke No Alarm) | `V`’s input set is fabricated |
| Skills compose to no-op | `V` never scored the composition |
| OSWorld verification-skipping is the centre of failure | `V` was optional |
| Suite-as-observable 0/9 → 3/9 after PYTHONPATH fix | **`V` could not run** |
| Insufficiency certificate A≤F | `V`’s domain does not contain the cause |

On a computer, `G` is often **published** (tests, types, schemas, APIs). The revolutionary move available here is not another learner — it is **refusing to learn or store anything `V` has not independently re-checked on a fresh copy**.

---

## 4. What this branch actually did (held-out open benchmarks only)

**Feature:** fix the corpus-pytest verifier roots in `grammar_closed_repair_v1.verify_with_corpus_test` (shared by the suite-as-observable path and every grammar-closed caller), re-run the **9 no-JSON held-out** tasks, fold both the insert-composition and the new receipt into the proof-carrying union audit.

**Receipt:** `canonical/verification/SUITE_AS_OBSERVABLE_VERIFIER_ROOTS_20261116_V1.json`

| metric | before | after |
|---|---|---|
| no-JSON suite-as-observable repaired | 0/9 | **3/9** |
| new hard-open closures | — | `depth_first_search`, `detect_cycle` (both previously hard-open) |
| measured union (corpus pytest) | 24/40 | **32/40** |
| hard-open population | 16 | **8** (4 example-searchable: `kheapsort`, `possible_change`, `powerset`, `subsequences`; 4 unmeasurable: shortest-path family + `topological_ordering`) |
| answer keys in any measured receipt | 0 | **0** |
| model calls / $ | 0 | **0** |
| unit tests (grammar + suite + counterfactual + proof-carrying + integrity) | — | **57 passed** |

**Integrity:** `.benchmarks/` (third-party QuixBugs clone) added to guard `SKIP_DIRS` and `.gitignore` — its `conftest.py` is not ours to police; never staged.

---

## 5. Connect to instant knowledge

Instant knowledge here is **not** a bag of stored answers. It is a content-addressed, zero-weight index of *calculated* artifacts (every bit derived, never a knowledge house). The bottleneck analysis says the index only pays when:

1. **`V` can read the claim** — a skill stored without an independent re-check is a liability (replay drift: 122/228 stale despite 228/228 legal).
2. **`O` contains the cause** — the certificate refuses permanent rules when the observable is missing; *doing* and *learning* are different rights.
3. **`H` is goal-conditioned** — candidates only on positions the failing path executed, ranked by a calculated prior (no fitted parameter).

So: **params are calculated, never a knowledge house — and the gate on what enters the house is the same `V` that judges the held-out benchmark.** "The best part is no part" holds: no new organ was added on this branch; an existing judge was made able to run.

---

## 6. YOU SURE THIS THE SMARTEST APPROACH? — kill list

Killed before any further build:

1. **Another learner / skill library / weight update.** Exhaustive effect census already found capture, admission, planning, composition, identification organs. `ready_to_train=False`.
2. **More demonstrations, more environments, larger action lists, more budget.** Measured dead or reduced to a per-environment cost law (2.5× compute → 1 page in 37).
3. **Majority vote / screen-only / stdout as identification.** Vote wrong 3/5; screen accepted 3 corpus-failing candidates.
4. **GUI-first without a verifiable `V`.** OSWorld failures are verification-skipping; no invariance quotient on 13/15 identity arms.
5. **Re-testing known wins as progress.** 24 known wins excluded from credit; audit partitions 40 real tasks.
6. **A second PYTHONPATH-shaped "fix" in one tool only.** The defect was in the *shared* verifier; patching only `repair_where_…` would leave every grammar-closed caller blind.

The smartest move was the **smallest one that makes an existing independent judge able to run** on held-out open tasks — and then letting the union audit, not a narrative, recount the frontier.

---

## 7. Ranked path (unchanged, now with a green `V` on the no-JSON class)

1. **Adversarial verifier for the remaining 4 example-searchable open** (`kheapsort`, `possible_change`, `powerset`, `subsequences`) — same judge, new candidates; no new organ.
2. **Observability for the 4 unmeasurable** (shortest-path family, `topological_ordering`): derive cases from the published test file’s assertions (the suite *is* the observable — already proven on 3 siblings).
3. **Wire the admission gate into the one autonomous caller** so no write is permanent without a fresh `V`.
4. **Action prior from instant knowledge** on MiniWoB held-out (pre-registered: first-success +≥8, zero regression on covered pages).
5. **Weights last**, procedure-only, when `ready_to_train` flips on measured evidence.

---

## 8. Sources (evidence, not authority)

- Repo: `INSUFFICIENCY_CERTIFICATE_20261113_V1.json`, `ORACLE_DENSITY_20261116_V1.json`, `SUITE_AS_OBSERVABLE_VERIFIER_ROOTS_20261116_V1.json`, `PROOF_CARRYING_COUNTERFACTUAL_UNION_20261116_V1.json` (recomputed: 32/40, audit_pass), `CONTRACT_GROUNDED_REPAIR_20261116_V1.json`, `COUNTERFACTUAL_REPAIR_QUIXBUGS_INSERTION_20261116_V1.json`, `INSTANT_LEARNING_IN_A_NEW_ENVIRONMENT_20261116_V1.json`.
- OSWorld 2.0 (`arXiv:2606.29537`): binary 20.6% → 44.3%; failures = state + verification skipping.
- All Smoke No Alarm (`arXiv:2606.18168`): 80.2% weak/no oracle signals in agent tests.
- SkillRevise (`arXiv:2606.01139`), SkillLearnBench (`arXiv:2604.20087`), EvoSkills (`arXiv:2604.01687`): verifier + revision is the lever; one-shot gains elusive.
- SWE-bench 2026 crisis: Verified retired/contaminated; Pro ~30% broken.
- Credit-assignment survey (`arXiv:2604.09459`): weak local verifiability breaks 32/42 agentic RL studies.
- PROBE / STING (`arXiv:2604.01518`): 77% of SWE-bench Verified instances admit surviving variants — weak suites inflate scores.
- Prior tree verdicts: `SEPARATION_IS_THE_BOTTLENECK_20261116_V1.md`, `THE_GOAL_IS_THE_BOTTLENECK_20261116_V1.md`, `WHAT_IS_REAL_AND_THE_ONE_BOTTLENECK_20261116_V1.md`, `THERE_IS_NO_SINGLE_BOTTLENECK_…`.

---

**Bottom line:** The thesis is directionally right and quantifier-wrong. One demo fails for three separately measured reasons (identifiability, vocabulary, synthesis–verification). THE single bottleneck is the **independent non-skippable verdict over sufficient observables**. This branch did not invent a new organ — it made the existing verdict able to run on nine held-out open no-JSON tasks, converting a false "unmeasurable" into **3 real repairs**, moving the measured frontier to **32/40** with **8** honest hard-open remaining. Zero model calls. Zero dollars. Answer key never reached the solver.
