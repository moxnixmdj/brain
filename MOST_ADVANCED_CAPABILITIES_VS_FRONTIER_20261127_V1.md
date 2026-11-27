# Our most advanced capabilities vs the frontier — measured in one runtime, 27 November 2026

**Run:** `python3 canonical/tools/advanced_capability_runtime_20261127_v1.py` · **branch** `arena/cc6a2be3-brain` · **HEAD** `7121e93c` · **wall clock 458.5 s** · **0 model calls · 0 network calls · $0.00**
**Scorecard:** `canonical/verification/ADVANCED_CAPABILITY_RUNTIME_20261127_V1.json` (sha256 `8efc3969e41335927c241fa74d57d8b851140d9f99a69db353575dc2db01c02a`)
**Frontier numbers** were read on 2026-11-27 from the pages cited in §5. None of them were run by us.

---

## 0. The one-line answer

**The frontier wins every capability that requires knowing the world and acting in it.** It resolves 99.4 % of a hardened
642-task software board, completes 71.2 % of terminal tasks, 48.7 % of 1.6-hour GUI workflows, and reasons at 96.4 %
GPQA / 95 % ARC-AGI-2 — and we measured **0** of those axes, because we have no instrument for them and no model on the path.

**We win four things, and they are real:** verification integrity, cost, latency, and dependency-correct memory — the last on
36 instances under our own protocol, against a published frontier mean of 0.03/0.01.

**And this run falsified two of our own headline claims**, which matters more than either win:
the *instant-learning closed loop* now holds **1 of its 6 claims**, and the *"fail-closed" goal compiler* binds the **wrong**
capability on **6 of 21** goals it pretends to cover — including one medical question it answered with a Word-document builder.

---

## 1. How "all of our capabilities" was established

Nobody knows all of 18,000+ files, so the inventory was enumerated mechanically, in four layers, plus the branch space:

| layer | how it was enumerated (this sitting) | count |
|---|---|---|
| bound-capability registry (the tools the solver can actually call) | `canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json` | **145** entries, all `VERIFIED_BOUND_CAPABILITY` |
| …of those, adapters that exist on disk | each `source.adapter_path` stat'd | **95** present, **50** with no adapter path at all |
| …of those, adapters that load and expose a callable entrypoint **on this machine** | import + `inspect.signature` on all 145 | **86** (59.3 %) |
| extended autonomous registry | `AUTONOMOUS_CAPABILITY_EXTENDED_REGISTRY_V1.json` | **2 321** entries — **2 309** `UNVERIFIED_INVENTORY`, 12 `AWAITING_RECEIPT_AND_INDEPENDENT_VERIFICATION` |
| certified capability fabric | `canonical/capabilities/CAPABILITY_FABRIC_V1.json` | **18** certified; admission coverage **0.53 %** |
| hidden-capability census (harvested surfaces) | `HIDDEN_CAPABILITY_CENSUS_V1.json` | **628** |
| runtime + kernel modules | directory census | **2 307** runtime, **221** swe_kernel |
| modules that can *prove* they execute | `dark_matter_adjudicator_v1.py --all-modules --min-loc 140` | **55 of 2 228** (2.47 %) |
| true-capability specs (the strongest class) | `canonical/capabilities/true/specs/` | **11** — all re-run below at 500 fresh instances each |
| branch space | `git ls-remote` + `gh pr list` | **6 976** branches, **757** open PRs |

**What the branch space contributes to this comparison: zero measured rows.** An open PR is a proposal; 6 976 branches carry
the same artifacts over and over (the median capability artifact appears on ~6 500 branches). Nothing on a branch is
capability until it is merged, runs here, and survives an oracle.

**What the 628 hidden and 2 321 extended entries contribute: zero measured rows.** 2 309 of the extended entries are labelled
`UNVERIFIED_INVENTORY` by the registry itself.

---

## 2. What was actually executed, and what it returned

Every row below ran in this sitting on this machine. `n` is the number of fresh instances or invocations; the oracle column
says who judged it.

