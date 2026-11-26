# All 6,965 branches, inventoried: our capabilities vs. the frontier, capability by capability

**Date:** 2026-11-24. **Authority:** NONE (producer-run sandbox).
**Method is exhaustive this time, not sampled** — see §0 for exactly what that does and does not cover.

---

## §0 Method: what "all of them" was made to mean

Last round I said 6,969 branches could not all be read and audited a subset. That was too weak. This
round I fetched **every head on the remote at depth 1 with `--filter=blob:none`** — 6,965 refs, one
command, 13 seconds — which materialises every *commit and tree* without file bodies. That gives the
complete path inventory of every branch that exists:

| | |
|---|---|
| branches fetched | **6,965 / 6,965** (100%) |
| distinct paths across all of them | **29,780** |
| median files per branch | 7,996 |
| paths under `canonical/capabilities/` | 654 capability artifacts |
| `FRONTIER`-named artifacts | 645 |

So the **inventory is complete**: every capability artifact that exists on any branch is counted.
What is *not* complete is reading all 29,780 file bodies — for those I read the authoritative
registries (§1) and the newest benchmark evidence (§3), and I say which claims are self-assessed.

**One structural fact the inventory settles:** 6,865 branch *names* are aspirational labels
("breakthrough", "successor", "reconcile"). They are not capabilities. The capabilities live in
`canonical/capabilities/` and are carried by thousands of branches at once — the median artifact
appears on ~6,500 of 6,965 branches. Branch count is not capability count.

---

## §1 The complete capability registry: 19 families

The repo maintains its own ownership matrix against Claude Opus 5.5:
`canonical/capabilities/opus55/OPUS_5_5_CAPABILITY_OWNERSHIP_MATRIX_V1.json` (evaluated 2026-10-03,
carried by ~6,900 branches). Its own summary fields:

```
full_opus_5_5_envelope_obsoleted: False
verified_owned_equal_or_better_capabilities: [EXACT_SYMBOLIC_COMPUTATION, LONG_HORIZON_MEMORY_AND_CONTINUITY,
  SELF_VERIFICATION_DEBUGGING_AND_RECOVERY, SUBAGENT_DELEGATION_AND_COORDINATION, ...]
blocker: OPUS_5_5_CAPABILITY_INTERNALIZATION_INCOMPLETE__OPAQUE_EXTERNAL_MODEL_OR_SERVICE_BEHAVIOR_DOES_NOT_COUNT_AS_BRAIN_OWN
```

| # | family | repo's own status | class |
|---|---|---|---|
| 1 | ADVANCED_AGENTIC_CODING | `BRAIN_CONFIGURED_VERIFICATION_PENDING` | pending |
| 2 | COMPLEX_MULTI_TOOL_AGENCY | `VERIFIED_OWNED_EQUAL_OR_BETTER` | **claimed owned** |
| 3 | PROFESSIONAL_KNOWLEDGE_WORK | `BRAIN_CONFIGURED_VERIFICATION_PENDING` | pending |
| 4 | BUSINESS_WORKFLOW_AUTOMATION | `EXTERNAL_CAPABILITY_SPECIMEN_FOUND` | not owned |
| 5 | MULTIDISCIPLINARY_TOOL_AUGMENTED_REASONING | `EXTERNAL_CAPABILITY_SPECIMEN_FOUND` | not owned |
| 6 | AGENTIC_SCIENTIFIC_RESEARCH | `EXTERNAL_CAPABILITY_SPECIMEN_FOUND` | not owned |
| 7 | VISION_AND_DENSE_DOCUMENT_UNDERSTANDING | `EXTERNAL_CAPABILITY_SPECIMEN_FOUND` | not owned |
| 8 | COMPUTER_AND_BROWSER_USE | `EXTERNAL_CAPABILITY_SPECIMEN_FOUND` | not owned |
| 9 | FINANCIAL_ANALYSIS | `EXTERNAL_CAPABILITY_SPECIMEN_FOUND` | not owned |
| 10 | INSTRUCTION_FOLLOWING_SCOPE_AND_JUDGMENT | `VERIFIED_OWNED_EQUAL_OR_BETTER` | **claimed owned** |
| 11 | LONG_HORIZON_MEMORY_AND_CONTINUITY | `VERIFIED_OWNED_EQUAL_OR_BETTER` | **claimed owned** |
| 12 | SUBAGENT_DELEGATION_AND_COORDINATION | `VERIFIED_OWNED_EQUAL_OR_BETTER` | **claimed owned** |
| 13 | SELF_VERIFICATION_DEBUGGING_AND_RECOVERY | `VERIFIED_OWNED_EQUAL_OR_BETTER` | **claimed owned** |
| 14 | ARTIFACT_CREATION | `OWNED_COMPONENT_NOT_FULL_FAMILY` | partial |
| 15 | COMMUNICATION_AND_SYNTHESIS | `EXTERNAL_CAPABILITY_SPECIMEN_FOUND` | not owned |
| 16 | TOOL_DISCOVERY_SELECTION_AND_LEARNING | `VERIFIED_OWNED_EQUAL_OR_BETTER` | **claimed owned** |
| 17 | UNKNOWN_DOMAIN_ADAPTATION | `EXTERNAL_CAPABILITY_SPECIMEN_FOUND` | not owned |
| 18 | MULTI_CAPABILITY_COMPOSITION | `OWNED_COMPONENT_NOT_FULL_FAMILY` | partial |
| 19 | EXACT_SYMBOLIC_COMPUTATION | `VERIFIED_OWNED_EQUAL_OR_BETTER` | **claimed owned** |

