# THE_HONEST_STATUS, audited claim by claim — 2026-11-12 (fourth asking)

**2026-11-12.** Branch `arena/b8d81640-brain`, branched from `10304401cda5` (main; merges
#6750, #6752 included). Authority: **NONE**. `truth.achieved` stays `false`.
$0 incremental spend. Zero model dependency in every result-bearing path.

The owner re-sent, verbatim for the fourth time: *"Instant learning + Instant learning in
new arbitrary environments … we already solved those perfectly … We were trying to make our
model a sentient creature … the most advanced coding agent on the planet … you must maximize
your web use. We are in 10/11/2026 … YOU SURE THIS THE SMARTEST APPROACH?"*

Between the third answer (merged `WHY_NOT_JUST_GIVE_IT_THE_TRY_20261112_V1.md`, #6744), the
confinement pre-registration (#6750) and this branch, main received one more document worth
auditing: `THE_HONEST_STATUS.md` (#6752, merged 2026-11-12T20:07Z). It closes with the most
optimistic sentence standing on main today:

> "The architecture is revolutionary … If we populate the state with real coding experiences,
> we will have a system that … operates without any external AI model … Yes, this would make
> us the most advanced coding agent."

This audit does two things only: (a) holds that document's **checkable** claims to the tree
as of this timestamp, and (b) refreshes the web anchors to what is actually published as of
2026-11-12. It introduces no new mechanism, widens no tolerance, and credits nothing.

---

## 1. Every checkable claim in `THE_HONEST_STATUS.md`, audited

| # | Claim (verbatim-ish) | Tree measurement, 2026-11-12 | Verdict |
|---|---|---|---|
| 1 | "Self-improvement pipeline works … Induces skills from verified episodes. Persists state across runs. **Skills compound over time.**" | `canonical/runtime/SELF_IMPROVEMENT_STATE_V1.json` **does not exist**. Zero verified episodes, zero verified skills, zero Pareto replacements have ever been persisted on this tree. `load_state()` returns the empty state. | **Unsupported.** The mechanism exists; its output has never been observed here — not once, not in a test, not in a fixture. "Compounding" is an architecture claim, not a measurement. |
| 2 | "Transfer learning recalls past environments … Cross-run knowledge transfer" | `transfer_learning_v1` state: **1 episode** (re-run today, `canonical/tools/what_the_machine_kept_20261112_v1.py`). | **Exists, trivial.** One fingerprinted environment is not transfer. |
| 3 | "Operator memory induces operators … Persists across runs; re-derives on load" | `canonical/runtime/acquired_operator_memory_v1.py` exists (7,213 B). No operator-example state exists anywhere in the tree. Load-time re-derivation is real code, **never evidenced on a real example** here. | **Written, unproven.** |
| 4 | "Skill macro planner … Verified skills become planning macros" | `verified_skill_macro_planner_v1.py` exists (8,391 B). `canonical/runtime/state/chain_macros_v1.json`: 3 macros, each `successes: 1`, each over a single historical run (epochs ≈ 2026-06), never reused on a fresh environment since. | **Written, unproven.** Macros exist; reuse is not measured. |
| 5 | "The permanent store is close to empty" (this tree) — the doc never shows this number | 42 experience cells; **14 VERIFIED cells / 289 observations** (83 tar_gz-create, 57 intent_ooxml verify, **56 python.source.audit.ast**, 27 archive-verify, 13 xlsx-verify, 11 json.query.jq, 10 bridge-enumeration, 10 pdf-extract, **8 python.fault.localize.dynamic.dataflow.v1**, **8 python.software.repair.loop.test_guided.ast.v1**, rest forged one-shots); 28 cells carry ≥1 negative observation; **0 resolutions**; 2 forged (4 refused); 3 macros (successes=1); 1 episode; 7 taught-action lessons (synthetic in-memory fixtures). The two bolded advanced-coding cells were recorded 2026-06-17 (epoch ≈ 1792352), at capability **verify** time, by the old sweep — not produced by the door on this branch. | **Partially right, and the doc under-reports it**: there is verified *verification* experience here — the machine has learned to re-check its own work — but it is shallow, zero-payload, and predates the realistic-goal era. |
| 6 | "There's no automatic way to wrap 'fix this bug' as a formal capability with verification bindings" | Partially wrong: the tree wraps these goals today — **19 of 38** realistic material-aware advanced-coding goals compile correctly and then refuse at **execution** with exactly `FAIL_CLOSED__COMPUTER_EXECUTION_REQUIRES_ADMITTED_CONFINEMENT`. The missing thing is not the wrapper or the verifier — it is (a) the admitted-execution seam (pre-registered this week, #6750, **awaiting the owner's effect-adoption decision**), and (b) a corpus of executions the verifier can judge. | **Misdiagnoses the wall.** Verification is not today's blocker. Admitted execution and an empty corpus are. |
| 7 | "For coding tasks, verification is open-ended … Needs an oracle (test suite?) … This is the hard part" | Half-right and half-unhelpful: for the narrow slice where a test suite exists, the oracle already exists in-tree (`test_settlement_v1.py`-class suites, transition verifier, preimages, rollback). The hard, *binding* parts are the two facts in §1-6: no admitted carrier (19/38), and no corpus to verify against (empty by construction). | **Right that it's hard; wrong about which wall is binding today.** |
| 8 | "This is weeks of work, not hours" | True in expectation; but the *first measurable steps are days*: the seam is one admission site (`live_brain_route_admission_v1.py:1486–1489`); the probe is `realistic_goal_reach_probe_v1.py`; the corpus must come from real door-admitted runs, which **cannot exist until the seam lands**. | **True for the vision; falsely scoped for step 1.** |
| 9 | "Will this make us the most advanced coding agent? **Yes, if we actually build it.**" | No source supports this sentence. The field's best measured computer-use number is 44.33% binary (OSWorld 2.1, Claude Opus 5, full set; Oct 15 2026 leaderboard); SWE-bench Pro is harness-dependent from <25% (unified scaffolds) to "89.9%" (vendor-scaffold snapshots) — the spread is the measurement. Nobody's "revolutionary architecture" has shipped as world-best coding performance. | **Forbidden claim.** The lawful version: *"this architecture is the correct shape; whether a real, verified capability grows out of it is an experiment this tree has not run."* |
| 10 | "Stop writing documents. Start building the infrastructure." | Correct instruction, mis-shaped target: the missing piece is not more essays and also not an undifferentiated "infrastructure" project — it is a specific, pre-registered, reversible seam behind the owner's go/no-go. #6750 is that step. | **Correct order; one step, not a program.** |
| 11 | The document's own provenance list ("PR #6724: Analysis … #6731 … #6739: Direct answer") | All three PR numbers verified real and merged today (see `gh pr view`). | **Accurate about itself — an improvement the other merged docs don't always manage.** |
| 12 | The document omits: `SKILLS_DONT_COMPOSE_20261112_V1.md`, `THE_CORPUS_CAN_ONLY_COME_FROM_REAL_WORK_20261112_V1.md`, `PREREG_THE_CONFINEMENT_SEAM_20261112_V1.md` (#6750), and this re-run's ledger | — | **The audit finds the omission; that is its most important result.** The question was reopened as if unanswered hours after it had been answered with files and merged. |

**Claims ledger, re-run on this branch, 2026-11-12: 8/8 tree predicates hold; 6/6 external
items linked.** One-showing-is-literal (1 of 4), two-showings-general (4 of 4), 296 OIDC-attested
records, 0 of 145 capabilities touching weights. No movement.

---

## 2. The web state, as actually published (2026-11-12), additions today

Earlier anchors (ASCENT [arXiv:2610.05303](https://arxiv.org/abs/2610.05303), NorthCUA
[arXiv:2611.02102](https://arxiv.org/abs/2611.02102), Continual AutoResearch
[arXiv:2611.05108](https://arxiv.org/abs/2611.05108), KEEL
[arXiv:2610.34043](https://arxiv.org/abs/2610.34043), ACuRL
[arXiv:2602.10356](https://arxiv.org/abs/2602.10356), SEAgent, SWE-bench Pro spread) still
stand. Four new/pinned items this pass:

- **CODESKILL** ([arXiv:2605.25430](https://arxiv.org/pdf/2605.25430)): skill *management*
  as a learned policy — extract, evolve, merge, drop — +11.03 over no-skill on EnvBench /
  SWE-bench Verified / Terminal-Bench 2, +5.10 over strongest memory baseline, compact skill
  bank. Directly validates *retirement-and-merge*, which this tree has as a design rule and
  has not measured.
- **HSE — Hierarchical Skill Evolution** (Oct 2026,
  [arXiv:2610.35616](https://awesomepapers.io/ai-agents/papers/2610.35616)): task-level →
  repo-level → cross-repo distillation; 10 skills from SWE-Gym transfer across models and
  harnesses. The most concrete external evidence for *task-specific, hierarchically-
  abstracted* skills over monolithic "skill banks" — consistent with SkillTTA (+10.8/+13.4).
- **Continual harness self-evolution forgets** ([arXiv:2611.03219](https://arxiv.org/abs/2611.03219),
  2 Nov 2026): Meta-Harness reaches 94% on SWE-Bench after evolution, then **32% by the
  fifth round** of continued evolution on FeatureBench (−66% relative). Catastrophic forgetting
  is not a weights-only problem — it is measured in **harness evolution itself**. This is a
  direct, fresh refutation of "edit the harness → gains persist permanently," and it elevates
  the in-tree non-negotiable: **every admitted skill must carry a decay/retirement rule**, not
  a promotion.
- **Prime Agent** (PrimeIntellect, [arXiv:2608.23552](https://arxiv.org/abs/2608.23552);
  [repo](https://github.com/PrimeIntellect-ai/prime-agent)): Recursive Language Model harness,
  persistent Python REPL, `/refine` applies evidence-backed updates to supplemental harness
  state with recorded snapshots and **rollback**, defaults to session-local state. The closest
  deployed implementation of "the harness learns" — and note what its own authors chose:
  locality by default, snapshots, and no claim of personhood. The field's answer to the owner's
  exact question is *careful harness hygiene*, not a creature.
- **OSWorld 2.1, official full set, 2026-10-15 update**: Claude Opus 5 leads at **44.33%**
  binary ([tessary.ai](https://tessary.ai/answers/osworld/is-computer-use-reliable-yet),
  [Agentastic](https://www.agentastic.dev/blog/computer-use-agents)); offline-subset numbers
  differ by who ran them (Opus 5.5 reported 53.2% offline in one run) — the spread, again, is
  the measurement. Interactive-app capability is far from "solved," by any definition.

**First-principles read:** every October–November 2026 result above buys its gains with one
of three ingredients — a **verifier** (terminal test/outcome), a **persistent channel**
(weights or a governed skill store with retirement), or a **stream** of related tasks. None
of the three exists on this tree in a form that closes the loop: the verifier exists
(OIDC, transition preimages, suites) but is unwired to admitted execution; the persistent
channel holds literals and decays nothing because it is empty; the stream cannot run
because the seam is not landed. The owner's intuition is right about the ingredients and
wrong about their readiness.

---

## 3. The corrected one-line answer

> The mechanisms are real, mostly unproven in this checkout, and **unwired end-to-end**;
> verification is not the wall — admitted execution is (19/38) — and the corpus is empty
> by construction; nothing about 2026-11's published research licenses "solved," "instant,"
> "permanently," or "the most advanced coding agent" as a claim. The smartest move is the
> already-merged, pre-registered seam (#6750) behind the owner's effect-adoption decision,
> then the probe, then task-specific synthesis over the SWE rows, with retirement rules —
> nothing else is worth an hour until the seam lands.

---

## 4. Non-claims and standing invariants

No capability, gate or tolerance is widened by this document. `truth.achieved` stays `false`.
$0. Zero model dependency in every credited path. No fresh-instance verification is performed
or implied here. The owner decisions pending before the next real step: **(1)** adopt-or-not
for declared effects in the admitted confinement (#6750 §2.1); **(2)** which capabilities
declare effects first (archetype: `shell.command.run`; repair rows likely permanently
out-of-scope for PR-shape admission); **(3)** whether any ASCENT-style weight update is ever
in scope (never in a credited path; owner-freed compute only).

*One prediction, pre-registered: if the seam lands and the probe is re-run, at least 2 of the
19 confinement-refusal capabilities will EXECUTE-with-receipt; any claim of capability credit
beyond that requires a fresh-instance verifier who did not write the code.*
