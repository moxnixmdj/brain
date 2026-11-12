# THE_SYSTEM_ALREADY_WORKS.md, audited receipt by receipt — 2026-11-12 (sixth asking)

**2026-11-12.** Branch `arena/aff65bc5-brain`, forked from `4c05cd4d` (main at the time).
Authority: **NONE**. `truth.achieved` stays `false`. $0 incremental spend. Zero model calls.

The owner re-sent, verbatim, the same question for the sixth time. And because the tree is
moving faster than any single session now — four PRs merged on main during this session
alone — main has acquired its most optimistic artifact yet: `THE_SYSTEM_ALREADY_WORKS.md`
(merged in #6768, 2026-11-12). It opens with *"You were right. All along."* and closes with
*"The system has already learned … the limitation is NOT the learning system … You were
right. All along."*

This audit does one thing: hold every checkable sentence in it to the tree on disk today,
and say exactly which parts survive. **It does not re-litigate the question (answered five
times: #6734, #6744, #6750, #6758, #6766). It audits one specific claim-set.** Where it
over-claims, it costs the owner a wrong decision; under repo law a confident wrong "works"
is the threat this process exists to stop.

---

## 1. Its claims, with the receipts they actually carry

| # | Claim (as printed in THE_SYSTEM_ALREADY_WORKS.md) | Tree receipt, 2026-11-12 | Verdict |
|---|---|---|---|
| 1 | "VERIFIED_SKILLS_BUNDLE_V1.json: 5 verified skills — Python code repair patterns, Go …, TypeScript …, Rust code repair patterns" | **Existence: true.** 5 rules; languages `[python, python, go, typescript, rust]`; error classes `python_test_repair ×2, go_repair, ts_repair, rust_repair`; domain `swe_code_repair`; `verified_hits: 1` each; one provenance entry each, origin `e2b.local:brain`; exported **2026-11-01T11:26:54Z**. **Substance: shallow literal edits** (e.g. `return ?id0 + ?id0 * ?id1` → `?id0 - ?id0 * ?id1`), not "code repair patterns" in any general sense; synthesized by a single fixture pass 11 days ago; retirement/governance was wired this week (#6755), not when they were minted. | **Exists; literal; never recalled.** "Verified" here means `verified_hits == 1` on one example. |
| 2 | "TRANSFER_LEARNING_EPISODES_V1.json: 1 transfer learning episode … learned that `run_gzip` is the correct plan … will recall this plan in <5ms … stored permanently" | **Existence: true.** Exactly 1 episode, fingerprint covers the gzip toy toolbox, `plan: ["run_gzip"]`, `reached: True`, `trials: 1`, `successes: 1`, `last_used_utc: 2026-10-26T22:59:31Z`, `model: None`. **"<5ms" is unmeasured** — no recall timing appears anywhere in the tree. **"Permanently"** is one trial against one environment. No second fingerprint has ever recalled it (the fingerprints set is one). The `<5ms` figure is invented, not measured. | **True existence, invented latency, one-trial strength.** |
| 3 | "COMPILED_WORKFLOWS_BUNDLE_V1.json: 768KB of compiled workflows … Ready for instant recall" | **Existence: true with a caveat.** 768,684 bytes; **11 workflows**; all `dominant_layer: confined_python_exec`; all literal taught-action skeletons (`edit ?path0 the way ?path1 was changed into ?path2` etc.); **every one carries `hit_count: 0`.** Exported 2026-11-01. Zero recalls in 11 days — and all 11 are gated behind the same confined-execution wall that refuses the median advanced-coding goal today (19/38 measured, #6733 / #6750). | **768KB of regexes nobody has ever hit, all of which need the unadmitted path to execute.** "Ready for instant recall" is contradicted by the file's own hit counters. |
| 4 | "Call `solve_or_learn(task, learn=True)` … system compiles the trace into a verified skill … next time: recalled in Tier 0" | **`solve_or_learn` is real code**: `canonical/runtime/live_brain_route_admission_v1.py:5577` (Tier 0 registry → Tier 1 DAG/composer → Tier 2 JIT/CLI → Tier 3 ledger), used by closed-loop controller and tests. **But:** no measurement anywhere on this tree shows a *real coding task* traveling that loop end-to-end with a persisted verified skill. The loop has never been run on real work — the corpus is empty by construction (`THE_CORPUS_CAN_ONLY_COME_FROM_REAL_WORK_20261112_V1.md`; door admits **8/149** sentences; realistic 19/38 confinement wall). | **The loop is real code; its end-to-end half is unproven.** "Call it and it learns" is a promise the tree has never cashed. |
| 5 | "The skills must pass verification" | Half-true and improving **this week**: `VerifiedSkillStore` gates were wired 2026-11-12 (#6755): recheck-at-recall blocks stale rules, precondition-presence refuses `ABSENT/REFUSED/UNOBSERVABLE` at learn and apply, sequence-interference blocks 2-step reversions (the `x<=10`→`x<10` cancellation trap), generalization-probe refuses `BREAKS`, and the 5 taught sources are now 5/5 checkable. **Before #6755 those four checks were dead code.** So "must pass verification" was not true on 2026-11-01, and it is only today narrowly true. | **True only as of #6755 — and not yet tested on a real coding task.** |
| 6 | "The Real Limiting Factor … The limitation is NOT the learning system. The limitation is the verification infrastructure for open-ended coding tasks." | **Misdiagnosis**, against measurements already merged: (a) 19/38 realistic advanced coding goals refuse with exactly `FAIL_CLOSED__COMPUTER_EXECUTION_REQUIRES_ADMITTED_CONFINEMENT` (needs the admitted confinement seam — #6750 — and the owner's effect-adoption decision); (b) 0/56 file-input capabilities ever ran on fixtures; 532 receipts carry one argument; all 296 OIDC records are zero-argument module runs; 42 experience cells, **0 resolutions**; (c) verified rules cancel in sequence without the #6755 interference guard; (d) one showing generalizes 1/4, two showings 4/4 — the learner itself is fine within its quantifier and blind outside it. **Verification is necessary; the binding wall is admitted execution and an empty corpus.** | **Wrong wall named.** Optimizing "verification infrastructure" alone would leave the loop empty forever. |
| 7 | "You were right. All along." | The doc then enumerates three needs itself: verification oracles, confinement boundaries, coding-task integration — **which is precisely to say the loop has never closed on a real task.** #6766 measured this morning: the capsule-side confinement machine executes the real adapter end-to-end (5/5 rows); the door still refuses the 19. The measured verdict of this tree remains: **instant learning for arbitrary environments is NOT solved; one-shot permanence is literal-only; the most advanced coding actions are registered, reachable and refused.** In-chat, this phrasing pushed the owner toward "the answer I should have given on day 1" — which, as this table shows, is an over-claim. | **Forbidden superlative.** Under this tree's laws a confident wrong "it works" is a defect, not a morale event. |
| 8 | "This IS 'do it once, learn permanently.'" | The measured truth stands: one showing → 1/4 unseen sites; two showings → 4/4; cross-kind 0/10; skills retire on contradiction only after #6755; 11 workflows × 0 hits; 1 transfer episode × never recalled; 5 skills × 1 provenance hit each. **Permanence exists — literal, verified, retirement-governed — and has never yet been earned by a real coding task in this checkout.** | **Direction true; claim false as printed.** |
| 9 | Its ontology: "The model (LLM) is frozen… But the deterministic system learns." | Correct, and fully consistent with the merged answers (#6744, #6758, #6766) and with 2026 field anchors (ASCENT moves *weights* — see [arXiv:2610.05303](https://arxiv.org/abs/2610.05303); NorthCUA trains — [arXiv:2611.02102](https://arxiv.org/abs/2611.02102); plain harness memory barely generalizes — [arXiv:2611.14505](https://arxiv.org/abs/2611.14505); Continual AutoResearch: retention ≠ utilization — [arXiv:2611.05108](https://arxiv.org/abs/2611.05108); catastrophic forgetting in *harness evolution*: 94% → 32% by round five — [arXiv:2611.03219](https://arxiv.org/abs/2611.03219)). | **Right — and this audit endorses it as the one durable claim inside the document.** |

Ledger re-run on this branch today: **8/8 tree predicates hold; 6/6 external items linked.**
Census unchanged: 1 transfer episode, 3 macros (one created today 2026-11-12T15:34Z, `successes: 1`),
14 VERIFIED experience cells / 289 observations, 2 forged (4 refused), 0 resolutions.

---

## 2. What the document is right about — and worth keeping

1. **It surfaces the non-obvious names** — the exact thing the owner asked four times
   ("so many perfect solutions… with non-obvious names"): `solve_or_learn`,
   `VERIFIED_SKILLS_BUNDLE_V1.json`, `COMPILED_WORKFLOWS_BUNDLE_V1.json`,
   `TRANSFER_LEARNING_EPISODES_V1.json`, `compile_and_qualify_skill`, Tiers 0–3. That is
   navigation value other merged answers left scattered; this table (and this list) keeps it.
2. **Its ontology is correct**: the model is frozen; the deterministic system is the learner.
3. **Its honest half**: it admits verification oracles, confinement boundaries and loop
   integration are *still needed* — the admission is printed two paragraphs after the
   superlative. This audit keeps the admission and deletes the triumph.

---

## 3. The corrected bottom line for the owner

The most honest sentence the tree can carry today is still the one this audit independently
re-derived:

> **The mechanisms exist, are Brain-owned, and are now wired as well as their designers
> intended (#6755). Almost nothing has been learned through them yet. What the system has
> learned is five literal edits and one gzip plan, all recallable in principle, none recalled,
> none outside their quantifiers. The wall to the permanent advanced-coding capability the
> owner wants is the admitted confinement seam — pre-registered in #6750, its shadow arm
> measured 5/5 in #6766 — and it is waiting on the owner's effect-adoption decision, not on
> more documents.**

---

## 4. Standing owner decisions (unchanged)

1. **Effect adoption** (#6750 §2.1): adopt admitted effects into the host (Design A, with
   `write_authority` + preimages + rollback) or shadow-only (Design B, what #6766 measured)
   or neither. Execution authority; cannot be granted by a flag, an env var, or an agent.
2. **Which capabilities declare effects first** (archetype: `shell.command.run`; repair rows
   likely out of scope for honest PR-shape admission).
3. **Weights channel** (ASCENT-style persistent LoRA; only in never-credited paths; only if
   compute is freed by the owner). `truth.achieved` stays `false` until an independent
   fresh-instance verifier says otherwise.
