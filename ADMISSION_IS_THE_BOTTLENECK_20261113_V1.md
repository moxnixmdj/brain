# Admission is the bottleneck — measured on the live learn path, 13 November 2026

Authority: **NONE**. Sandbox measurement on this tree plus published research. No capability is
registered, no family flips, `truth.achieved` is untouched, no base-model/LLM weights are updated.

Companion to `WHAT_IS_REAL_AND_WHAT_TO_DO_20261113_V1.md`. That report answered *what is real*.
This one closes a specific hole it named: **the store granted permanence without executing a
single unseen program.**

---

## 1. The claim under test

> "Show it once, it learns permanently, therefore we solve any computer task and the most advanced
> software engineering."

Every clause of that is achievable except the inference. Permanence is a property of *storage*.
Correctness is a property of *evidence*. If the evidence that grants permanence is the
demonstration itself, then permanence amplifies the demonstration's blind spots forever.

## 2. What the live path actually executed (measured before changing anything)

One boundary lesson, `x <= 100` → `x < 100`, taught through the real store with its **strongest
available option** (`oracle=` plus `probes=`):

```text
python3 canonical/tools/lesson_admission_harm_measure_20261113_v1.py

without victims : crystallized=True state=ACTIVE held_out_programs_executed=0 admission=UNGATED
    strict_bucket   (own spec: under 100)   -> REPAIRED
    inclusive_cap   (own spec: at most 100) -> BROKEN
with the gate   : crystallized=False rows=0 ADMISSION_REJECT:BROKE_CORRECT_PROGRAM:inclusive_cap
safe suite      : crystallized=True rows=1
```

The recorded probe said `{"verdict": "HOLDS", "probes_checked": 4}`. All four executions were of
the taught snippet: `crystallize_code_fix` passed `victim_snippet=before_snippet` to
`rule_generalization_probe_v1.probe_rule`, whose own docstring calls that "the weaker question".

So the rule went **ACTIVE** having repaired one unseen program and broken another, and the tree
only discovers the break later, via `probe_skill_on_victim(..., invalidate_on_break=True)`. The
detection instrument already existed. It was pointed at the wrong moment: after the write.

## 3. What changed

`canonical/swe_kernel/lesson_admission_gate_v1.py` — the lesson is applied to held-out programs
**in memory, before persistence**, and the write is refused unless the evidence is there.

- **Families are computed, never declared.** Each victim's baseline is executed against *its own*
  spec. Disagreement ⇒ `DEFECT_PRESENT`; agreement ⇒ `ALREADY_CORRECT`. The caller cannot label a
  program "falsification" and be believed.
- **Gain must be new.** `ADMIT` needs ≥1 `REPAIRED` on a held-out program that is not the
  demonstration. Archive rows cannot supply gain (`archive_repaired` is counted separately) — a
  bug the tests caught before commit.
- **Do no harm.** Any `BROKEN` ⇒ `REJECT`, naming the victim. An archived program that regresses ⇒
  `REJECT: ARCHIVE_REGRESSION`.
- **Not firing is not safety.** `NOT_APPLICABLE` yields no observation. If no already-correct
  program was ever touched, the verdict is `REFINE: FALSIFICATION_UNEXERCISED`, never `ADMIT`.
- **Unreadable evidence is a refusal.** No probe points, an oracle that raises, a victim that does
  not run, or victims that are all the demonstration ⇒ `REFUSED` with a named reason.
- **The ungated case is now visible.** Every legacy admission stores
  `admission.verdict = "UNGATED"` and `oracle_probe.held_out_programs_executed = 0`, so the corpus
  can be counted instead of assumed. Re-teaching with victims upgrades `UNGATED` → `ADMIT`.

Wired at the single chokepoint every learn path uses: `VerifiedSkillStore.crystallize_code_fix`
(`admission_victims=`, `admission_archive=`). A refusal returns `crystallized: False` and writes
no row — verified by reading the database, not by trusting the return value.

## 4. What this does **not** say

- `ADMIT` is bounded by the victims and probe points supplied. `probe_bounded: True`,
  `whole_task_correctness_proved: False`. It is not a proof and not a capability.
- The gate cannot repair a wrong oracle. It inherits the caller's specification.
- **The shipped autonomous callers still pass no victims**, so they still admit `UNGATED`. The
  seam and the one keyword each needs are named here rather than papered over:
  `autonomous_awake_loop_v1`, `cow_impact_repair_engine_v1`, `multistep_repo_closed_loop_solver_v1`,
  `retained_repair_session_v1`, `swe_self_improvement_bridge_v1`. Turning that on requires each
  caller to own a victim corpus with specs; `retained_repair_session_v1` structurally cannot yet
  (one target, one `ProjectTestOracle`).
- Nothing here updates model weights, and nothing here establishes sentience.

## 5. Why this is the fastest real lever (current research, not intuition)

