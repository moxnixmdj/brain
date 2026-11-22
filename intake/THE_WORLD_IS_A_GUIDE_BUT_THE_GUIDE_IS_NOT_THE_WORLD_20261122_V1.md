# The world is a guide, but the guide is not the world — what the owner's new idea is really proposing, measured against the tree and the frontier

**2026-11-22 · branch `arena/67c67d7e-brain` · Authority NONE__PRODUCER_RUN_SANDBOX · model calls 0 · network 0 at measure time (the one live read below is marked as such)**
**Code: `canonical/swe_kernel/the_environment_broker_v1.py` · tests `canonical/tests/test_the_environment_broker_v1.py` (9 passed) · receipts `intake/RECEIPT_WORLD_BROKER_{COLD,WARM}_20261122_V1.json`**

Requirement restated: own model; zero runtime model calls; parameters never a fact warehouse; knowledge in an
inspectable store written from single experiences; research before build; first principles; the best part is no
part; honest verified/unverified/failed; one branch; no §6 claim. The §2 contradiction is resolved as in the
global law: **parameters hold computed mechanisms only; persistence lives in the external store; a fact may be
added/removed without retraining; anything else is forbidden.** Nothing below changes that boundary.

---

## 1. The idea, stated exactly as given

> A perfect algorithm. It goes into any new arbitrary environment, knows nothing, and its whole job is to ask
> the right questions and know everything it should know — from instant knowledge and the web, because in
> today's world everything already has a guide. Should it learn everything, or only what it needs? What should
> it save, what should it generalise, what is experience vs a dumb recording? Is it goal-directed, or should it
> eventually learn everything and generalise later?

Four questions live in there. All four have been asked in this tree before, and three of them already have
measured answers. This round adds the missing link and marks the one thing that is genuinely unproven.

---

## 2. What the tree already holds (so nothing here is rebuilt)

### 2.1 The owner's scan→retrieve→fetch loop — built, and measured, on 2026-11-21
`canonical/tools/scan_retrieve_fetch_v1.py` + `intake/SCAN_RETRIEVE_FETCH_20261121_V1.md`:

| visit | host | memory | probed | from memory | learned | time |
|---|---|---|---|---|---|---|
| 1 cold | `/usr/bin`, 635 names | empty | 635 | 0 | 429 | 10.99 s |
| 2 warm | same | 429 records | 206 | 429 | 0 | 6.44 s |
| 3 busybox | `/usr/bin` + 401 applets | 429 | 607 | 429 | 165 | 9.57 s |
| 4 busybox-only | 9 names, GNU memory | GNU | 9 | 0 | 9 | 0.118 s |

Findings that decide the design, all measured: (1) the cache key must be `(content-digest, invoked-name)` —
635 names → 481 distinct files, and `xz` vs `unxz` are byte-identical with opposite behaviour; (2) a printed
option is a modifier, not an action: 164 catalogue options run against a real repo/archive/patch, 80 accepted,
**0 changed a byte** (`THE_REPERTOIRE_IS_A_QUERY_20261129_V1.md`); (3) the memory stores a *typed fact about a
program at a content*, never a chain, an order, or an example — and it transfers to foreign hosts (busybox: 4/4
round trips, 0.118 s); (4) 206/635 programs answer `--help` with nothing legible — reported, never guessed.

### 2.2 goal-directed beats learn-everything — already measured
`canonical/tools/cost_to_learn_a_host_v1.py` + `intake/RECEIPT_COST_TO_LEARN_A_HOST_20261121_V1.json`:
**LEARN_EVERYTHING** runs every executable on a host and was killed by the OOM killer (exit 137, twice);
**GOAL_DIRECTED** runs only the programs whose own name can produce the wanted type — to find `gzip` it probed
**1 of 635**. The everything-sweep is not merely slower; it is unsafe and it cannot terminate. Combine with
what the host census already says (`/usr/bin` 635 names = 481 files; the catalogue re-derives in 46.6 s, 0
parameters), and "learn the world first, generalise later" is not a candidate design.

### 2.3 The web channel — measured, and deferred on evidence
From the 2026-11-21 instruments: asking the host costs **6.78 ms** vs **255.2 ms** for the web; of the
7,432 man-page citations on this host, zero resolve to files present locally. The web is strictly the
fallback. **No web retrieval mechanism has ever been run in this tree.** This document does not claim one.

### 2.4 The verdict docs that already exist on the user's exact question
- `INSTANT_LEARNING_IS_RETENTION_NOT_IDENTIFICATION_20261118_V1.md` — instant learning is retention; it is
  solved and keeps. It says nothing about *which* thing to retain.
