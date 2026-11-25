# The capability census, corrected — and the four levels my first answer missed

**2026-11-25.** This supersedes the scope of
`OUR_CAPABILITIES_AGAINST_THE_FRONTIER_20261125_V1.md`, which compared 15 capabilities. It
did not compare 15. It compared the 15 I happened to notice, and three of them turned out
to be understated by the repository's own artifacts.

**Answer to "are you sure": no, and here is the measurement of by how much.**

---

## 1. What my first answer missed

| what I said | what is actually there | how I missed it |
|---|---|---|
| "no container, browser or GUI result" | MiniWoB **1/37**, zero-LLM Terminal-Bench **6/11** | I had written this *before* looking at branches; my own memory flagged it as stale and I still repeated the frame |
| "15 capabilities" | **19 families + 12 components + 11 measured specs** | I used the target map (14 families) instead of the audit (19) |
| "9 measured capabilities" | **11 pass 500/500** | I read the ledger; the ledger's own `specs/` has two more that measure and were never promoted |
| never mentioned | `TRUE_CAPABILITY_AUDIT` classifying all 19 under a law | I did not look in `canonical/capabilities/true/` at all |
| never mentioned | 2238 runtime modules, 1064 action intents, 3042 receipts | I sampled directories instead of querying them |

The pattern in all five: **I sampled what was in front of me and called it complete.** That
is the same failure the audit found in the system itself — a claim asserted from a partial
read. It is worth naming because it is the error this repository exists to catch.

---

## 2. The real census, four levels

A "capability" here means four different things depending on altitude, and the ledger has
been mixing them:

```
LEVEL 1  19 capability families          (broad areas, e.g. COMPUTER_AND_BROWSER_USE)
LEVEL 2  12 named components             (e.g. DOCX editors, SA-CCR kernel)
LEVEL 3  11 measured specs               (claim + generator + independent oracles)
LEVEL 4  ~10 benchmark insertions        (MiniWoB, Terminal-Bench, SWE-bench, OSWorld)
         and ~2238 runtime modules, 1064 action intents, 3042 receipts
```

### Level 1 — 19 families, classified under `TRUE_CAPABILITY_TEST_LAW_V1`

| classification | count | families |
|---|---|---|
| **EXTERNAL_MODEL_ROUTE** | **12** | ADVANCED_AGENTIC_CODING, COMPLEX_MULTI_TOOL_AGENCY, BUSINESS_WORKFLOW_AUTOMATION, MULTIDISCIPLINARY_TOOL_AUGMENTED_REASONING, AGENTIC_SCIENTIFIC_RESEARCH, VISION_AND_DENSE_DOCUMENT_UNDERSTANDING, COMPUTER_AND_BROWSER_USE, INSTRUCTION_FOLLOWING_SCOPE_AND_JUDGMENT, COMMUNICATION_AND_SYNTHESIS, TOOL_DISCOVERY_SELECTION_AND_LEARNING, UNKNOWN_DOMAIN_ADAPTATION, MULTI_CAPABILITY_COMPOSITION |
| EXTERNAL_MODEL_ROUTE **with** measurable components | 2 | PROFESSIONAL_KNOWLEDGE_WORK, FINANCIAL_ANALYSIS |
| COMPONENT_MEASURED_PASS | 2 | LONG_HORIZON_MEMORY_AND_CONTINUITY, ARTIFACT_CREATION |
| MEASURABLE_PENDING (no model in route) | 2 | SUBAGENT_DELEGATION_AND_COORDINATION, SELF_VERIFICATION_DEBUGGING_AND_RECOVERY |
| EXTERNAL_LIBRARY_IS_THE_CAPABILITY | 1 | EXACT_SYMBOLIC_COMPUTATION |

**15 of 19 families have a model in their quoted best route.** Only **4** are model-free,
and of those 4, two are measured-pass and two are pending. That is the single most
important number about our advanced capabilities, and it is not in my first answer.

It also falsifies a matrix claim: four families were marked `PASS`/`VERIFIED` whose route
contains a model — `COMPLEX_MULTI_TOOL_AGENCY`, `INSTRUCTION_FOLLOWING_SCOPE_AND_JUDGMENT`,
`TOOL_DISCOVERY_SELECTION_AND_LEARNING`, `EXACT_SYMBOLIC_COMPUTATION`.

### Level 2 — 12 components, measured individually

