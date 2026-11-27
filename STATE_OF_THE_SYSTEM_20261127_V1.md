# State of the system, 27 November 2026: what this checkout can prove, what it cannot, and the one bottleneck

**Branch `arena/4d7c568f-brain`, base `7121e93c` · producer-run · no terminal authority · §6 not met.**
This document is the required confirmation + research summary + §3 verdict + plan. It does not redo
the 2026-11-26 audit it cites; it re-runs the checks that can be re-run here, adds two primary-source
confirmations of the frontier numbers, and reports the measurement this branch actually contributed
(`GUIDE_EXAMPLE_IS_A_SPOT_CHECK_20261127_V1.md`).

---

## 1. The requirements, restated in my own words (confirmation)

1. Ship a system that does computer work -- coding, GUIs, browsers, new environments -- using **its
   own** mechanisms: no runtime model call of any kind, no parameters that warehouse world knowledge.
2. All knowledge is external, inspectable and editable, retrievable per goal; runtime document fetch
   is a data fetch, a retrieval service that internally calls a model is forbidden.
3. "Own weights" does not mean a neural network; it means a computed core, judged by results.
4. Test on the hardest open benchmarks, un-gated, with only our system, no leakage, single-experience
   learning on held-out environments, and memory ablations. Anything less is progress, not completion.
5. Loop: find the bottleneck, research it, design the minimal ultimate fix, try to kill it, build,
   test on the hardest open failure, record honestly, repeat. Never stop before §6, never ask.

**§2 contradiction (persistence vs zero-knowledge house), resolved and unchanged from 2026-11-26:**
forbidden = weights as a fact lookup, or any runtime dependency on another model; allowed = an
external store of verified, provenance-carrying, O(1)-deletable entries that the system computes with,
plus one-exposure learning that writes to it. The operational test stays: *can the entry be removed
without retraining, and does the core hold only computed mechanisms?* Evidence that the boundary is
right: the live `CanonicalLawStore` / `SkillStoreV2` / `NegativeInvariantStore` are external JSON with
provenance and deletion, and no module added this session stores a parameter.

---

## 2. What is in this checkout, and what state it is in

| fact | value | how measured |
|---|---|---|
| files / Python / Markdown | 19,440 / 6,678 / 891 | `find` |
| test files under `canonical/tests` | 3,025 | `ls` |
| git history available here | **1 commit** (shallow, depth 1) | `git rev-list --count HEAD` → 1 |
| branches present | `main`, `arena/4d7c568f-brain` only | `git branch -a` |
| runtime dependencies installed | **none** (no `pytest`, `z3`, `numpy`) | `python3 -m pytest` → `No module named pytest` |
| live registry, as last measured in-repo | 462 capabilities, 234 engines, 18 skills | `CONFIRMATION_REQUIREMENTS...20261126_V1.md` §0 |
| modules that can prove they run | **8 of 2,174** substantial modules | `CAPABILITY_VS_FRONTIER_20261126.md` §1.1 |

The single most consequential fact for anyone reading this on a fresh sandbox: **this clone cannot
resolve any cited commit hash**. `209bbc6c`, `92b6db85`, `d6c1661a`, `8fe5f749`, `9026f2bc`,
`39d26eb4`, `aab1b545`, `b81b2217` and the rest are not objects here, and the split-brain branches
named in the brief are not refs here. That is a property of the carrier, not a finding about the
claims: on 2026-11-26 a full clone reached the same verdict by the same command, and the repository's
own `AUDIT_THE_PROMPT_CLAIMS_20261124_V1.json` marks all nine hashes FAILED. **A hash that cannot be
resolved is unverified, not false**, and no capability claim may rest on one.

Also chronological: the brief is dated 10 November 2026; today is 27 November 2026; this tree
contains documents dated to 4 December 2026 and receipts for runs on 3-4 December. Filename dates are
therefore **labels, not a chronology**, and I do not use them to order evidence. Where a document
claims a future date, the receipt's own `generated_utc` and the commands it names are the evidence,
not the name.

---

## 3. Claim ledger, re-checked today

