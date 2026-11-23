# The Perfect Algorithm as the model — §3 verdict and ultimate plan — 2026-11-22

Authority: `NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT`. This is the owner's question, measured honestly against the Perfect Algorithm loop as it exists on main and as it was re-built on this branch: **goal-directed generalization or broad learning-of-everything; what exactly is saved and what is never saved; what to admit and what to persist.** It is not a benchmark score, a GUI/browser success, an OSWorld 2.1 result, an SWE-bench Pro result, a Terminal-Bench result, or §6 completion. It is the verdict on what the Perfect Algorithm already is and the one plan that makes it honest.

## 0. Requirements confirmed

Read the mission as new: make the Perfect Algorithm the model. Scan ANY arbitrary new environment, ask the right question, know everything that must be known through the instant-knowledge source (every component on the computer already has a guide), then act, verify, and save. The standing global laws bind: own model + agent, zero model calls at runtime, own weights + instant-knowledge store only, learning from a single experience in ANY environment, goal: solve computer use, honesty, integrity, no leakage, never stop at milestones, never ask questions, merge once when complete.

**§2 contradiction confirmation (resolved by default, not by omission):** the standing law "instant learning permanently" vs "zero knowledge-house" is resolved the way the Perfect Algorithm already encodes it:

- **Parameters** = computed mechanisms only (scan, right-question, plan, act-and-verify, learn, admit, save). No world facts, no action rows, no learned statistics in weights.
- **Knowledge** = an external, inspectable, editable, deletable store — `canonical/astra_runtime/state/PERFECT_ALGORITHM_MEMORY_V1.json` — that the system computes with. Learning writes to it from one experience, and one experience writes only a hypothesis: the generalization (goal family + plan sketch + evidence hash), never the raw trace.
- **Instant knowledge** = the external, completeness-gated source used when the plan fails after the scan (the jit_knowledge fetcher), never counted as capability.

The default is the design the repo already embodies; no alternative default was found. What remains unsolved about it is what §5 names.

## 1. Research findings

### Project (exhaustive, non-obvious names included)

- `canonical/swe_kernel/perfect_algorithm_v1.py` — the loop, re-read this round end to end. The durable unit is the **generalization** (`generalize()`): goal family + plan sketch + evidence hash + admission verdict history. The raw trace is archived inside the evidence payload and never served as knowledge. `admit()` requires fresh instances to reach the goal; `remember_priors()` saves observed transitions unconditionally; `verify_priors()` re-executes root rows on a fresh instance and discards everything that does not replay; the fresh-family receipt refused the rule honestly. `run()` does not persist the plan rule unless admission passes.
- `canonical/runtime/environment_learning_v1.py` — `learn_model()`, `shortest_plan()`, `state_key()`. The affordance learner is the shared substrate; `state_key` is type/structure-preserving, namespaced by STATE_KEY_SCHEMA so stored rows are not silently reinterpreted.
- `canonical/runtime/jit_knowledge_v1.py` — the instant-knowledge web source. `resolve()` refuses single-source conclusions; one source cannot conclude anything (`DEFAULT_MIN_SOURCES=2`, `DEFAULT_MIN_KINDS=2`). Registered kinds: code_host, package_registry, documentation, open_web. It fetches the **web**; it does **not** read the computer's own local guides (man pages, README, AGENTS.md, `--help`).
- `canonical/runtime/local_guide_v1.py` — the instant-knowledge LOCAL tier, built this round. Reads the computer's own guides (README, AGENTS.md, `.md` docs, offline, bounded at 500 files), completeness-gated: a document answers only if one paragraph shares ≥2 content tokens with the query (60% of the query's content tokens, minimum 2). Function words carry no conclusion — one keyword anywhere in a doc is a thin hit, not a guide. `lookup()` is asked by the Perfect Algorithm whenever the scan cannot plan; the web tier stays — and only runs when the caller passes `allow_instant_knowledge=True`.
- `canonical/verification/PERFECT_ALGORITHM_RECEIPT_20261122_FRESH_FAMILY_V1.json` — measured: instance A (no walls) saved priors, refused the rule; instance B (firewall) kept 3 root transitions, discarded 43, re-derived plan 6, reached the goal, refused the rule honestly. Priors are observed facts about instance A; they seed instance B only after re-execution. Not trusted blindly.
- `canonical/verification/PERFECT_ALGORITHM_RECEIPT_20261122_REPLAY_V1.json` — measured this round: on a repeated identical-shape goal, an admitted rule replays instantly via `INSTANT_RECALL` with **no scan run** — the admitted rule is served, not re-learned. Priors were still saved as observed facts.
- `canonical/tests/test_perfect_algorithm_v1.py` — 23 tests (21 pre-existing + 2 new `ReplayFromMemoryTests` added this round). The fresh-family tests verify that instance B refuses the rule honestly and that stale rows are discarded.
- Pre-existing benchmark failure not this work: `EXT_JQ_TABLE <- GOAL_COMPILATION_BEST_MATCH_UNBINDABLE | near-miss json.query.jq`. Not counted here.

