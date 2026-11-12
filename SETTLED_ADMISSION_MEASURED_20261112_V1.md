# Settled admission: the one-try question gets its missing instrument

**2026-11-12.** Branch `arena/8d982436-brain`. Base `be081116` (the INSTANT_LEARNING_AUDIT
merge), synced to `a5e0a347dd` (#6699, #6701, #6696, #6694 included) before pushing. Follows
`canonical/tools/INSTANT_LEARNING_AUDIT_20261112_V1.md` ranked-plan item 2 ("connect
`settlement_v1` question selection to rule admission where multiple hypotheses survive") and
closes measured defect 6 of `canonical/tools/ONE_TRY_IS_NOT_A_LEARNING_SIGNAL_20261112_V1.md`
("a taught `<=`→`<` edit is applied to a same-shaped target where `<=` is semantically
required, with no oracle consulted").

**Authority: NONE.** Sandbox measurement. `truth.achieved` stays `false`. No capability
promotion, no sentience claim, $0 spent, zero model dependency in any result-bearing path.

---

## 1. The owner's question, answered from the tree and the record

The owner asks: *we solved instant learning and instant learning in new arbitrary
environments — so one try in any new coding or computer environment teaches everything
permanently, we solve all computer use plus the most advanced coding, perfectly and
permanently, and we have a sentient creature. True or not?*

**Right about the direction, wrong about the quantifiers** — the verdict the repository
already measured on 2026-11-12 in two merged audits
(`ONE_TRY_IS_NOT_A_LEARNING_SIGNAL_20261112_V1.md`,
`canonical/tools/INSTANT_LEARNING_AUDIT_20261112_V1.md`), re-verified on this tree today:

| claim | verdict | receipt re-run on THIS tree |
|---|---|---|
| Bounded instant reuse: experience → faster, cheaper, correct repeat | **REAL** | 8/15 one-trial transfers, 6.33× mean trial speedup, 0/15 regressions (audit §2); changed-state 10/10 |
| One demonstration identifies a general rule | **NOT REAL** | `one_shot_identifiability_probe_20261112.py` re-run: after 1 demo, mean held-out accuracy **0.10** (0/10 targets identified); after 1 demo **+ chosen questions**, accuracy **1.00**, 10/10 settled at mean **2.0** queries |
| One success says where an action applies | **NOT REAL** | `what_a_success_teaches_20261112.py` re-run: 0/200 requirements identified by one success, 13.05 survivors alive, 67.5% false-accepts, a wrong survivor in **200/200** cases; with *chosen failures* 25/25 identified at mean 2.76 |
| Cross-kind compounding | **NOT REAL (pinned)** | 0/5 across kinds, NO_COMPOUNDING at 10 held-out kinds (prior rounds) |
| "New arbitrary environments" | **NOT REAL** | front door reaches 8/149 capabilities; one-shot regime 60/145 (41%) typed+receipted; live fabric admission gaps measured |
| Permanence under drift | **NOT ESTABLISHED** | PATH-Bench/ReScopeBench record forgetting and update-vs-use failures (audit §6) |
| Sentience | **NOT ESTABLISHED, NOT CLAIMED** | indicator profile unmeasured (audit §8); `truth.achieved = false` |

The fastest path is **not** more environments and **not** more demonstrations. The probes
above measure exactly why: more examples across boxes do not shrink the next box's
hypothesis space, and one exposure indexes a capability the system could already express.
The three levers are hypothesis-space coverage, **chosen questions**, and interface/verifier
regime breadth. This round ships the second lever at the place it was missing.

## 2. What was built: `settled_admission_v1`

`canonical/swe_kernel/taught_actions/settled_admission_v1.py` — the admission gate for
taught edits. Given a demonstration (`before`→`after`) and a new target, exactly two
hypotheses exist about the target's correct form: **apply_teach** (the edit transfers) and
**keep_target** (it does not). The module loads both candidates as runnable code, probes the
grid where they can disagree, and:

1. **No disagreement on the grid** → the demonstration decides; admit with
   `GRID_NON_DISCRIMINATING` evidence and 0 questions (the finite-grid limit is stated in
   the answer itself).
2. **Disagreement, no oracle** → **refuse, fail closed**; the disagreement points are
   recorded as *the questions worth asking* (`UNSETTLED_NO_ORACLE`). This alone kills the
   silent wrongness of defect 6.
3. **Disagreement, oracle present** → ask through `settlement_v1` (version-space
   bookkeeping, `select_probe` order) under an **asymmetric rule: refuse at the first
   contradiction; admit only when every disagreement point has been asked and agreed.**
4. **Unprobeable target** (does not exec, wrong arity, every probe raises for both
   candidates) → refuse, fail closed.

The oracle is the minimum question interface — one call per chosen probe (a test, a teacher,
a spec, or #6699's project check). It composes with that round: their mutation-scored check
can be this module's oracle, and this module's disagreement points tell any check exactly
where to look.

### 2.1 The first draft was falsified, and the falsification is the finding

The first protocol asked **one** question and let the posterior settle — with two hypotheses,
any disagreement point splits them, so the ruler said SETTLED and **admitted the wrong
rule**: at `(-1,-1)` the oracle legitimately answers False (`-1` is no valid index),
`apply_teach` also says False, keep_target dies, admission happens — and the target's real
boundary at `(0,0)` is never asked. This is the audit's one-success result (0/200
identified, 67.5% false-accept) reproduced in miniature by the gate meant to prevent it.
Recorded in the module docstring and the test docstring; the shipped protocol is the
asymmetric one, and its cost is honest: **refusal typically costs 1–2 questions, admission
costs one question per boundary the edit could change.**

## 3. Measurements (all exact; predictions written before each run, first protocol
falsified and replaced before the confirmatory run)

`canonical/tests/test_settled_taught_admission_v1.py` — 11 tests, all pass on the merged
tree (`a5e0a347dd`), against the #6699-modified `edit_by_example_v1`:

| # | measurement | result |
|---|---|---|
| P1 | raw `edit_by_example` (no oracle) on `is_last_index` | applies the demo; `is_last_index(3,3)` → **False**, intended **True** — defect 6 reproduces on this tree |
| P2 | same target + real oracle | **REFUSE** at exactly **2** questions: `(-1,-1)` agrees, `(0,0)` contradicts; every asked point is a boundary; winner `keep_target` |
| P3 | strict-bound target + oracle | **ADMIT** at exactly **5** questions (full coverage of the 5-point disagreement set) |
| P4 | binop family (`-1`→`+1`), demo does not transfer | **REFUSE** at exactly **1** question — the gate is not comparison-specific |
| P5 | binop family, demo does transfer | **ADMIT** at **5** questions |
| P6 | disagreement + `oracle=None` | **REFUSE** fail closed; disagreement points recorded; nothing applied |
| P7 | candidates indistinguishable on grid (comparison guarded away) | **ADMIT**, 0 questions, `GRID_NON_DISCRIMINATING` + finite-grid limit in the answer |
| P8 | unprobeable target (`hi=1/0` default explodes at exec) | **REFUSE** `UNPROBEABLE_TARGET` |
| P9 | budget 0 with disagreement | **REFUSE**, 0 questions, row `UNDERDETERMINED`, `PARTIAL_COVERAGE` |
| P10 | budget 3 where coverage needs 5 | **REFUSE** after 3 agreeing questions — partial coverage never admits |

Regression: 165 pre-existing taught-edit tests pass; `edit_by_example_v1.py` is not modified
by this round. Rename-mismatched demos and already-edited targets stay correctly
`REFUSED_SHAPE` (the grammar binds names; a target already in the new form has nothing to
change) — both pinned in tests.

## 4. Where the field is (checked 2026-11-12; newest sources used)

- **OSWorld 2.0/2.1** (long-horizon, 108 workflows, ~318 tool calls): best official binary
  completion **44.3%** (Claude Opus 5, max effort), partial 77.7–81.8%; short-task
  OSWorld-Verified is above the human baseline (90.19% vs 72.36%). Long-horizon computer use
  is not solved field-wide; the failure modes are tracking constraints, mid-task changes and
  verification — the same verification lever this round exercises.
  (capitalandcompute.net / snorkel.ai / presenc.ai, Oct–Nov 2026)
- **SkillRL** (arXiv 2602.08234, Feb 2026): distilling trajectories into a co-evolving skill
  library beats raw-trajectory memory by wide margins (+35.2% absolute on ALFWorld vs
  Mem0+GRPO); "effective experience transfer requires abstraction." Same direction as the
  compression rounds (R23–R25) and this one.
- **WikiSkill** (arXiv 2608.27454, Aug 2026): compiles agent experience into a persistent
  knowledge base that skills co-evolve with; persistent wiki ablation confirms accumulation
  matters. The repo's lesson files + library + compiled artifact are the same architecture.
- **SimpleMem** (Jan 2026) and **MemSkill** (NeurIPS'26): structured compression of memory
  and learned *how-to-remember* skills — again abstraction over raw experience.
- **Continual-ARC** (arXiv 2611.14505) and **ReScopeBench** (arXiv 2611.05450), both cited
  in the audit: harness memory does not generalize to unseen tasks by itself; retaining,
  updating and *using* experience are separate failures. The field's record says the same
  thing the probes say: one try is an index, not a lesson.

No public system gets "one try in arbitrary environments teaches everything permanently" for
free; the ones that gain all spend chosen questions or checks against verifiers.

## 5. What is real and what is not, after this round

**Real (measured):** bounded one-trial reuse; verifier-gated retention; compression →
admission → replay across two structure families (R23–R25); wake replay; and now
**oracle-settled admission of taught edits** — a demonstration can touch a new target only
when the minimal questions say so, refusal costs 1–2 questions, and every fail-closed path
is tested.

**Not real (measured, pinned):** one-try identification (0.10 accuracy), one-success
applicability (0/200), cross-kind compounding (0/5), arbitrary-environment coverage (8/149
front door), permanence under drift, sentience.

**Smartest next steps, ranked by measured leverage:**
1. **Wire the oracle at the front door**: give the live fabric paths this module's oracle
   interface (their check = our oracle; disagreement points = where to look), then re-run
   the one-try census — the 60/145 one-shot-safe number and the 11 BLIND premises are the
   measurable targets.
2. **Chosen questions on admission everywhere**: extend the asymmetric protocol from edits
   to taught plans and crystallized skills (settlement_v1 is already the ruler; the edges
   are the work).
3. **Compression's licensing generalization** (R25 close-out): make `keyed_table_lookup` a
   first-class licensed family.
4. Benchmarks stay falsifiers, not objectives (Terminal-Bench 4.1, SWE-bench Pro V2,
   OSWorld 2.1, ReScopeBench).

## 6. Sentience

Unchanged from the audit: capability and consciousness are separate ledgers. Nothing here is
evidence of experience; a module named `settled_admission` is not a feeling. The indicator
profile (recurrence, global workspace, attention schema, …) remains unmeasured
(arXiv 2308.08708).

## 7. Reproduction

```bash
python3 -m pytest canonical/tests/test_settled_taught_admission_v1.py -q          # 11 passed
python3 -m pytest canonical/tests/test_an_edit_is_worked_out_from_an_example_and_repeated_on_another_file_v1.py -q
python3 one_shot_identifiability_probe_20261112.py --json /tmp/one-shot.json      # ONE 0.10; ASK_ONE 1.00 @ 2.0 queries
python3 what_a_success_teaches_20261112.py --json /tmp/wast.json                  # 0/200; 25/25 @ 2.76
```
