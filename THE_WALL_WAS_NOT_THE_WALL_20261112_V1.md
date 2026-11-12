# The wall was not the wall: nine rounds counted a refusal nobody had ever lifted

**2026-11-12.** Branch `arena/9ef12a45-brain`. Base `dcbbba05` (#6735).

The owner asked the same question a fifth time, and the fifth asking deserves a different
kind of answer than the first four. The previous rounds answered with arguments, then with
identifiability measurements, then with 2026 papers, then with a chain of priced links. Every
one of them pointed at the same obstacle and none of them had ever *removed* it.

This round removes it. The obstacle was not the obstacle, and the finding is a
counterfactual result about this tree, produced by a reusable instrument.

Authority **NONE**. One machine, $0, zero model dependency, disposable clones only, host
`git status --porcelain` byte-identical before and after (`host_untouched: True`).
`truth.achieved` stays `false`. No capability registered. No family flipped. No guard touched.

---

## 1. What was claimed, and by whom

Four documents written on this same day, in good faith, built a staircase on one number:

| document | PR | says |
|---|---|---|
| `THE_ADMITTED_CONFINEMENT_EXISTS_20261112_V1.md` | #6733 | **19 of 38** realistic advanced-coding sentences refuse with `FAIL_CLOSED__COMPUTER_EXECUTION_REQUIRES_ADMITTED_CONFINEMENT`; builds `confinement_v1.py` as the substrate |
| `WHAT_2026_SAYS_ABOUT_THIS_20261112_V1.md` | #6734 | prices "step 1: wire the seam" as the highest-value work item |
| `WHY_NOT_JUST_GIVE_IT_THE_TRY_20261112_V1.md` | #6744 | repeats the count as fact and says "the door admits 8/149, the confinement bucket is the current wall" |
| `THE_CORPUS_CAN_ONLY_COME_FROM_REAL_WORK_20261112_V1.md` | #6736 | explains the near-empty store as downstream of the unwired seam |

This tree has a law for exactly this situation, written by an earlier round that caught
itself making the same mistake:

> **A blocker is not the first obstacle. It is the obstacle whose removal makes the thing
> work. A census finds symptoms; only a counterfactual finds causes.**
> — `what_actually_blocks_the_front_door.md` (§3, and the test that pins it)

Nothing in the #6733–#6744 chain ran the counterfactual. This round does.

## 2. Re-measured first, because the tree had moved

`canonical/tools/realistic_goal_reach_probe_v1.py` on this base: **21 of 38** refuse with
the confinement status, not 19 — the wall had grown by two since #6733 measured it on
`8439f609`. Three execute (`git.repository.operate.v1`, `python.refactor.rename_symbol.v1`,
`software.review.synthesis.supercomposer.v1`). The published number was already stale by the
time it was quoted a fourth time.

## 3. The instrument

`canonical/tools/lift_the_refusal_and_see_what_remains_v1.py` — four stages in disposable
`git clone --no-local` clones, each strictly stronger than the last:

| stage | what is removed | what it answers |
|---|---|---|
| **S0** baseline | nothing | does this tool reproduce the published count? |
| **S1** boundary lifted | `computer_execution_boundary_v1.refuses_execution` → `False` | what does "wire the confinement seam" actually buy? |
| **S2** + discovery lifted | `live_brain_route_admission_v1._serve_by_acting` → `None` | is there a second refusal site wearing the same status string? |
| **S3** + arguments bound | the capability is handed the arguments its own `action_template` declares | was it leaving confinement, or leaving *binding*? |

The tool **refuses to run on a dirty tree** — not a formality: the first invocation aborted
with `HOST_NOT_CLEAN` because this very file was untracked, and that is the property that
makes its `host_untouched` result worth quoting.

## 4. The result

### 4.1 Lifting the boundary alone buys nothing — and cannot

```
stage                                    passes   still-confinement
S0  baseline                                  0   21 of 21
S1  boundary decision lifted                  0   21 of 21
S2  + automatic-discovery refusal lifted      0    3 of 21
S3  + declared arguments bound                2    —        (2 of 21 work)
```

**S1 = 21 of 21 still refuse.** Lifting the execution boundary — the exact change four
documents priced as the next step — changed **zero** verdicts. The wall the last nine rounds
were aimed at is not load-bearing at the point they were aiming.

### 4.2 Why: the decision was spelled twice, and the copy was the wall

Instrumenting every emitter of the status string found that the dominant source was **not**
`computer_execution_boundary_v1` at all. It was
`live_brain_route_admission_v1._serve_by_acting`, a refusal about automatic *computer
discovery* that stamps the boundary's status and failure class onto its result. On the 21
sentences it fires **18 times**; the boundary's own decision fires for 3.

And beneath that, a second structural defect, measured rather than argued:

```
with the boundary's own decision lifted, 3 of 21 sentences
still came back FAIL_CLOSED__COMPUTER_EXECUTION_REQUIRES_ADMITTED_CONFINEMENT
emitted by canonical/runtime/composer_route_v1.py:4089
```

`composer_route_v1.execute_chain` and `live_integrated_brain_v1` both **re-derived** the rule
from the boundary's three small predicates instead of asking `refuses_execution`, which its
own docstring calls *"the single decision every execution site must use"*. A caller that
re-derives a rule cannot be reached by changing the rule — so a release condition admitted in
the boundary would have been silently ignored by two sites, and the wiring diff that four
documents recommended would have measured as ineffective and been reverted.

That is the finding. **The previous rounds were not wrong about the refusal. They were wrong
about who was emitting it.**

### 4.3 The thing nobody had tried: binding

S2 lifts both refusal sites; 21 → 0 confinement refusals. Still **0 execute**. S3 hands each
capability the arguments its own `action_template` declares, resolving what the sentence names:

| capability | S0 → S3 | evidence |
|---|---|---|
| `python.source.symbols.index.ast` | refusal → **works** | `output_verified: True`, `symbol_count`, `call_edge_count`, index on disk |
| `python.source.taint_flow.v1` | refusal → **works** | `output_verified: True`, `finding_count`, `reaches`, report on disk |
| `python.fault.localize.dynamic.dataflow.v1` | → `TEST_TIMEOUT` | the capability ran; the test suite it was pointed at did not finish |
| `python.software.repair.apply.verified.v1` | → `TEST_PATHS_REQUIRED` | a real interface requirement it states |
| `code.index.tree_sitter.incremental.v1` | → `TREE_SITTER_SUBSTRATE_IDENTITY_UNAVAILABLE` | the tool is not installed on this box |
| `python.contract.check.crosshair.v1` | → `ORACLE_INCONCLUSIVE` | the adapter's own typed "tool absent" verdict |
| `software.repair.choreograph.crossfile.v1` | → `REFUSING_BROAD_REPO_MUTATION` | a real safety refusal, correctly standing |

Two full capabilities execute end-to-end the moment their declared arguments are bound, after
twenty-one of twenty-one refusals said the obstacle was confinement. The remaining failures
are substrate absence (2), interface requirements the capability states (1), real safety
refusals (1), and harness cost (1).

**The measured order is: binding before confinement, and confinement contributes 0 of 21 even
when fully lifted.**

## 5. What was fixed, and the refusals that did not move

Two additive de-duplications, pinned by `canonical/tests/test_one_decision_spelled_once_v1`
(**7/7**), so that a future admission of a release condition actually propagates:

| file | before | after |
|---|---|---|
| `canonical/runtime/composer_route_v1.py` | re-derived the three predicates at `execute_chain` | `_chain_refuses` asks `refuses_execution` |
| `canonical/runtime/live_integrated_brain_v1.py` | kept its own `is_unconfined_repair_entry` copy | `_plan_refuses` asks the decision twice, `repair=False` then `repair=True` |

The test pins four things: every one of 153 registry ids moves when the decision is
substituted; no runtime module re-derives the rule from the small predicates; **every existing
refusal is unchanged** (identical status, failure class, empty `steps`, same `failed_step`);
and the repair row still splits its two halves exactly as `refuses_execution`'s docstring says
it must.

And the instrument confirms the repair on the same corpus:

| stage | before the fix | after the fix |
|---|---|---|
| S0 baseline | 21 confine | **21 confine** (nothing released) |
| S1 boundary lifted | 21 confine | **18 confine** (the 3 trapped rows now track the boundary) |
| S2 + discovery lifted | 3 confine | **0 confine** |

A single decision that can be released is a safety property. A decision spelled three times is
three independent walls, only one of which has a release condition.

## 6. What this does and does not settle

**Settles, measured:** "wire the confinement seam and the advanced-coding wall falls" is false —
lifting it buys 0 of 21. The dominant emitter of the confinement status was a different refusal
site wearing the same label. Two callers could not have honoured a release even if one had been
admitted. Binding the declared arguments is worth more than every confinement decision in the
tree combined, on this corpus.

**Does not settle:** that confinement is unnecessary. 18 of 21 sentences do route through
`_serve_by_acting`, which refuses *automatic discovery* — a genuinely broader authority than any
one capability's declared effects, and lifting it is not a change any agent may make on its own
say-so. The honest statement is narrower: **the confinement substrate is not what is blocking
these sentences today, and it is not the next thing to build.**

**Does not claim:** that the 2 working capabilities are new capability. They were registered,
verified and bound before this round. What is new is the measurement that says the wall in front
of them was misidentified for nine rounds, and the fix that makes the real decision singular.

## 7. The limiting factor, restated from the measurement

The owner's engineering intuition — *give it the most advanced actions and let it try* — survives
this round better than the last four did. What the numbers say blocks it is:

1. **The interface (binding).** 21 refusals that were all labelled "confinement"; bind the
   declared arguments and 2 execute immediately, with 5 more reaching their real next obstacle.
   Every document in the #6733–#6744 chain ranked this *below* the seam. The measurement ranks
   it above.
2. **The label.** Three different refusals emitted one status string, so nine rounds measured
   the label and concluded about the mechanism. This is the cheapest defect in the tree to fix
   and it cost the most.
3. **The substrate.** `tree_sitter`, `crosshair` absent on this box; each costs one
   `pip --user --break-system-packages` (measured in `THE_CENSUS_WAS_WRONG_20261112_V1.md` §2)
   and each unlocks a capability that is already written.
4. **Confinement, last, for what actually needs it.** Repair loops and shell execution still
   need a carrier. On this corpus that is 1–3 rows, not 19.

The fastest lawful route is therefore the reverse of the one four documents recommended:
**bind, then install, then confine** — and before any of them, **measure which refusal is
actually firing**, because for nine rounds none of us did.

## 8. Receipts

```bash
# the instrument (refuses to run on a dirty tree; disposable clones only)
python3 canonical/tools/lift_the_refusal_and_see_what_remains_v1.py --json /tmp/lift.json

# the fix and its pin
python3 -m unittest canonical.tests.test_one_decision_spelled_once_v1 -v     # 7/7

# the corpus this round re-measured first
python3 canonical/tools/realistic_goal_reach_probe_v1.py                     # 21/38 confine
```

Both instrument runs are recorded: `S0 21→21`, `S1 21→18`, `S2 3→0`, `S3 2 works`, and the
second run's `host_untouched: True` over 311 s. The first run's `S1 = 21 of 21` is the number
that refutes the previous four documents, and it was produced on base `dcbbba05` before any fix
landed.