### Web / frontier (inputs only, no capability credit)

- [1] Doc consumption is agent-specific: agents fetch and read in the moment, need specific information now, truncate, and skim — a different access pattern than training crawlers. Page size and content density matter more than layout.
- [2] Documentation for agents is working context, read at the moment of acting; a single page must carry purpose, preconditions, inputs, success shape, failure modes, and the neighbouring capability — otherwise the agent cannot act without a second fetch.
- [3] Documentation is "last known state," not ground truth — every write is stamped with a timestamp, and an agent must not treat a document marked current as verified; it must re-check current state before writing, especially time-sensitive or high-stakes.
- [4] Local, offline, standardized references exist for agents: man pages (offline, section-numbered, apropos-searchable, version-matched, packaged with the tool), AGENTS.md (structured local project context loaded before each prompt), and llms.txt / markdown twins as site-level indexes. Man pages already encode exactly the key the mission names: "everything on the computer already has a guide."

[1] https://dacharycarey.com/2026/02/26/llms-vs-agents-as-docs-consumers/
[2] https://agentexperience.tech/insights/make-documentation-legible/
[3] https://inetanel.com/articles/documentation-is-code-machine-first-knowledge-architecture
[4] https://wunsch.substack.com/p/when-the-man-comes-around

## 2. §3 verdict

### Q1 — Goal-directed generalization vs broad learning-of-everything

**Verdict: goal-directed, broadly explored, narrowly persisted.**

The scan is broad — it tries every action and learns the affordance map of the environment, nothing is assumed. That is the right shape: you do not know what is interesting until you have looked. But the stored knowledge is narrow — one plan rule per goal family, admitted only on instances it was never taught on, plus observed priors scoped by env kind, never a world model in weights. Broad learning-of-everything is **rejected**: a model that knows everything it observed is (a) unverifiable on anything it was not taught on, (b) not a generalization of one experience but a warehouse of one instance's trace, (c) useless the moment the environment changes shape, and (d) exactly the "knowledge-house" the standing law forbids. The honest shape is: explore broadly, persist narrowly, re-verify at use, and use instant knowledge for the gap the environment cannot answer.

### Q2 — What exactly is saved, and what is never saved

| Saved | Kind | Trust rule |
|---|---|---|
| **Priors** (observed transitions of THIS instance, keyed by env kind, inside the learned model) | Observed facts | Never trusted blindly — root rows re-execute on each fresh instance before seeding; non-root rows are discarded and re-derived |
| **Admitted rules** (goal family + plan sketch + evidence hash + admission history) | Hypothesis that survived replay on fresh instances | Served only on a repeat goal of the same family, only if the replay reaches the goal on THIS instance — otherwise fell through honestly |

| Never saved | Why |
|---|---|
| Raw traces | A trace is the instance, not the condition. It is archived inside the evidence payload as a hash, never served as knowledge |
| Exact instance-specific actions | A plan that works on instance A does not transfer to instance B (different walls, different target). Fresh instances refuse such rules honestly |
| Unverified plan rules | A plan that has not survived admission is a hypothesis. It is never persisted |
| Stale priors | Priors from a different instance are claims about a different instance. Non-root rows are discarded and re-derived |

**Verdict:** goal family + plan sketch + evidence + admission verdict — never the trace, never the exact action sequence, never an unadmitted rule. The plan rule is a hypothesis that has survived replay on instances it was not taught on. That is the ceiling of what one experience can honestly buy.

### Q3 — What to admit and what to persist

| Admit | Persist |
|---|---|
| A plan rule (hypothesis) on at least one fresh instance reaching the goal | Only on ADMIT — the rule is written to the store with its evidence and verdict history, so it is inspectable and deletable |
| An observed fact (prior row) whenever the scan verified it | Priors are saved unconditionally — they are facts, not hypotheses | 

**Then never again:** no rule persists on zero fresh instances (the fresh-family receipt refused it honestly); no prior is served that did not re-execute; no raw trace is served as knowledge.

### Q4 — §2 confirmation as an engineering statement

The default is confirmed. One experience writes to the store only a hypothesis; the admission gate decides whether it persists; the store is inspectable, editable, deletable; zero model calls at runtime; the scan re-derives what it cannot trust. There is no stored statistic that is not either an observed fact or an admitted hypothesis.

