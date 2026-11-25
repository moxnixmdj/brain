# Everything we have, and who wins at each — 25 November 2026 (V2)

Supersedes `CAPABILITY_VERSUS_FRONTIER_20261124_V1.md`. V1 was written before the
harvest landed, so it described 447 capabilities. The tree owns more than that,
and one of the things it owned was *a comparison of this exact question* sitting
unmerged on `arena/b81b2217-brain` — which is itself evidence for the point.

## 1. How "all of them" was established

Mechanically, from artefacts, three layers with three different statuses:

| layer | count | produced by | what a claim on it is worth |
| --- | --- | --- | --- |
| **admitted** | **447** capabilities (153 bound, 294 receipt-backed), 26 engines, 18 skills | `BRAIN_UNIFIED_MODEL_V1.json` compiled from the live registry | executable through the front door |
| **discovered** | **621** executable surfaces no registry declares | `harvest_hidden_capabilities_v1` (AST invocation shape) | callable with evidence, never routed |
| **branch-only** | **82 diverged `arena/*` branches**, **1,776 files** absent from `main` (759 after excluding tests, receipts and JSON dumps: 146 runtime modules, 82 tools, 53 swe-kernel, 30 bound adapters) | GitHub compare of every `arena/*` branch against `main` | **zero credit** — in-flight work |

Plus the inventory that a parallel session left on `arena/b81b2217-brain`
(`MOST_ADVANCED_CAPABILITIES_VS_FRONTIER_20261125_V1.md`): 9 harness-measured true
capabilities, a 19-family ownership matrix, 367 root ledgers, 2,927 receipts, and
three CI benchmark reports, one of which is a **claimable 0.0 % on 51 SWE-bench
Pro tasks** — the run passed both gates, so the zero is published rather than
dropped. That document is the best inventory we had; it just was not reachable
from `main` until now, which is what today's earlier lift was about.

Domain split (reproducible: `canonical/tools/capability_inventory_by_domain_v1.py`):

| domain | admitted | discovered | branch-only |
| --- | ---: | ---: | ---: |
| orchestration / runtime | 152 | 87 | 124 |
| verification / proof | 94 | 69 | 38 |
| code comprehension | 44 | 29 | 11 |
| blind repair | 31 | 99 | 30 |
| planning / agency | 28 | 54 | 71 |
| security / policy | 25 | 14 | 12 |
| perception / documents | 21 | 13 | 8 |
| terminal / shell | 14 | 15 | 7 |
| benchmark harness | 8 | 27 | 95 |
| data / query | 10 | 4 | 13 |
| math / symbolic | 6 | 7 | 7 |
| memory / learning | 4 | 62 | 32 |
| search / retrieval | 2 | 24 | 16 |
| computer-use / GUI | 1 | 4 | 21 |

The shape is the story: we are deep in orchestration and verification, thin in
memory and GUI, and the GUI depth we do have is on branches.

## 2. Head to head

`V` = I fetched the source in this session. `B` = reported by the parallel
session's document with a dated board, not fetched by me. `U` = vendor- or
self-reported, treat as unverified. Our column is only what a receipt in this
tree supports.