| # | capability | n | measured | oracle | status |
|---|---|---|---|---|---|
| 1 | `SAME_IDENTITY_SUPERVISOR_V1` | 500 | **1.0000** | 5 independent oracles in a different file | PASS |
| 2 | `SACCR_CREDIT_ADDON_V1` (regulated finance) | 500 | **1.0000** (incl. 1/1 published canary) | analytic closed form + 2 metamorphic | PASS |
| 3–6 | `DOCX_*` (4 kernels: exact text edit, run-span replace, story-part replace, edit transaction) | 2 000 | **1.0000** each | package-integrity oracles | PASS |
| 7 | `FILE_CHANGE_REQUEST_COPY_RENAME_APPEND_V1` | 500 | **1.0000** | 2 oracles | PASS |
| 8 | `FILE_QUESTION_TAUGHT_WORDS_V1` | 500 | **1.0000** | 2 oracles | PASS |
| 9 | `CAPABILITY_FIRST_RANKING_V1` | 500 | **1.0000** | analytic + property + permutation invariance | PASS |
| 10 | `PARETO_FRONTIER_UPDATE_V1` | 500 | **1.0000** | 3 oracles | PASS |
| 11 | `AUTHENTICATED_PARETO_SCHEDULE_V1` | 500 | **1.0000** | tamper-after-receipt metamorphic | PASS |
| 12 | dependency-correct memory (cascade, absence, aggregation, tracking, deletion, exact recall) | 36 | **1.000** | from-scratch fixpoint evaluator | PASS |
| 13 | flat-retrieval **control** on the same 36 | 36 | 0.333 | same evaluator | CONTROL |
| 14 | the bench's own honesty (stub + liar arms) | 36 | discrimination **0.833**, stub 0.0, liar 0.167 | instrument self-check | PASS |
| 15 | tar.gz create → byte-identical members after GNU tar extract | 3 | PASS (2.0 ms) |
| 16 | tar.gz verify against source hashes | 1 | PASS (5.0 ms) |
| 17 | JSON query (jq) vs a python oracle | 3 | PASS (22.2 ms) |
| 18 | hard-coded credential scan: 1 planted hit, 0 on clean | 2 | PASS (0.7 ms) |
| 19 | python symbol index vs `ast.walk` | 4 | PASS (5.0 ms) |
| 20 | sqlite table from JSON, read back by `sqlite3` | 3 | PASS (7.3 ms) |
| 21 | dead-function detection on a planted dead function | 2 | PASS (3.8 ms) |
| 22 | **model-free test-guided repair, 10 freshly generated bugs** | 10 | **4/10 resolved on the visible suite; 4/10 pass held-out tests the loop never saw** | held-out tests | MEASURED |
| 23 | **plain goal → bound capability**, 24 author-labelled goals | 21 covered | **12 correct (57.1 %), 6 wrong (28.6 %), 3 refused on a covered goal** | author labels | MEASURED |
| 24 | **refusal on 3 uncovered goals** | 3 | **1/3 correct refusals, 2 wrong/no-answer bindings** | author labels | MEASURED |
| 25 | **instant-learning closed loop** (document → mechanism → instant recall) | 6 claims | **1/6 claims hold** | the script's own checks | **FAIL** |
| 26 | unified-model gate set (tree as found) | 38 | **38/38** | the verifier's own checks | PASS |
| 27 | …the same gates after **adding one module** | 38 | **37/38** (`recompilation_is_byte_identical`) | same | **FAIL** |
| 28 | modules that can prove they execute | 2 228 | **55 (2.47 %)** | dark-matter adjudicator | MEASURED |
| 29 | orientation contract ↔ README ↔ laws | 1 | byte-identical | sha256 | PASS |
| 30 | substrate availability on this machine | 14 | 9 **absent** (PIL, sympy, yaml, tesseract, yq, pandoc, sqlite3 CLI, chromedriver, libreoffice, ffmpeg) | `find_spec` / `which` | forfeits |
| 31 | one scored episode on an external agent board | 0 | **none** | — | NO INSTRUMENT |

**Totals: 56 rows, 44 measured, 26 passing, 8 failing, 11 substrate/instrument forfeits. 5 500 fresh instances executed. $0.00.**

