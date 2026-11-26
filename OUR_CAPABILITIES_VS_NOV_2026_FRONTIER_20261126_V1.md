# Every capability we hold, against the November-2026 frontier — and who wins at each

**2026-11-26 · branch `arena/ca730726-brain` · base `c5d59dd0`**
Model calls 0 · stored parameters 0 · incremental spend $0 · **authority NONE**

This is the seventh pass at this question in this repository. Passes 1–6 are listed in §9; each
found surfaces the previous one had missed, and the honest starting sentence is that the same
thing happened again. What is different here is not more enumeration — it is that the comparison
is anchored to **measured frontier numbers read from the web today**, and that **eleven of our
own claims were re-run from scratch on seeds I could not choose** rather than quoted from the
ledger. Both changes moved the answer.

---

## 0. The answer in eight lines

1. **At doing real work, the frontier wins everything that either side has actually measured —
   by 18× to 32×.** Coding agents: 71.2% vs our 2.2% on SWE-bench Verified. Computer use: 86–100%
   bounded vs 31.1% ours with a *half-observation* sensor. Terminal work: 71.2% vs 54.5% on a
   chosen 11-task set.
2. **At the general capability the owner actually asked for — figure out the goal, plan the
   cheapest route, act in an unseen environment — neither side has a number.** The frontier's best
   long-horizon computer-use result is 44.3% binary and collapses to zero past 163 minutes. Ours on
   that axis is unmeasured and its one measured substitute is 31.1% with a degraded sensor.
3. **We win on six properties, and four of them are not task capability**: $0.00 marginal cost,
   bit-exact reproducibility, composition-by-hash (which the frontier cannot do because its
   mutations are not content-addressed), and auditable refusal.
4. **We win outright on two narrow artefacts**: the plain-language file front door (500/500,
   twice, on unseen seeds) and the DOCX exact-edit family (2,000/2,000 across four kernels).
5. **Our matrix says we own 7 of 19 families. Our own audit says 15 of 19 routes contain a model.
   Both are out of date.** Where a component is genuinely ours, it is denied access today: the
   `route()` → `solve()` binding fails at `AUTO` on *every* plain goal I tried, including the two
   capabilities we hold most strongly.
6. **Two frontier numbers we have been quoting are stale by 30–47 points.** Terminal-Bench 4.0's
   66.4% is now 4.1's 71.2%; Frontier-Bench's 34.4% is now 43.3%; ARC-AGI-3's 7.78% is now 81.2%.
7. **The largest asset here is not any single capability. It is 38 unfalsified receipt-lane
   transactions, 1,190 production-reachable modules behind 145 bound ids, and an unusual habit of
   killing its own ideas.**
8. **The honest single sentence**: we are a rigorously instrumented, zero-cost, deterministic
   kernel with a handful of genuine small wins and no measured general capability, competing
   against systems that do thousands of real tasks per benchmark run at 40-hour time horizons.

---

## 1. Method — what makes this pass different

### 1.1 What I re-ran instead of quoting

The true-capability harness (`execution_guard/true_capability_harness_v1.py`) generates instances
from `OS_URANDOM`, so the author cannot choose the seed, and judges them from oracle files that may
not import the solver. I ran **all eleven specs**, 500 instances each, twice on two of them.

| spec | instances | result | seed (I did not choose) |
|---|---|---|---|
| DOCX_EXACT_TEXT_EDIT_V1 | 500 | **PASS 500/500** | `63dee5c2…` |
| DOCX_RUN_SPAN_REPLACE_V1 | 500 | **PASS 500/500** | `33ece810…` |
| DOCX_STORY_PART_REPLACE_V1 | 500 | **PASS 500/500** | `9cd0b2f3…` |
| DOCX_TEXT_EDIT_TRANSACTION_V1 | 500 | **PASS 500/500** | `45397774…` |
| SACCR_CREDIT_ADDON_V1 | 500 | **PASS 500/500**, canary 1/1 | `6919427e…` |
| SAME_IDENTITY_SUPERVISOR_V1 | 500 | **PASS 500/500** | `b1983173…` |
| AUTHENTICATED_PARETO_SCHEDULE_V1 | 500 | **PASS 500/500** | `110041e6…` |
| PARETO_FRONTIER_UPDATE_V1 | 500 | **PASS 500/500** | `5b6fb624…` |
| CAPABILITY_FIRST_RANKING_V1 | 500 | **PASS 500/500** | `6f86233b…` |
| FILE_CHANGE_REQUEST_COPY_RENAME_APPEND_V1 | 500 | **PASS 500/500** ×2 | `66bee2dd…`, `d90561df…` |
| FILE_QUESTION_TAUGHT_WORDS_V1 | 500 | **PASS 500/500** | `02230218…` |

