# Scorer-maximum route — applicability to every open row (2026-10-14)

## Source of the method (owner doctrine, already law in the Brain)
- `canonical/laws/BENCHMARK_OUTPUT_INFORMATION_EQUIVALENCE_LAW_V1.md`: "A benchmark is a measurement instrument, not an intrinsic goal. For every benchmark-linked obligation, first identify the exact terminal decision output the benchmark is being used to determine. Then minimize the actions and genuinely new information required to determine that output truthfully."
- `canonical/laws/BENCHMARK_MEASUREMENT_VS_CAPABILITY_PROOF_LAW_V2.md`: propositions B (exact branded statistic), C (capability relation), O (ownership); C closes by `EXACT_EQUIVALENCE | CONSERVATIVE_DOMINANCE | OWNER_ACCEPTED_RELATION`; B closes only by `NATIVE_OWNER_RECEIPT | EXACT_STATISTIC_BRIDGE`.
- Precedent that closed a PUBLIC_FIXED_BAR row with zero owner involvement — `LIVEBENCH_IF_GE_65_7` (`OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V3.json`): the scorer's classification space was enumerated (356,352 states, 15 active constraint types), a deterministic solver attains the **pointwise maximum of the scorer on every case**, therefore no Opus response can exceed the Brain's same-case score; Opus's public mean 65.74 ≥ 65.7 ⇒ Brain ≥ 65.7. Zero target rows, responses, or scores used.

## Finding
The pointwise-maximum method has been applied to **none** of the 9 open benchmark rows (0 artifacts match `POINTWISE_MAX|SAME_CASE_MAXIMUM|SCORER_MAX` for CHARTOGRAPHY, OSWORLD, TB4, HLE, GDPVAL, FRONTIERCODE, CURSORBENCH, AUTOMATIONBENCH, FINANCE).

## The criterion (what the IF proof actually required)
A PUBLIC_FIXED_BAR row closes without its owner iff all four hold:
- **(a) Public scorer**: `M` is a public deterministic function (or has a public exact specification).
- **(b) Computable argmax from the public input**: for each case `d`, `max_X M(X, d)` is attainable by a Brain-executable procedure reading only the case input (prompt/instruction/image), without general-purpose cognition.
- **(c) Complete scope**: the scorer's state/constraint universe is finitely classified, so "every case attains the maximum" is proved, not sampled.
- **(d) No leakage**: no benchmark answers, hidden tests, or target responses are used.
Then `Brain(d) ≥ Opus(d)` pointwise, and `Opus_public_mean ≥ bar ⇒ Brain ≥ bar` (CONSERVATIVE_DOMINANCE).

## Row-by-row

| Row | (a) public M | (b) argmax computable from input w/o cognition | (c) finite scope | (d) leakage-free possible | Verdict | P(bar) zero-model |
|---|---|---|---|---|---|---|
| CHARTOGRAPHY_TOOLS_GE_89 | yes (numeric tolerance ranges) | **yes** — value = v₀ + (p − p₀)(v₁ − v₀)/(p₁ − p₀): axis calibration + series extraction is measurement geometry; question arithmetic (lookup/diff/ratio/CAGR/extrema) is a finite grammar | yes — chart-type × encoding × question-type taxonomy (Brain already has `family_atom` cells) | yes — blind solver container, answers held out by the harness | **ROUTE APPLIES** | 0.15–0.25 in 6–10 weeks (bar allows ≤ 11 misses; long tail = dense scatter, 3-D, hand-drawn, OCR of ticks) |
| OSWORLD_2_1_PARTIAL_GE_81_8 | yes (public evaluator functions, finite set) | partial — expected state is reachable via deterministic app drivers (LibreOffice UNO, Chrome prefs/DOM, GIMP script-fu, VLC/Thunderbird prefs, VS Code settings, shell); the instruction → operation mapping is the cognition component; legitimate version covers each app's **operation universe from official docs**, not the 369 sentences | yes — evaluator-type × app-operation universe | yes — read instruction only, never `evaluator.expected` | ROUTE APPLIES IN PRINCIPLE; large program; VM-grade execution needed | 0.03–0.05 in 90 days; P(≥ 40 %) ≈ 0.25 |
| CODING_TB4_GE_66_4 / TB_SCIENCE_GE_58_7 | tests public in repo but task-specific code, hidden at runtime | **no** — each `M_d` is arbitrary code; attaining it from an under-specified NL instruction is program synthesis = general cognition; formally mechanizable subset ≤ ~5 % | **no** finite scorer universe | using tests = leakage | ROUTE DOES NOT APPLY (plus physical cap 46/330 on 4-CPU free runner) | ≈ 0 |
| HLE_TOOLS_GE_67_7 | yes (exact match) | **no** — the argmax is the expert answer itself; only knowledge/reasoning computes it; public gold answers are pure leakage | n/a | lookup = leakage | ROUTE DOES NOT APPLY | 0 |
| PROWORK_GDPVAL_GE_1846, PROWORK/ARTIFACT_AA_BRIEFCASE_GE_1822 | **no** — private LLM-judge pairwise Elo; no computable maximum exists for a black-box preference model | no | no | n/a | ROUTE DOES NOT APPLY; B-class needs owner receipt or exact-statistic bridge (impossible for a hidden judge) | 0 under no-outreach |
| CODING_FRONTIERCODE_GE_54_4, CODING_CURSORBENCH_GE_57_8, AUTOMATIONBENCH_GE_40, FINANCE_AGENT_V2_GE_58_59, FINANCE_ACCOUNTING_INDEX_GE_61, MYSTERYMECHANISM_GE_49_55 | hidden D and/or hidden M | no | **no** — characterizing hidden D = reconstructing hidden task identity (forbidden by both laws) | n/a | ROUTE DOES NOT APPLY | 0 under no-outreach |

## Consequence
- Rows where the Brain's own proven, zero-model, zero-owner route is live: **Chartography (now), OSWorld (large program)**.
- Rows where it is mathematically inapplicable: 10 — because the scorer has no computable argmax (LLM judges), is task-specific code (TB), measures knowledge (HLE), or the case set is hidden (6 private rows).
- The checkpoint conjunction therefore remains 0 under the current ledger regardless of Chartography/OSWorld success; that changes only by owner ledger amendment.

## Execution order for the live row (Chartography)
1. Owner self-service (not outreach, ~2 min): accept the Chartography dataset terms on a free Hugging Face account; add `HF_TOKEN` to the public `verification-capsule-runner`. P = 0.99.
2. Blind harness: solver container receives images + questions only; scorer container holds answers; both pinned by blob. P = 0.9 (agent, 1 day).
3. Scope enumeration from the 100 inputs (never answers): chart-type × encoding × question-arithmetic taxonomy — the Chartography analog of "active 15". P = 0.9 (agent, 1–2 days).
4. Deterministic extractor per taxonomy cell with proved error bound < tolerance under stated rendering assumptions; tick-label reading via deterministic digit templates (or a narrow OCR engine — owner must rule on narrow-tool admissibility under V10). P(all cells covered) ≈ 0.4 (agent, 4–8 weeks).
5. Blind run on the public runner → first real zero-model bar-grade score. P(≥ 89) ≈ 0.15–0.25; P(≥ 60) ≈ 0.5. Independent verification and promotion of the atom if ≥ 89; the family also needs `VISION_DENSE_NONCHART_SCOPE` (MATCHED_SCOPE_AUDIT).

Zero credit is claimed by this document.