- `EXPERIENCE_SUPPLIES_ACTIONS_INTENT_SUPPLIES_SPECIFICATIONS_20261116_V1.md` — experience cannot supply the
  specification; a test, an exit code, or a stated intent can.
- `THE_GOAL_IS_THE_BOTTLENECK_20261116_V1.md` — the invariant bottleneck: an executable, falsifiable statement
  of the GOAL cannot be derived from the environment over a usable observable vocabulary.
- `LEARN_ONCE_KEEP_FOREVER_SERVES_A_TWENTIETH_OF_REAL_EDITS_20261116_V1.md` / `ONE_DEMONSTRATION_AMORTISES_A_SIXTH_OF_REAL_WORK_20261116_V1.md` — 84–88% of real commits have no sibling for a one-shot lesson to amortise onto.
- `THE_VERIFIER_IS_KNOWLEDGE_NOT_LEARNING_20261116_V1.md` — 0 of 40 real commits rejected by 188 confirmed laws;
  the judge that would let one experience be made permanent is mostly absent.
- `ONE_EXPERIENCE_IS_ENOUGH_ONLY_WITH_THREE_THINGS_20261113_V1.md` — named admission conditions for permanence.
- `WAKE_REPLAY_CLOSES_THE_LIBRARY_LOOP_20261112_V1.md` — closed-loop "wake" recall test of the library.

---

## 3. What the frontier did by mid-2026 (the design space the owner is describing)

- **OSWorld-Verified tops out ~85–90%** (Intelligence-Indeed 90.19%, 2026-07-25; above the 72.36% human
  baseline) — but those are short, narrow tasks. **OSWorld 2.0** (108 long-horizon tasks, June 2026): best
  binary completion **~44%** (Claude Opus 5, max effort), best partial 81.8% (Anthropic-reported, v2.1).
  Failure taxonomy: **final-state exactness 84.3–95.4%**, **premature stop / false done 75–83.3%**, GUI
  grounding 20–61%. The killer is not action vocabulary — it is *knowing when the goal actually happened*.
- **Pointer (2026-05-26)** — production OSWorld agent: "feasibility gate decides what not to attempt" (~1/13
  benchmark tasks deliberately impossible), GUI-first, then *superscore* analysis showing evaluator blind
  spots. Architecturally confirms: completion gating + refusal > more clicking.
- **Voyager** (Bo cooking, 2023–still canonical 2026) — executable skill library in external memory, iterative
  prompting with env feedback, skills transfer to new worlds and **to other agents**. Costs a GPT-4 call per
  revision — the shape, not the mechanism, applies here.
- **ContDa** — continual *documentation adaptation*: updates tool documentation from execution feedback as a
  parameter-free substrate for adapting to evolving toolsets; limited forgetting, no weight updates.
- **OpaqueToolsBench / ToolObserver** (arXiv 2602.15197, Feb 2026) — when docs underspecify tools, iteratively
  refining documentation from execution trajectories beats baselines by **18.6%** and cuts tokens 3.5–7.5×.
  The web page is the *prior*; execution feedback is the *posterior*.
- **TOOL-REX** (ICLR 2026) — document-expanded retrieval; models generalise better with structured docs
  (when-to-use, limitations, tags) than with raw docs. Retrieval quality is a documentation problem first.
- **Tool Documentation Enables Zero-Shot Tool-Usage** (2308.00675) — docs substitute for demonstrations;
  quality beats quantity up to ~600 tokens.
- **Continual learning at 2026 scale** — negative transfer hits hardest exactly on the hardest tasks
  (arXiv 2604.27003); self-evolving shared prompts/workspaces interfere with unseen tasks and no evaluated
  method achieves both stability and plasticity (arXiv 2610.25858). An append-only "everything I learned"
  memory is therefore not a free asset; it is a liability whose interest is interference.
- **Infinite-Parameter LLMs** (arXiv 2609.18842) — online Bayesian belief re-derived as the session proceeds;
  the frontier's shot at instant knowledge stays *trained*. Not available to us; noted as the boundary.

The pattern is unanimous: **documentation at test time works, but only when (a) the retrieval is scoped to the
task, (b) the retrieved procedure is exercised against the environment, and (c) the store keeps the procedure —
never the fact of having retrieved it.** All three map onto constraints already in this project's design; none
maps onto "download the web into parameters".

---

## 4. The verdict: real, not real, missing

### Real (verified, this branch or held receipts)
1. **Instant knowledge is real as retention and as re-derivation** — exact, reversible, auditable, zero
   parameters. The 2026-11-21 loop proves the host re-derives its own catalogue in 11 s cold, and transfers to
   a foreign host (busybox) in 0.118 s without a single carried bite.
