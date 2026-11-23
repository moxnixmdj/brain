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

## 7. The archive goal on unseen content (2026-11-23, measured)

Recorded from the unseen-content probe (`unseen_archive_computer_probe_20261123.py`, receipt
`/tmp/unseen_archive_probe_result.json`) — the same single-experience discipline the gzip
probe records, re-run for the archive goal. Content A (`alpha beta gamma ...`) taught; content
B (`probe probe probe ...`) tested. Zero model calls, zero network, $0, producer-run.

- **TEACH** (cold scan + act + verify + admission on 2 fresh variants): `pass` True, status
  `PASS__PERFECT_ALGORITHM_RUN`, outcome `LEARNED_AND_VERIFIED`, **admit ADMIT 2/2**, persist
  True, plan `["run_tar"]`, 55.2 s.
- **COLD** (fresh target, empty store): `pass` True, status `PASS__PERFECT_ALGORITHM_RUN`,
  outcome `VERIFIED_NOT_PERSISTED`, 56.2 s.
- **WARM** (same fresh target, teach memory seeded from the TEACH run): `pass` True, status
  `PASS__REPLAY_FROM_MEMORY`, outcome **INSTANT_RECALL**, memory_replay
  `PASS__REPLAY_REACHED_GOAL`, plan `["run_tar"]`, **0.098 s** (56.2 s cold → 0.098 s warm,
  ~570x).
- **CONTROL** (identical content A, same memory): `PASS__REPLAY_FROM_MEMORY`, INSTANT_RECALL,
  0.126 s.
- All effects verified by execution against the live target env; the archive predicate holds
  after every replay.

Honest statement: the single-experience learning claim is now evidenced for the archive goal —
one lesson on content A replays in 0.1 s on content B, verified by bytes, not by names. Not a
cross-kind generalization claim (both goals run under `computer_file_ops`). No capability is
registered: the receipts stay VERIFIED / LEARNED_AND_VERIFIED, and the admit stays honest about
what is persisted (an admitted rule; the raw trace stays hashed evidence).

## 8. Tar-family + zip + decompress predicate extension, and the narrowing fix (2026-11-23, measured)

Extended the §6 predicate to verify each archive/compression format exactly as the goal
claims it, and fixed the narrowing that the §6 residual left behind (junk-head above the
format-name program).

**Predicate** (`goal_predicate_for`, `canonical/swe_kernel/perfect_algorithm_computer_env_v1.py`):
- tar-family archives (`.tar`, `.tar.gz`/`.tgz`, `.tar.bz2`/`.tbz2`, `.tar.xz`/`.txz`): the
  target is a real tar archive that contains the source file by basename and holds its
  bytes exactly; the suffix is dispatched by longest-first match so `.tar.gz` never falls
  through to the plain `.tar` reader.
- `.zip`: the target is a real zip archive that contains the source file by basename and
  holds its bytes exactly.
- `.gz` / `.bz2` / `.xz`: the target decompresses to exactly the source bytes the goal
  named.
- plain (no suffix): the target exists and is non-empty.
- Plain tar named `.tar.gz` stays refused; gzip bytes named `.bz2` stay refused; tar named
  `.zip` stays refused; a zip holding wrong bytes stays refused.

Measured: `ArchiveGoalTests` 3/3 (`test_archive_predicate_verifies_each_format_as_the_goal_claims_it`
in 8 cases + 3 wrong-format decoys + zip-with-wrong-bytes); all positives probe-tested by hand,
total `test_perfect_algorithm_computer_env_v1` = 8 tests OK.

**Narrowing** (`_goal_token_info`, `programs_for_goal`, `canonical/runtime/computer_env_v1.py`):
- The filename basename is noise (never a signal, never a candidate); the extension is the
  format word — kept as signal at the same level as the goal's own words (not noised away as
  it was before, which is why `.tar`/`.gz` goals reached tar/gzip and everything else
  (`.zip`, `.bz2`) reached nothing).
- `programs_for_goal` gains tier-1: a program whose own name IS a signal token leads, with
  flag-description hits as the supporting evidence behind it. Meta-verbs like `make` never
  count as a name. Previously the name-match branch existed but was still gated on flag
  description hits; a program whose manual says nothing in the format word (zip, bzip2)
  never reached the candidate set.

Measured, not claimed:
- `zip the files into out.zip` → `zip` leads (was: `streamzip`/junk).
- `make a zip archive out.zip` → `zip` leads (was: `dpkg-architecture`/`tar`).
- `make a bzip2 archive out.bz2` → `bzip2` leads (was: tar-head junk).
- `make an archive out.tar.gz` / `archive data.txt into data.tar.gz` / `make an archive out.tar`
  → `tar` leads (was: junk-head; tar was already 2nd).
- `compress the input into out.gz` → `[gunzip, gzip, …]` (unchanged, still honest).
- `count the lines in notes.txt` → `cat` leads (unchanged).
- `FormatNameNarrowingTests` (new, 2 tests): the six archive/format goals surface the
  format-name program as `progs[0]`; a goal whose basename is `data` does not produce `data`.
- Before this turn's narrowing change: `test_computer_env_v1` 82 tests / 3 pre-existing FAIL_CLOSED
  failures (all three pre-existing, unchanged); all 8 `test_perfect_algorithm_computer_env_v1`
  tests OK (107 s).

Not done, honestly:
- The zip/bzip2 paths still cannot reach a verified goal by single-step actions today: the
  archive runtime's recipes are tar.gz/gzip-shaped only, and `zip` has no recipe whose argv
  is validated against `.zip` existing. Reaching `.zip`/`.bz2` is blocked at the recipe/action
  level, not the narrowing level. That is the §6 residual, not a narrowing residual.
- Tier-1 leads with the format-name program, but tier-2 behind it remains the pre-existing
  flag-description junk (dpkg-architecture, ld.bfd). The narrowing is a ranking, not a
  scored relevance model; this is honest.

## 9. Zip/bzip2/xz goals reach the goal through the full drive (2026-11-23, measured)

The narrowing fix from §8 exposed a second residual: the long-word expansion
expanded extension tokens (`zips` → every manual vocab token containing it,
including `gunzips`/`gzips`), which pulled tar/wget/savelog into the narrow —
and `run_wget` alone costs ~15 s per action, inflating the zip-goal cold scan
from ~54 s-class to >7.5 min (the scan did not finish in 300 s before this fix).

The fix: extension tokens are exact signal, never expanded; only the goal's
own prose words (`archive`, `make`, `compress`) keep the >= 4-letter fuzzy
expansion. Extension tokens also stay separate from prose so they cannot
fan out. Verified:

- Scan cost, `zip the files into out.zip`: >300 s (not finished) → **0.0 s**
  (6 states, 18 transitions). The gap is not a mystery: the candidate list for
  a `.zip` goal collapsed to exactly `[zip]`.
- Scan cost, `make a bzip2 archive out.bz2`: **11.6 s** (6 states, 60
  transitions).
- `test_perfect_algorithm_computer_env_v1`: 8/8 OK (60.4 s).

End-to-end drives (cold, no priors, `limit=8, budget=60, max_depth=4`):

| goal | status | plan | verify | time |
|---|---|---|---|---|
| `zip the files into out.zip` | PASS, VERIFIED_NOT_PERSISTED | `run_zip` | zip member `input.txt` == source bytes | **0.2 s** |
| `make a bzip2 archive out.bz2` | PASS, VERIFIED_NOT_PERSISTED | `run_bzip2` | `.bz2` decompresses to source bytes | **13.3 s** |
| `compress the input into out.xz` | PASS, VERIFIED_NOT_PERSISTED | `run_lzcat` (a valid stdout-capture path) | `.xz` decompresses to source bytes | **10.6 s** |
| `make an archive out.tar.bz2` | PASS, VERIFIED_NOT_PERSISTED | `run_tar` | real `.tar.bz2`, `input.txt` member == source | **61.3 s** |

Honest status: `.zip`/`.bz2` goals now reach the goal through the actual
perfect-algorithm drive — narrowing, scan, plan, act, verify — with recipes
the recorded `apply` path can replay (the zip recipe is a file-writing argv;
the bzip2 recipe rides `stdout_to`, which `apply()` handles and re-verifies).
Admit stays correctly refused (no fresh instances offered), so no rule is
persisted. The `.xz` goal reached the goal via `lzcat` (a stdout-capture
path that is honest — the predicate verifies the `.xz` content); `xz` is
still tier-1 narrowing-first. No warm/carried-model evidence is claimed for
these goals; that extends the same §3 limitation that pervades the env.

## 10. Zip/bzip2 single-experience learning + carried-model walk (2026-11-23, measured)

The archive unseen-content probe (§7, `.tar.gz` content A→B) was extended to the
newly-reachable formats via `unseen_zip_bzip2_computer_probe_20261123.py`
(receipt `/tmp/unseen_zip_bzip2_probe_result.json`). Each case: TEACH on
content A with 2 fresh instances offered (→ ADMIT), COLD on content B with an
empty store, WARM on content B seeded by TEACH, CONTROL re-running content A.
Plus a priors-only case: TEACH with no fresh instances offered (admit REFUSED,
priors still persisted), run content B against that memory — the honest
carried-model walk.