**5,500 fresh instances, 5,500 passes, zero model imports, zero network.** Every oracle
distribution is as declared: an analytic closed form plus a metamorphic relation plus a property
for the file and DOCX kernels; a donor differential plus two metamorphics plus a property for
SA-CCR. This is a real, repeatable, independently-oracled result, and it is the strongest thing in
this document.

It is also `MEASURED_SANDBOX`, which under this repository's own law is **zero credit**. That law
is correct and I am not asking for an exception — but the distinction matters for this question:
*our own law refuses to count it; the frontier has no comparable artefact at all.* A 200-instance
audit at 2000 instances is a weaker claim than a 500-instance run at 500, and I am reporting the
weaker one on purpose.

### 1.2 What I ran instead of reading

- `verify_brain_unified_model_v1.py` → **38/38 PASS**, digest `b9a782c3…` (sandbox, authority NONE).
- `brain_unified_model_v1.open_model()` → 462 capabilities, 153 bound, 309 receipt-backed, 206
  engines, 18 skills, 754 knowledge documents, 656 harvested surfaces, 2,258 source-index modules.
- A 20-goal routing probe and a 10-goal end-to-end `solve()` probe (§4.3).
- The whole-tree census: **6,521 Python files, 2,448 runtime modules, 18,441 runtime functions.**
  Pass 6 said 2,238/16,155 on 2026-11-25; the tree grew by 210 modules and 2,286 functions in one
  day of merged work (PRs #7127–#7136).

### 1.3 What I read from the web today (all in §10)

Terminal-Bench 4.1 official board (Nov 19–22), OSWorld-Verified and OSWorld 2.0 boards, Frontier-Bench
v0.1, ARC-AGI-3 (ARC Prize), HLE and HLE-Diamond, GPQA Diamond (Epoch AI), GDPval-AA v2.1, Chartography,
AutomationBench, METR Q4 2026 time horizons, SWE-bench Verified/Pro status.

**Where sources disagree, I report the disagreement rather than picking the flattering number.**
OSWorld 2.0 is published as 20.6% (paper, release), 31.4%, 44.3%, and 72.6% by four sources on the
same 108 tasks. That is not a benchmark, it is a rumour with a leaderboard — and I use the lowest
honest reading (20.6–44.3%) in the comparison, which is generous to us, and say so.

---

## 2. The full inventory — every capability layer we hold

Nothing below is a capability claim. The layers are separated because "exists", "is measured" and
"counts" give three different answers to "who wins".

| # | layer | count | what it proves | credit |
|---|---|---|---|---|
| L1 | **True-capability specs measured** | **11** | 5,500 fresh instances, 5,500 passes, independent oracles | 0 (`MEASURED_SANDBOX`) |
| L2 | **Bound capabilities, live-verified** | **145** | each re-read from the live registry + evidence on every execute | 0 |
| L3 | **Receipt-backed capabilities** | **309** | producer receipt + a different identity's reproduction under signed OIDC | 0 |
| L4 | **Total routable ids** | **462** | 153 bound + 309 receipt-backed, all in `solve()`'s route | 0 |
| L5 | **Engines (fabric + federated)** | **206** | 180 federated kernels + 25 fabric modes + 1 orchestrator | 0 |
| L6 | **Harvested surfaces** | **656** | executable, `admitted: false` by construction, disjoint from L4 | 0 |
| L7 | **Source-index modules** | **2,258** (566 entry points) | addressable, **not** executable from `solve()` | 0 |
| L8 | **Extended source index** | **675** | reachable cross-tree; same limit | 0 |
| L9 | **Runtime modules** | **2,448** | 1,190 production-reachable, 836 test-only, 212 orphan | 0 |
| L10 | **Public-runner verifications** | **595 → 742** | 578+ distinct mechanisms, referee-signed, **0 with credit** | 0 |
| L11 | **Internalized skill procedures** | **18** | human-written playbooks (TDD, debugging, subagents) — text, not code | 0 |
| L12 | **Knowledge documents** | **754** | hashes + headings + terms, retrieved just-in-time, never stored | n/a |
| L13 | **Research index** | **7,436** | evidence *about* capabilities | n/a |
| L14 | **ASTRA mission specs** | **321** | 1 verified unfamiliar-repo repair (mypy#21968), 3 blocked | 0 (`LOCAL`) |
| L15 | **Ownership matrix families** | **19** | 7 marked owned; audit says 15/19 routes contain a model | 0 |
| L16 | **Atomic acceptance predicates** | **38** | 18 proved, 20 unresolved, terminal false | 0 |
| L17 | **Honest test suite** | **11,525 cases** | 11,166 pass, 344 fail, 1 error at last baseline | n/a |

**The one number that is not in any of these layers** and is the real ceiling: `terminal_truth_achieved:
false`, `TRUE_CAPABILITY_LEDGER.authority: NONE`, `capability_credit_delta: 0` on all 742
public-runner receipts. **By our own law our creditable capability is zero.** Every "we win" below
is therefore stated as a property of an artefact, not as an ownership claim.

---

## 3. The frontier, November 2026 — measured, with the disagreements kept

| capability | frontier leader | score | runner-up | our best comparable | verdict |
|---|---|---|---|---|---|
| Agentic coding, terminal | **GitHub Copilot Fusion** | **71.2% ±2.9** (TB 4.1) | Claude Code + Opus 5.5 / Fable 5.2, 65.8% | 54.5% on 11 *chosen* tasks | **LOSE** |
| Agentic coding, terminal (4.0 legacy) | Opus 5.5 | 64.8% | Kimi K3.1 Pro 60.9% | same 6/11 | LOSE |
| Repo issue resolution | — | 61.5% Pro, 76.8% Verified (retired/contaminated) | — | **2.2%** (5 resolved of 225 judged) | **LOSE 32×** |
| Long-horizon terminal + 6 domains | Opus 5 | **43.3%** (Frontier-Bench v0.1) | GPT-5.6 Sol 34.4% | — | **NONE** |
| Computer use, bounded | Opus 5.5 | **81.8% partial** (OSWorld 2.0 partial) | best framework 90.2% (Verified) | **31.1%** total-reward, held-out | **LOSE ~2.4×** |
| Computer use, long-horizon | Opus 5.5 | **44.3% binary** (one source: 20.6%) | — | unmeasured | **NONE / LOSE** |
| Interactive novel environments | GPT-6 Astra | **81.2%** (ARC-AGI-3, Standard) | Gemini 4 Argon 49.8% | unmeasured | **NONE** |
| Hard science + reasoning | Fable 5.2 | **72.4–74.3%** (HLE-Diamond) | GPT-6.2 Astra 66.6% | never scored | **NONE** |
| With tools | GPT-6 Astra | **82.9%** (HLE-Diamond + web + code) | Opus 5.5 73.9% | never scored | **NONE** |
| Graduate science MCQ | GPT-6.2 Astra / Gemini 4 Hydrogen | **96.8%** (GPQA-D) | Gemini 4 Carbon 96.5% | `math.numeric_expression.sympy` (SymPy, not ours) | **NONE** |
| Professional deliverables | Opus 5.5 | **1,866.3 Elo / 68.3%** (GDPval-AA 2.1) | Kimi K3.1 Pro 1,858 | 4 DOCX kernels, no layout/track-changes | **LOSE** |
| Charts and dense documents | Sonnet 5.5 / Kimi K3.1 Pro | **90.2%** (Chartography +tools) | Opus 5.5 89.0% | chart-raster kernels, needs OCR axis anchors | **LOSE** |
| Business workflow automation | Gemini 4 Neon | **79%** (AutomationBench, 1 source: 62.2%) | Gemini 4 Carbon 78% | — | **NONE** |
| Long-horizon continuity | GPT-6 Astra / Opus 5.5 | **40 h / 39 h at 50%** (METR Q4) | CI 13–2,645 h | lease-exclusive supervisor, sandbox | **LOSE (incomparable)** |

Three things in that table are worth more than the numbers.

**3.1 Two of the numbers in our own canon are stale, and one is stale by 47 points.**
`FRONTIER_CAPABILITY_SURFACE_NORMALIZED_V1` (2026-09-28) records ARC-AGI-3 at **7.78%** for GPT-5.6
Sol. The ARC Prize board today records **81.2%** for GPT-6 Astra and **49.8%** for Gemini 4 Argon on
the provider-neutral Standard harness. The matrix records Terminal-Bench 4.0 at 66.4%; 4.1 is 71.2%.
The frontier plan records Frontier-Bench at 34.4%; Opus 5 is at 43.3%. Our own documents therefore
understate the frontier on three of sixteen rows — which is the one direction of error that cannot
flatter us, and it still means every "we are close" reading built on those files is wrong.

**3.2 The frontier's weak column is exactly the owner's request, and it is still weak.**
OSWorld 2.0's own paper: no model exceeds 10% binary in the 137–163-minute bin, and **above 163
minutes binary completion falls to zero for every model**. ARC-AGI-3's cost is $21.9K–$24.2K per run.
METR's error bars span 200×. So the frontier has: (a) no measured general goal-identification, (b) no
measured zero-cost operation, (c) no measured content-addressed composition — the very three things
the owner's objective is about, and the three things this repository has spent 500 documents on.

**3.3 The frontier is being measured on harnesses, not models.** Copilot Fusion is a *multi-model
router* and it is #1. The same model moves 15–25 points with the scaffold. That is a fact about where
capability lives — in the harness — and it is the single most encouraging fact in this document for a
project whose entire thesis is that the harness is the capability.

---

## 4. Who wins at each capability — the full table

`WIN` = we are ahead on a dimension that matters. `LOSE` = behind. `NONE` = never measured by one
side. Every row carries its evidence.

### 4.1 Task capabilities

| # | capability | ours (measured) | frontier (measured) | winner | on what |
|---|---|---|---|---|---|
| 1 | Exact text edit in a `.docx`, all-or-nothing, up to 64 edits | **500/500 ×4 kernels, fresh seeds** | no public comparable | **BRAIN** | determinism, byte-preservation of every other member |
| 2 | Replace a span crossing run boundaries / story parts (header, footer, footnote) | **500/500 ×2** | no public comparable | **BRAIN** | no SDK does run-span surgery with package integrity |
| 3 | Basel SA-CCR credit add-on with per-trade trace | **500/500**, 5 oracle classes incl. donor differential | vendor risk systems | **BRAIN (narrow)** | auditability; refuses options/tranches/PFE |
| 4 | Plain-language file operation (copy/rename/append, 15 phrasings) | **500/500 twice** | no comparable | **BRAIN** | end-to-end from prose, $0, 35–195 ms |
| 5 | Plain-language file question (28 taught words, 9 aggregates) | **500/500** | LLMs, unscored | **BRAIN (narrow)** | refuses an untaught word instead of guessing |
| 6 | Pareto schedule under authenticated receipts | **500/500**, 4 oracle classes | no comparable | **BRAIN (niche)** | tamper-after-receipt is refused |
| 7 | Leased exactly-once task execution across crash/resume | **500/500**, 5 oracle classes | no public comparable | **BRAIN (niche)** | lease exclusivity + no-terminal-re-execution |
| 8 | `jq` / YAML→JSON / msgpack / CBOR / BSON codecs | 8/8 per family, live-bound | trivial for any model | **DRAW** | we bind the tool; so do they |
| 9 | PDF text / OCR / QR / chart raster | bound; OCR blocked on this machine | 90.2% Chartography | **LOSE** | we need tesseract + axis anchors they read natively |
| 10 | XLSX/PPTX/DOCX creation from records | bound, 8/8 create + 8/8 verify | GDPval 68.3% | **LOSE** | ours is mechanical, theirs produces judged deliverables |
| 11 | Fix a real repo issue from text | **2.2%** (5/225 judged) | 76.8% Verified, 61.5% Pro | **LOSE 32×** | resolution rate |
| 12 | Unfamiliar repo, one issue, causal diagnosis | **1 instance** (mypy#21968, local) | thousands per run | **LOSE** | sample size |
| 13 | Multi-file refactor | 0 eligible rows; 2-file fixtures | 4.1 files / 107 lines per fix | **LOSE** | it has never been done on real code here |
| 14 | Terminal tasks | 54.5% on 11 chosen / 0 on full TB-4 | 71.2% on 66 tasks | **LOSE** | task set is chosen, and one whole family is `TRANSPORT_INADMISSIBLE` |
| 15 | Bounded GUI operation | **31.1%** total-reward, held-out, headless Chromium | 81.8–90.2% | **LOSE ~2.4×** | and ours needs a *half-observation* sensor (below) |
| 16 | Long-horizon computer use | unmeasured | 44.3% binary, 0% past 163 min | **NONE** | neither side has the owner's capability |
| 17 | Novel interactive environments (infer the goal) | unmeasured | 81.2% ARC-AGI-3 | **NONE** | but see §5.3: our own result says the goal cannot be identified from traces |
| 18 | Web research with provenance | never scored | GAIA ~52%, HLE+tools 82.9% | **NONE** | — |
| 19 | Professional deliverables | 4 mechanical kernels | 68.3% judged | **LOSE** | no judge has ever rated our output |
| 20 | Scientific reasoning | `sympy` binding only | 96.8% GPQA-D, 74.3% HLE-D | **NONE** | and the sympy route is not ours |

### 4.2 Properties — where the answer flips

| # | property | ours | frontier | winner |
|---|---|---|---|---|
| 21 | **Marginal cost per task** | **$0.0000** (5,500 instances, zero spend) | $0.76–$8.63 per task; $24.2K per ARC run | **BRAIN, unbounded** |
| 22 | **Bit-exact reproducibility** | yes — same seed, same bytes, verified by `git show` diff | no (sampling) | **BRAIN** |
| 23 | **Content-addressed composition** | solve A, write it down, dispatch B from A's *trace*, and C from A's *relation* — the library stores a program, not a description | providers cannot: their outputs are not composable by identity | **BRAIN, structurally** |
| 24 | **Composition under verification** | 228 of 228 replays held legality in composed settings | untested in this form | **BRAIN** |
| 25 | **Honest refusal as a product** | 3/3 out-of-domain goals fail closed; `GOAL_NOT_REPRESENTED_IN_MODEL` | abstention is a research area (BCEA: must refuse 82% for a 5% guarantee) | **BRAIN** |
| 26 | **Self-falsification rate** | 5 of its own claims falsified in one day, in writing | never published | **BRAIN** |
| 27 | **Zero-credit accounting** | 742/742 receipts at delta 0 | n/a | **BRAIN** |
| 28 | Speed per routed decision | 0.004–0.011 s | 100s–1,000s of seconds per task | **BRAIN** |
| 29 | Scope breadth | 28 words, 15 phrasings, 4 DOCX edit forms | open-ended | **LOSE** |
| 30 | Long-horizon persistence | lease-exclusive supervisor, sandbox | 40 h at 50% | **LOSE** |

### 4.3 The finding that is not in any previous pass: our own binding is the blocker

Passes 1–6 compared *artefacts*. They never asked whether the artefact can be reached from the front
door by a person saying a sentence. I asked, with `AUTO` mode, on ten ordinary goals in a real
directory:

```
goal                                                    AUTO            SOLVE_OR_LEARN
copy .tmp_probe/notes.txt to .tmp_probe/c1.txt          FAIL_CLOSED     PASS
rename .tmp_probe/c1.txt to .tmp_probe/c2.txt           FAIL_CLOSED     PASS
how many lines does .tmp_probe/notes.txt have           FAIL_CLOSED     PASS (answer=3 ✓)
how many blank lines are in the file …/notes.txt        FAIL_CLOSED     PASS (answer=1 ✓)
how many different lines does …/notes.txt have          FAIL_CLOSED     PASS (answer=3 ✓)
what is the longest line of …/notes.txt                 FAIL_CLOSED     FAIL_CLOSED
```

and the reason, from the execution envelope itself:

```
file.copy.v1 → BoundExecutionError:RENDERED_BOUND_ACTION_CAPABILITY_ID_MISMATCH
```

**Every one of our two strongest measured capabilities is unreachable by the default path, and the
one that works only works because a *different* route — the raw-goal compiler — fires instead.**
The copy that `SOLVE_OR_LEARN` produced was byte-identical, so the work is real; the binding between
`route()` and the executor is what fails. That is a defect, not a scoping choice: 145 bound
capabilities, 309 receipt-backed capabilities, and the plain path to them refuses the id it just
resolved.

Routing itself is fine and fast: 14 of 20 goals route confidently to the right family in 4–11 ms,
and 5 of 5 out-of-domain goals fail closed. The failure is one layer below routing, and it is the
highest-leverage thing in this repository that is not a capability claim.

**This is also why the "we own 7 of 19" figure should not be read as access.** Where a family *is*
genuinely ours (file ops, DOCX, SA-CCR, supervisor), a person cannot presently ask for it by
speaking.

---

## 5. What we have that the frontier structurally does not

These are the five claims worth defending. Each has a bound.

### 5.1 Composition by identity, not by description

`solve` writes down the *program* and the trace; the next goal is dispatched from the trace; the next
from the relation. 228 of 228 compositions held legality. A frontier agent stores a *description* of
what it did and re-reads it with a sampler, so composition is a prompt, not a proof. This is a real,
architectural difference. **Bound:** it composes only what has been measured, and the reachability
cap is 593 of 2,150 ids (§6).

### 5.2 Verification that is cheap enough to always run

Every instance is judged by a second file, on a fresh seed, for $0. The frontier's verification is
either a learned critic — measured at a **16.3% false-positive rate** on MBPP for Reflexion, which
scored *below its own baseline* — or a second sampler. A deterministic oracle that predates the
candidate is a different object. **Bound:** it only exists where a closed form or a metamorphic
relation exists, which is a narrow and hand-built set.

### 5.3 The falsification apparatus

This is the most under-credited asset in the tree and I want to state it plainly, because it is
better than the capability numbers:

- *successes only identify nothing*: 0 of 200 requirements identified at k = 1/2/4 demonstrations;
  accuracy 0.5625 / 0.7125 / 0.8625; retention 30/30.
- *the goal is not identifiable from the trace*: 11,935 hypotheses over 231 real runs collapse to 353
  behaviours; the owner's own goal is stated exactly by **79** different statements, and no
  experiment separates them. This is a **ceiling fact**, not a learner defect — and it is the most
  important measurement in the repository for the owner's thesis, because it says a machine cannot
  infer "make me a million dollars" from observation.
- *the repository's own history supplies 32.7% of the lines its own bugs need* — so history-mining
  cannot close the gap, and (usefully) is a contamination channel the frontier uses and we refuse.
- *four nulls from four engines*, and five of its own claims retracted the same day.

No frontier lab publishes this about itself. It is worth more than a 5-point benchmark gain and it
does not appear on any leaderboard. **Bound:** falsifying your own ideas produces papers, not
capability.

### 5.4 The one place the frontier is structurally excluded

The frontier's SWE-bench Pro number is partly contaminated — a claimed **32% verifier error rate** and
agents reading the fix out of Git history. This repository *cannot* do that: `history_template_repair_v1`
mines only `git log <PARENT>`, so the fix commit is unreachable by construction. **We are measuring
something strictly harder than the leaderboard is, at 2.2% instead of 61.5%.** That is a defence of
the measurement, not of the capability.

### 5.5 Cost asymmetry

$0.00 vs $0.76–$8.63 per professional task, $21.9K–$24.2K per ARC-AGI-3 run. A deterministic kernel
that costs nothing to run can afford to enumerate every candidate in a small space where a sampler
samples a few. **Bound:** the space was the wrong shape and the measured ceiling was 0 of 28.

---

## 6. The gap, quantified in one place

| axis | ours | frontier | ratio |
|---|---|---|---|
| Real repo issues resolved | 5 / 225 = **2.2%** | 76.8% | **35×** |
| Terminal tasks | 54.5% chosen / 0% full | 71.2% | **≥1.3×**, unbounded on the full set |
| Bounded GUI | 31.1% total-reward | 81.8–90.2% | **2.6–2.9×** |
| Long-horizon tasks completed | unmeasured | 44.3% → **0%** past 163 min | **undefined** |
| Professional deliverable quality | unjudged | 68.3% | **undefined** |
| Reachability of our own organs | **593 of 2,150** routable (27.6%) | n/a | 72% of the tree is addressable, not executable |
| Cost per task | **$0.00** | $0.76–$8.63 | **∞ in our favour** |
| Time horizon at 50% | requires a live lease per step | 39–40 h | **undefined** |

---

## 7. Nine falsifiable things this round has to say about itself

1. My §2 census is a census of **artefacts that carry a claim**, not of code. 18,441 functions in
   2,448 modules have not been read by a human, and the system's own audit declines to audit ~2,200 of
   them. "All of them" is not available, and that is a structural fact about this repository, not a
   limitation of this pass.
2. The 5,500-instance result is `MEASURED_SANDBOX`. Under this repository's own law it is **zero
   credit**. I re-ran it, which makes it current, not credited.
3. The frontier numbers are from secondary aggregators as much as from primary boards, and they
   disagree by up to 52 points on OSWorld 2.0. I used the lowest honest frontier reading where the
   disagreement is large, which biases the comparison toward us.
4. The 2.2% SWE-bench Verified figure is 225 of 500 tasks, on this machine's Python 3.11, **not** in
   the tasks' own images. It is a sample, not a submission.
5. The 54.5% Terminal-Bench figure is 11 **chosen** tasks. The 66-task population returned
   `TRANSPORT_INADMISSIBLE` for all seven leases.
6. The 31.1% GUI figure comes from an instrument that *removes the rendered screen* — it is a lower
   bound on capability and an upper bound on claim.
7. The `route()`→`solve()` binding defect in §4.3 is four weeks of merged PRs deep and nobody
   noticed, because passes 1–6 never executed the front door on a sentence.
8. Passes 1–6 each found new surfaces. There is no reason to believe pass 7 is the last, and every
   previous author said so too.
9. Nothing in this document changes `truth.achieved`, any scoreboard, any law, any credit, or any
   promotion. It is instrumentation.

---

## 8. Answer, stated once

**Who wins at each capability?**

- **Doing a real task a client would pay for** — the frontier, everywhere it has been measured, by
  2.6× to 35×.
- **Being right about a fact or a computation** — the frontier, but it is buying the same libraries
  we bind, so the margin is access, not cognition.
- **Being cheap, reproducible, auditable and composable** — **us**, by an unbounded margin, on
  narrow claims.
- **Knowing what to do without being told** — **nobody**. And this repository is the only place I can
  find that has *measured* why: the goal is not in the trace, 79 statements fit the same 231 runs,
  and asking eight questions carries the full 8.46 bits and still cannot separate them.
- **The owner's actual objective** — not reached by either side, and the frontier's 40-hour horizon
  with zero completion past 163 minutes is the closest published evidence that it is not imminent
  for anyone.

**Our single strongest capability:** `FILE_CHANGE_REQUEST_COPY_RENAME_APPEND_V1` — fifteen plain
phrasings, 500/500 on two unseen seeds, three independent oracle classes, $0, and it *refuses* a word
it was not taught. It is small, and it is real.

**Our single most over-claimed capability:** `EXACT_SYMBOLIC_COMPUTATION`, marked
`VERIFIED_OWNED_EQUAL_OR_BETTER` whose route is `SymPy 1.14.0 + Wolfram`. It was never ours.

**Our most over-claimed asset overall:** the belief that the capability exists and only needs
routing. Routing is 4–11 ms and 14 of 20 goals land correctly; the **binding below it fails on the
default path**, and 2,150 ids of real code sit behind a door that opens onto 593.

---

## 9. Previous passes, and what each one still contributes

| pass | file | what it found that the previous one missed |
|---|---|---|
| 1 | `CAPABILITY_VERSUS_FRONTIER_20261124_V1.md` | first comparison; 15 rows, partial |
| 2 | `OUR_CAPABILITIES_AGAINST_THE_FRONTIER_20261125_V1.md` | 19 families, 12 components, 11 specs |
| 3 | `EVERY_CAPABILITY_AGAINST_THE_FRONTIER_20261125_V2.md` | benchmark insertions tier; the `EXACT_SYMBOLIC` catch |
| 4 | `FOURTH_PASS_UNOPENED_SURFACES_20261125_V3.md` | `canonical/astra/`: mypy#21968, Wolfram-adjudicated 51/51 |
| 5 | `FIFTH_PASS_THE_94_FILE_DELTA_20261125_V4.md` | exact branch delta = 94 files; two claims overturned |
| 6 | `SIXTH_PASS_MEASURING_THE_UNREVIEWED_20261125_V5.md` | 1,190 / 836 / 212 reachability split instead of a fog |
| **7** | **this file** | **re-ran all 11 specs on fresh seeds; current frontier numbers from the live boards; and the `route`→`solve` binding defect that made passes 1–6 compare artefacts nobody can ask for** |

---

## 10. References

**Frontier (read 2026-11-26):**
Terminal-Bench 4.1 — https://www.morphllm.com/best-ai-coding-agents-2026 ·
https://reasonmachines.com/guides/best-coding-agents · https://mightybot.ai/blog/coding-ai-agents-for-accelerating-engineering-workflows/ ·
https://snorkel.ai/leaderboard/terminal-bench-science/ ·
OSWorld 2.0 — https://snorkel.ai/leaderboard/os-world-2-0/ · https://osworld-v2.xlang.ai/ ·
https://snorkel.ai/osworld-2-1-long-horizon-computer-use-evaluation/ · https://www.noxia.co.uk/field-notes/agents-beat-humans-and-still-finish-30-percent ·
Frontier-Bench — https://snorkel.ai/leaderboard/frontier-bench/ · https://aireleasetracker.com/benchmark/frontier-bench-v0.1 · https://backgrind.com/blog/agentic-coding-benchmarks-2026/ ·
ARC-AGI-3 — https://arcprize.org/leaderboard · https://ai.rs/ai-for-business/gpt-6-astra-benchmarks-arc-agi-3 ·
HLE / HLE-Diamond — https://trueiq.si/guides/humanitys-last-exam · https://klu.ai/benchmarks/humanitys-last-exam · https://pricepertoken.com/leaderboards/benchmark/hle ·
GPQA Diamond — https://www.benchleader.com/benchmarks/gpqa_diamond · https://ai.info/tracker/benchmarks/gpqa-diamond ·
GDPval-AA — https://modelmenu.dev/benchmarks/gdpval-aa · https://benchlm.ai/benchmarks/gdpvalaanormalized ·
Chartography — https://benchgap.net/b/chartographywithtools/current ·
AutomationBench — https://modelmenu.dev/benchmarks/automationbench-aa · https://benchlm.ai/benchmarks/automationbench ·
METR — https://inoryva.blogspot.com/2026/11/metr-q4-2026-ai-agents-reach-about-40.html · https://agitracker.io/blog/metr-time-horizons-2026/ · https://www.querynow.com/ai-agents/orchestration/long-running-agents

**Ours (re-read or re-run this session):**
`canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json` · `canonical/unified_model/BRAIN_UNIFIED_MODEL_V1.json`
(digest `b9a782c3…`, 38/38 verify) · `canonical/runtime/CAPABILITY_RECEIPT_PROJECTION_V1.json` ·
`canonical/capabilities/true/{TRUE_CAPABILITY_LEDGER_V1,TRUE_CAPABILITY_AUDIT_20261014_V1,LIVE_SOLVER_END_TO_END_MEASUREMENT_20261017_V1}.json` ·
`canonical/capabilities/opus55/OPUS_5_5_CAPABILITY_OWNERSHIP_MATRIX_V1.json` ·
`canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json` · `canonical/astra/ASTRA_{FINAL_FAMILY_WOLFRAM_ADJUDICATION,GLOBAL_WOLFRAM_ADJUDICATION,EXTERNAL_PARITY_CORRECTION}_V1.json` ·
`canonical/verification/MINIWOB_ONE_SUCCESS_GENERALISATION_20261111_V3.json` ·
`canonical/verification/CANDIDATE_UNDER_THE_TASKS_TESTS_SWEBENCH_VERIFIED_DJANGO_20261113_V1.json` ·
`canonical/verification/INDEPENDENT_REPLAY_FIVE_20261124_V1.json` ·
`canonical/verification/THE_GOAL_IS_NOT_IN_THE_ENVIRONMENT_20261130_V1.json` ·
`canonical/verification/FOURTH_PASS_UNOPENED_SURFACES_20261125_V3.md` …
`SIXTH_PASS_MEASURING_THE_UNREVIEWED_20261125_V5.md` ·
`THE_DEMONSTRATION_CARRIES_THE_ACTION_20261126_V1.md` · `THE_BRANCH_IS_THE_MODEL_20261128_V1.md` ·
`FRONTIER_LEAPFROG_PLAN_20261126_V1.md` · receipts written this session under `/tmp/tc/*.json` (11 files, seeds quoted in §1.1).