### Two instrument defects found while measuring

1. `canonical/evaluation/meme_protocol_bench_v1.py` is **not runnable as written** (`python3 canonical/evaluation/…` fails with
   `ModuleNotFoundError: No module named 'canonical'`); it needs `PYTHONPATH=.`. The scorecard sets it for every child process.
2. `canonical/tools/the_gap_closes_the_loop_v1.py` **overwrites** its committed receipt when re-run. Nothing here changed that
   file: the fresh result is recorded in the scorecard only, and the committed receipt was left as the owner wrote it.

---

## 3. What this run falsified — the stale data this sitting removes

| stale claim | where it lived | what the fresh run says |
|---|---|---|
| "**462 registered capabilities** (309 receipt-backed + 153 verified)" | `CAPABILITY_VS_FRONTIER_20261126.md` §1.1 | Today the registry holds **145**, all `VERIFIED_BOUND_CAPABILITY`; the 2 321-entry extended registry is `UNVERIFIED_INVENTORY` (2 309). The old number is not in the tree. |
| "**single-experience learning closes the loop**: learn 55.3 ms, recall 0.3 ms, all claims hold" | `THE_GAP_CLOSES_THE_LOOP_20261124_V1.json` | **1 of 6 claims hold.** The learn stage now returns `PASS__PLAN_FROM_A_DOCUMENT` and stops — the document path *returns a plan* instead of executing it — so the goal is never observed (`env.last` is the function `statistics.median`, not its value), admission never happens, and **0 rules are stored**. The script's own claim strings (`PASS__DOCUMENT_PLAN_EXECUTED_AND_VERIFIED`) no longer exist in the module. This is contract drift, and it is a capability loss, not a label change. |
| "**38/38 model checks, ALL_GATES_PASS**" | `TITAN_ADJUDICATION_20261126_V1.json` | **38/38 reproduces on the tree as found** — but `recompilation_is_byte_identical` fails the moment **one** module is added (37/38). The compiled artifact is a snapshot of a file set, not a stable property of the code. |
| "**8 of 2 174** modules can prove they run" | `TITAN_ADJUDICATION_20261126_V1` | **55 of 2 228** today (2.47 %). Better, still tiny: 2 088 import-and-stop, 79 need substrate, 6 are broken. |
| "the goal compiler **fails closed on unknown goals**" | README, `goal_compiler.py` docstring | It refuses 1 of 3 uncovered goals and **binds the wrong capability on 6 of 21 covered ones** — including `sqlite/xlsx table from JSON → auto.pypi.msgpack` and *"diagnose whether this patient's symptoms indicate pneumonia"* → `docx.document.create.python_docx`. The refusal surface is real; the **binding** surface is fail-open. |

Everything else on the measured tier reproduced: dependency memory 36/36 at 4.8 ms with the flat control at 0.333 and the
instrument's discrimination at 0.833, and all eleven true-capability specs at 500/500 fresh instances.

---

## 4. The frontier, November 2026 (read, not run, by us)