| # | capability | ours | frontier | winner |
| --- | --- | --- | --- | --- |
| 1 | **Agentic SWE at benchmark scale** | **claimable 0.0 % on 51 SWE-bench Pro tasks** (run `20261125T204359Z`, oracle 51/51, nop 0/51, 43 `NO_EDITS` because the skill store is absent by design); best repair engines elsewhere 2/89, 5/30, 6/30, 2/13 cJSON (15.4 %) | **99.4 %** SWE-bench Pro **V2**, Claude Opus 5, 642 tasks, Scale/Reflection, board 2026-11-06 (`V`); 93.0 % Fable 5.2 on the older public set (`V`); 61.5 % ±3.10 independent public-set leader (`V`) | **Frontier by ~99 points** |
| 2 | SWE-bench Verified | never run | 76.8 % bash-only, 79.2 % any-scaffold (`V`); 96 % provider-reported (`B`) | Frontier |
| 3 | **Terminal / shell agent** | one real TB4 task passed (wal-recovery-ordering, 97/97 tests, 10 determinism runs); no breadth run | **65.7 %** Kimi K3.1 Pro / 64.8 % Opus 5.5 on Terminal-Bench **4.0** (`V`); 65.2 % Vals board (`V`). Our earlier 82.7 % was TB **2.0** — different vintage, not comparable | Frontier on breadth; our single pass is a mechanism, not a rate |
| 4 | **Long-horizon autonomy** | not measured as duration; 878 s engine time across 51 tasks | METR 50 % time horizon ≈ **40 h** (GPT-6 Astra, CI 13–2,645 h), 39 h Opus 5.5 (`B`) | Frontier (their own CI spans two orders of magnitude) |
| 5 | **GUI / browser computer use** | **unmeasured**, and named as unmeasured; shell-with-consequences instead: observation 1.0 / coarse 0.9706, novel 0.5, false alarms 0 (`B`) | OSWorld-Verified 90.2 % saturated (`B`), OSWorld **2.0** best **20.6 %** strict binary, ~0 % past 163 min (`V`), GAIA 94.0 % (`B`) | Frontier where pixels are the only observable |
| 6 | **Professional documents** | XLSX+PPTX read-write 11/11 round-trips; four DOCX kernels 2,000–3,000 fresh instances each with package-integrity oracles; GDPval never run | GDPval-AA v2.1 leader 1846 Elo (`B`) | **Split** — they win judged quality of a fresh deliverable; we win "this edit cannot corrupt the other 40 parts" |
| 7 | **One-shot retention of a demonstrated action** | exact replay 30/30, legality 228/228 compositions, consequence differential 1.0 | no published replay-exactness guarantee; stochastic decoding by construction | **Us** — the frontier cannot compete on this axis |
| 8 | **One-shot generalisation** | 0/10 real actions had their condition identified at k=1,2,4; contrasts buy a condition only where the deciding fact is observable (0.9464 vs 0.5833); 0/200 requirements from successes | qualitative "learns a skill from one demo"; nothing falsifiable published | **Nobody certifies it.** Only we measured, and the measurement says unsolved |
| 9 | Hard math / science reasoning | not attempted, by design | GPQA-D 94.3 %, ARC-AGI-2 77.1 %, LiveCodeBench 87.8 % (`B`) | Frontier, uncontested — we do not have this capability |
| 10 | **Exact regulated computation with an audit trail** | SACCR credit addon 2000/2000 fresh portfolios vs a sha-pinned donor + independent closed form + 2 metamorphic relations; canary reproduces 167,116.60 USD to the cent; re-introducing the real bug gives 0/500 | no per-cent audit trail published | **Us at that scope** |
| 11 | **Knowing when to abstain, and why** | 43 of 51 refused with the named missing fact (`FAIL_CLOSED`, `store: STORE_FILE_ABSENT`); `PASS` is defined as never evidence of a fix | abstention is not a scored behaviour on any board | **Us** — the only row where a zero is a win |
| 12 | **Verification of one's own instrument** | mutation testing on every measured capability (10 supervisor, 7 DOCX, 11 scheduler mutants), false negatives documented, two of our own oracle bugs published | verifier-in-the-loop papers, but no published test-of-the-test with surviving mutants named | **Us** |
| 13 | **Memory / skill transfer as a quantity** | `memory_exact 0.0481`, coverage 0.1584, silent corruption 0.3114, operating point p_correct 0.2978 (`B`); independently on `main`: laws recur 6/6 across repos, edits 3.7 %, selector 50 % precision / 100 % recall, true detection repaired on attempt 1 | CL-Bench: dedicated memory systems **do not** beat naive in-context learning (`V`); no published exact-replay or corruption rate | **Us as a measurement, and a loss we quantified** — they did not quantify it |
| 14 | **Cost and dependency per verified outcome** | **0 model calls, $0.00**, network refused, CI-produced | $6.88–$14.30 per task at the top of Terminal-Bench (`B`) | **Us by construction** — worthless if the output is wrong, which row 1 says it is |
| 15 | **Authority governance** | `AUTHENTICATED_PARETO_SCHEDULE_V1` 2000/2000; a receipt edited after the fact is refused (`TAMPER_AFTER_RECEIPT_IS_REFUSED`); zero-spend enforced; no promotion authority granted — today's harvest was blocked from admitting itself by exactly this gate | no equivalent; governance is a prompt | **Us** |
| 16 | **Consistency of its own claims** | the run that produced nothing was kept; the next run's **0.0 %** is published with `why_not_claimable: []`; both are in the tree | vendor boards sit 15–20 points above shared-harness results (`V`); retractions are not published | **Us** |
| 17 | **Codebase comprehension / retrieval** | incremental semantic graph at **0.001 s warm**, 2,027 indexed modules, cross-language U-IR; now 2,238 source rows including swe-kernel | ~1M-token context, no persistent index | **Split** — we win latency and persistence, they win depth |
| 18 | **Oracle manufacture (no failing test given)** | metamorphic witnesses manufacture violations the repo never wrote; isolation keeps 2/2 true detections; issue-only audit 2/2 with the held-out suite passing | agents write their own tests routinely, with no "this violation explains this failure" discipline | **Contested** — ours auditable, theirs broader |
| 19 | **Pre-ship verification of a repair** | law suite refutes on the fixed tree; 889-test hidden suite reached after the patch was chosen | held-out grading only | **Us** |