| classification | component |
|---|---|
| MEASURED_PASS | SA-CCR credit asset-class add-on kernel |
| MEASURED_PASS | DOCX exact text-node replacement |
| MEASURED_PASS | DOCX span / transaction / story-part editors |
| MEASURED_PASS | Same-identity supervisor / checkpoint continuity |
| MEASURED_PASS | Authenticated & capability-first schedulers |
| MEASURABLE_PENDING | Remaining DOCX skills |
| MEASURABLE_PENDING | Vendored XLSX/PPTX agent skills (AWS sample, MS) |
| MEASURABLE_PENDING | Engineering dimension callout parser |
| MEASURABLE_PENDING_NEEDS_CADQUERY | CAD T0 drawing-to-geometry pipeline |
| **CHECKER_GAMING** | LiveBench legacy-15 visible-prompt compiler + joint witness |
| NOT_YET_AUDITED | `bytes_*` microkernels, "closed proof" kernel |
| NOT_YET_AUDITED | **"Everything else under `canonical/runtime` (about 2,200 modules)"** |

That last row is the honest answer to "are these all the capabilities": **no one knows.**
The repository's own audit says ~2,200 runtime modules have not been audited. I cannot
claim completeness over a directory the system itself has not read.

### Level 3 — 11 measured specs, and I ran the two nobody had

The ledger holds 9 rows; `specs/` holds 11. I ran the two missing ones myself today:

```
FILE_CHANGE_REQUEST_COPY_RENAME_APPEND_V1
  TRUE_CAPABILITY_PASS  fresh_pass_rate=1.0000 (500/500)  seed=d90561df62ccc534  OS_URANDOM
  FOLDER_BY_CONSTRUCTION / ASKED_AGAIN_RELATION / UNTOUCHED_AND_BY_THE_ROW

FILE_QUESTION_TAUGHT_WORDS_V1
  TRUE_CAPABILITY_PASS  fresh_pass_rate=1.0000 (500/500)  seed=b26e1377aebbe568  OS_URANDOM
  VALUE_BY_CONSTRUCTION / DOUBLED_FILE_RELATION / ANSWER_ENVELOPE
```

So the true-capability surface is **11, not 9**. The ledger under-counts its own measured
capabilities by two, and both are capabilities I would have called among the more
interesting ones: a fifteen-phrasing plain-language front door for copy/rename/append, and
"a word taught by example answers becomes an answer."

**But by the ledger's own rule these count for nothing in the terminal claim:**

> status `MEASURED_SANDBOX` never counts; `MEASURED_PUBLIC_RUNNER` counts only when the
> receipt is referee-signed.

All 11 are `MEASURED_SANDBOX`. Zero are referee-signed. **The ceiling on our credited
capability is zero, by our own definition, and that is the honest status.**

### Level 4 — benchmark insertions (the only externally comparable level)

| benchmark | result | tasks | comparable? |
|---|---|---|---|
| SWE-bench Verified | 5/128 = 3.9% | 128 judged | yes, task's own tests |
| MiniWoB GUI | 1/37 = 2.7% | 37 pages | yes, own harness |
| Terminal-Bench | 6/11 = 54.5% | 11 **chosen** | partially |
| OSWorld | never run to a score | — | no |
| SWE-bench Pro | never run | — | no |

---

## 3. What this corrects in my verdict table

Three verdicts change, and one is a new row:

| capability | my first answer | corrected |
|---|---|---|
| measured model-free capabilities | 9 (implied) | **11**, though 0 are referee-signed |
| family coverage | "15 comparisons" | **19 families, 15 model-routed** |
| artifact creation (DOCX/XLSX/PPTX) | not listed | **MEASURED_PASS** at component level — a real capability I omitted entirely |
| financial analysis (SA-CCR) | not listed | **MEASURED_PASS** component, inside a model-routed family |
| long-horizon memory/continuity | "no measurement" | **COMPONENT_MEASURED_PASS** — I was wrong |

On the last one I was simply mistaken in the first answer: I wrote "long-horizon autonomy:
no measurement," and there is a measured same-identity supervisor with checkpoint
continuity. It is measured in a sandbox against its own spec, which is much weaker than
METR's hours — but "no measurement" was false.

---

## 4. What I still cannot claim

1. **Completeness.** ~2,200 runtime modules are unaudited per the system's own audit. Any
   list I produce is a list of what was recorded, not what exists.
2. **Credit.** Zero capabilities are referee-signed. Our own law says that means zero
   creditable capability, whatever the pass rates say.
3. **That the 11 passing specs imply general ability.** Each is a narrow claim with
   explicit scope limits (`NO targets spanning two paragraphs`, `NO options/tranches`).
   500/500 on generated instances of a specified input class is a statement about that
   class.
4. **That the audit itself is the final word.** It is dated 2026-10-14, six weeks old, and
   it lists its own gaps in `next_in_order`.

---

## 5. The one-sentence answer

**No — those were not all of them, and the corrected count is 19 families / 12 components /
11 measured specs of which 15 families route through a model and 0 are referee-signed; the
system's own audit says about 2,200 runtime modules have never been read, so any claim of
completeness from me is a claim about the artifacts I found, not about the system.**

That sentence is worse for us than the first answer, and it is the true one.
