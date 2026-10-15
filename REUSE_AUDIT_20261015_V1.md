# REUSE AUDIT — 8 model-dependent families vs Brain-owned mechanisms (Phase A)

Date: 2026-10-15. Status: ANALYSIS (no code, no credit, no spend). Authority: none.

## Method
For each of the 8 `EXTERNAL_CAPABILITY_SPECIMEN_FOUND` families, map its required output to Brain's already-owned mechanisms (bound capabilities + runtime kernels). Classify: (i) already owned, needs integration (CONFIGURE/INTEGRATE, days); (ii) owned component + gap (ADAPT); (iii) genuine invention (SYNTHESIZE, with exhausted-reasons). Also audit the 13 open obligation bars the same way (work backwards from output to mechanism).

## Brain-owned mechanisms available (from BOUND_CAPABILITY_REGISTRY_V1.json, 66 entries + runtime kernels)
- Document: create/verify OOXML, PDF text/OCR, markdown→PDF, XLSX create/verify, chart read from pixels (axis title/unit binding, curve value/x-at-y, legend style, scene graph, binary phase solvus, legend linear intersection).
- Code: model-free test-guided Python repair loop (AST), strict-progress variant, fault localization (dynamic dataflow), source/test audit.
- Data: SQLite create/verify, JSON records, archive tar.gz create/verify, YAML→JSON, msgpack, CBOR, BSON, jq query.
- Vision/barcode: QR generate/decode, zbar decode.
- Reasoning: source ranking (BM25), evidence extract, decision synthesis, knowledge fetch/assess/assert, browser capture, HTTP JSON fetch.
- Meta: authenticated Pareto scheduler, capability-first ranking, same-identity supervisor (checkpoint/relaunch), terminal k* root assess.

## Family-by-family reuse map

| Family | Best external route (specimen only) | Brain-owned mechanisms that cover the OUTPUT | Classification | Route | Est. days |
|---|---|---|---|---|---|
| BUSINESS_WORKFLOW_AUTOMATION | GPT-6 Astra Work + connectors | browser capture, source ranking, evidence-to-decision synthesis, supervisor (checkpoint/relaunch), repair loop | owned components + gap (multi-app orchestration glue) | ADAPT/COMPOSE | 3–5 |
| MULTIDISCIPLINARY_TOOL_AUGMENTED_REASONING | GPT-6 Astra + web/code/Wolfram | source ranking, knowledge fetch/assess/assert, evidence extract, decision synthesis, repair loop, scheduler | owned components + gap (long-horizon planning loop) | ADAPT/COMPOSE | 4–6 |
| AGENTIC_SCIENTIFIC_RESEARCH | GPT-6 Astra Work/Codex + web/code/Wolfram | same as above + chart read from pixels, PDF text/OCR | owned components + gap (research loop, experiment tracking) | ADAPT/COMPOSE | 4–6 |
| VISION_AND_DENSE_DOCUMENT_UNDERSTANDING | GPT-6 Astra Work + image/file analysis; Sonnet 5.5 Chartography 90.2 | chart read from pixels (6 capabilities), doc verify OOXML, PDF text/OCR, XLSX verify, markdown→PDF | mostly owned; gap is dense visual understanding beyond charts | ADAPT (small gap) | 2–4 |
| COMPUTER_AND_BROWSER_USE | GPT-6 Astra Work computer use | browser capture, source ranking, supervisor, repair loop | owned components + gap (browser control primitives) | ADAPT/COMPOSE | 4–6 |
| FINANCIAL_ANALYSIS | GPT-6 Astra Work + Wolfram + spreadsheet | XLSX create/verify, SQLite verify, source ranking, evidence extract, decision synthesis, repair loop | owned components + gap (financial formulas, JIT filings) | ADAPT/COMPOSE | 3–5 |
| COMMUNICATION_AND_SYNTHESIS | GPT-6 Astra / GPT-5.6 Sol + Brain style policies | evidence-to-decision synthesis, source ranking, repair loop | owned components + gap (style/instruction policies, breadth) | ADAPT/COMPOSE | 2–4 |
| UNKNOWN_DOMAIN_ADAPTATION | GPT-6 Astra + JIT web + tool discovery | tool discovery/selection/learning (owned), knowledge fetch/assess/assert, source ranking, repair loop, scheduler | owned components + gap (novel-domain generalization) | ADAPT/COMPOSE | 4–6 |