And the instant-knowledge source has a local tier: the computer's own guides are read FIRST, offline, completeness-gated; the web tier stays as the fallback. A document answers only if one paragraph shares content tokens with the query — one keyword anywhere in a doc is not a conclusion.

## 3. Single ultimate plan and design kill

Bottleneck (resolved this round): the instant-knowledge source was **web-only**. The Perfect Algorithm already refused to conclude from one source, but it did not read the computer's own guides — README, AGENTS.md, `.md` documentation, which are offline, version-matched, cheap, and already encode the contract between a tool and its user. Docs for agents are "last known state," not ground truth — so the local guide orients the plan; it is never trusted over the environment's own verification.

Plan (minimal, ordered — executed this round):

1. **Local instant-knowledge source in front of the web source** — `local_guide_v1.py`, built and wired in BEFORE `jit_knowledge`. Completeness-gated: a document answers only if one paragraph shares ≥2 content tokens with the query (60% of content tokens, minimum 2). If the local tier misses, the web source is asked — and only when the caller passes `allow_instant_knowledge=True`; by default the loop is offline-only.
2. **Keep the scan → right question → plan → act+verify → learn → admit → save loop unchanged.** The local guide is a new instant-knowledge tier, not a new mechanism. No new learner, no new admission gate.
3. **Priors stay observed facts; rules stay hypotheses.** The plan rule persists only on fresh-instance admission; priors are saved unconditionally, re-verified at use, never trusted blindly.
4. **Honest refusal in place of a false persistent path.** When the local guide is absent or incomplete, the receipt says OPEN, not proceed.

Rejected ideas and why:

- **Broad learning-of-everything / a general world model in weights** — unverifiable on unseen instances, a world-fact warehouse, the forbidden knowledge-house. Rejected.
- **Storing the raw trace as knowledge** — the trace is the instance; it does not generalize to an unseen environment. Archive as evidence hash only. Rejected.
- **Storing exact instance-specific actions** — refuses honestly on fresh instances; the plan sketch that works on one instance is refused on the next. Rejected.
- **Trusting a prior without re-verification** — the fresh-family receipt showed 43 of 43 stale rows that did not replay. Rejected.
- **Web-first instant knowledge** — the web is slow, often blocked, and costs allowance for something the computer already has locally. Local first; web as fallback. Rejected.
- **A new admission gate or learner** — the existing one is sufficient; the local-guide tier is a source, not a mechanism. Rejected as unnecessary complexity.

Smartest-approach check: one new source tier, zero new learned mechanisms, the existing gates unchanged. There is no component left to remove except the local-guide source itself, which is the deliverable.

## 4. Build and hard tests

Built this round (branch arena/88194f15-brain):

