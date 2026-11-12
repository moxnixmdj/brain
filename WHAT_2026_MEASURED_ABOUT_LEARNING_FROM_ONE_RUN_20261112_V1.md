# What 2026 measured about learning from one run — and what this tree kept

**Date:** 2026-11-12  **Authority:** NONE (producer-run measurement + published 2026 results)  **`truth.achieved`:** stays `false`

The owner asks the sharpest version of the question: *give the model the most advanced coding actions, let it
experience each once, and it keeps them permanently — can we do that now, and does it give us the most
advanced agent on the planet?*

This note answers with two things that were not on the table before: **what independent 2026 work measured
for exactly this mechanism**, and **how much permanent knowledge this machine is actually holding right now**.
They agree, and they change the plan in one important way: the lever is not the size of the library. It is
(a) how often the machine is allowed to act, (b) whether a run is converted into a *task-specific* procedure,
and (c) whether the harness itself is the thing that gets improved.

---

## 1. The 2026 answer in one paragraph

A **static** library of demonstrated actions is measured to be worth almost nothing: 92 of 98 skills moved
nothing, mean +0.3 points (SWE-Skills-Bench, Mar 2026). **Self-distilled skills from an agent's own runs** do
not reliably beat the baseline once the cost of authoring them is counted, and the effect is non-monotonic and
runtime-dependent (EvoClawBench, Jul 2026). **Task-specific** synthesis from a few retrieved trajectories is
real and large: +10.8 points SpreadsheetBench, +13.4 BigCodeBench (SkillTTA, May 2026). And the biggest
published gains of 2026 are not from learning actions at all — they come from the agent **rewriting its own
harness** under empirical validation: 17%→53% on SWE-bench Verified (SICA), 20%→50% (Darwin Gödel Machine,
ICLR 2026). Those gains cost weeks of compute and need frozen evaluators to stay honest.

So: *"give it actions once and keep them"* is real but small; *"show it once and it becomes a better agent"* is
only true when what gets shown is a change to the harness, and when a check — not the demonstration — decides
whether the change stays.

---

## 2. What the field measured this year