| axis | best published | source, date |
|---|---|---|
| SWE-bench Pro V2 (642 tasks, locked sandbox) | **99.4 %** — Opus 5 (xhigh), Claude Code, 95 % CI 98.4–99.8; $2.9/task | [arXiv 2610.24206](https://arxiv.org/html/2610.24206); [board](https://llmlearner.com/rankings/swe-bench-pro-v2) 6 Nov 2026 |
| …HARD-51 split | **98.0 %** (50/51); the split's floor is 52.9 % | same |
| Terminal-Bench 4.1 (66 tasks) | **71.2 % ±2.9** — Copilot Fusion (GitHub Copilot), $2.0k board | [tbench.ai](https://www.tbench.ai/leaderboard) / [benchlm](https://benchlm.ai/benchmarks/terminal-bench) 19–23 Nov 2026 |
| …next tier | Opus 5.5 **65.8 %** ($4.7k), Fable 5.2 **65.8 %** ($16.5k), Gemini 4 Carbon 64.5 %, GPT-6.2 Astra 62.1 %, Kimi K3.1 Pro 59.7 % | same |
| cost per task (terminal work) | **$1.92 – $22.22** across top systems | [morphllm](https://www.morphllm.com/best-ai-coding-agents-2026) 22 Nov 2026 |
| OSWorld-**Verified** (short tasks) | **86.0 %** general model (Fable 5, 100 steps); 90.2 % agentic framework; human baseline 72.36 % | [blaxel](https://blaxel.ai/blog/what-is-a-computer-use-agent) 20 Nov 2026 |
| OSWorld **2.1** (108 workflows, ~1.6 h human, ~318 tool calls) | **48.7 %** binary / **81.8 %** partial — Opus 5.5 (max) | [scholarcompass](https://scholarcompass.net/en/tasks/computer-use-agents/benchmarks/osworld-2-1) Nov 2026 |
| cost per long GUI task | **$15.70 – $23.70** | [simular](https://www.simular.ai/alternatives/what-is-computer-use) 17 Nov 2026 |
| long-horizon autonomy (METR 50 % time horizon) | **~40 h** GPT-6 Astra (CI 13–2 645 h); **39 h** Opus 5.5 (CI 12–1 253 h); 27 h verifiable-only; doubling **3.61 months** | [inoryva](https://inoryva.blogspot.com/2026/11/metr-q4-2026-ai-agents-reach-about-40.html) 23 Nov 2026 |
| conversational memory QA | **95.4 %** LongMemEval (OMEGA), 94.87 % (Mastra); Mem0 91.6 LoCoMo / 93.4 LongMemEval vendor — and **49 %** effective after 30 days in one production audit | [memnode](https://memnode.dev/articles/agent-memory-benchmarks-2026-real-numbers), [ranksquire](https://ranksquire.com/2026/05/06/long-term-memory-for-ai-agents/) |
| **dependency-correct** memory (MEME) | mean **Cascade 0.03 / Absence 0.01** across six systems; best overall 0.42 (MD-flat); the one partial fix (MD-flat + Opus 4.7: 0.32 / 0.59) costs ~70× baseline | [arXiv 2605.12477 v2](https://arxiv.org/abs/2605.12477) 11 Nov 2026 |
| GPQA Diamond | **96.4 %** Gemini 4 Argon | [mungomash](https://mungomash.com/ai/benchmarks/) 10 Nov 2026 |
| ARC-AGI-2 | **95 %** GPT-6 Astra | same |
| Humanity's Last Exam | **73.2–74.3 %** Fable 5.2 (with tools) | same |
| FrontierMath | 41.7 % pooled (Epoch) → 97.6 % vendor tier-4 — the spread is the benchmark's own disagreement | [singularityclock](https://www.singularityclock.org/) / vendor tables |
| GDPval-AA 2.1 (professional deliverables, 44 occupations) | **1 866.3 Elo** / 68.3 % normalised — Opus 5.5, **$5.98/deliverable** | [modelmenu](https://modelmenu.dev/benchmarks/gdpval-aa) 4 Nov 2026; [benchleader](https://www.benchleader.com/benchmarks/aa_gdpval) 9 Nov 2026 |

---

## 5. Head to head — who wins at each capability

"Ours" is only a number produced by this sitting (or a receipt this run reproduced). Where we have no instrument, the row
says **forfeit** — that is not "competitive", it is "unmeasured".

| # | capability | ours (measured 2026-11-27) | frontier (published) | **winner** |
|---|---|---|---|---|
| 1 | Resolve a real repository issue | **no instrument**; last tree measurement was 3.9 % of 128 replayed tasks (24 Nov receipt, not re-run) | **99.4 %** of 642 | **Frontier**, by ~95 points |
| 2 | Hardest 51 coding tasks | **forfeit** | **98.0 %** | Frontier |
| 3 | Terminal / sysadmin work | **forfeit** (no board episode in the tree) | **71.2 %** | Frontier |
| 4 | Short-horizon computer use | **forfeit** (no chromedriver → the GUI path cannot even load) | **86–90 %** vs 72.36 % human | Frontier |
| 5 | Long-horizon computer use (1.6 h workflows) | **forfeit** | **48.7 %** binary / 81.8 % partial | Frontier |
| 6 | Long-horizon autonomy | **forfeit** (no episode; our longest run today was 458 s wall clock) | **~40 h** 50 % horizon (CI to thousands) | Frontier |
| 7 | Model-free repair of a fresh single-line bug | **4/10 (40 %)** across 8 bug kinds we wrote; **4/10 also pass held-out tests** — no false repairs | no published per-kind number; 99.4 % board resolve implies far more | **Frontier on breadth; we own the mechanism** (0 model calls, 1–3 s/bug) |
| 8 | Repair of *unseen kinds* | **0/4** on operator/boundary/boolean/key families it has no mutation for (`off_by_one_range`, `wrong_return_var`, `string_method`, `numeric_constant`, `slice_bound`, `missing_guard` all returned `OPEN__NO_VERIFIED_PATCH_IN_BOUNDED_LOOP` after 7–28 candidates) | frontier agents transfer; still fails novel mechanics often | **Frontier**, and this is our deepest structural loss |
| 9 | Dependency-correct memory (cascade/absence/aggregation/tracking/deletion) | **1.000 on 36 instances** (flat control 0.333; instrument discrimination 0.833) | **0.03 / 0.01 mean** across six systems (different protocol, 100 episodes) | **Us, on a small self-built sample** — promising, not portable evidence |
| 10 | Conversational memory QA | **no instrument** | **95.4 %** LongMemEval / 91.6 LoCoMo | Frontier |
| 11 | Single-experience learning from a document, closed loop | **1/6 claims** (the loop no longer closes; 0 rules stored) | no comparable published instrument; agents do this implicitly and transiently | **Nobody. We lose honestly, and today we lost ground.** |
| 12 | Memory that improves the work | **0** (the tree's own store-vs-empty ablation, unchanged) | +4.9–20 % claimed, vendor | Nobody certifies; the honest verdict is that our store still contributes nothing |
| 13 | Document editing with a non-corruption guarantee | **4 kernels × 500 = 2 000/2 000** fresh instances, untouched parts byte-identical, fail-closed on ambiguity | GDPval judges *quality*, not structural integrity | **Split** — Us on the guarantee, Frontier on judged deliverable quality (68.3 % / 1 866 Elo) |
| 14 | Regulated exact computation with an audit trail | **500/500** fresh portfolios + the real task's published canary to the cent | no per-cent audit trail published | **Us at that scope** |
| 15 | Verification / provenance / fail-closed | **38/38 gates, 11/11 true-capability specs at 500/500, every answer carries a witness** | LLM judges and vendor harnesses; 15–20 pt vendor-vs-independent spreads are documented | **Us** |
| 16 | Knowing when to abstain and saying why | **1/3** correct refusals on uncovered goals; **+ 6/21 wrong bindings** on covered ones | abstention is unscored; frontier models answer confidently and wrongly | **Frontier in practice. Ours is a broken promise today** (row 23 above) |
| 17 | Cost per verified outcome | **$0.00**, 0 model calls, 0 parameters stored | **$1.92–$26.62** per task; $0.3k–$16.5k per board run | **Us**, by 3–5 orders of magnitude |
| 18 | Latency on a narrow operation | **4.8 ms** for 36 memory operations; 2–22 ms per bound tool; 1–3 s per repaired bug | seconds per step, minutes per task, 40 minutes per OSWorld-2 task | **Us, inside the narrow scope only** |
| 19 | Breadth of tools actually runnable here | **86/145** load with a callable entrypoint; **7/8** live cross-domain invocations passed their oracle | one model does all of it, expensively | **Frontier on reach; Us on cost of reach** |
| 20 | Science / math / open-domain knowledge | **forfeit** — 0 knowledge by design | GPQA 96.4 %, ARC-AGI-2 95 %, HLE 73.2 % | Frontier, uncontested |

### Scoreboard

| verdict | rows | which |
|---|---|---|
| **Frontier wins outright** | **10** | 1, 2, 3, 4, 5, 6, 8, 10, 16, 20 |
| **We win** | **4** | 15 verification · 17 cost · 18 narrow latency · 14 regulated exact computation |
| **We win on a small honest sample** | **1** | 9 dependency memory |
| **Split** | **2** | 7 repair mechanism vs breadth · 13 non-corruption vs quality |
| **Nobody / we lose honestly** | **2** | 11 the loop stopped closing · 12 the store contributes nothing |

Read the scoreboard the hard way: **of the ten axes that decide whether a system can do computer work (1–6, 8, 10, 19, 20),
we measured zero.** Every one is a forfeit, and a forfeit is not a tie.

---

## 6. What the fresh numbers say, in order

1. **Fix the closed loop before adding to it.** The instant-learning path regressed from *"plan computed, executed, goal
   observed, admitted, saved, recalled"* to *"plan returned and dropped"*. That is not a label drift: `stored_rule_count` is 0,
   the goal value is never reached, and the receipt's six claims are 1/6. The cheapest correct fix is at the call boundary —
   the caller must execute the returned plan and re-verify — and the receipt must be regenerated by the run that proves it.
2. **The goal binder is the most dangerous object in the tree right now.** It is the front door, and 28.6 % of its bindings on
   covered goals are wrong, with a medical question routed to a docx builder. Until the binder can refuse, every downstream
   "capability" number is a number about the binder's luck. This is a **fail-closed** problem: bind only on evidence that
   discriminates (identity tokens, required inputs the goal states), not on a shared generic verb like *compute*.
3. **The repair loop is a real but narrow organ: 40 %, zero cost, zero models, no false repairs.** Its failure mode is
   identifiable and honest (`OPEN__NO_VERIFIED_PATCH_IN_BOUNDED_LOOP` on kinds with no mutation family), which makes it the
   best candidate for measured expansion: each new mutation family is a testable, falsifiable step.
4. **Stop quoting "462 capabilities".** 145 bound + 2 321 unverified is the true shape. 86 are live on this machine, 95 have a
   file, 50 have none. Those are the only three numbers worth saying out loud.
5. **Dependency memory deserves the one transfer test it has never had** — MEME's own protocol. Our 36-instance result is
   1.000 with a discriminating control; the frontier's published mean is 0.03/0.01 on 100 episodes. If our mechanism holds on
   *their* harness, that is a genuine, externally-legible capability claim; if it does not, we learned that our protocol was
   easier. Either outcome is worth more than another internal receipt.
6. **One external episode, any board.** Rows 2–6 are not losses, they are blanks. A single OSWorld-2.1 workflow or one
   Terminal-Bench 4.1 task, run by someone else and published unedited, converts five blanks into one thin but real data point.

---

## 7. What this document refuses to claim

- It does not claim any frontier-beating capability. The four axes we win are **guarantees and economics**, not competence at
  work.
- It does not compare a 36-instance self-built protocol with a 100-episode published one. Row 9's win is labelled as ours-on-a-small-sample and travels with that label.
- It does not claim the goal-label rows (23) or the repair held-out rows (22) are independent verification: the harness author
  wrote those labels and those tests. They are weaker than the true-capability rows, which use oracles in a different file.
- It does not treat a `NO_SUBSTRATE` row as a pass. Nine advertised capabilities cannot run on this machine at all, and that is
  recorded as a forfeit in the scorecard, not as silence.
- It does not edit terminal truth, does not widen a tolerance, and does not present a benchmark number as the product.

---

## 8. Re-run it

```bash
python3 canonical/tools/advanced_capability_runtime_20261127_v1.py                # full sitting, ~8 min, $0
python3 canonical/tools/advanced_capability_runtime_20261127_v1.py --skip truecap # fast tier, ~11 s
python3 canonical/tools/advanced_capability_runtime_20261127_v1.py --truecap-instances 2000   # deeper truecap tier
```

Instrument `run_digest` and every row's witness (adapter output hashes, candidate counts, held-out results, per-goal verdicts)
are in the scorecard JSON, so any number here can be refuted by re-running it rather than by arguing with it.