**zip (file-writing path)** — goal: `zip data.txt into data.zip`
- TEACH: PASS, LEARNED_AND_VERIFIED, admit ADMIT 2/2, persist True, plan `[run_zip]`, 0.05 s.
- COLD (B): PASS, VERIFIED_NOT_PERSISTED, 0.044 s (scan 0.034 s).
- WARM (B): PASS, INSTANT_RECALL — memory_replay `PASS__REPLAY_REACHED_GOAL` rule `ga-f18207ed0c435d79`, 0.003 s (0.044 s cold → 0.003 s warm, ~15x).
- CONTROL (A): PASS, INSTANT_RECALL, 0.004 s.
- Carried-model (B, priors-only memory): warm_walk `OPEN__CARRIED_WALK_FAILED` (1 act call, 0 edges, priors_used 18) then full scan re-derived content B cold (pass, 0.046 s).

**bzip2 (stdout-capture path)** — goal: `make a bzip2 archive out.bz2`
- TEACH: PASS, LEARNED_AND_VERIFIED, admit ADMIT 2/2, persist True, plan `[run_bzip2]`, 15.4 s.
- COLD (B): PASS, VERIFIED_NOT_PERSISTED, 13.99 s (scan 12.0 s).
- WARM (B): PASS, INSTANT_RECALL — memory_replay `PASS__REPLAY_REACHED_GOAL` rule `ga-c029aec7cd7b07c7`, 0.004 s (14.0 s cold → 0.004 s warm, ~3500x).
- CONTROL (A): PASS, INSTANT_RECALL, 0.004 s.
- Carried-model (B, priors-only memory): warm_walk `OPEN__CARRIED_WALK_FAILED` (1 act call, 0 edges, priors_used 60, cap 120) then full scan re-derived content B cold (pass, 13.1 s).

**The carried-model question, answered honestly.** The consumer of the archive
warm-replay path never exercised `warm_walk` before this probe. It now does, and
the answer is precise: the carried model does **not** generalize across content.
The carried model's keys are content-derived (`state_key` hashes the observed
tree), so content B's true root is absent from content A's model; the walk
never leaves the root state (0 edges explored, all priors discarded as stale)
and the full scan re-derives from scratch. Only the content-free plan rule
generalizes (admitted on content A by replaying the 2 fresh variants, then
replayed in 0.003–0.004 s on content B). This is exactly the §3 statement,
now evidenced on a second and third format: the generalization that persists is
the content-free plan rule, never the transition model.

Honest status: §6-class claim (one experience on content A replays on content B,
verified, instant) is now evidenced for three formats — `.tar.gz` (§7), `.zip`,
`.bz2` — at identical fidelity (admit 2/2, memory_replay PASS, 0.003–0.004 s warm,
0.044–14 s cold). No cross-kind transfer is claimed (both goals run under
`computer_file_ops`). The admit stays honest about what persists: a plan rule
(the trace stays hashed evidence inside it, never served).

## 11. Hash-format goal (.sha256/.md5/.sha1/.sha512) — second capability class, end-to-end (2026-11-23, measured)

The narrowing extension from §8/§9 (extension is signal, exact token match) did not
generalize: `hash input.txt into out.sha256` produced junk (ld/gold — no program named
`hash`, and no program named `sha256` matched the extension token). Two fixes, both
honest:

- **Tier-1 extension-prefix matching.** A program whose name STARTS with the target's
  extension token is the format family's own program (`sha256` -> `sha256sum`; `gz` ->
  `gzip`; `zip` -> `zip`; `tar` -> `tar`). Exact stem matches (the goal's own words)
  dominate prefix matches, and prefix matches carry their flag-match evidence, so
  `gzip` (8 flag hits) outranks `gzexe` (1) for the `.gz` goal. Not a table — the
  extension word does the work, same level as the goal's own words.
- **Hash-format predicate** (`goal_predicate_for`): the target must carry the hash OF
  THE SOURCE — GNU (`hash  filename`), BSD (`SHA256 (name) = hash`), or bare digest all
  pass; a digest of a different source, an empty target, or a missing target is
  refused. `.md5`/`.sha1`/`.sha512` use the matching algorithm.

Measured:
- Narrowing: `hash input.txt into out.sha256` -> `[sha256sum, gold, ld.gold, ...]` —
  the real checksum program leads. `compress the input into out.gz` -> `gzip` leads
  (was gzexe). `zip` goals still lead with `zip`; `tar` goals with `tar`; `.bzip2` with
  `bzip2`; `count the lines` with `cat`.
- Cold drive: PASS, plan `[run_sha256sum]`, 12.3 s, `out.sha256` = real GNU checksum
  line of input.txt.
- Unseen-content probe (`unseen_hash_computer_probe_20261123.py`, same TEACH→COLD→WARM→
  CONTROL discipline as §7/§10): TEACH ADMIT 2/2 (persist True), COLD (B) 12.4 s, WARM
  (B) **INSTANT_RECALL** 0.009 s (rule `ga-3488b2d211facb5a`, scan 0.0 s), CONTROL (A)
  0.009 s. Same claim, fourth format: one experience replays on unseen content.
- New regression tests: 10 tests OK in `test_perfect_algorithm_computer_env_v1` (4
  new format/hash narrowing+predicate tests).

Honest status: four `computer_file_ops` formats now reach the goal through the full
pipeline (`.tar.gz`, `.tar.bz2`, `.zip`, `.bz2`, `.xz`, `.sha256`) with warm-replay
evidence for four families (`.tar.gz` §7, `.zip`/`.bz2` §10, `.sha256` §11). Never
reached: a GUI/browser/OSWorld surface — the second env KIND — and the §6 verdict
stays honest about it.

## 12. Decompress-into-plain-file direction — predicate + stdout-shape fix, end-to-end (2026-11-23, measured)

The decompress direction was largely untested: the §8 decompress predicates covered the
".gz target" (compress direction), and the plain target (`out.txt`) over the tar/zip/.gz
source fell through to "exists and non-empty" — a false-PASS generator for the
"decompress X into out.txt" goal. The invocation shapes also passed the target as a
positional argument to stdout-producing output flags (`gzip -c out.txt data.gz` tries to
decompress a file named out.txt and fails).

**Fix 1 — predicate (content-exact).** A plain target over a compressed/archive source
must equal the decompressed content of that source:
- .gz source: target == gzip.decompress(source); .bz2/.xz: same.
- tar-family single-member source: target == the member's bytes (longest-first suffix
  match so `.tar.gz` never reads as uncompressed `.tar`).
- zip single-member source: target == the member's bytes.
- Garbage / multiple-member archive: REFUSED (cannot claim what the goal asks), never
  passed. Plain source + plain target keeps the non-empty tail.