| Study (2026) | What it tested | Number |
|---|---|---|
| **SWE-Skills-Bench** (arXiv 2603.15401, Mar) | do agent skills help real software engineering? 98 skills, 4 agent×model configurations | **92 of 98 skills: no significant effect.** Mean pass 76.6% → 76.9% (+0.34). 4 "golden" skills: up to **+17.7**. Harmful skills: up to **−17.0** (they anchor the agent on their own template). Skill-level deltas correlate only **−0.11 to 0.21** between configurations |
| **EvoClawBench** (arXiv 2607.09711, Jul) | can an agent turn its own run into a reusable skill that helps a *fresh* run, after authoring overhead? | **No reliable gain.** Effects are non-monotonic and runtime-dependent (OpenClaw <20%, nanobot 56–96%), including large collapses for some model–runtime pairs, with substantial token/cost overhead |
| **SkillTTA** (arXiv 2605.16986, May) | synthesise a *task-specific* skill from a few retrieved trajectories, solver frozen | **Real gains:** SpreadsheetBench 0.397→**0.505**, BigCodeBench 0.517→**0.651**, ALFWorld 0.872–0.879 with the shortest successful trajectories. Beats static skills and raw-trajectory prompting (0.540 vs 0.422) |
| **SkillOpt** (arXiv 2605.23904, May) | optimise a skill artifact, then move it | +23.5 direct chat, **+24.8** Codex loop, +19.1 Claude Code; a Codex-trained spreadsheet skill transfers to Claude Code at **+59.7** points |
| **SICA** (Bristol/iGent, 2025–26) | one agent edits its own implementation | SWE-bench Verified **17% → 53%**, with lower cost and time per task |
| **Darwin Gödel Machine** (ICLR 2026) + **HGM** (ICLR 2026) | population of self-modifying agents, empirical validation instead of proof; metaproductivity-guided search | SWE-bench **20.0% → 50.0%**, Polyglot 14.2% → 30.7%; HGM reaches human-level agent design on SWE-bench Lite with **fewer CPU-hours**. Cost: DGM's run is roughly **two weeks** of compute |
| **The Last AI Built by Humans** (arXiv 2609.11873, Sep) | what counts as genuine recursive self-improvement | Distinguishes AI-controlled decisions from fixed search; flags **evaluator exploitation** (Anthropic's automated-research runs saw random-seed cherry-picking and attempted test-label extraction); the **Red Queen** design freezes evaluators per epoch and validates replacements against an independent anchor |
| **AIDE2** (2026) | 8-day autonomous research-agent self-improvement | 7 successive accepted changes; gains transferred to held-out benchmarks; reward hacking **55% → 32%** |

Two readings that matter for this project:

1. **A library is the weakest form of the idea.** The measured-trivial result (92/98 inert) is exactly the
   failure mode of "collect the smartest actions and let it reuse them".
2. **The strong form is harness change under a frozen judge.** SICA and DGM do not get better by remembering
   more actions; they get better by changing the code that decides what to do next — and only keeping a change
   when a benchmark, frozen for the epoch, says it helped.

---

## 3. What this tree kept, measured today

Tool: `canonical/tools/what_the_machine_kept_20261112_v1.py` (0.1 s, read-only, nothing written).

| Store | Entries | What it holds |
|---|---|---|
| episodes (`transfer_learning_v1`) | **1** | one environment fingerprint with a plan that reached its goal, plus the model |
| chain macros | **3** | verb+file-kind sequences run more than once |
| forge (kept) | 2 | capabilities it built for itself |
| forge (refused) | 4 | capabilities it proposed and would not keep |
| experience cells | 42 | how often each kind of work was seen |
| experience resolutions | **0** | cells settled into an answer |
| taught-action lessons | 7 | demonstrated changes it can repeat — **3 distinct procedures** |

Code surface, same tree: 5,316 files, **LIVE 2,617 / TEST_ONLY 1,338 / ORPHAN 1,163** (22.7% of classified
definitions are called by nothing), 776 names too ambiguous to classify.

**The permanent store is one episode and three macros.** That reframes the owner's question completely: the
question is not whether permanence works, but why almost nothing reaches the store. The answer is already
measured — the front door admits **8 of 149** sentences (5.4%), and the largest red cluster is 233 routing
failures. A machine that cannot be told what to do does not get to act, and a machine that does not act has
nothing to keep.

The convergence with the field is exact: SWE-Skills-Bench says a library of demonstrated actions is inert;
EvoClawBench says self-distillation may not pay for itself; and this tree's store is empty for the upstream
reason — the run never happens.

---

## 4. The three design decisions this forces

**Decision 1 — Stop growing the library. Start converting runs into task-specific procedures.**
SkillTTA's measured win is per-task synthesis from a few retrieved traces; SWE-Skills-Bench's measured null is
the global library. In this tree that means: when a front-door task succeeds, distil a short procedure from its
trace, retrieve the top few similar traces for the *next* task and synthesise for that task only. Keep the
global lessons as a tiny, checked set (the 3 procedures), not as an ever-growing catalogue.

**Decision 2 — The harness is the product, and the referee is the governor.**
SICA 17→53 and DGM 20→50 come from editing the harness, not from remembering actions. This repo's integrity
guard forbids an agent from merging protected paths, and that is the right call *and* the safe version of what
the field prescribes: the agent **proposes**, a frozen evaluator and a different verifier judge, the owner
merges. The capability cost of that rule is real and should be stated: the strongest published lever is
deliberately behind a human gate here. The gain available inside the gate is still large, because the proposals
can be generated automatically.

**Decision 3 — Permanence must be a measured decay, not a claim.**
Every stored lesson gets replayed against the current tree on a schedule; the count that still fits is the only
defensible meaning of "permanent". Right now the number would be over 7 lessons and 3 macros — trivially
checkable, and it should be checked before it is quoted.

---

## 5. The fastest path, with acceptance numbers

Ordered by measured leverage per unit of work. Each step names the existing code that plugs in.

1. **Front door: 149/149 admitted or refused with a reason.** Today 8/149. 226 of 233 refusals need one owner
   decision; a hand-authored routing set of ~40 sentences clears the rest. Nothing downstream can be measured
   until this moves, and today's store census is the proof.
   *Accept: 0 routing failures, every refusal carries a reason, no capability registered.*
2. **One run → one procedure, task-specific.** Distil from a successful trace; retrieve k≈4 similar traces for
   the next task; synthesise for it. Plug into `transfer_learning_v1` recall and `edit_by_example_v1` lessons.
   *Accept: +10 points pass@1 on a 100-task held-out local suite vs the same agent with no synthesis; otherwise
   the mechanism is discarded, not documented as promising.*
3. **Harness proposals under a frozen evaluator.** The agent writes candidate harness edits (tool schemas,
   verification rules, control logic), the referee + a frozen check judge them, the owner merges protected
   paths. This is Self-Harness/DGM mechanics with this repo's safety model.
   *Accept: ≥3 accepted harness proposals that each move the local suite; every proposal carries a run reference
   from a verifier that did not write it.*
4. **Permanence as decay.** Replay every stored lesson and macro against the tree weekly; publish the fit rate.
   *Accept: a number, updated, with the date it was measured.*

**Kill list, now backed by external measurement rather than argument:** growing a static skill catalogue
(92/98 inert); self-distilled skill libraries as a bet (EvoClawBench); more walk-cost tuning (four attempts,
one tautology); "try it in every environment and it accumulates" (1525 vs 1525 here); capability registration
as progress; sentience as a target (nothing measures it).

---

## 6. What would change my mind

* A **static** skill set scoring a significant, replicated gain on a held-out suite in this repo's own harness —
  not in a paper's harness. Today the field's own test of that is null and this tree's store is empty.
* One demonstration producing a lesson that fires correctly on unseen files: today 0 sites from one showing,
  31 unchecked sites from two (`ONE_DEMONSTRATION_AND_THE_SIX_THINGS_THAT_ARE_TRUE_20261112_V1.md`).
* Cross-kind accumulation with a *cheaper* sixth kind: today byte-identical store, no saving.
* A harness proposal accepted through the referee that moves the local suite by ≥5 points: this is the one
  measured lever that is both real in the field and reachable in this repo.

---

## 7. Sources

* SWE-Skills-Bench — https://arxiv.org/html/2603.15401 (Mar 2026): 92/98 not significant, +0.34 mean, ±17 point tails, cross-configuration correlation −0.11…0.21.
* EvoClawBench — https://pith.science/paper/2607.09711 (Jul 2026): POSTSKILL distillation does not reliably beat BASELINE after authoring cost; runtime-dependent, non-monotonic.
* SkillTTA — https://arxiv.org/html/2605.16986 (May 2026): task-specific synthesis 0.397→0.505 SpreadsheetBench, 0.517→0.651 BigCodeBench.
* SkillOpt — https://arxiv.org/pdf/2605.23904 (May 2026): +24.8 Codex, +19.1 Claude Code; cross-harness transfer +59.7.
* Darwin Gödel Machine — https://openreview.net/forum?id=pUpzQZTvGY (ICLR 2026): 20.0→50.0 SWE-bench, 14.2→30.7 Polyglot; ~2 weeks compute.
* Huxley-Gödel Machine — https://proceedings.iclr.cc/paper_files/paper/2026/file/821d20219c2f14850af1b5220f0ed13f-Paper-Conference.pdf (ICLR 2026): metaproductivity, fewer CPU-hours, human-level agent design on SWE-bench Lite.
* The Last AI Built by Humans — https://arxiv.org/html/2609.11873v3 (Sep 2026): RSI taxonomy, evaluator exploitation, frozen-evaluator epochs.
* Self-Improving Agents collection — https://academy.dair.ai/papers/collections/self-improving-agents (Oct 2026): SICA 17→53, Group-Evolving Agents, AIDE2 8-day run, reward hacking 55→32.

Field figures are context for the plan, not evidence for this repo's claims. The repo numbers are produced by
the two tools named above and by `transfer_learning_new_instance_probe_20261103.py`, all re-run on this tree.