2. **Goal-directed beats learn-everything** — 1 probe vs an OOM kill; not close.
3. **A verified, content-keyed external memory survives re-use** *only if it is re-checked, never believed*.
   This round's broker does exactly that (§5) — 9/9 tests including corrupt-cache and garbage-cache attacks.
4. **Small closed question sets are sufficient to enter an arbitrary environment that must run a suite** — the
   broker needed five questions, not an ontology.

### Not real (measured false or refused honestly)
1. **"Anything on a computer already has a guide, so reading it is enough."** False twice: 206/635 programs
   print nothing legible, and a guide describes the *documented surface only* — the 2026 failure data says the
   damage lives outside it (final-state exactness 84–95%; ToolObserver only pays after *execution*).
2. **"Learn the environment once, keep everything."** Unbounded, unstable (negative transfer), and 84–88% of
   real work has no sibling for a lesson to amortise onto.
3. **"Save the experience so it never happens again."** Traces don't transfer: 53.5% of action compositions go
   stale under change, 31.1% corrupt **silently**; byte-level experience is the one thing that provably does not
   transfer across releases of the same library.
4. **"The web already knows everything, so knowledge is free."** The web answers for *your version of X* only if
   pinned; unpinned, it confidently answers for a different one. And a page written for a human is not readable
   by this system with zero model calls outside a machine-readable tier — see §6.

### Missing (this is the honest frontier of the idea as of today)
1. **The question→web→verify→cache closure, live, on a machine-readable source.** PyPI's JSON API answers
   existence, exact version, requires-python, dependencies, and digests — **I read
   `https://pypi.org/pypi/tomli/2.0.2/json` in this round and it parses with one regex** — but no in-tree
   mechanism has ever fetched it. (This one read was performed via the research tool, not by a shipped path.)
2. **A selection policy for what a *future* goal will need** — store cache eviction/scoring, not append-only.
3. **Prose tiers.** README/man/forums need either computed mechanisms (unbuilt) or stay out, by name.
4. **Cross-environment semantics.** Everything here is byte-stream and process truth, not GUI effect-in-world;
   truth.achieved remains false.
5. **§6.** Zero-model-call performance on the hardest open tests (OSWorld 2.0, SWE-bench-class) is not claimed,
   not close, and not measured here.

---

## 5. What this round built (and what it cost)

`canonical/swe_kernel/the_environment_broker_v1.py` — the link the 2026-11-21 round left open: it turns
*scanned evidence* into *a verified world contract*, or refuses.