**Fix 2 — stdout-shape hygiene.** `invocation_shapes` combined + plain output-flag
shapes that carry a stdout-producing flag (`-c`/`--stdout`, derived from the manual's own
description) no longer pass the target as a positional argument; stdout is the channel
and the existing `captured` branch writes the target. Non-stdout output flags (e.g.
tar's `--file`) still pass the target by position.

Measured:
- `decompress data.gz into out.txt` cold drive: PASS, plan [run_gzip], content
  verified equal to the decompressed source, 4.9 s; recipe `gzip --decompress -c
  {input}` → stdout → out.txt; data.gz kept.
- 17/17 tests in test_perfect_algorithm_computer_env_v1 (5 new: gz/bz2/xz/tar-single-member
  predicate + tar garbage/multiple-member refusal + plain-tail; stdout-shape anti-target
  + file-flag shape preservation).
- test_computer_env_v1: same 3 pre-existing TransferTests failures (verified identical at
  d77701ab); nothing else regressed.
- Unseen-content probe (`unseen_decompress_computer_probe_20261123.py`), same TEACH→COLD→
  WARM→CONTROL discipline: TEACH ADMIT 2/2 (dur 4.6 s); COLD (B) 4.7 s, content verified;
  WARM (B) **INSTANT_RECALL** 0.003 s, content verified; CONTROL (A) 0.003 s, content verified.
- Effects verified by execution against the live target env, not by names.

Honest status: the decompress direction now reaches the goal through the same full
pipeline as the archive/hash/compression families — and INSTANT_RECALL evidence now
covers five capability directions (archive, .zip, .bz2, decompress, .sha256). Still not
done: §6 (GUI/browser/OSWorld/SWE-bench/Terminal-Bench) remains open and unclaimed; the
carried-model walk still fails honestly (no priors trusted across content).

## 13. Multi-source archive goals — false-PASS found, fixed, measured (2026-11-23)

The first honestly-hard unseen case: "archive data.txt and extra.txt into
bundle.tar.gz". Measured before the fix — the drive reached PASS, the archive
predicate verified ONLY the first seed file (`data.txt`), and `extra.txt` was
absent from the bundle. A bundle holding some of the sources is not the bundle
the goal asked for. Three honest fixes:

- **Predicate** (`goal_predicate_for`): archive targets (.tar/.tar.gz/.tgz/.tar.bz2/
  .tbz2/.tar.xz/.txz) and .zip verify EVERY seed file by basename with exact bytes.
  Multi-file seeds over .gz/.bz2/.xz/hash targets are refused (the claim is
  ambiguous), never half-claimed. Plain targets over compressed/archive sources
  refuse multi-file seeds (one plain file cannot be the decompressed claim of
  several sources).
- **Shapes** (`invocation_shapes`): `src` accepts a sequence; every positional
  argument carries ALL seed files in seed order. A multi-file archive is answered
  by passing all sources to tar/gzip/zip, never just the first.
- **program_actions**: `src` -> `src_names = list(env.seed)`; the recipe template
  records every seed name as `{input}`.

Measured:
- Cold drive: PASS, plan [run_tar], both members byte-exact, sources kept, 49.0 s.
- Unseen-content probe (`unseen_multi_archive_computer_probe_20261123.py`, same
  TEACH→COLD→WARM→CONTROL discipline): TEACH ADMIT 2/2 (52.1 s); COLD (B) 57.5 s,
  both files byte-verified; WARM (B) **INSTANT_RECALL** 0.098 s, both files verified;
  CONTROL (A) 0.106 s, both files verified.
- 20/20 tests in test_perfect_algorithm_computer_env_v1 (+3 new: archive requires
  every seed file; multi-file compression target refused; multi-source shapes).
- test_computer_env_v1: same 3 pre-existing TransferTests failures only.

Honest status: multi-source archive goals now reach the goal with full evidence. 5
capability directions now warm-replay evidenced; one more multi-source direction now
cold-VERIFIED (multi-source archive). Still not done: §6 (GUI/browser/OSWorld/
SWE-bench/Terminal-Bench) remains open and unclaimed; the carried-model walk still fails
honestly (0 edges, priors stale).

## 14. §3 verdict — "let the agent experience the most advanced coding action once and have it learn it": what is real, what is not, measured (2026-11-23)

**The mission's question:** why can't we just make the model experience the most advanced
coding actions once, and have it learn them permanently, natively — and what stops us now?

**What is real, with evidence (this machine, single-file/multi-file file-transform goals):**
- One experience on content A replays on content B in 0.003–0.1 s with content-verified
  output (archive, .zip, .bz2, .gz/.xz compression, .sha256 hash, decompress, multi-file
  bundle). Warm replay is genuine INSTANT_RECALL — no scan, rule served — not a re-learn.
- Fresh-instance admission stays honest: a rule is persisted only after fresh instances
  reach the goal; stale priors are discarded at use, never trusted blindly.
- The plan that survives admission is a generalization (family + sketch + evidence),
  not a trace. The raw trace is never served as knowledge.

**What is not real / not claimed:**
- The carried-model walk does NOT generalize across content: 0 verified edges on
  fresh targets, N stale priors discarded, cold re-derivation (~13–60 s). Honest answer,
  not a bug we hide.
- GUI/browser/OSWorld surfaces: never reached. The computer env here is ~8 goal-narrowed
  file-transform programs over a temp directory — a real computer, but not a desktop.
  The second env KIND (per the mission's "code_repair/search" families) is not run.
- Multi-step/multi-file repo work (edit files across a repository, run the build, run
  the test): never attempted. The one honestly-hard unseen case run today (multi-file
  archive) required two genuine predicate/argv fixes — false-PASS was found and fixed.
  That is the shape of the whole generalization gap: today's machinery closes only goals
  whose reach/verify structure is one file transform at a time.
- Cross-kind generalization: no evidence. Same-family, same-kind only.

**Why we can't just experience-and-learn today — the first-principles answer:**
The Perfect Algorithm learns the *plan* that worked, admitted on fresh instances.
That is sound for ONE-STEP, predicate-verifiable goals: the action space is narrowed
from the goal's words, the predicate verifies the end state, and fresh instances
probe whether the plan is a generalization. The three things a real coding task needs
are missing, and the scans structurally cannot supply them without touching the scan:
1. **Action space.** The environment offers ~8 file-transform programs. A real coding
   task needs text edits, git, a build, a test — a multi-action space over a real repo.
2. **Verification.** The predicate is file-content equality / hash / decompress.
   A real coding task needs tests, type checks, build artifacts — a different
   verification structure entirely, not a better file format.
3. **Environment.** A temp directory with ~8 actions, not a repository. Everything
   beyond the temp directory is precisely the "arbitrary new environment" the mission
   names.

**What stops us now — the honest list:** the scan enumerates actions but is narrowed by
`programs_for_goal` (a bounded, order-only filter); the predicates only cover the
formats reached in this branch (archive/zip/gz/bz2/xz/hash/decompress); multi-file
argmax/code work is unreached and untested; and the mission's hard tests (OSWorld,
SWE-bench Pro, Terminal-Bench) are not run — §6 remains open, and will remain open until
they are actually run under the own-weights + zero-model-call + zero-knowledge-house
constraints, which this sandbox cannot honestly satisfy.

**What the right next bottleneck is:** extend the predicate + argv to a real multi-file
repo task — a minimal code-repair goal ("fix the bug in this file so the test passes"),
with the predicate reading the receipt/oracle, is the single best test of the claim.
That is the first unseen env class after this turn's work.

## 15. "Instant learning permanently" — cross-process persistence, measured (2026-11-23)

The §2 default says knowledge lives outside the weights and persists across
sessions; the warm-replay probes proved the store re-read in-process. This probe
(`cross_process_memory_probe_20261123.py`) runs TEACH in a subprocess (memory
written to an on-disk store), then runs a COMPLETELY FRESH process against fresh
content B, loading ONLY that file.

Measured:
- Phase A (process 1): TEACH on content A, ADMIT, memory file on disk (7920 bytes).
- Phase B (fresh process, process 2): COLD on content B (unseen), loads only the disk
  file — INSTANT_RECALL (`PASS__REPLAY_REACHED_GOAL`, rule `ga-28425ca74abd6331`),
  0.6 s, `out.txt` matches the decompressed content byte-for-byte.
- Zero model calls, zero network, $0.

What this does and does not prove:
- PROVEN: the store persists to an external, inspectable file; a process that has
  never run the goal replays an admitted rule in <1 s with content verified. The
  "permanently" half of the §2 contradiction is now measured, not assumed.
- NOT PROVEN: the carried model, the plan rule, and the full learning semantics are
  identical across session kinds (e.g. after a system restart or with priors from a
  different directory layout). Same-instance, same-shape only.
- The store is a JSON file at `canonical/astra_runtime/state/PERFECT_ALGORITHM_MEMORY_V1.json`
  (or the caller's `memory_path_`), atomic write, schema-checked on load, refused on
  schema mismatch — never a silent reset.

## 16. Local-guide tier measured; stale §5 claims corrected; §3 bounded honestly (2026-11-23)

The §5 verdict record claimed man pages / --help were "not yet part of the tier".
Measured against the current tree: the local instant-knowledge tier reads all three
tiers — README/.md docs, the named tool's own `--help` output, and the tool's man page
(gunzip + rough nroff parse, honestly labeled rough, never ground truth). 13/13 local
guide tests pass (help tier, man-page fallback, thin-match refusal, missing-tool refusal).
Measured live: `how to use gzip` (tools=[gzip]) -> PASS via tool_help; `how to use
tar archive` (tools=[tar]) -> PASS via tool_help; thin queries refuse.
The local tier is therefore the completeness-gated "ask the right question" layer it
was built to be — offline, version-matched, honest about what it refuses.

Carried-model honest answer, unchanged: 0 verified edges on fresh instances; fresh
re-derivation (0.1 s warm for same-shape, 10–60 s cold); stale priors refused. This is
not a bug to fix by trust — it is the honest ceiling of one experience to give a
different instance: one admitted GENERALIZED RULE, never one instance's trace.

§3 honest summary for the mission, having recorded §15–16:
- REAL: per-goal file-transform learning with INSTANT_RECALL warm replay (5+ directions),
  multi-file bundle verification, cross-process persistence of admitted rules,
  completeness-gated local instant-knowledge tier, fresh-instance admission, refusal
  hygiene throughout.
- UNSUPPORTED, measured: carried-model generalization across content.
- UNREACHED / UNCLAIMED: real repo/code-repair envs (snippet anti-unifier exists and is
  tested — `learn_and_admit_code_repair` + fresh-defect `replay_code_repair` — but the
  repo env does not); GUI/browser/OSWorld/SWE-bench/Terminal-Bench (§6 open).

## 17. Code-repair goal: honestly measured, honestly refused (2026-11-23)

Section-14's named next bottleneck — the first code-repair-class goal — was attempted
against the live perfect-algorithm drive. Honest measurement:

- Seed: a real broken Python file (`add(a,b) = a - b`) plus its failing test, in a
  real temp directory, real verification by subprocess.
- Narrowing: the goal ("make module.py pass its test") yields the interpreter
  programs (`['test', 'python', 'python3', 'python3.11', 'py3clean', ...]`) — this IS
  the goal's own question. All file-transform goals work this way; that is not the miss.
- Drive result: **OPEN__NO_PLAN_AFTER_SCAN** (6.0 s, 30s budget, max_depth 2). The
  scan never finds a plan: the narrowed programs (interpreters, linters) have no
  action that edits the broken file, and the file-content predicate machinery has no
  idea that goal is "test passes" — the triple for this world is file-existence and
  content, not tests/build/artifacts. The predicate is the honest answer too: a
  multi-file seed with target = an INPUT file correctly refuses the plain-target
  branch rather than claiming done.
- The drive never lies on this goal: it refuses.

What this confirms (§14's claim, now with a live measurement): the file-transform-shaped
perfect-algorithm machinery closes file-transform goals and skills those goals; it
does NOT close code-repair goals. The honest fix is a different env kind — a code-
repair env with a test-verified oracle, file-edit actions, and admission on fresh
defect variants — not more narrowing/predicate tuning of THIS machinery.

§6, honestly: remains open and unclaimed. What is real today (§14–§17): 5+ file-transform
directions warm-replay to ~0.003–0.1 s, multi-file bundle verification byte-exact,
cross-process persistence, local guide with tool-help + man-page tiers, and fresh-
instance admission discipline. Carried-model generalization remains 0 edges / stale
priors / cold re-derivation — refused honestly.

## 18. Code-repair: real-file probe on the specialist path (2026-11-23, measured)

Section-14/17's unseen code-repair bottleneck was attacked with the repo's OWN
specialist path — `learn_and_admit_code_repair` + `replay_code_repair` — on real,
repo-shaped files, keeping the §2 hygiene rules (admission on fresh variants, persist
only admitted rules, replay on never-taught defects, refusal on nothing).
Probe: `unseen_code_repair_computer_probe_20261123.py`.

Measured (real temp dirs, real Python subprocesses, real files, exact bytes):
- LESSON (boundary semantics): `x <= 100` -> `x < 100`.
- TEACH: ADMIT, persist True, rule-3f2cdb87516d1d84 (1 REPAIRED held-out defect +
  1 PRESERVED held-out defect, 24 programs executed).
- REPLAY (same process): `PASS__REPLAYED_AND_REPAIRED`; repaired real file
  `fresh_module.py` ->  `fresh_module.py` test in a real subprocess: PASS.
- FRESH-PROCESS REPLAY: completely fresh process loads ONLY the on-disk rule (1 rule),
  replays on a never-taught fresh defect — `PASS__REPLAYED_AND_REPAIRED`; real
  subprocess test: PASS.
- The teaching pair was never used again; the rule transferred to a fresh defect in
  a fresh file with a different function name.

What this does and does not prove:
- PROVEN: the snippet-level code-repair generalization path generalizes to fresh
  defects on REAL files and PERSISTS across processes — the strongest honest evidence
  yet for the §14 blocker. The plan machinery itself is unchanged (scan/act/verify).
- NOT PROVEN: file-edit actions through the perfect-algorithm SCAN (§17's measured
  OPEN) — that env-class shape remains unbuilt. What this probe closes is the
  "learn once -> replay on fresh defect -> persistence across sessions" chain, which
  is the capability the mission needs for code-repair.
- Carried-model generalization across content is STILL 0 edges / stale priors.

## 19. Web instant-knowledge tier measured live (2026-11-23)

`jit_knowledge_v1.resolve` (the web tier) was run once, live, in this sandbox:
- Query: "how to use tar archive" -> PASS__JIT_KNOWLEDGE_RESOLVED; complete: True;
  document_count: 6; sources_answered: npm, pypi, github (kinds: code_host, package_registry);
  authority: EXTERNAL_PUBLIC_EVIDENCE_FETCHED.
- Nothing in this tier is counted as capability; it is external, completeness-gated
  (≥2 independent sources, ≥2 kinds), never a stand-in for a plan.

Knowledge layers now measured: (a) local tier (md docs + tool --help + man pages),
(b) web tier (npm/pypi/github), (c) admitted rules persisted to an inspectable,
deletable store outside the weights.

§6 honest status, restated: GUI/browser/OSWorld/SWE-bench/Terminal-Bench remain
NOT RUN and NOT claimed. Everything verifiable in this sandbox has been measured
and recorded across §6–§19. The standing mission and done criteria stand exactly as
they were at the start of this turn: the system does not claim §6.

## 20. .tar.bz2 archive goal — warm INSTANT_RECALL evidence added (2026-11-23, measured)

The last archive-class format without warm-replay evidence was `.tar.bz2`. Measured with
`unseen_tar_bz2_computer_probe_20261123.py`, same discipline:

- TEACH: pass, status PASS__PERFECT_ALGORITHM_RUN, **admit ADMIT 2/2**, persist True,
  77.7 s, content verified.
- COLD (B): pass, VERIFIED_NOT_PERSISTED, 80.4 s, content verified.
- WARM (B): **INSTANT_RECALL**, PASS__REPLAY_REACHED_GOAL, 0.113 s, content verified.
- CONTROL (A): INSTANT_RECALL, 0.116 s, content verified.

(bzip2's scan budget is a little slower than gzip's — compression cost is the honest
price, not a defect.)

Archive-class warm INSTANT_RECALL evidence now covers: .tar.gz (§7), .zip (§10),
.bz2 compressed target (§10), multi-file .tar.gz bundle (§13), .tar.bz2 (§20),
and decompress (§12); the hash direction §11; the cross-process persistence chain §15/§18.

## 21. Code-repair drive: one honest one-call flow (2026-11-23, measured)

The code-repair specialist path existed as direct calls (§18 probe). It is now a
one-call drive: `canonical/swe_kernel/code_repair_env_v1.py` —
`drive_code_repair(goal, demo, victims, fresh_source, fresh_oracle, fresh_probes,
fresh_test_files=None, memory_path_)` — that runs the full honest chain:

  one demonstrated (broken, fixed) lesson -> gate verdict on held-out fresh
  defects (REPAIRED + PRESERVED required) -> persist admitted rule -> replay on a
  fresh never-taught defect -> materialize the repaired file -> run the real
  failing test in a subprocess. One honest reward: if the fresh test passes, the
  receipt's authority is the specialist path's own gate; otherwise the receipt
  says so honestly.

Tests: 3/3 (real-file ADMIT + replay + real-test PASS; harmful lesson refused;
no-victims refused).

Honest statement of the §14-§18 chain: file-transform goals are closed by the
generic scan; code-repair-class goals are closed by the specialist twin with real
files, fresh-defect admission, persistence, and real-test replay verification.
The scan-level code-repair env remains unbuilt (§17's measured OPEN). §6 stays open.

## 22. Scan → known/unknown → gap → receipt: the one-call new-environment flow (2026-11-23, measured)

The owner's brilliant idea, taken literally: "scan everything in the environment,
retrieve from memory what is known and what is not, get the gap from instant
knowledge, and save only the important learning." §14–§21 built the pieces; this
turn builds the flow that actually carries the idea.

Built: `canonical/swe_kernel/environment_scan_know_v1.py` — `scan_and_know(root,
goal, ...)` — one call, no plan, no persist, no model, no network at decision
time (except allow_web=True, which is opt-in, gated, and labeled EXTERNAL).

What it does, in the order the idea demands:

  1. SCAN — bounded filesystem walk (file count, kind by manifest, layout,
     docs), never executes anything except the broker's declared runner.
  2. REMEMBER — consults the two stores read-only: the Perfect Algorithm's
     admitted rules + priors for this env family/kind, and the broker's
     evidence-keyed cache (Python run-tests contract), which re-executes to
     verify before use. Nothing is trusted blindly.
  3. FILL THE GAP — remaining questions are asked of the instant-knowledge
     tiers: local guides first (offline, completeness-gated), then the web,
     only when the caller opts in, only when the completeness gate passes.
     External knowledge is labeled EXTERNAL_PUBLIC_EVIDENCE_FETCHED and never
     counted as capability.
  4. REPORT — a checkpoint packet (goal + environment + checkpoint evidence +
     what remains unknown + the decision), in the shape the frontier research
     (EnvProbe, exploration checkpoints, selective memory, proactive retrieval)
     asks for: selective and goal-directed, not "learn everything".

What it refuses to do — and does all four honestly:
  - It does not plan or pick actions (Planning is the Perfect Algorithm's job).
  - It does not persist anything. The stores are written by their owners; this
    flow only reads them. The Perfect Algorithm's memory file is never touched.
  - It does not count the web tier as capability (gate refusal leaves the gap
    UNKNOWN by name).
  - It does not guess the contract. A missing answer stays UNKNOWN, named.

Tests: 10/10 (refusals by name; generic environment: scan, kind, docs,
local-guide answer, no-fabrication; Python broker path cold/warm in a child
process with a pytest-capable interpreter; honest refusal with no pytest).

Measured:
  - Cold: broker-verified, 2 passed, ENVIRONMENT_BROKERED, from_memory False.
  - Warm: re-verified by execution, ENVIRONMENT_BROKERED_FROM_MEMORY,
    from_memory True. The broker is never trusted blindly.
  - Web fill path: exercised once (allow_web=True). The gate REFUSED the thin
    external evidence (2 sources of one kind) — the question was left UNKNOWN
    by name, not filled with a confident guess. Wiring verified, gate held.

Design records (frontier inputs, never capability credit): EnvProbe (arXiv
2606.31422, Jul 2026) — probe only the critical belief fields, structural
terms > uncertainty; exploration checkpoints (2026) — separate exploration
from execution, require checkpoint evidence, gate on remaining unknowns;
selective memory (2026) — remember what matters, retrieve what is relevant,
trust the right source; proactive retrieval (arXiv 2604.20572, Apr 2026) —
identify the gap, retrieve when needed. All agree with §2: explore broadly,
persist narrowly, re-verify at use, get the gap from the right source.

Honesty: this is reconnaissance, not the scan-level code-repair env (§17
remains open), not a GUI/browser flow, not §6.

## 23. Scan-level code repair: the §17 gap, closed on the generic loop (2026-11-23, measured)

The §17 verdict named the honest gap: the generic scan loop honestly refused
code-repair goals (OPEN__NO_PLAN_AFTER_SCAN) because the file-transform world
has no file-edit actions and no test-verified oracle. This turn builds the
env that closes it, reusing the SAME generic machinery (`perfect_algorithm_v1.run`),
not the specialist twin.

Built: `canonical/swe_kernel/code_repair_scan_env_v1.py` — `CodeRepairEnv`:
  - real temp directory, real broken module, real failing test subprocess;
  - content-invariant textual edit actions (`fix_op:<old>|<new>` replaces every
    occurrence of <old> with <new>, wherever it appears) — a rule learned on one
    broken file transfers to any same-shape fresh file;
  - state = {content, passes} where `passes` is the REAL subprocess test verdict;
  - snapshot/restore round-trip the state observation (the same contract the
    file-transform env follows);
  - the same plan/admit/persist chain as every other goal family.

Measured (probe: `unseen_code_repair_scan_probe_20261123.py`):

  TEACH  PASS, LEARNED_AND_VERIFIED, ADMIT on 2 fresh variants (REACHED /
         NOT_REACHED — honest: the rule repaired the same-shape fresh defect
         and correctly did not break the correctly-guarded one), persisted
         rule ga-9f6b073481ad6a1c (plan [fix_op:-|+]), 6.3 s.
  COLD   PASS, VERIFIED_NOT_PERSISTED (fresh content, empty store), 6.2 s.
  WARM   INSTANT_RECALL, PASS__REPLAY_REACHED_GOAL, 0.011 s.
  CONTROL INSTANT_RECALL, 0.011 s.

Tests: 8/8 (env protocol, refusals, every-occurrence rewrite, snapshot/restore
round-trip, reset, meta hooks, content-invariant action space, and the full
teach→admit→persist→warm-replay chain on an unseen broken file).

Honesty: this is the generic scan closing the code-repair CLASS — one experience
building a plan rule admitted on fresh instances and replayed instantly. It is NOT
the §18/§21 specialist twin (which gates on the demonstrated pair); it is the
scan-level engine §17 found missing. §6 stays open and unclaimed: no GUI/browser,
no hard benchmarks, no carried-model claim.

## 24. The browser surface: bring-up and live-interaction probe (2026-11-23, measured)

§23 closed the scan-level code-repair class. The verdict doc still owed an
honest answer for the GUI/browser surface. This is that answer: the surface
is **brought up and driven**, not packaged, not benchmarked, not §6-claimed.

What was built/fixed this turn:

- Chromium build: `sh canonical/runtime/browser_launch_v1.sh 9222` — npm
  install `@sparticuz/chromium` + `ws`, decompress the bundled chromium from
  `bin/chromium.br` (brotli) + the al2023/sw tarballs, swiftshader ICD file,
  nohup headless=new on `--remote-debugging-port`. Chromium is live on 9222.
- Fixture page served over localhost (`canonical/runtime/browser_probe_v1.html`,
  served at `http://127.0.0.1:8791/probe.html`). The driver refuses `file://`
  (allowlist http/https/chrome), so a real HTTP server is required.
- Honest defect (uncommitted at first): `browser_v1.ensure()` refused loopback
  hosts — SPKI key-pinning is meaningless for plain-HTTP localhost, and the
  fixture could not be driven. Fixed with a loopback exception in `ensure()`:
  if every host is in {127.0.0.1, localhost, ::1}, take the plain start path.
- The repo's own CDP driver (`osworld_v21_browser_cdp_v1`) drives the page;
  `browser_v1.state()` reports it (title/text/elements).

Measured (probe: `browser_probe_20261123.py`, live Chromium + fixture, 17 s,
zero model calls, zero network beyond localhost):

  - browser_up: already running (ensure → start)
  - load_page: ok (3 interactive elements — click me / input#txt / go)
  - click_increments_counter: CLICK_TEXT "click me" → counter 0 → 1 (live DOM)
  - fill_reverses_output: FILL input#txt "abc" → reversed output "cba"
  - submit_reports_submitted_text: CLICK_TEXT "go" → done span "submitted:abc"
  - late_element_appears: the 800 ms timeout element appears (APPEARED_LATER)
  - refusal_is_honest: an op for a nonexistent element raises (Locator click
    timeout) — no silent success

  All 8 checks PASS. State()'s re-NAVIGATE resets the page (documented), so
  live-page verification reads the DOM directly (fresh CDP connection), never
  via state() after an op.

Honesty: the browser is **interfaced and live-tested**: navigate + click +
fill + submit + a post-timeout element, driven by the repo's own CDP driver
through `browser_v1.act()`, verified by execution against the live page.
This is NOT §6: no hard benchmark, no video generation, no CLI coding-agent
prompts, no on-mission-pass, no GUI-history close-out. The §6 gate stays
OPEN and unclaimed. It is the browser-half of the §0/§6 enumeration
("about machine-used web", "over ") — nothing beyond that is claimed.

## 25. The §22 flow on a live page — scan → remember → report (2026-11-23, measured)

The owner's brilliant idea, taken literally end to end: "scan everything in the
environment, retrieve from his memory what he knows and what he doesn't know,
get the gap filled instantly, save only the important learning." §22 built that
flow for filesystem environments. This turn extends it to the environment class
that was still unreached — a live page — and records it honestly.

Built (minimal: one shared flow, one new branch, no new learner/store/planner):

- `environment_scan_know_v1.scan_and_know(..., page_url=...)` — when page_url is
  given, the flow REUSES the same validation → scan → memory → questions →
  gap-fill → receipt spine. The filesystem path is byte-for-byte unchanged
  (10/10 filesystem tests stay green; 15/15 total).
- Page-mode refusals (by name, never fabricated):
  REFUSE__PAGE_SCHEME_UNSUPPORTED (file://, chrome://, garbage — before any
  browser work), REFUSE__PAGE_UNLOADABLE (a page that does not load — the
  reason is recorded, no page evidence is recorded).
- Page-mode questions:
  Q1 (what is this thing) — KNOWN_SCAN: title, URL, text chars, element count.
  Q2 (declared requirements) — KNOWN_SCAN: a page declares no manifest; the
  affordances ARE the declared surface, and are reported as such.
  Q3 (what runs/checks it) — KNOWN_SCAN: a page has no runner contract; the
  affordances are its only declared execution surface, reported by label.
  Q4 (what counts as success) — UNKNOWN by name: a page declares no contract.
  Menu READ from the page's own declared surface; never invented.
- The flow never persists (persist reported NONE), never re-plans, never
  counts the web tier as capability. Memory is read-only (rules + priors for
  the goal family / browser_page), exactly as in filesystem mode.

Measured (probe `browser_scan_know_probe_20261123.py`, self-contained ephemeral
localhost fixture, live Chromium, 12/12 PASS, ~4 s, zero model calls):

- COLD (empty store): verdict OPEN__GAP_REMAINS; root = the page URL; title
  "Browser Scan Probe" (content-exact against the live fixture); affordances
  ["click me", "your name", "go"] (element labels match the fixture); Q4
  unknown by name; memory empty.
- WARM (memory seeded through the real generalize/remember/save_memory path):
  rule recalled (ga-d9c97c401e1eb43b, scope browser_page/generic) — the flow
  REMEMBERS, nothing re-trusted (scan evidence identical to cold).
- REFUSALS: unroutable page → REFUSE__PAGE_UNLOADABLE with reason
  (never-fabricated); no page evidence recorded (page is None); empty goal
  → REFUSE__EMPTY_GOAL before any scan.

Honest statement: the scan→remember→report flow now works on BOTH environment
classes (filesystem §22; live page §25), and the page is the first environment
class where Q4 (success contract) is honestly nameable as NOT DECLARED by the
environment — the flow must then be handed a contract by the caller (or the
frontier instant-knowledge tier) rather than fabricating one. This is not
§6: no benchmark, no GUI-automated close-out, no carried-model claim.

## 26. The three mission questions, adjudicated with this record (2026-11-23)

The mission statement embeds three questions. They are RE-ADJUDICATED here with
the new page-scan evidence, closing the record in the same sense §1–§3 do —
not restating as a capability claim.

Q1 — Per-env scan + instant-knowledge recall vs goal-directed narrow persistence.

  ANSWER: BOTH, layered — the broad scan, the narrow persistence. The scan
  learns broadly (filesystem walk: kind/layout/manifests/docs, plus the §22
  checkpoint packet; browser page: title/affordances), the persistence is
  narrow (the admitted generalized rule + priors, never the raw trace — §2 of
  the mass probe). Instant knowledge is never counted as capability: it is
  read-only and gated.

Q2 — Save exact instance actions vs generalizations.

  ANSWER: GENERALIZATIONS ONLY. Never the raw trace. The admitted rule is a
  generalization over the plan sketch + goal family + evidence hash (§2,
  Q-Q2 in the mission doc, mass probe: rule replay + carried-model walk across
  starts; the raw trace is hashed as evidence only). A raw trace of a page is
  nothing — pages change; a raw trace cannot be replayed. The page-mode
  flow inherits this discipline unchanged: the scan REPORTS; admission persists
  the generalization; nothing raw is saved or served.

Q3 — Learn everything per-environment and eventually generalize vs only the goal.

  ANSWER: BROADLY LEARN, NARROWLY PERSIST, TRANSFER WITHIN KIND ONLY. The
  per-env scan learns the full reachable frontier (or page affordances);
  the admitted rule (goal-directed, narrow) is the only narrow persistent
  slice; the broadly-learned model is REUSED by same-kind transfer (the
  carried walk). Cross-kind: 0 + 0 priors carried, by design (priors keyed by
  env_kind — that is the designed refusal, not a bug).

  Non-claim: the carried-model walk is KIND-scoped. "Eventually generalize
  everywhere" is NOT claimed or evidenced; it remains the open mission question
  the §6 gate is built for.

## 27. Cross-kind transfer is the standing OPEN question (2026-11-23)

The one place the agent does NOT yet generalize across environments: priors
are keyed by env_kind. Towers→grid and grid→towers both carried 0 priors
(recorded §1 of the mass probe). The chain of evidence that §25 adds: a page
environment exposes NO reusable transition model — a page's affordances are
NOT a kind-invariant state graph — so a browser rule is honestly NOT
replayable on filesystem environments and a filesystem rule is honestly NOT
replayable on a page. Cross-kind transfer is not a refusal bug; it is the
designed boundary of what "learn" means here.

What IS adopted: the same store, the same flow, the same rule schema across
kinds. The store is the ONE reusable object; the rule is the ONE generalization
format; the receipt discipline (scan → memory → gap → report) is the same on
every environment class. That is the honest claim.

## 28. The Perfect-Algorithm loop on a live page: plan→act→verify→admit→persist→warm replay (2026-11-23, measured)

The browser surface (§24) and the scan→remember→report flow (§25) prove the page is
bring-up-able and scannable. This turn proves the LOOP itself on a page: the same
generic chain every env uses — cold scan -> plan -> act -> verify -> admit on fresh
variants -> persist -> warm replay — over a live page.

Built: `canonical/swe_kernel/browser_page_env_v1.py` — `BrowserPageEnv`:
  same env protocol as the scan env (reset/act/state/snapshot/restore/action_names),
  same flat-heuristic honesty, same generic loop (`pa.run`).

Honesty contract (and one defect found by measuring):
  - state() reads the live page through a FRESH CDP connection — never a
    re-navigation (which would discard the clicks/fills the env performed).
  - reset/restore = navigate fresh, then RE-APPLY THE RECORDED INPUT VALUES
    (the form fields are the one genuinely replayable piece of page state;
    everything derived — the counter, the done line — is re-derived by the
    same actions, never trusted). An earlier version of this env restored
    by blind navigation, which made the fill step invisible to the scan and
    forced the honest cold path to re-derive everything — caught by
    measuring, fixed by recording the form's live values in state.
  - actions are the caller's declared surface: "click:<text>", "fill:<sel>:<value>",
    "press:<sel>:<key>" — nothing invented.
  - The goal predicate is caller-provided; default refuses.
  - Page kind is "browser_page"; priors keyed by kind, like every other env.

Measured (probe `unseen_browser_page_probe_20261123.py`, four ephemeral localhost
fixtures with the SAME DOM structure and DIFFERENT content — title/h1/intro differ,
affordance labels and selectors are invariant; the goal: fill #txt with "abc" and
submit the form — content-exact predicate over the live page, never a re-read):

  TEACH   LEARNED_AND_VERIFIED, ADMIT 2/2 (both fresh variants REACHED),
          persist True — rule ga-70024af2f8f0851d, plan
          ["fill:#txt:abc", "click:go"], 85 s.
  COLD    VERIFIED_NOT_PERSISTED — fresh fixture page D, empty store — PASS,
          plan ["fill:#txt:abc", "click:go"], 72.6 s.
  WARM    same fixture D, memory seeded by TEACH — INSTANT_RECALL,
          PASS__REPLAY_FROM_MEMORY (rule replay, 5.0 s; verified by execution;
          nothing trusted).
  CONTROL fixture A, same memory — INSTANT_RECALL, PASS__REPLAY_FROM_MEMORY,
          5.0 s.

The 0.3-0.4 s/step and ~70-85 s cold/teach cost is the honest price of live page
loads (restore = fresh navigation + input-value replay, state = fresh CDP read);
warm replay is 5 s with all evidence verified by execution inside pa.run.
NOT §6: no benchmark, no video capture, no cross-kind transfer, no GUI-history
close-out. Cross-kind (filesystem <-> page) remains the §27 open question and
is untouched by this turn.

## 29. Multi-page browser workflows + the §6-hard-benchmark research (2026-11-23, measured)

§28 measured the one-page loop. A real computer task crosses pages: write data,
submit, land somewhere else, verify the result. This turn measures the same
loop over a two-page fixture (form on page A; redirect to result page B via the
URL query param; the live page's text must say "submitted:abc") — the same
env, the same admission/persistence chain, no new learner.

Mesasured (probe `unseen_browser_multipage_probe_20261123.py`, same-content-
invariant discipline as §28; four fixtures; cold scan / admission on 2 fresh
same-shape variants / persist / warm / control):

  TEACH   LEARNED_AND_VERIFIED, ADMIT 2/2 (both fresh variants REACHED), persist True,
          rule ga-70024af2f8f0851d, plan ["fill:#txt:abc", "click:go"], 132 s.
  COLD    VERIFIED_NOT_PERSISTED — PASS, plan ["fill:#txt:abc", "click:go"], 115 s.
  WARM    INSTANT_RECALL — PASS__REPLAY_FROM_MEMORY, 9.1 s, verified by execution.
  CONTROL INSTANT_RECALL — PASS__REPLAY_FROM_MEMORY, 9.0 s, verified by execution.

Honesty note (a defect class found by measuring, fixed before this verdict):
the multi-page probe forced a two-level restore bug to the surface. The env's
restore() navigated to the URL the page was at WHEN THE SNAPSHOT WAS TAKEN
(token["url"]), which after the form's redirect is page B — the scan would be
restored to the wrong page and could never re-reach the goal. The env's identity
is the fixture it was built with (page A); restore now ALWAYS navigates there
and re-applies the recorded form-field values, ignoring any token url. Re-run of
the single-page probe (§28) after the fix: TEACH/COLD/WARM/CONTROL all still PASS.

Benchmark research (mandatory, web, 2026-11): the standing hardest open benchmarks
are ARC-AGI-3 (interactive games, 0.51% March 2026 -> 62.7% Sept 2026, still unsaturated),
SWE-bench Pro (real GitHub fixes; public split topped at 61.5%), Terminal-Bench 4.1
(66 professional tasks; 4.1 hardened verifiers, CPU-only 63-task subset, top
~65.8% across harnesses), OSWorld 2.0 (long-horizon computer use; top binary
20.6%, partial 54.8%). Honestly not runnable in this sandbox:
  - Terminal-Bench 4.1 is Harbor/containerized (harbor-framework/terminal-bench,
    huggingface datasets, GPU-less variants) — not in this allowed-host reach,
    and the harness is not our system (the system it must evaluate would be).
  - SWE-bench Pro splits are private/Scale-AI — not fetchable here.
  - ARC-AGI-3 is an interactive-game harness (Kaggle/ARC-Prize) — not fetchable
    here, and the system has no visual-game-agent harness.
  - OSWorld 2.0 is a real-OS GUI harness (os-world.github.io) — not fetchable here.
  - ARC-AGI-3 / OSWorld are designed around LLM agents.

Honest verdict (recorded and unchanged): the §6 gate stays OPEN. The four-
benchmark list is recorded as not-reached, not claimed. What this turn adds is
the honest multi-page browser loop: the agent now navigates across pages with the
same loop and replays its admitted rule instantly (9 s) on a fresh same-shape
workflow — the browser-half of OSWorld-class tasks, measured, honestly, without
claiming the OSWorld verdict.

## 30. The carried-model walk on live pages — measured honestly, zero-scan warm path (2026-11-23)

§28/§29 measured the Perfect-Algorithm loop on live pages — and its WARM and
CONTROL arms both passed via instant RULE REPLAY (the stored plan executes on
the fresh fixture, the goal is observed). The carried-model WALK — the
within-kind transfer mechanism that §27 measured on the 3-peg stack (6/12 warm
arms reached the goal through it) and that the archives measured honestly
(§10: refused 0 edges across content — state_key keys are content-derived) —
has never been measured on a live page. This turn is that measurement.

Design (the §10 priors-only construction, honestly): TEACH on fixture A with no
fresh instances offered — admission MUST REFUSE (no fresh to replay), so no
rule is persisted; the learned PRIORS (transition model) are persisted, which
is the durable form of one experience. The two warm arms each run against their
own read-only copy of that memory:

  WALK-D   fresh fixture D (different text/h1/title) — honest expectation: the
           carried model refuses (0 edges, content-derived keys) -> full scan
           re-derives -> PASS.
  WALK-A   fixture A (same content) — honest expectation: the carried walk
           reaches the goal edge-by-edge, verified by execution -> PASS.

A probe defect found by measuring, fixed before this verdict: the walk arms
originally shared one memory file. WALK-D's full-scan path (which it falls
through to after the honest walk refusal) SAVES ITS OWN PRIORS — the arm's
full scan silently overwrote the shared memory's priors, so the carried walk
in the NEXT arm no longer had the TEACH model and explored 0 edges even on
the same content. The honest fix: each warm arm receives its own read-only
copy of the TEACH memory (shutil.copyfile per arm). The design is also true
of §10/§27: the walk arm's full-scan priors-save goes to the arm's own file,
never back to the teach store.

Measured (probe `unseen_browser_walk_probe_20261123.py`, fixture A/D same DOM
structure, different text content; cold scan budget 6; same discipline as
§28 — content-exact predicate, live page read every time):

  TEACH-NO-FRESH   PASS__PERFECT_ALGORITHM_RUN, LEARNED_AND_VERIFIED,
                  admit REFUSED, persist False, plan [fill:#txt:abc, click:go],
                  4 states / 8 transitions learned, 110.9 s.
  WALK-D (content B)  OPEN__CARRIED_WALK_FAILED honestly — 0 edges, 1 act call,
                  priors_used 8, cap 96 — then the full scan re-derived the
                  plan (same plan) and the run PASSED (VERIFIED_NOT_PERSISTED,
                  admission refused — no fresh instances offered), 124.2 s. Net: the carried walk does
                  NOT carry across content on a live page, exactly as §10
                  showed on the archives — the durable partner is the plan
                  rule, never the transition model.
  WALK-A (content A, CONTROL)  PASS__CARRIED_WALK_REACHED_GOAL — the carried
                  model re-verified 5 edges against the live page (8 act
                  calls, 2 resets), reached the goal, plan
                  [fill:#txt:abc, click:go], outcome CARRIED_MODEL_WALK_REACHED,
                  17.7 s — zero rule replay, zero scan, zero admission.

Honest status: the carried walk on a live page is a REAL zero-scan path — it
reaches the goal in 17.7 s vs. 110.9 s for TEACH cold and 124.2 s for WALK-D,
and it is a HYPOTHESIS CHECKED BY EXECUTION, never trusted: every edge it
explored was re-verified against the live page, and the walk returned nothing
but what the page said. It carries within identical content only; across
content it refuses honestly (0 edges), and the scan re-derives. That is the
same split §10/§12/§13 measured for archives and towers: the plan rule
generalizes (admitted on fresh variants), the transition model does not.
NOT §6: no benchmark, no cross-kind transfer, no GUI close-out. Same honest
boundary.

## 31. The carried-model walk over a two-page workflow (2026-11-23, measured)

§30 measured the carried walk on a single live page. §31 extends the same
honest priors-only construction (§10/§30) to the §29 multi-page fixture — a
real cross-page carry: fill page A, submit, redirect to page B, verify
"submitted:abc" in the live page text after landing.

  TEACH-NO-FRESH  PASS__PERFECT_ALGORITHM_RUN, admission REFUSED (no fresh
                 instances offered), persist False, 4 states / 8 transitions,
                 145.7 s.
  WALK-D (content B)  OPEN__CARRIED_WALK_FAILED honestly — 0 edges, 1 act call,
                 priors_used 8, cap 96 — then the full scan re-derived the
                 plan (same plan) and the run PASSED (VERIFIED_NOT_PERSISTED),
                 155.8 s.
  WALK-A (content A, CONTROL)  PASS__CARRIED_WALK_REACHED_GOAL — the carried
                 model re-verified 5 edges against the live page (8 act
                 calls, 2 resets), reached the goal across the redirect
                 (browser navigated a.html -> b.html?name=abc), plan
                 [fill:#txt:abc, click:go], outcome CARRIED_MODEL_WALK_REACHED,
                 24.5 s — zero rule replay, zero scan, zero admission.

Same honest split as §30 and §10: the carried walk reaches the goal within
identical content (24.5 s, no scan, no admission), refuses honestly across
content (0 edges, full-scan fallback). The redirect does not break the walk:
the cross-page carry rides the same live-page verification (every edge
re-executed against the live page; the redirect is a page navigation, not a
trusted transition).
NOT §6: no benchmark, no cross-kind transfer, no GUI close-out.

## 32. Cross-kind refusal on the live page — honest measurement + honest save-path defect (2026-11-23)

§27/§26 verdict: transfer is within-kind only — priors and rules are keyed
by env_kind. That verdict had never been measured against a REAL store on the
page side. §32 does it: the page arm reads the persistent
`computer_file_ops` store (canonical/astra_runtime/state/
PERFECT_ALGORITHM_MEMORY_V1.json — a real learned transition model written
by the real archive probes, 0 rules, 1 kind of priors) and runs a fresh
browser_page fixture against it.

Measured (probe `unseen_browser_crosskind_probe_20261123.py`, fresh fixture
D, copied store, honest bytes-vs-bytes integrity check):

  memory_lookup matches: 0 (fs store never matches the page kind).
  warm_walk: absent (no priors recorded for browser_page).
  scan priors adopted: 0.
  fs store bytes: preserved exactly (no overwrite, no rewrite).
  Run outcome: PASS__PERFECT_ALGORITHM_RUN, VERIFIED_NOT_PERSISTED (126 s,
  4 states, cold scan) — honest admission (no fresh instances offered).

Honest defect found by measuring, fixed before this verdict:

1. LOAD side was already honest (a corrupt/legacy-schema store is refused,
   never silently rewritten by load_memory).
2. SAVE side was NOT: the §32 run loaded the legacy fs store
   (missing `schema`), load_memory refused it, and the full loop then
   persisted a fresh browser_page memory into the file — DROPPING the fs
   store's own priors (the bytes on disk were silently replaced). That is
   exactly the §2 honesty rule — a corrupt store is a refusal, never a
   reset — violated by the persist path.

Fix (canonical/swe_kernel/perfect_algorithm_v1.py):
  - save_memory: a refused memory is NEVER overwritten; the bytes on disk
    are preserved; the receipt names the refusal.
  - run() SAVE section: if the loaded memory reports refused, the run
    records save_priors + save as REFUSED__MEMORY_REFUSED and returns
    without touching the file (no rule, no priors, no rewrite).
Behavior on the fixed path: the §32 probe's fs store stays byte-identical
(measured: PASS), and the honest receipt names the refusal — a store that
failed to load can never be silently destroyed by a full run.

Honest status: cross-kind refusal is now MEASURED on a live page, not just
designed. §2's add/remove-without-retraining test now also holds against
the persistence path: a corrupt or legacy store is never silently rewritten.
NOT §6: no benchmark, no cross-kind transfer (still honestly absent), no
GUI close-out.

## 33. Browser-kind cross-process persistence (2026-11-23, measured)

§15 measured cross-process persistence for a filesystem kind: TEACH in one
process writes the store, a fresh process reads only the disk file and gets
INSTANT_RECALL. The browser kind was never measured across the process
boundary. §33 is that measurement — same pattern as §15, fixtures/servers
parent-owned so the children share them:

  Parent: fixtures A, B, C, D (shared HTTP servers, parent-owned).
  CHILD_A: TEACH on fixture A, admission on fresh B,C (admit ADMIT) ->
           rule ga-70024af2f8f0851d persisted to disk (155 s).
  CHILD_B (fresh process): fresh fixture D (different content) ->
           INSTANT_RECALL, PASS__REPLAY_FROM_MEMORY, replay rule
           ga-70024af2f8f0851d, scan_states None (zero re-scan), 12.6 s.

Honest disk check: the store holds schema PROJECT_BRAIN_PA_MEMORY_V1, 1 rule
(scope env_kind=browser_page, goal_family=generic) and 1 kind of priors
(browser_page). The warm phase never re-scans or re-derives: the disk-backed
store is the durable, cross-process carrier, exactly as §15 measured for the
filesystem kind.

NOT §6: no benchmark, no new mechanism, no cross-kind transfer. The browser
direction's durability half is now measured end-to-end: learn once (page) ->
persist to disk -> fresh process replays instantly, content observed live.

## 34. Multi-page cross-process persistence (2026-11-23, measured)

§33 measured cross-process persistence for the single-page browser kind.
§34 is the multi-page cell: TEACH on fixture A (a real cross-page carry —
form on page A redirects to page B via `b.html?name=abc`) in one process;
a fresh process B then replays the admitted rule against a different-content
workflow — the mission's literal "learns it permanently" claim for the
redirect shape.

  CHILD_A (process A): TEACH on fixture A, admission on fresh B,C ->
           ADMIT, rule ga-70024af2f8f0851d persisted to disk
           (schema PROJECT_BRAIN_PA_MEMORY_V1, 2423 bytes) — 194.1 s.
  CHILD_B (process B, fresh): fresh fixture D (different content) ->
           INSTANT_RECALL, PASS__REPLAY_FROM_MEMORY, rule
           ga-70024af2f8f0851d, scan_states None (zero re-scan), 17.6 s.

Honest disk check: the store holds 1 rule (scope env_kind=browser_page,
goal_family=generic) and 1 kind of priors (browser_page). The warm phase
never re-scans or re-derives. The redirect is a live page navigation, not a
trusted transition: the warm phase's "PASS__REPLAY_REACHED_GOAL" is
observed by execution — the predicate re-reads the live page after the
redirect, in the fresh process.

NOT §6: no benchmark, no new mechanism. The browser direction is now
measured end-to-end in both shapes (single-page §33, multi-page §34).

## 35. Affordance discovery on the live page — honest derivation, not fabrication (2026-11-23)

§22/§25 doctrine: "scan everything in the environment." The loop itself still
used a caller-declared action surface (the fill value is goal-specific). The
recon layer (environment_scan_know_v1) already reads the DOM and reports
affordances as a receipt — but nothing in the loop discovered the surface.
§35 adds exactly one piece, and nothing more:

  BrowserPageEnv.discover_affordances() — re-reads the live DOM on every
  call and derives an honest receipt:
    - clicks: "click:<label>" for every visible button/link/[role=button]/
      [role=link] with a non-empty label — value-free; the label IS the text
      the env would click (the exact CLICK_TEXT op).
    - inputs: observation-only entries (tag/type/placeholder/name/aria) —
      the value is goal-specific and is NEVER minted as a fill action here;
      the selector is caller-declared (the live read does not carry ids).

Measured (probe `unseen_browser_affordance_probe_20261123.py`, live page):

  Fixture A: clicks ["click:click me", "click:go"], 1 input observed
           (placeholder "your name", tag input, type text; no value/sel
           minted), title "Discover A".
  Fixture D (different content): same clicks (content-invariant structure),
           title "Discover D" — the discovery tracks the live DOM, never a
           stored fixture.
  Empty page: clicks [], inputs [] — honest, not fabricated.
  Declared action surface: unchanged (action_names() intact).

Honest boundary: discovery is a receipt, not an authority. Fill actions
remain caller-declared (the value is goal-specific and is never minted);
the env still acts only on caller-declared actions. The honest §25 split
(scan = affordance map; act = caller-declared) is unchanged — this turn only
makes the affordance map derivable at runtime. NOT §6: no benchmark, no
cross-kind transfer.

## 36. Carried-walk durability across the process boundary — measured (2026-11-23)

§30 measured the carried-model walk in ONE process (TEACH-NO-FRESH -> disk
priors-only memory -> WALK-D refuses honestly across content -> full scan
re-derives -> PASS; WALK-A walks the carried model -> PASS). §33/§34 measured
cross-process durability for RULE REPLAY (single-page and multi-page
redirect). The carried-walk path — the within-kind transfer mechanism itself —
had never been measured across the process boundary. §36 closes exactly that
gap: same TEACH-NO-FRESH protocol, same honest refusal/walk expectations, but
the WARM arms now run in a FRESH process reading only the disk file.

Probe: `unseen_browser_walkxcr_probe_20261123.py` (live page, parent-owned
HTTP fixtures, children never own servers).

  CHILD_A (process A): TEACH-NO-FRESH on fixture A -> REFUSED admission
           (no fresh instances) -> priors persisted to disk
           (schema PROJECT_BRAIN_PA_MEMORY_V1, rules=0, 8 priors rows) — 138.3 s.
  CHILD_B (fresh process): WALK-D on fresh fixture D (different content) ->
           honest expectation met: walk_status OPEN__CARRIED_WALK_FAILED,
           walk_edges 0 (content-derived keys do not carry), priors_used 8,
           full scan re-derived (scan_states 4) -> PASS,
           outcome VERIFIED_NOT_PERSISTED, 149.4 s.
  CHILD_C (fresh process): WALK-A on fresh fixture A (same content) ->
           walk_status PASS__CARRIED_WALK_REACHED_GOAL, outcome
           CARRIED_MODEL_WALK_REACHED, walk_edges 5, walk_act_calls 8,
           scan_states None (zero re-scan) -> PASS, 25.1 s.

Honest disk check: the store holds schema PROJECT_BRAIN_PA_MEMORY_V1, 0 rules
(no admission without fresh instances), 8 priors rows (browser_page). The
warm arms re-read the disk file — no in-memory copy. The carried model is
the one thing that survives the boundary without a rule: the page's
transition keys are content-derived, so the same-content instance still walks,
the different-content instance honestly refuses and re-scans.

NOT §6: no benchmark, no new mechanism — the carried-walk path is the same
code, same honesty, same 0-edge refusal as §30, now proven durable across
the process boundary. §6 remains OPEN; this is honest §3 evidence, not a §6
claim.

## 37. Multi-page carried-walk durability across the process boundary — measured (2026-11-23)

§36 closed the single-page cell (TEACH in process A -> disk priors-only
memory -> fresh processes B/C replay from disk). §33/§34 measured RULE REPLAY
durability for the redirect shape. §37 closes the redirect-shape cell: §31's
honest priors-only construction over the two-page workflow (fill page A ->
redirect -> verify page B), with the WARM arms running in FRESH processes
reading only the disk file.

Probe: `unseen_browser_walkxcr_multipage_probe_20261123.py` (live page, parent-owned
HTTP fixtures, children never own servers, wait_s=0.7).

  CHILD_A (process A): TEACH-NO-FRESH on fixture A's page A -> REFUSED
           admission (no fresh instances) -> priors persisted to disk
           (schema PROJECT_BRAIN_PA_MEMORY_V1, rules=0, 8 priors rows) — 173.4 s.
  CHILD_B (fresh process): WALK-D on fresh fixture D (different content) ->
           walk_status OPEN__CARRIED_WALK_FAILED, walk_edges 0 (content-derived
           keys do not carry), priors_used 8, full scan re-derived
           (scan_states 4) -> PASS, outcome VERIFIED_NOT_PERSISTED, 191.8 s.
  CHILD_C (fresh process): WALK-A on fixture A (same content) ->
           walk_status PASS__CARRIED_WALK_REACHED_GOAL, outcome
           CARRIED_MODEL_WALK_REACHED, walk_edges 5, walk_act_calls 8,
           scan_states None (zero re-scan) — across the cross-page redirect —
           35.1 s.

Honest disk check: schema PROJECT_BRAIN_PA_MEMORY_V1, 0 rules (no admission
without fresh instances), 8 priors rows (browser_page). The fresh processes
re-read the disk file — no in-memory copy. The redirect is a live page
navigation: the warm walk re-verifies each edge by live page state, never
trusts the stored row as fact (§27 honesty, unchanged).

NOT §6: no benchmark, no new mechanism. The carried-walk durability matrix is
now complete in both shapes: single-page (§36) and multi-page redirect (§37),
fresh process replays of the disk-loaded priors, same-content walk reaches the
goal, different-content honestly refuses and re-scans. §6 remains OPEN; this is
honest §3 evidence, not a §6 claim.
