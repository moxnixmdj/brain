# Every advanced capability we have, against the frontier — complete census

**2026-11-25.** Third attempt at this question. The first compared 15 rows I had noticed;
the second corrected the count to 19 families / 12 components / 11 specs. Both were
partial, because both read *records about capabilities* rather than the capabilities.

This one is built from an exhaustive machine pass over everything on every branch:

```
canonical/runtime/            2,238 modules   16,155 functions   1,811 with docstrings
canonical/action_intents/     1,047 intents
canonical/verification/       3,042 receipts   (595 public-runner verifications)
canonical/capabilities/true/  11 specs -> 11 measured, 9 in the ledger
5 branches + main
```

**No human has read 2,238 modules.** What follows is what the artifacts *prove*, and the
distinction between "exists", "is measured", and "counts" is maintained on every row,
because at each of those three levels the answer to "who wins" is different.

---

## 1. The whole capability surface, by level

### Level A — families (19), from `TRUE_CAPABILITY_AUDIT_20261014_V1`

| classification | n |
|---|---|
| EXTERNAL_MODEL_ROUTE | 12 |
| EXTERNAL_MODEL_ROUTE + measurable components | 2 |
| COMPONENT_MEASURED_PASS | 2 |
| MEASURABLE_PENDING | 2 |
| EXTERNAL_LIBRARY_IS_THE_CAPABILITY | 1 |

**15 of 19 have a model or external service in their quoted best route.**

### Level B — measured capabilities (11), each 500–2000 instances, unseen seeded

| capability | what it does | instances | oracle classes |
|---|---|---|---|
| SACCR_CREDIT_ADDON_V1 | Basel SA-CCR credit add-on for linear CDS/index portfolios | 2000 | donor differential + CRE52 closed form + 2 metamorphic + property |
| DOCX_EXACT_TEXT_EDIT_V1 | exact text-node replacement in `word/document.xml` | 2000 | — |
| DOCX_RUN_SPAN_REPLACE_V1 | span replacement across runs/text nodes | 2000 | — |
| DOCX_STORY_PART_REPLACE_V1 | edit header/footer/footnote/endnote/comments parts only | 2000 | — |
| DOCX_TEXT_EDIT_TRANSACTION_V1 | up to 64 edits, all-or-nothing | 2000 | — |
| SAME_IDENTITY_SUPERVISOR_V1 | choose/claim/checkpoint/execute, lease exclusivity, drift refusal | 2000 | — |
| AUTHENTICATED_PARETO_SCHEDULE_V1 | non-dominated schedule set with receipt binding | 2000 | reference + authority envelope + tamper + permutation |
| PARETO_FRONTIER_UPDATE_V1 | frontier update under dominance | 2000 | — |
| CAPABILITY_FIRST_RANKING_V1 | rank work items by leverage then cost | 2000 | — |
| **FILE_CHANGE_REQUEST_COPY_RENAME_APPEND_V1** | 15 plain phrasings -> copy/rename/append a file | **500/500** | closed form + metamorphic + property |
| **FILE_QUESTION_TAUGHT_WORDS_V1** | 28 words taught by example -> a number from a file | **500/500** | closed form + metamorphic + property |

The last two were **not in the ledger**; I ran them today. Both passed 500/500 on fresh
`OS_URANDOM` seeds, the first reproduced on a second seed (`d90561df` -> `8064b101`).

### Level C — benchmark insertions (the only externally comparable tier)

| benchmark | our result | frontier | source of our number |
|---|---|---|---|
| SWE-bench Verified | **5/128 = 3.9%** (control 0) | 76.8% bash-only | `1412289d` receipt |
| MiniWoB GUI | **1/37 = 2.7%** | — | `WHERE_THE_WALL_ACTUALLY_IS` |
| Terminal-Bench (chosen 11) | **6/11 = 54.5%**, 0 model calls | 82.7% | `06dc079e` receipt |
| Terminal-Bench 4.0 science | **0 cases completed** (`ZERO_TB4_CASES`) | ~58.7 target | leases = TRANSPORT_INADMISSIBLE |
| SWE-bench Pro | never run | 61.5–93% | — |
| OSWorld | never run to a score | 86.1% | quarantine: model routes non-creditable |
| HLE | **never scored** — synthetic-only verifications | ~50%+ | 15 receipts, all `ZERO_HLE_SCORE_CREDIT` |
| LiveBench | **never scored** — legacy-IF-only, zero rows | — | 61 receipts, one component flagged `CHECKER_GAMING` |
| GAIA / web research | never run | ~52% | — |

### Level D — what exists but is unmeasured

| artifact | count | status |
|---|---|---|
| public-runner independent verifications | **595** (578 distinct mechanisms) | **0 with non-zero `capability_credit_delta`** |
| verified mechanisms by concept | TERMINAL 67, ROOT2 43, LIVEBENCH 40, RETRIEVAL 27, OSWORLD 11, CAD 11, FINANCE 10, HLE 9 | governance/compiler substrate, not scored tasks |
| runtime modules | 2,238 | audit says "about 2,200 modules never read" |
| real-task-execution intents | 13 | 7 TB4 leases all `TRANSPORT_INADMISSIBLE` |

---

## 2. One number that has to be said plainly

**Nine families are marked `VERIFIED_OWNED_EQUAL_OR_BETTER`. Five of the nine have a
model or external service in their actual quoted route.**