- **Five declared questions only**: LAYOUT (files) → INTERPRETER (requires-python, executed check) → RUNNER
  (candidate commands, **executed**, exit code is the verdict) → DEPS (the project's own declarations) →
  CONTRACT (goal `run-tests` or `REFUSE__GOAL_OUTSIDE_THE_CLOSED_CONTRACTS`).
- **No trust, ever.** On a warm run the cached runner is **re-executed**; a corrupt record is caught by the
  check, discarded, re-derived. Garbage cache file → cold path. Failed suite → refusal, and **nothing is
  cached** — a failure is not an environment.
- **Cache key = digest of evidence file *contents*, not paths.** Moving the tree does not fool it; editing
  `pyproject.toml` invalidates everything downstream (tested).
- Measured on a tree the broker had never seen (`hukkin/tomli@2.0.2`, fresh clone):
  **cold 0.54 s** → `ENVIRONMENT_BROKERED`, suite 14 passed; **warm 0.61 s** → `BROKERED_FROM_MEMORY`
  (derivation skipped; the check re-runs by design — a stale cache is one check stale, never forever).
  Corrupt-cache attack restored to exit 0 by re-derivation. Non-Python tree refused by name. The one
  interpreter-mismatch run (no pytest in `/usr/bin/python3`) refused honestly — see RECEIPT files.
- Cost honesty: warm is not faster here because pytest dominates (0.54→0.61 s). The cache buys **inspectable
  provenance + correctness**, not speed, until a fetch costs real time (e.g., a web or install step). Claiming
  a speed win would be fake.

9/9 tests pass (`canonical/tests/test_the_environment_broker_v1.py`).

---

## 6. The ultimate plan (the smart answer to the user's questions), with the rejected ideas

### The answers, directly

**Q — "Learn everything, or only what he needs?"** Goal-directed. Always. Keep a *fixed orientation scan*
(seconds, bounded, 635 names measured) that answers "what kind of place is this?" — that is not
"learning everything", it is a schema check. Beyond that: never cache anything the goal did not force you to
answer, and cache it only after the check that proved it.

**Q — "What should the memory hold?"** Exactly this shape, and nothing else:
```
key     = sha256(evidence-file-contents)             # never a path, never a name
value   = (contract, answers, the check that passed, when, from which evidence)
```
No action sequences, no bytes, no chains, no "I once saw…". Generalisation **is** the typed fact plus the
re-check — the 2026-11-21 loop proved that fact transfers to a host that shares zero bytes of code.

**Q — "How does it generalise instead of recording dumb experience?"** It generalises at write time by
*refusing the ungeneralisable*: a record is written only if it is re-checkable anywhere, and retired when the
re-check fails. A trace fails this test by construction. This is also the stability–plasticity fix from the
2026 literature: the store cannot forget what it cannot verify, because verification is part of read-back.

**Q — "Then what is the next step after scan/retrieve/fetch?"** This, in order, and nothing else:
1. **Goal → contract** (closed kinds; refuse otherwise). *Intent supplies specifications; experience cannot.*
2. **Locate** evidence (files → local docs → machine-readable web registries, **version-pinned to what the
   environment itself declares**; prose only with computed mechanisms, else refuse).
3. **Derive** candidate procedures (the project's own engine: trace-abduction repair, compositional search).
4. **Verify in the environment** (bounded execution; exit code / state check; the OSWorld 2.0 wall says this
   is the only kind of completion signal worth having).
5. **Cache** the record + the check, keyed by evidence digest.
6. **Re-check on every reuse.** Cache is a hint that survived one execution, never an authority.
7. **Out of scope → refuse by name.** "Run the suite" is in scope today; "make the bug fix" is not, yet.

### The rejected designs, and why

| Alternative | Why rejected |
|---|---|
| Learn everything eagerly (the sweep) | OOM-killed twice; unbounded; violates "no storage you can't re-derive" |
| Append-only experience store | Negative transfer (2604.27003); stability–plasticity failure (2610.25858); 53.5% silent stale actions |
| Keep action traces | 0/164 catalogue options changed a byte; 31.1% silent corruption under change |
| Web as oracle, unpinned | Version drift; confidently wrong; no machine check → no sound cache entry |
| Prose-web autonavigated with zero model calls | No measured mechanism in-tree; would be claimed without evidence. Machine-readable tier only |
| Bigger retrieval / embeddings | Adds a model-like dependency or a tuned artifact; solved nothing in the negative-transfer data |
| Chain/pipeline storage | Composed-skills-no-op result; plans are re-derived in 0.37 s — storing them is a bug multiplier |
| Merge web-2.0-style partial credit as success | OSWorld 2.0 checkpoints exist precisely because binary completion is what transfers to reality |

### Expansion-rule test for the one expansion involved — web as a runtime knowledge source
① What changes: nothing in the storage boundary — it stays external, digest-keyed, re-checked.
② What the old design already covers: the typed-record + re-check skeleton is identical; the web supplies *evidence*,
never *authority*. ③ Zero new parts that fail either test: it reuses the resolver interface of the online loop;
no new parameters, no new store type. ④ Discipline: host→local→machine-registry web→(prose: refuse), all
bounded, all version-pinned to the environment's declared floor. ⑤ Constraints hold: zero model calls; zero
parameters-as-facts; the record survives removal of the web URL (provenance is data, not a dependency).
⑥ Verified where honestly verifiable: the live read happened once (this file); the fetcher does not exist in-tree,
so **no runtime claim is made** — it is deferred with this receipt as its blocker, not smuggled in.

---

## 7. Honest state, and the one bottleneck

- The owner's intuition — *the computer already has the guide, and a small algorithm that refuses to guess can
  live off it* — is **supported** by everything measured here, and by the frontier's shift from "train for it"
  to "retrieve, exercise, cache".
- The owner's other instinct — *maybe it should just learn everything and generalise later* — is **refuted by
  measurement** (OOM; negative transfer; 0/164).
- The idea as an architecture is real and minimal: **orient → contract → locate → derive → verify → cache →
  re-check**. Each arrow exists in code in this tree as of today. What does not exist is the web arm (machine
  tier) wired into the resolver, and the identification problem it cannot dissolve: **an ambiguous goal has no
  environment answer.** Every environment question here dies unless the goal arrives as a checkable contract,
  which is to say the world can be asked only what a machine can check.
- **The single next bottleneck: make `GOAL` a measured object.** Close the loop from "the suite passed" to
  "the goal happened" for one more goal kind beyond `run-tests`, with the same re-check discipline, on trees
  this project has never seen; then refuse everything else with the same honesty as now. Until then §6 is not
  reachable; everything else — the web arm, more contracts, GUI evidence — is downstream of that.