Conclusion of Phase A: **0 of the 8 require pure invention (SYNTHESIZE_NEW_PRIMITIVE).** All 8 are ADAPT/COMPOSE over already-owned deterministic mechanisms. The "learned residual" (if any) is harvested from open-source donors (trymeka/agent, visnia-ai/browser-agent, Alibaba-NLP/DeepResearch, genspark-ai/genoffice) through the transfer gate (causal ablation, held-out, donor deletion) — donor is acquisition-time only, never runtime.

Expected requalification: 4–6 of 8 in 45 days (not 2), because the work is integration, not invention. P(≥4 requalified in 45d) revised upward from 0.3 to ~0.7.

## Bar-by-bar reuse audit (work backwards from output to mechanism)

| Bar | Required output | Brain-owned mechanism that produces it | Gap | Est. days |
|---|---|---|---|---|
| CODING_TB4_GE_66_4 | code repair success ≥66.4% | model-free test-guided Python repair loop (bound, MEASURED_SANDBOX) | scale + held-out verification | 7–14 |
| CODING_FRONTIERCODE_GE_54_4 | code gen ≥54.4% | repair loop + source audit + test audit | gen (not just repair) — gap | 14–28 |
| CODING_CURSORBENCH_GE_57_8 | code editing ≥57.8% | repair loop (strict progress) + fault localization | editing-specific oracle | 7–14 |
| CHARTOGRAPHY_TOOLS_GE_89 | chart reading ≥89% with tools | chart read from pixels (6 capabilities, MEASURED_PASS components) | already close; verify on held-out | 3–7 |
| HLE_TOOLS_GE_67_7 | HLE with tools ≥67.7% | source ranking + evidence extract + decision synthesis + repair loop + knowledge fetch | orchestration + held-out | 14–28 |
| OSWORLD_2_1_PARTIAL_GE_81_8 | computer use ≥81.8% | browser capture + tool discovery + supervisor | browser control primitives (gap) | 14–28 |
| TB_SCIENCE_GE_58_7 | science tasks ≥58.7% | research loop (source ranking + evidence + synthesis + repair) | science-specific tooling | 14–28 |
| AUTOMATIONBENCH_GE_40 | automation ≥40% | browser capture + tool discovery + synthesis | multi-app orchestration (gap) | 14–28 |
| FINANCE_ACCOUNTING_INDEX_GE_61 | finance ≥61 | XLSX verify + SQLite + source ranking + JIT filings | financial formulas + filings (gap) | 14–28 |
| FINANCE_AGENT_V2_GE_58_59 | finance agent ≥58.59 | same + repair loop | agent orchestration | 14–28 |
| PROWORK_GDPVAL_GE_1846 | professional work ≥18.46 | doc verify + XLSX + PDF + synthesis | professional-task breadth | 21–42 |
| PROWORK_AA_BRIEFCASE_GE_1822 | artifact ≥18.22 (shared measurement) | doc verify + XLSX + PDF + chart read | shared measurement protocol | 21–42 |
| MYSTERYMECHANISM_INTRINSIC_OPUS55_NONINFERIORITY_OR_STRONGER | intrinsic noninferiority | exact linear parameter polytope + interval-information frontier (both built) | internal proof work | 7–14 |

Conclusion: 1 bar (CHARTOGRAPHY) is likely achievable in days (mechanism already MEASURED_PASS). 1 (CODING_TB4) is achievable in 1–2 weeks (repair loop exists). The rest are 2–6 weeks. None require invention beyond what's already owned + integration.

## Impact of Phase A
- Phase D revised: 4–6 of 8 requalified in 45 days (P 0.7), not 2 (P 0.6).
- Phase E revised: 2 bars achievable in <14 days (CHARTOGRAPHY, CODING_TB4); rest 2–6 weeks.
- The "sky" move: the creature's credit and bars are mostly an INTEGRATION problem over already-owned mechanisms, not an invention problem. This is the single most important finding of this audit.

## What I will do next (decisive, no more hedging)
1. Phase A is complete (this file). 
2. Start Phase B (provably alive) now: B1 reachability fix (3 caps), B2 adapter import fix (11), B3 measurement coverage (15 families), B4 public receipt (gated on billing), B5 ledger promotion.
3. Phase B is verification, not invention — it can run in parallel with Phase A's implications.
4. I will prepare the Phase B PR (intent + registry edit + referencing-file sha update + adapter fixes) and run intent-check + heartbeat before opening it. No merge over red referee.

Next: I begin Phase B. First concrete action: write the action intent and the registry edit for B1 (3 zero-input capabilities), then run intent-check and the heartbeat to confirm 66/66 reachability.