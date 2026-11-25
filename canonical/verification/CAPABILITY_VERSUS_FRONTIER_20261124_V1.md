# Capability versus frontier — 24 November 2026

The question: what are *our* most advanced capabilities, including work that never landed on `main`, and who wins at each
one against the frontier. This document answers per capability, with the evidence and where it came from. Nothing here is
asserted that is not either measured in this repository or cited to a dated outside source; where the honest answer is
"unknown", it says so.

---

## 1. What was audited (our side)

| surface | size | how it was read |
| --- | --- | --- |
| repository | 6,249 Python modules, 44 top-level domains | enumerations, not memory |
| unified model | **447 capabilities, 294 receipt-backed, 153 bound, 26 engines, 18 skills, 701 knowledge documents, 2,027 source-index modules, 7,377 research records** | `canonical/unified_model/BRAIN_UNIFIED_MODEL_V1.json` |
| remote branches | **6,963 total; 98 `arena/*` session branches** | GitHub API sweep of every `arena/*` branch against `main` |
| landed | **17 of 98** session branches fully in `main` (behind/identical) | `compare/main...<branch>` per branch |
| not landed | **81 diverged**, carrying capability work | head subject per branch |
| measured receipts | 17 result files under `canonical/Immediate_Results/`, plus rounds V5–V27 | parsed, headline numbers quoted below |

The unified model's own non-claims are worth quoting because they bound everything else:
`NOT_A_TRAINED_NEURAL_NETWORK__CONTAINS_NO_WEIGHTS`, `NOT_AN_INDEPENDENT_VERIFICATION__SANDBOX_MEASUREMENT_ONLY`,
`NOT_TERMINAL_AUTHORITY__ZERO_CAPABILITY_AND_TERMINAL_CREDIT`, `KNOWLEDGE_IS_INDEXED_NOT_EMBEDDED__RETRIEVED_JUST_IN_TIME`.

### Capability work found only on other branches (not on `main`)

| branch | ahead | what it holds |
| --- | --- | --- |
| `arena/cdfc4713-brain` | 171 | closed-loop slider control, 2/5 measured — corrections remove coarse error but not error below actuator resolution |
| `arena/4f36ef34-brain` | 169 | "the loop that had nothing to decide with, and now does" — decision substrate |
| `arena/b81b2217-brain` | 75 | causal-angelic CoW engine, OSWorld-style long-horizon slicing |
| `arena/3c70152b-brain` | 72 | transfer of reviewed experience as bounded input challenges |
| `arena/4ca3a720-brain` | 69 | scoped composer safeguards |
| `arena/e705f1be-brain` | 24 | BugsInPy blind corpus runner, donor retrieval, contract refusal |
| `arena/086851e2-brain` | 9 | Chartography: kernel-backed chart/table extractor, 13 tests |
| `arena/98e3c624-brain` | 8 | "a lesson is a substitution, an edit is a composition" — selection vs composition on 47 real files |
| `arena/9026f2bc-brain` | 9 | the store knows a format under a name it was never taught |
| `arena/00723d68-brain` | 1 | tree repair solver on 100 HumanEvalFix bugs: 53 pass their tests |

These are capabilities we own but have not merged; several are thematically adjacent to what I measured on `main` this
week (V24–V27 are about selection vs composition, which `98e3c624` attacked independently).

---

## 2. Frontier reference points (outside sources, November 2026)

| benchmark | best number | caveat |
| --- | --- | --- |
| SWE-bench Pro, independent (Scale SEAL, public set) | **61.5%** — Muse Spark 1.1, then GPT-5.4 (xHigh) 59.1% | the credible cross-model number |
| SWE-bench Pro, vendor-reported | 89.9% Claude Opus 5.5; 93.0% Claude Fable 5.2 | vendor scaffolds; not comparable to Scale's |
| SWE-bench Verified | 76.8% bash-only harness; 79.2% with custom scaffolds | different benchmark, not comparable to Pro |
| Terminal-Bench 2.0 | 82.7% GPT-5.5 (xHigh) vendor; agent-level 90.2% (vix on Opus 4.7) | versioning is a mess (2.0 vs 2.1) |
| OSWorld 2.0, strict binary completion | **20.6%** — Claude Opus 4.8, max thinking, 500 steps, 54.8% partial | 108 long workflows, ~318 tool calls, median 1.6 h human time |
| OSWorld 2.0 horizon decay | 20–24% under 45 min; **~0% above 163 min** for every model plotted | the failure is state management, not clicking |
| continual learning (CL-Bench, 2026) | dedicated memory systems **do not** improve continual learning; naive in-context learning beats them | the frontier's own memory products do not clear this bar |

Two numbers in circulation conflict and I will not paper over it: the OSWorld 2.0 paper and two aggregators report
20.6% strict binary completion, while one secondary source lists GPT-6 Astra at 72.6%. The 72.6% figure is not the
strict binary metric of the paper. I treat **20.6% strict** as the frontier reference.

---

## 3. Who wins, capability by capability

Verdicts are per capability, not overall. "Ours" means measured in this repository; "frontier" means the numbers above.