| claim in the brief | verdict | evidence from this session |
|---|---|---|
| commit `209bbc6c` / `92b6db85` / `d6c1661a` and the branch findings | **UNVERIFIED (unresolvable here)** | `git cat-file -t` → not an object; history depth 1 |
| `instant_swe_skill_store_v1.py`, `verified_skill_crystallizer_ir_bridge_v1.py`, `universal_semantic_ir_v1.py`, `typed_invention_v1.py`, `witness_inversion_v1.py`, `zygote_worker_pool_v1.py` exist | **VERIFIED as files** | `find` hits, e.g. `canonical/runtime/instant_swe_skill_store_v1.py` |
| `hold_a_constraint_v1`, `effect_oracle_v1`, `MorphismSkillStore`, `IncrementalSemanticGraph` exist as named engines | **PARTLY FALSE** | `hold_a_constraint` appears only in JSON/Markdown; the effect oracle is `byte_effect_oracle_v1.py`; `MorphismSkillStore` is a class inside `frontier_unified_engine_v1.py` and `structural_rewrite_induction_v1.py`; `IncrementalSemanticGraph` is a class in `incremental_semantic_graph_v1.py` |
| 447 capabilities / 226 hand-written tricks | **FAILED as current** | live registry is 462 capabilities (2026-11-26 read); "226 tricks" has no live artefact |
| 51.11% 1-shot cross-commit transfer | **CONTRADICTED by later in-repo measurement** | `CAPABILITY_VS_FRONTIER_20261126.md` §1.2: skill-store contribution "identical to empty store", and 0/7 on a further unseen set |
| NO_COMPOUNDING (`8fe5f749`): unindexed library slows later tasks | **UNVERIFIED as a commit; superseded** | the later ablation says the store contributes nothing at all, indexed or not -- the bottleneck is not the index |
| `HONEST_SUITE_BASELINE` = 344 failing cases | **FALSE as stated, TRUE as files** | `HONEST_SUITE_BASELINE_20261103_V1.json`: 16,361 cases, **984 failed**, 42 errors, **344 files** with failures. The Oct-14 baseline had 11,525 cases / **344 failures**; the number grew fourfold by 3 Nov |
| 75.2% of real hunks lie outside fixed mutation grammars | **UNVERIFIED as a grammar ceiling** | repo re-derivation: 16/45 (35.6%) introduce an identifier absent from the old line; 75.2% is a context-bound statistic, not a ceiling |
| the 94%-matching guide round (`THE_GUIDE_IS_A_TEST_SUITE_20261204`) | **VERIFIED locally, narrower than printed** | re-ran the instrument: 6 stdlib guides / 180 examples / 138 ran / **130 matched** = same 130 as the receipt; the 3 README guides (9 examples) are not in the checkout, so 189/9 is not reproducible here |
| SWE-bench Pro V2: 642 tasks, up to 99.4%, HARD-51 span 52.9-98.0% | **VERIFIED (primary source)** | arXiv:2610.24206 v2 abstract, fetched today |
| Terminal-Bench 4.1: Copilot Fusion 71.2% ± 2.9 at $2.0k; Opus 5.5 / Fable 5.2 65.8%; GPT-6.2 Sol 61.5% at $0.3k | **VERIFIED (primary source)** | tbench.ai board, fetched today (the brief's "GPT-6.1 Sol 61.5%" is 6.2 Sol; GPT-6.1 Sol is 60.9%) |
| OSWorld verified human baseline 72.36% | **VERIFIED (primary source)** | osworld-v1.xlang.ai, fetched today; the page also confirms an OSWorld 2.0 successor exists |
| OSWorld 2.0/2.1 44.3% binary, ~318 steps | **UNVERIFIED here** | not fetched in this session; the repo's own citation is the OSWorld 2.1 release page |
| our measured capability | **3.9% of 128 judged SWE-style tasks; 0/51 HARD-51; 0/2 Terminal-Bench; 1/26 WebMCP call matches; memory ablation = 0** | the repo's 2026-11-26 receipts, not replaced by anything this session |

Frontier comparison is therefore possible on *versioned published numbers* and impossible on
*like-for-like harness*, exactly as the 2026-11-26 report says. Nothing in this session changes that.

---

## 4. §3 verdict, updated with this session's evidence

**True.** Single-exposure learning exists as a *mechanism* with a witness and a deletion control
(learn 55 ms from a document, recall 0.3 ms, prose-only control refused, 0 model calls). Verified
answers carry provenance. Cost is $0 of model spend. The guide's examples really do execute: 130 of
138 reproduce their own printed answer, re-run here.

**False.** That the mechanism compounds into task capability. Store-vs-empty is identical; the
one-experience ARC result is 17 -> 17 actions against an empty store; the 51.11% transfer figure does
not survive the later ablation. "The guide is a test suite" is also false in the sense that matters:
this session measures it at **85% of gross faults and 0% of faults inside guards the examples never
enter** -- 24 of 36 decision branches are never executed.

**Missing, and now measured.** The gap is not storage, not indexing, not retrieval speed. It is
**admission of a requirement-specific, executable, failing observation**. The new round sharpens it:
the guide supplies 16 concrete failing calls for injected faults, and 13 named unknowns at guards it
never enters -- but the *expected values* at those boundaries do not exist anywhere in the guide. A
receiver that passes its guide is verified on the interior of its domain and unverified at the edge.

**The one bottleneck.** *Acquiring an expected value at the boundary of a documented contract on a
receiver nobody here wrote.* Everything downstream -- repair, skill filing, compounding -- is starved
of that artefact. This is consistent with the 2026-11-26 reports ("file ranking and an irrelevant
failed test cannot tell Brain which public behaviour is wrong") and it explains why the store buys
nothing: what it stores is admission evidence, which is not what the next task needs.

---

## 5. The plan, with what was rejected and why

**Do, in this order** (each step falsifiable on the same fault set from §2.2 of the round report):

1. **Boundary oracle from the receiver's own tests.** Run the identical mutant set against (a) the
   guide's examples and (b) the receiver's test suite. Falsifier: if (b) does not beat 85% by more
   than the boundary share, this ordering is wrong.
2. **Boundary oracle from a second implementation** of the same documented contract (differential
   execution needs agreement, not expected values). Falsifier: if the pair does not disagree on the
   boundary mutants, it adds nothing.
3. **Only then** file skills, and only ones whose admission includes a boundary witness.

**Rejected, with the reason this session measured:**

* *Augment the example with perturbations and check them* -- a perturbation has no expected value, so
  it kills zero faults. Measured: the corpus that matters is the one with expected values, not the
  one with more inputs.
* *Derive a property from the example* -- self-confirming on the receiver; the only genuinely
  documented property in the sample was already counted by the 2026-12-04 round.
* *Store "the guide confirms this receiver"* -- at 85% gross / 0% boundary that is a claim the
  evidence does not support. It is the exact failure mode the repository keeps rediscovering.
* *Rebuild the skill store, re-index it, or grow the registry* -- the ablation already says the store
  contributes nothing; more of it cannot help while the admission artefact is missing.

---

## 6. What this session added

| artefact | what it establishes |
|---|---|
| `canonical/tools/guide_example_detection_power_v1.py` | detection-power measurement over real code: 131 injected faults, 108 separated by an independent corpus, 92 refused by real documentation |
| `canonical/verification/GUIDE_EXAMPLE_DETECTION_POWER_20261127_V1.json` | the receipt, with a witness call for every fault, and 13 guard-reaching inputs |
| `canonical/tests/test_guide_example_detection_power_v1.py` | 8 tests, including the four defects that made the first numbers meaningless |
| `GUIDE_EXAMPLE_IS_A_SPOT_CHECK_20261127_V1.md` | the round report, its limits, and the next decisive experiment |

**Not done here, and not claimed:** no official benchmark run (no Docker, no display, no official
images in this sandbox), no independent verification, no new capability promotion, no merge. §6 is
not met. The honest state is: one over-claim removed from the path, one bottleneck named more
precisely, and one measurement that any reader can re-run in six seconds.