**Tally: frontier 6 (1, 2, 3, 4, 5, 9) + the quality half of 6; us 8 (7, 10, 11, 12, 13,
14, 15, 16) + the guarantee half of 6; split 2 (6, 17); contested 1 (18); nobody 1 (8).**

## 3. The pattern, stated once

Every row we win is a **guarantee at a stated scope**: exact replay, byte-identical
non-corruption, refusal with a reason, tamper rejection, zero spend, a measured
statement about our own knowledge. Every row we lose is **breadth of world
knowledge**, which the zero-model design declines to have.

Row 1 is not a mystery and should not be dressed up: with the store absent, 43 of
51 tasks never attempted an edit, and the ones that did resolved none. The
frontier's 99.4 % is a rate over 642 tasks produced by a rented model. Both
numbers are true, and they are not measuring the same thing — but if the question
is "can it fix real software bugs", the frontier wins and it is not close.

## 4. Conflicts this document resolves rather than hides

* **Terminal-Bench**: 82.7 % (TB 2.0, `V`) and 64.8–65.7 % (TB 4.0, `V`) are
  different benchmark vintages. Quoting either as "the" number is a protocol
  error, so both are stated with their version.
* **SWE-bench Pro**: 61.5 % independent public-set leader, 89.9–93.0 % on the
  vendor-owned public board, **99.4 % on Pro V2** — three numbers, three sets. Our
  0/51 is against V2.
* **OSWorld**: 90.2 % on *Verified* (saturated, `B`) and 20.6 % on *2.0* strict
  binary (`V`) are the same vendorship and different tasks; the gap is the
  benchmark, not a contradiction.
* **Memory**: "laws recur 6/6" and "`memory_exact` 0.0481" are both ours and
  point opposite ways: recurrence of a *law* is common; exact replay of a *lesson*
  is rare. Neither is allowed to stand in for the other.
* **Parallel session**: `arena/b81b2217-brain` produced a longer comparison
  today. Its frontier readings are labelled `B` here and its 0/51 run is used as
  the primary row-1 evidence, because it is the only claimable benchmark number
  we have.

## 5. Non-claims

No frontier number here was produced by us. No official benchmark of ours except
the 0/51 exists, and that one is a zero. The 84.6 % test-present figure from V1
was a 13-commit stream, not a benchmark, and is not used. The 244-verified-commits
and 45/45 figures from older reports do not reproduce and are excluded. Sandbox
measurement only; authority NONE.
