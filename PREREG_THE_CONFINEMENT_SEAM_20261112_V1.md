# Pre-registration: the confinement seam — where it plugs in, what it must prove, and the one decision only the owner can make

**2026-11-12, third asking.** Branch `arena/808035d4-brain`. Authority: **NONE**.
`truth.achieved` stays `false`. $0 incremental spend. Zero model dependency.

The owner has asked three times: *why can't we just give Brain the most advanced coding
actions and experience them once?* Two answers are already merged on `main`:
`WHAT_2026_SAYS_ABOUT_THIS_20261112_V1.md` (#6734 — full scorecard vs the 2026 frontier) and
`WHY_NOT_JUST_GIVE_IT_THE_TRY_20261112_V1.md` (#6744 — the chain, link by link, with the
front door/replay prices). They both name the same next step: **wire the seam** — let the
door consult `canonical/runtime/confinement_v1.py` at the boundary's refusal sites so the
most advanced coding capabilities can actually run under the admitted confinement instead of
refusing forever. This document is that step's pre-registration. It exists because the step
is small to say and dangerous to improvise, and because one blocking decision in it belongs
to the owner, not to an agent.

---

## 0. What is already true on this tree (re-verified 2026-11-12)

| claim | state |
|---|---|
| Store census (re-run today) | 1 episode / 3 macros / 7 lessons (3 procedures) / 0 resolutions — unchanged |
| Claims ledger (re-run today) | **8/8** tree predicates hold; 6/6 external linked |
| Confinement substrate (`confinement_v1.py`, merged #6733) | exists, measures 9/9, **wired nowhere**; every door refusal stands exactly as before |
| The dominant advanced-coding wall | **19 of 38** realistic material-aware goals refuse with `FAIL_CLOSED__COMPUTER_EXECUTION_REQUIRES_ADMITTED_CONFINEMENT` |
| Why not just "replay the lessons" as the permanence metric | checked today: the 7 taught-action lessons are **synthetic in-memory fixtures** pointing at paths like `lessons_q7/ledger_q7.py` that do not exist in this repo; the episode store holds one fingerprinted environment. **No lesson was ever learned from this repository's own history**, so "permanence as a decay rate" is not measurable here yet — measuring it requires the loop to run on real work first |

---

## 1. The refusal-site inventory (what "wiring the seam" actually touches)

Decision points that return the confined-refusal status (changeable in one place):

| site | role | touch? |
|---|---|---|
| `canonical/runtime/live_brain_route_admission_v1.py:1486–1489` (`run_adapter_locally`, raise `LocalExecutionFailure(boundary.STATUS)` before adapter import) | the single admission check every local adapter call passes through | **site of the seam** |
| `live_brain_route_admission_v1.py:1627–1629` (`_execute_locally`, maps the raise to `_fail(boundary.STATUS)`) | reporting; converts the typed refusal into the door result | keep — but attach the confinement receipt when one exists (reporting only) |

Reporting/consistency sites (do NOT touch; crashes here are outside the seam's scope):
`composer_route_v1.py:329`, `composer_route_v1.py:4092`, `brokered_workspace_execution_v1.py:562,1531`,
`creature_runtime_v1.py:1489–1526`, `curriculum_v1.py` (comparisons), `bound_capabilities/software_analysis_diagnose_and_architect_v1.py:27–31`,
`goal_front_compiler_v1.py:3552` (comment), `live_brain_route_admission_v1.py:1985,2030,2077,2181` (re-entries of the same typed refusal).

One site. Additive. Everything else stays byte-identical.

---

## 2. The design constraint nobody may skip: effect ADOPTION

`confinement_v1.run_confined(ROOT, argv, declared_effects=[...])` clones the repository into
a temporary directory, runs `argv` there with `shell=False`, restricted `PATH`/`HOME`, a hard
budget, and verifies that each declared effect **exists inside the disposable clone** with a
sha256. Then it deletes the clone.

That is the seam's fundamental asymmetry and it has exactly two honest resolutions, and
one dishonest one:

**Design A — adopt verified effects into the host (the only semantically complete one).**
Before the confined run: capture `transition_verifier_v1` preimages for each declared-effect
destination path. Run confined. Verify the receipt (effects exist inside the clone,
`host_untouched: True`, budget respected). Then copy **only the declared effects** from the
worktree into `ROOT`, after `write_authority_v1.check(ROOT, args, cid)` passes on every
destination, keeping the preimages so any adopted-then-detected-bad file is rolled back
exactly as the in-place adapters are rolled back today. What confined code can write is
then, by construction, what the goal declared — no more than what an admitted in-place
adapter may write today, and with stronger containment (clone, restricted env, budget,
receipt).

**Design B — verify, don't adopt (stepping stone at best).** The door returns a result whose
`declared_effects` are marked `verified_in_clone: true` but whose bytes are deleted with
the worktree. This makes `python3 --version` "execute" and produce nothing readable; a
capability whose job is to *write the output report* would report success and leave no
report. Green-looking, empty-handed — theater. Use only as an internal shadow measurement
(§4 PR6), never as the admitted path.

**The dishonest option — lift arbitrary bytes.** Copy everything the clone produced, or adopt
without `write_authority`/preimages. That re-admits the exact class the boundary and
`write_authority_v1` exist to stop: arbitrary code writing arbitrary bytes into the host
repo. **Forbidden**, whatever the probe says afterwards.

### 2.1 The one decision only the owner can make

Design A means: bytes produced by door-admitted arbitrary code may land in this repository,
bounded to declared destination paths, through `write_authority` and preimage rollback.

- **If the owner says yes:** the seam wires exactly as in §1+Design A. The 19/38 bucket
  becomes measurable work, split per capability (shell.command.run first — the archetype).
- **If the owner says no:** no file-producing capability may ever run through the seam.
  Report-class capabilities (emit a verdict, not repo bytes; e.g., diagnose operations that
  return their answer inline) may still pass, which leaves roughly zero of the 19 solvable,
  and the wall stays by design. That is a legitimate endpoint — but it must be chosen, not
  stumbled into.

*An agent must not make this call, because the boundary explicitly says: no request flag,
process environment or caller instruction can grant execution authority. Adoption policy IS
execution authority. This is the owner's vote, not mine.*

---

## 3. Pre-registered predictions (written before any build; falsifiable)

Environment: this repository at the base commit; `python3 canonical/tools/realistic_goal_reach_probe_v1.py`
in a fresh clone; `canonical/runtime/confinement_v1.py` unmodified at build time.

- **PR1 (refusal preserved by default).** With no confined-execution request and no
  declared effects in the action args, `run_adapter_locally` refuses **exactly as today**
  (`LocalExecutionFailure(boundary.STATUS)`), and every existing refusal site's output is
  byte-identical. Any other outcome voids the build.
- **PR2 (mkdir/host hygiene).** After any confined run admitted by the seam, the host
  repository's `git status --porcelain` is byte-identical to before, and the clone is
  removed (`confinement_v1.release` in `finally`). Verified by the receipts, not by belief.
- **PR3 (effect honesty).** A goal whose adapter would write outside its declared effects
  produces a refusal at admission (`EFFECT_ESCAPES_CONFINEMENT`) or a receipt with the
  undeclared path marked absent — never a silent write. Measured on at least two fixture
  capabilities.
- **PR4 (rollback works).** Adoption that detects a bad adopted file (hash mismatch vs
  receipt, or Python-source replacement detected by
  `restore_if_a_source_was_replaced`) restores preimages byte-identically. Measured on an
  injected defect, not asserted.
- **PR5 (probe movement, honest quantifiers).** On the realistic probe after wiring:
  `shell.command.run` moves from `NOT_COMPILED: FAIL_CLOSED__COMPUTER_EXECUTION_...` to
  EXECUTED-with-receipt (verified output `version.txt` written by adoption). At least **2
  of the 19** confinement-refusal capabilities move to EXECUTED or COMPILED_TO_SELF_BUT_FAILED
  with a **confinement receipt attached** — and the document states the count as measured,
  not as achieved capability. Repair-loop rows are expected to remain refused or fail inside
  the clone (their tests are the work) — a non-result there is honest, not a regression.
- **PR6 (Design B shadow, optional).** With adoption disabled (shadow), the same probe rows
  show the same executions but **no host bytes land** — the control that proves adoption, not
  the receipt, is what carries effects to the host. Kill this arm if it becomes a back door.
- **PR7 (no progress credit by default).** The landing PR claims **no** capability/ownership
  credit unless a fresh-instance verifier that did not write the code reproduces PR5. Pre-said,
  because "19/38 → executed" reads like a win and isn't one.

**Kill rule:** if any of PR1–PR4 fail, revert the seam; the refusal that remains is the
honest state. If PR2 fails, the build is unsafe and stops regardless of probe movement.

---

## 4. The tests that must land with it

`canonical/tests/test_confinement_seam_v1.py` (new):

1. default refusal unchanged (no marker, no effects) — against two known-refuse capabilities;
2. confined happy path: `shell.command.run`-class fixture executes, receipt attached, host
   status byte-identical, clone gone, declared effect adopted;
3. declared effect outside the worktree refused (`EFFECT_ESCAPES_CONFINEMENT`);
4. adoption under a forced hash mismatch → preimages restored byte-identically;
5. adoption over an existing Python source replaced by non-Python → refused and rolled back;
6. budget exceeded → `BUDGET_EXCEEDED` recorded, adoption refused, host untouched;
7. no `shell=True` anywhere in the seam path (structural pin, mirroring the substrate's own);
8. ledger: `whole_task_correctness_proved` is still read zero times by the seam.

Existing suites that must stay as they are: `test_admitted_confinement_v1.py` (9/9),
`test_raw_goal_*`, `test_live_brain_route_admission_v1*`. If the seam changes their outputs,
the seam is wrong — stop, do not edit the baselines.

---

## 5. The action intent this will carry (constraints; the fields come from the base schema)

The landing PR is a sensitive path, so it carries exactly one action intent built from the
real base-commit schema (`PROJECT_BRAIN_ACTION_INTENT_WITH_RECURSIVE_OBS_V11`), not one
inferred here. The constraints on that intent are fixed now:

- `agent_orientation.producer_cognition_model_dependency_count` is **0** and
  `incremental_spend_usd` is **0** — the seam introduces no model call and no spend.
- progress class may be credited **only if** PR5 (probe movement) and PR7 (fresh-instance
  verifier reproduction) both complete; otherwise the intent lands as a governance guard
  with no capability or progress credit. The receipts block must quote the real probe
  output and fail closed if it does not.
- `scope_complete_discharge` stays `false`; `truth.achieved` stays `false`.

`canonical/runtime/live_brain_route_admission_v1.py` is a sensitive path: it must pass the
drift guard and the load-bearing primary gate at the base commit. The PR body includes the
before/after probe outputs verbatim — failing closed if the two differ in any bit other
than the status lines enumerated in §1.

---

## 6. Why this turn ships the design, not the build

Three blockers, all named, none worked around:

1. **Effect adoption is execution authority** → owner's decision (§2.1). Building Design A
   without it enforces a policy nobody chose — exactly what "no request flag may grant
   authority" forbids.
2. **Which capabilities declare effects first** — `shell.command.run` is obvious; the
   repair-loop rows are not (their "declared effect" is a patched tree; honest admission may
   be permanently out of scope for PR-shape goals). A wrong guess here registers a half-built
   contract as an interface.
3. **Probe movement is a forecast, not a result.** PR5 is written to be falsified. Landing
   half a wiring on a guessed forecast is the pattern this repository's laws exist to stop.

What this document does land, push and merge: the inventory, the constraint, the owner
decision, the falsifiable predictions — so the build, when authorized, is an afternoon, not
an excavation.

---

## 6.5 The web state this design answers to (verified 2026-11-12)

- OSWorld 2.1 (108 long-horizon tasks): ~20.6% binary at release; the 2.0 leaderboard now
  shows Claude Opus 5 at 44.3% ([Snorkel, 2026-11-10](https://snorkel.ai/osworld-2-1-long-horizon-computer-use-evaluation/));
  leaderboard aggregators list Claude Opus 5.5 at 48.7% — treat aggregator rows as
  self-reported, not audited. No agent clears ~50% on long-horizon computer use.
- SWE-bench Pro: numbers are harness-dependent to the point of non-comparability — one
  November snapshot lists Claude Opus 5.5 at 89.9% ([BenchLM, 2026-11-07](https://benchlm.ai/benchmarks/swe-bench-pro)),
  while unified-scaffold evaluations still report frontier models below 25% ([Hugging Face daily papers, 2026-10-27](https://huggingface.co/papers?q=SWE-bench+Pro))
  and strong open agents at 45.8% (Live-SWE-agent) / 54.3% (Confucius Code Agent).
  Any single "the number" is wrong; the spread itself is the measurement.
- ASCENT (Oct 2026): one-pass deployment, verified trajectory → hindsight self-distillation
  → persistent LoRA; gains grow later in the stream and transfer held-out
  ([arXiv:2610.05303](https://arxiv.org/abs/2610.05303)). Mechanically confirms the design
  constraint in §2: experience only becomes capability through a *persistent* channel, and
  ASCENT needs a terminal verifier — exactly what this tree's refusals/receipts provide.
- NorthCUA (Nov 2026): experience flywheel → verified-trajectory curation → mid-training +
  long-horizon SFT → joint desktop-web RL; open-source SOTA under reported settings
  ([arXiv:2611.02102](https://arxiv.org/abs/2611.02102)). Confirms "experience at scale"
  is a training pipeline, not a memory lookup.
- Continual AutoResearch (Nov 2026): persistent state improved research *efficiency* for all
  five frontier agents, but gains did **not** consistently translate to better final
  solutions; retaining vs. utilizing experience are distinct capabilities
  ([arXiv:2611.05108](https://arxiv.org/abs/2611.05108)). The direct refutation of
  "experience once → permanent capability" as a general claim.
- KEEL (Oct 2026): verifier-evidenced skill/lesson evolution, +4.2–21.7pp over no-knowledge
  baseline on SkillFlow ([arXiv:2610.34043](https://arxiv.org/abs/2610.34043)); ACuRL:
  zero-human continual adaptation for CUAs, 3–29% absolute gains
  ([arXiv:2602.10356](https://pith.science/paper/2602.10356)); SEAgent (ICML 2026): 0% →
  20.6% on GrassGIS, generalist 40% OSWorld > specialist ensemble 36.4%.

**Read across all of it:** nobody, anywhere, has "instant learning in arbitrary environments,
perfectly, permanently." The closest things require (a) real verified trajectories, (b) a
persistent channel (weights, or verifier-evolved skill stores with retirement), and (c)
streams of related tasks so reuse pays back. This design inherits (a) and can build (c);
(b) beyond the lesson/macro stores requires either an owner-freed compute budget (ASCENT)
or continued admission of verified skill claims — both are owner calls, not agent calls.

---

## 7. Standing non-claims

Nothing here moves 8/149, the 19/38 bucket, the ledger, or any capability. No seam exists
in code by this PR. No gate is opened or widened. `truth.achieved` remains `false`.
$0. Zero model dependency in every result-bearing path. Authority: NONE.