| Quantity | Result |
|---|---|
| Repeat-goal replay tests | 2 new `ReplayFromMemoryTests` — an admitted rule serves `INSTANT_RECALL` with no scan; a stale rule is never served (fell through to full loop honestly) |
| Full Perfect Algorithm test suite | **23/23 OK** (was 21, +2 replay tests) |
| Repeat-goal receipt | `canonical/verification/PERFECT_ALGORITHM_RECEIPT_20261122_REPLAY_V1.json` — same family, repeated goal, rule replayed instantly, no scan run, priors still saved |
| Fresh-family receipt (prior branch, merged) | instance B: 3 root transitions kept, 43 discarded, plan re-derived, goal reached, rule refused |
| **Local instant-knowledge tier** — `canonical/runtime/local_guide_v1.py` — reads the computer's own guides: README, AGENTS.md, `.md` docs, offline, completeness-gated | 8/8 local-guide tests pass; the local tier is the FIRST instant-knowledge tier, the web tier is the fallback. A document answers only if one paragraph shares ≥2 content tokens with the query (60% of content tokens, minimum 2): the repo's own docs do NOT answer "how to use grid world" honestly |
| Local-guide receipt | `canonical/verification/LOCAL_GUIDE_RECEIPT_20261122_V1.json` — offline measurement: "how to use grid world" → OPEN__LOCAL_GUIDE_NOT_FOUND (no honest guide in this repo); "how to use dial lock" → PASS (the repo's own dial-lock fixture docs are genuine); integration test: plan fails → local tier answers → receipt stays OPEN and honest |
| Local-guide + Perfect Algorithm + environment-learning suite | **66/66 OK** (perfect_algorithm 23 + local_guide 8 + environment_learning 35) |
| Full unified-model verify | 33/33 PASS (unchanged this round) |

| Hard tests | Status |
|---|---|
| OSWorld 2.1 | NOT RUN — §6 remains open |
| SWE-bench Pro | NOT RUN |
| Terminal-Bench | NOT RUN |
| GUI/browser competence | NOT RUN |

Honest statement: **the §6-class hard tests are NOT done.** This document is the verdict and the ultimate plan, not a completion claim. No GUI, browser, OSWorld 2.1, SWE-bench Pro, or Terminal-Bench task was run this round. §6 is open.

## 5. Honest limits and next bottleneck

- Producer-run sandbox only. No independent identity re-ran any measurement. No benchmark score is claimed or earned.
- The local instant-knowledge tier reads `.md` guides (README, AGENTS.md, repo docs). Man pages and `--help` output are not (yet) part of the tier — the honest improvement is wiring man-page/help reading into the same local lookup. Honestly: the local tier is offline-only and completeness-gated, but it is not yet a man-page reader on this machine, which has no man pages and no declared help for the examples.
- The plan rule remains instance-invariant only for goals whose plans do not depend on a specific layout; grid-world-style goals refuse honestly. The generic plan rule is admitted on identical-shape instances only (existing tests). No fresh-family admission of a generic plan rule is claimed yet.
- Priors are saved unconditionally but are only re-verified for the root; deeper rows are always re-derived by the scan. This is the honest trade, not a gap in the implementation.
- Next §5 bottleneck: carry the same discipline to a genuinely new environment class — an OSWorld-shaped surface where the local guide is XML/DOM/GUI rather than Markdown docs — and measure the local tier there rather than assuming it. Priors remain root-only verified by design; deeper rows are always re-derived by the scan.

## 6. The archive (.tar.gz) goal — honest status, 2026-11-23

A new task surfaced after the above verdict: an `.tar.gz` goal ("archive data.txt into data.tar.gz") was narrowed by the same machinery and found nothing to act with. The goal was never reachable: no goal state was ever observed, although tar (2nd of 8 programs by narrowing) can do it.

What was false or missing, and what is now fixed:

- **False: the file existence check was the success condition.** `tar --append --file data.tar.gz data.txt` creates a plain, uncompressed tar named data.tar.gz and the old action loop declared it success. An archive with the right name is not an archive. The action now holds itself to the goal's own predicate over the observed tree (the same predicate the scan applies), and only then returns success. The recorded recipe is the exact argv that made the predicate true.
- **Missing: a file-valued flag whose manual line carries no output-ish keyword was dropped**, so `--file` — whose manual says `=ARCHIVE use archive file or device ARCHIVE` — never appeared in `output_flags`, and no shape like `[tar, --create, --file, data.tar.gz, data.txt]` was ever generated. `--file` now follows the manual for the argument family itself.
- **Missing: goal-flag and output-flag combinations.** The shapes that answered the goal (create an archive, with an auto-compress filter, and name the archive) needed three flags in one argv; the generator only built one goal flag with one output flag. It now combines each output flag with all single and pair combinations of goal flags, both manual-derived. `tar --auto-compress --create --file data.tar.gz data.txt` is generated and is the one that works.
- **The predicate itself is .tar.gz-exact** (this turn's fix): the archive must open as gz, contain the source file by basename, and hold its bytes exactly. Plain (uncompressed) tar named `.tar.gz`, a gz archive holding the wrong bytes, and a gz archive holding the source under another name are all refused.

Measured, not claimed:
- Cold run: `archive data.txt into data.tar.gz` → plan `["run_tar"]`, plan_length 1, `act` status PASS, reached True, goal_states_observed 24, `status` PASS, `pass` True, `outcome` VERIFIED_NOT_PERSISTED (admit REFUSED — no fresh instances offered, correctly not persisted). Recipe recorded: `[tar, --auto-compress, --create, --file, data.tar.gz, {input}]`.
- Two honest tests added (`ArchiveGoalTests`): the predicate refuses uncompressed tar / wrong bytes / wrong name, and `run_tar` reaches the verified goal with a recipe naming the archive.
- Tests: AskingTests (7), EnvironmentTests (15), test_perfect_algorithm_computer_env_v1 (5) — all OK. test_computer_env_v1 82 tests: 3 failures, all pre-existing (confirmed identical with these edits stashed) — the explore channel's `FAIL_CLOSED__COMPUTER_EXECUTION_REQUIRES_ADMITTED_CONFINEMENT`.

Not done, honestly:
- No fresh-family admission for the archive rule; the receipt is VERIFIED_NOT_PERSISTED. No rule is admitted.
- The scan takes ~46 s (budget 150, 27 states, 270 transitions) dominated by the cheap-but-numerous failed action attempts; this is the cost of learning without hand-written stripes, not a defect.
- The narrowing still offers junk programs (dpkg-architecture, ld.bfd) above tar; the narrowing is limit-8 and manual-word-derived, not a scored relevance model. This is pre-existing and honest.