| # | capability | ours (evidence) | frontier (evidence) | winner |
| --- | --- | --- | --- | --- |
| 1 | **Blind repair at benchmark scale** | 2/89 (2.2%) on blind real fixes; 5/30; 2/13 cJSON (15.4%); 6/30 packaging; 11/13 (84.6%) on a 13-commit test-present stream — all own corpora, n ≤ 89 | **61.5%** on SWE-bench Pro's 1,865 tasks, independently measured | **Frontier**, decisively, on breadth and credibility |
| 2 | **Cost per solved task** | **$0.00, 0 model calls** on every run cited above | $2.75K–$3.87K per OSWorld 2.0 task suite; $20/M tokens | **Ours** |
| 3 | **Determinism and reproducibility** | identical inputs give identical outputs; every claim carries a receipt and a rerunnable command | sampling, scaffold drift, vendor-vs-independent spread (61.5% vs 89.9% on the same benchmark name) | **Ours** |
| 4 | **Refusal discipline (knowing it cannot observe)** | `attrs@3b0378dd66` refused with `REFUSED__OBSERVER_CHANGES_THE_PROGRAM`, violations discarded, exit 3; a 17-rule referee that cannot be bypassed even by the owner's token | no frontier system reports "my instrument changed the program" | **Ours** |
| 5 | **Single-experience accumulation** | laws recur across independent repos: **6 of 6** laws fire in ≥2 commits, `iterable_retyping` in 4; edits recur in **3.7%** of occurrences; isolation selector 50% precision / 100% recall; true detection repaired on attempt 1 | CL-Bench: memory systems do not improve continual learning, ICL beats them | **Ours** — by default, because the frontier has no measured positive here |
| 6 | **Long-horizon computer use (300+ steps)** | designed (Petri slicing, CoW rollouts, checkpoints) but **unmeasured** on any official OS benchmark; no Docker or KVM in this sandbox | **20.6%** strict binary, collapsing to ~0% beyond 163 minutes | **Frontier** — our claim is a design, not a number |
| 7 | **GUI perception (charts, canvas, OCR)** | Chartography branch: 13 tests, synthetic receipts, not on `main` | frontier VLMs read charts and screenshots natively at scale | **Frontier** |
| 8 | **Multi-file coupled edits** | ideas (def-use zipper, dual-program splicing) exist; not measured end-to-end | SWE-bench Pro patches average ~4.1 files; models solve them at 61.5% (independent) | **Frontier** |
| 9 | **Natural-language understanding and instruction following** | none of our own: retrieval, laws, and AST machinery; no language model in the runtime | the entire frontier product | **Frontier**, and it is not close |
| 10 | **Codebase-scale comprehension** | incremental semantic graph at **0.001 s warm**; 2,027 indexed modules; U-IR lifted across C/Python/JS | ~1M-token context; reads what it is given, no persistent index | **Split**: ours wins retrieval latency and persistence, frontier wins depth and generality |
| 11 | **Oracle manufacture (no failing test given)** | metamorphic laws manufacture violations the repo never wrote; isolation keeps 2/2 true detections; issue-only audit 2/2 with the held-out upstream suite passing | frontier agents write their own tests routinely, but their tests are proposals with no discipline for "this violation is about this failure" | **Contested**: ours is auditable and cheap, frontier is broader; neither is demonstrated at scale |
| 12 | **Verification of a repair before shipping** | law suite refutes on the fixed tree; 889-test hidden suite reached after the patch was chosen (`click@05f6fd0`) | held-out grading only; no in-loop behavioural law | **Ours** |

**Scoreboard: ours 4 (cost, determinism, refusal, single-experience recurrence) + 1 split; frontier 6; contested 1.**
On raw capability the frontier wins the capabilities that matter most for "computer use": general repair, long-horizon
execution, perception, language. We win the capabilities that no frontier system has at all: zero-cost determinism,
refusal discipline, and measured single-experience recurrence.

---

## 4. What the audit changed about our own picture

1. **The honest centre of gravity is not the 447-capability registry.** Those are bound OS/file/CLI adapters. The
   capabilities that are actually ahead of the frontier are the measurement disciplines (V22, V25–V27), and the ones that
   are behind are general reasoning and perception — which we do not have and do not claim.
2. **Eighty-one session branches hold unmerged capability work**, including a chart extractor, a slider controller, and an
   independent attack on selection-vs-composition. Nothing in this document claims them as shipped capability; they are
   listed as owned but unlanded.
3. **Our best public claim is not a benchmark score.** It is that a repair can be produced for $0.00 with zero model
   calls, refuted by a law, refused when the instrument lies, and reproduced by anyone — and that the recurring unit of
   learning is a law (6/6) rather than an edit (3.7%).
4. **The frontier's weakest measured point is exactly our target**: long-horizon state, where the best system completes
   20.6% and collapses to ~0% past 163 minutes. That is where our Petri/CoW/checkpoint design would have to be tested on
   an official harness to mean anything.

## 5. Non-claims

- No number here is a claim of parity with frontier models on any public benchmark. We have not run SWE-bench Pro,
  Terminal-Bench, or OSWorld on an official image; this environment has no Docker or KVM.
- The 84.6% figure is a 13-commit stream, not a benchmark.
- The "244 verified commits" and "45/45 corpus" figures that appear in earlier reports were **not** reproducible from this
  checkout and are not used here.