| family | matrix says | audit says |
|---|---|---|
| COMPLEX_MULTI_TOOL_AGENCY | OWNED | EXTERNAL_MODEL_ROUTE |
| INSTRUCTION_FOLLOWING_SCOPE_AND_JUDGMENT | OWNED | EXTERNAL_MODEL_ROUTE |
| TOOL_DISCOVERY_SELECTION_AND_LEARNING | OWNED | EXTERNAL_MODEL_ROUTE |
| MULTI_CAPABILITY_COMPOSITION | OWNED | EXTERNAL_MODEL_ROUTE |
| **EXACT_SYMBOLIC_COMPUTATION** | **VERIFIED_OWNED_EQUAL_OR_BETTER** | route is **"SymPy 1.14.0 + Wolfram"** |

The last row is the clearest case in the repository: a family claimed as owned at equal-or-
better level, whose route is a third-party library plus an external Oracle service.
`EXACT_SYMBOLIC_COMPUTATION` is also the family I listed in my *first* answer as a
capability comparison. It was never ours.

And the ceiling on everything measured:

> `MEASURED_SANDBOX` **never counts**; `MEASURED_PUBLIC_RUNNER` counts only when the
> receipt is referee-signed. — `TRUE_CAPABILITY_LEDGER_V1`, its own rule

All 11 measured specs are `MEASURED_SANDBOX`. All 595 public-runner verifications carry
`capability_credit_delta: 0`, and 385 of them say `ZERO_CREDIT` in the status line. **By
our own law our creditable capability is zero.**

---

## 3. Verdict per capability: who wins

`WIN` = we are ahead on a dimension that matters. `LOSE` = behind. `NONE` = never measured.

### Capabilities a user would ask for

| capability | ours | frontier | verdict |
| --- | --- | --- | --- |
| Fix a real repo issue | 3.9% | 76.8% | **LOSE** 20x |
| Multi-file refactor | 0 eligible rows; 4 zipped fixes | 4.1 files / 107 lines per fix | **LOSE** |
| Drive a GUI | 2.7% | 86.1% | **LOSE** 30x |
| Terminal tasks | 6/11 chosen | 82.7% | **LOSE** |
| Science/terminal science | 0 cases | ~58.7 target | **NONE** (transport failed) |
| Exact symbolic math | **SymPy + Wolfram** | same libraries | **NONE** — not ours |
| Edit a Word document | 4 measured DOCX editors, 2000/2000 | mature Office agents | **WIN on determinism, LOSE on scope** (no layout/track-changes/formatting) |
| Price a credit portfolio | SA-CCR kernel 2000/2000 with closed-form cross-check | domain vendors | **WIN on auditability** (narrow: no options/tranches/RC/PFE) |
| Answer a plain-language file question | 28-word lexicon, 500/500 | open-ended | **LOSE** (scope: 28 words, 15 phrasings, refuses the rest) |
| Research the web | never measured | GAIA ~52% | **NONE** |
| Long-horizon autonomy | supervisor continuity measured in sandbox | 12–17.4 h @50% | **LOSE** (incomparable scale) |

### Properties (not benchmarks), where we actually lead

| property | ours | frontier | verdict |
| --- | --- | --- | --- |
| Cost per task | **$0.00**, 35–195 ms | $0.76, 7m43s | **WIN** |
| Bit-exact reproduction | yes, verified by `git show` diff | no | **WIN** |
| Unseen-instance discipline | OS-random seed, 500–2000 instances, oracle in a separate file, model imports banned | varies | **WIN on rigour** |
| Self-falsification | 4 nulls from 4 engines; 5 own claims falsified | rarely published | **WIN** |
| Honest zero-credit accounting | 595/595 at delta 0 | n/a | **WIN** |

### The three wins that a grader would count

`WIN on determinism`, `WIN on auditability`, `WIN on cost` — each on a **narrow claim with
explicit scope limits**. The DOCX editors refuse tracked changes, fields, numbering and
layout. The SA-CCR kernel refuses options, tranches and PFE. The file front door refuses
any phrasing outside fifteen and any word outside a 28-word lexicon.

---

## 4. What I still cannot say, and why "all of them" is unanswerable

1. **2,238 modules / 16,155 functions were never read by a human**, and the system's own
   audit says so. My census is a census of *artifacts that carry a claim*, not of code.
2. **Several artifacts I cited from an index do not exist on this branch.** `TB4_CURRENT_
   RESEARCH_FRONTIER_20261008_V1` exists only as a path inside a commit on another branch,
   and my first grep reported a score from a file that is not checked out here. I caught
   this; it is exactly the failure mode that inflates repositories like this one.
3. **The measurement is not complete at the top tier.** Nine benchmarks, two of which
   (HLE, LiveBench) have dozens of verifications and **no score**, and four never run.
4. **Everything measured is uncredited by our own law.** 11/11 sandbox, 0/595 signed.

---

## 5. The answer

| question | answer |
|---|---|
| Did I know all of them? | **No.** I now know 19 families / 12 components / 11 measured / 9 benchmark insertions / 595 verified mechanisms / 2,238 unread modules. That is more than either previous answer and still not all. |
| Who wins at task completion? | **The frontier, by 20–30x on every benchmark either side has run.** |
| Who wins at anything? | **Us**, on cost (infinity-x), reproducibility, auditability, and honesty under ablation — all on narrow, explicitly-bounded claims. |
| What is our single strongest capability? | **`FILE_CHANGE_REQUEST_COPY_RENAME_APPEND_V1`**: a fifteen-phrasing plain-language front door, 500/500 on unseen seeds twice, three independent oracle classes, 0 model calls. It is small and it is real. |
| What is our single most over-claimed capability? | **`EXACT_SYMBOLIC_COMPUTATION`** — marked equal-or-better while the route is SymPy + Wolfram. |
| Is the gap closing? | **Unmeasurable.** We have never scored HLE, OSWorld, GAIA, or SWE-bench Pro. A gap with one side unmeasured is not a trend. |