| Source | Date | What it measured |
|---|---|---|
| **FGSE**, arXiv:2611.14326 | 10 Nov 2026 | Candidate lesson = hypothesis (precondition, behaviour change, expected effect, verifier), applied in temporary state, tested on target-transfer / falsification / archived-regression before commit. Budgets 8/16/16, ≤3 candidates per episode. Falsification failures **5.0%**, regression damage **1.3%**, harmful committed updates **3.6%**. Notes coding/math have cleaner verifiers, while **SWE-bench stays regression-prone because repository changes are contextual**. Memory gains saturate with size: quality and selective retention are the bottleneck. |
| **GRASP**, arXiv:2605.29668 | 2026 | Admits a library edit only on net held-out improvement under a hard regression budget. **+21.0 points** over the strongest of five memory baselines; ablation localises the gain to **the gate**, not skill writing — writing without validation is *no better than no skills*. |
| **Skill-V**, arXiv:2610.11781 | Oct 2026 | Versioned falsifiable contracts + non-regression evidence gate. Acquisition-only **68.8%** vs full **95.3%**; without the gate 9 of 46 committed revisions regressed. |
| **The Regression Tax**, arXiv:2607.22520 | Jul 2026 | Harm can come from skill *descriptions* alone, with the body never invoked — an interpretation shift, not a wrong instruction. Presence is an intervention too. |
| **SkillApt**, arXiv:2609.26863 | Sep 2026 | Separates gating *edits* from estimating the per-state counterfactual effect of *activating* a skill; applicability cannot repair a capability failure shared by both arms. |
| **When Does Continual Learning Require Learning**, arXiv:2607.07847 | Jul 2026 | Prompt/playbook optimisation fits fast (**+~40%** on one stage) then falls back to baseline after the next domain; methods that never do a full weight update struggle to accumulate capability under domain shift. |
| **SDFT**, arXiv:2601.19897 | 2026 | Demonstration-conditioned self-distillation makes demonstration learning on-policy: higher new-task accuracy with substantially less forgetting than SFT; sequential skills accumulate without regression. |
| **OSWorld 2.0**, official site | Jun–Sep 2026 | 108 long-horizon workflows, 31 self-hosted sites, ~318 tool calls/task (vs ~30 in 1.0), 27.25 scoring checkpoints. Best binary completion **31.4%** (partial 68.3%) on v2026.08.08. Authors' residual failures: losing constraints, missing mid-task information, guessing instead of asking, **skipping verification**, hidden state. |

Read together: the field's own ablations say the *admission gate* is where the gain lives, and the
frontier's remaining computer-use failures are verification and state-tracking failures — not
"has never seen this action once".

## 6. The four gaps, with the fastest honest mechanism for each

1. **Weight updates.** Real and eventually necessary (2607.07847). Order: gate the memory first,
   then consolidate only admitted, deduplicated, contrastive traces via on-policy self-distillation
   (SDFT) or sparse/low-rank updates, with replay and reserved no-retrieval probes. Never train on
   every success.
2. **Conceptual understanding.** Typed task representations + executable contracts + refusal
   boundaries; this tree already has the read-only typed lane and the compositional engine. The
   missing quantity is not more wording, it is preconditions and postconditions that a checker can
   fail.
3. **Transfer.** Buy scope with executed observations (`skill_scope_acquisition_v1`), then measure
   transfer as an intervention: with/without on the same held-out instances, repairs and
   regressions counted separately. One demonstration in this repo recovered 0.529 of developer
   changes at precision 1.000; a second showing from a second place is what enabled transfer.
4. **Reasoning why.** Every durable lesson carries its source trajectory, its verifier, a positive
   probe, a null probe, and now an admission record naming the programs it was tested on. "It
   worked once" is not a reason.

## 7. Killed before implementation

- Training on all successful traces immediately (forgetting; 2607.07847, SLoRA).
- Growing the library and hoping (Skill-V acquisition-only 68.8%; FGSE saturation).
- Counting a non-firing rule as evidence of safety (this gate refuses it).
- Letting the caller declare which victims are falsification cases (families are executed).
- Relaxing the 50 ms wake-sleep assertion to make a run green (never).

## 8. Test ledger (real counts, including the failure)

```text
.venv/bin/python -m pytest -q <9 suites, includes the 19 new admission tests>
181 passed in 12.14s

.venv/bin/python -m pytest -q <19 skill-store suites>
243 passed in 17.76s
```

- New: `canonical/tests/test_lesson_admission_gate_v1.py` — **19 tests**, all executing real
  programs against real specs on a real temporary SQLite store.
- **One failure observed and not hidden:** the first 9-suite run reported
  `1 failed, 180 passed in 16.04s` —
  `test_tier0_compiled_http_skill_recall_stays_under_50ms_across_even_wake_episodes`,
  `2194.82 ms not less than 50.0`. It did not reproduce: the same file alone passed (6 in 5.07s),
  the unchanged 8-suite ledger passed (162 in 11.52s), and the 9-suite rerun passed (181 in 12.14s).
  Load-sensitive; **no assertion was relaxed** and no performance fix is claimed.
- One environment gap was fixed honestly, not patched around: `test_the_repo_ships_its_lessons_v1`
  failed with `TREE_SITTER_SUBSTRATE_MISSING` until the real `tree_sitter` /
  `tree_sitter_languages` packages were installed in the venv; then 7 passed.
- `compileall` clean on all four changed/added Python files; `git diff --check` clean.

## 9. The one-sentence answer

The direction is real; the quantifier is false. **One showing buys a hypothesis. Admission buys
permanence.** Until today this store granted permanence on the hypothesis alone — measured, one
repair and one broken program, zero unseen programs executed. Now the write is refused until the
lesson has repaired something it never saw and left something correct alone.