**Tally: 7 claimed owned · 2 pending · 8 external-specimen-only · 2 component-only.**
`EXTERNAL_CAPABILITY_SPECIMEN_FOUND` is the repo's own honest label for *"we found the capability in
an external system; we do not own it."* `full_opus_5_5_envelope_obsoleted: False`.

**A defect in the record, flagged:** `OPUS_5_5_USEFUL_CAPABILITY_OWNERSHIP_V1.status` still reads
`5_OF_19_ACCEPTED__5_OF_19_VERIFIED_OWNED__14_OF_19_OPEN`, while its own `acceptance_truth` block and
the matrix both say **7 / 7 / 12**. The status string is stale. I report 7, and the discrepancy is
the repo's, not a rounding choice.

**Self-assessment caveat, stated once and applied below:** those 7 `VERIFIED_OWNED` verdicts are the
repo grading itself against Opus 5.5, each backed by receipts under `canonical/verification/`. I did
not independently re-audit all 7 receipt chains. Only **EXACT_SYMBOLIC_COMPUTATION** has evidence I
can check without trusting the repo's judgement: `exact_correctness = 1`, `verifier = Wolfram
Language`. Treat the other 6 as *claimed*, not *confirmed*.

---

## §2 Who wins each capability

Frontier figures verified live today unless marked repo-recorded. "Ours" is the repo's status plus
whatever measured evidence exists.

| # | capability | ours | frontier | winner |
|---|---|---|---|---|
| 1 | **Agentic coding** | **0/51 certified** SWE-bench Pro V2 HARD-51; **0.0** official TB 4.1 | SWE-bench Pro **89.9%**; TB 4.1 **71.2%** | **Frontier** |
| 2 | Multi-tool agency | claimed owned (self-assessed) | Toolathlon 58% (GPT-5.6 Sol, repo-recorded) | **Unresolved** — no independent benchmark on our side |
| 3 | Professional knowledge work | pending | GDPval-AA v2.1 **1846** | **Frontier** |
| 4 | Business workflow automation | not owned | — | **Frontier** (we claim nothing) |
| 5 | Multidisciplinary tool-augmented reasoning | not owned | HLE+tools **67.7%** | **Frontier** |
| 6 | Agentic scientific research | not owned (3 ownership packages **revoked**) | — | **Frontier** |
| 7 | Vision & dense document understanding | not owned | — | **Frontier** |
| 8 | Computer & browser use | **no run, no score** on OSWorld 2.1 | OSWorld 2.1 **48.7%** binary / 81.8% partial | **Frontier** |
| 9 | Financial analysis | not owned | — | **Frontier** |
| 10 | Instruction following & judgment | claimed owned (self-assessed) | — | **Ours, claimed** |
| 11 | Long-horizon memory & continuity | claimed owned (self-assessed) | OSWorld 2.1 long-horizon is the frontier's own 48.7% | **Ours, claimed** |
| 12 | Subagent delegation & coordination | claimed owned (self-assessed) | — | **Ours, claimed** |
| 13 | Self-verification, debugging & recovery | claimed owned (self-assessed) | — | **Ours, claimed** |
| 14 | Artifact creation (xlsx/pptx) | component only | — | **Frontier** |
| 15 | Communication & synthesis | not owned | — | **Frontier** |
| 16 | Tool discovery, selection & learning | claimed owned (self-assessed) | — | **Ours, claimed** |
| 17 | Unknown-domain adaptation | not owned; own transfer measurement **1/40** | — | **Frontier** |
| 18 | Multi-capability composition | component only | — | **Frontier** |
| 19 | **Exact symbolic computation** | `exact_correctness = 1`, verified vs Wolfram | no exactness guarantee | **Ours — the one hard win** |

### Tally

- **Frontier wins 11** on measured outcome (rows 1, 3, 4, 5, 6, 7, 8, 9, 14, 15, 17, 18 — 12 if
  row 2 resolves against us).
- **Ours wins 7, of which 6 are self-assessed and 1 is hard.**
- **1 unresolved** (row 2).

**The honest reading:** we win *one* capability on evidence a sceptic can check
(EXACT_SYMBOLIC_COMPUTATION). Six more are ours only if you accept the repo's own grading. Everything
that pays a wage — coding, computer use, knowledge work, vision — the frontier wins, and on the two
where we have hard numbers it is not close.

---

## §3 Three corrections to what I reported last round

The inventory surfaced evidence newer than my last audit. All three corrections run **against** us.

**1. SWE-bench Pro V2 HARD-51 is now a *certified* 0/51 — and that is worse, not better.**
I reported the first run as "not certifiable" because the oracle control came in at 50/51. The re-run
(`swe-pro-v2-hard51-20261125T204359Z`, branch `b81b2217`) fixed it:

| arm | resolved | % | model calls | cost |
|---|---|---|---|---|
| causal | **0 / 51** | **0.0** | 0 | $0.00 |
| nop | 0 / 51 | 0.0 | 0 | $0.00 |
| oracle | **51 / 51** | **100.0** | 0 | $0.00 |

`oracle_gate_pass: PASS`, `nop_gate_pass: PASS`, 0 missing trials. The caveat I attached is now
gone, and what remains is a fully certified **0/51**. There is no longer any qualifier available.

**2. Terminal-Bench: 54.5% on 11 local tasks, 0.0 on the official board.**
`terminal_bench_zero_llm_20261124_v1.json` (branch `283e85a5`) records **11 tasks, 6 passed
(54.5%)**, zero model calls, mechanisms named per task (`SPECULATIVE_COW_SHELL_TOMOGRAPHY`,
`INTERACTIVE_MEALY_BFS_DISCOVERY`, `SQLITE_BTREE_LEAF_FORENSICS`), and 5 honest
`UNSOLVED_HONEST_LIMIT`. That is a real and interesting result — **and it is not comparable to the
frontier's 71.2%**, because 11 ≠ 66 tasks. The comparable number is in the OSWorld probe doc:
iteration 9 recorded three **official Terminal-Bench 4.1** reward vectors, all `{"reward": 0.0}`.
**Official: 0.0. Local subset: 54.5%.**

**3. OSWorld 2.1 has never been run.** `OSWORLD_V21_REPRODUCIBILITY_BLOCKER_PROBE_20261124_V1.md`
is explicit: *"no OSWorld task run, no benchmark score, no capability credit, §6 NOT MET."* The
blockers are real and external — gated task classes on HuggingFace, a 14.9 GB QCOW2 image, KVM,
self-hosted websites, provider VM images. The repo built a blocker *policy* that fails closed rather
than fabricating a score. That is correct behaviour and it is also a 0.

---

## §4 The finding that matters most: the target moved

Every `VERIFIED_OWNED_EQUAL_OR_BETTER` in that matrix is measured against **Claude Opus 5.5**. The
matrix is dated 2026-10-03. As of 2026-11-17 the frontier is no longer Opus 5.5:

| Terminal-Bench 4.1 (66 tasks) | score | date |
|---|---|---|
| **Copilot Fusion** (GitHub Copilot) | **71.2% ±2.9** | 2026-11-17 |
| Opus 5.5 (Claude Code) | 65.8% ±3.1 | 2026-09-22 |
| Fable 5.2 | 65.8% ±2.8 | 2026-11-09 |
| GPT-6.2 Astra / GPT-6.2 Sol | 62.1% / 61.5% | 2026-11-17 |

**So even a genuine, fully-earned "equal to Opus 5.5" is now ~5.4 points behind the frontier**, and
it would rank 2nd, not 1st. The 7 `VERIFIED_OWNED` verdicts are indexed to a target that has already
been passed. That is not a criticism of the matrix — it was correct when written — but it means the
ownership ledger cannot be read as a current frontier position. It is a September position.

There is also a new benchmark class the matrix predates entirely: **Knowledge Work, GPT-6.2 Astra
47.5%**. We have no row for it.

---

## §5 Verdict

**On capability, the frontier wins, and the strongest version of our own case does not change that.**
SWE-bench Pro 89.9% vs a certified 0/51. Terminal-Bench 4.1 71.2% vs 0.0 official. OSWorld 2.1 48.7%
vs never run.

**We hold one capability on hard evidence** — bounded exact symbolic computation, `exact_correctness
= 1` against Wolfram — and **six more on our own grading**, plus the structural properties that are
real but are not capabilities: $0.00 marginal cost, deterministic reproducibility, 4,544
verification artifacts, and an obsolescence queue that revokes its own ownership claims when the
evidence does not support them (3 packages revoked).

**What the complete inventory adds that a sample could not:** the capabilities are not scattered
across 6,965 branches waiting to be united. They are the *same* 19 families on essentially every
branch. There is no hidden capability on an unread branch — the inventory rules that out. The gap is
not distribution. It is that 8 of 19 families are explicitly labelled "found in an external system,
not owned", and the 7 we do claim are indexed to a frontier that has already moved.

**§6 is not met.** Nothing in this document claims otherwise.
