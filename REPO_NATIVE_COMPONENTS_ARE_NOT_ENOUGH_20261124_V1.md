# Repo-native components are not enough when the failing case has no differential

**Round.** `arena/3fc9b5f0-brain`, 2026-11-24. **Authority:** `NONE__PRODUCER_RUN_SANDBOX`.
Producer-run measurements, no third-party verifier. §6 is not met; no merge.

**Artifacts.** `canonical/swe_kernel/repo_native_component_mining_v1.py`,
`canonical/verification/REPO_NATIVE_COMPONENT_MINING_20261124_V1.json`,
`canonical/tests/test_repo_native_component_mining_v1.py` (4 tests, OK).

## 0. Requirements and §2

Own weights/architecture/agent; zero runtime model calls; no world-fact warehouse in parameters;
every parameter calculated and justified; external inspectable instant-knowledge store; one
experience writes an abstracted rule there; research before building; first principles; remove
parts; hardest real tests with no leakage, hand-solving or borrowed outputs; one branch, one final
merge only after §6. §2 stays as settled: forbidden = parameter fact lookup or runtime model
dependency; allowed = an external computed-with store plus one-experience learning.

## 1. Claim audit from the quoted architecture thesis

Verified in this checkout: the 75.2% reach figure is a **project measurement** over 2,178 fix pieces
from 500 SWE-bench Verified tasks (`WHY_ONE_EXPERIENCE_IS_NOT_ENOUGH_20261116_V1.md`);
`HONEST_SUITE_BASELINE_20261014_V1.json` records 344 failed cases, but later receipts record 380 and
984, so "344" is stale, not current; `zygote_worker_pool_v1.py` claims a ~1–2 ms CoW fork;
`incremental_semantic_graph_v1.py` claims ~0.35 s warm indexing. Those are code/receipt claims, not
newly re-measured here.

Not present under the quoted names in this checkout: `typed_invention_v1.py`,
`CUMentalWorldModel`, `MealyAPICompiler`, `epistemic_doc_compiler`,
`calculate_separating_projection`, `verified_skill_crystallizer_ir_bridge_v1`,
`epistemic_scan_acquire_compress_v1.py`, `BRAIN_POLYGLOT_CST_SKILL_STORE_V1` as named,
iteration `209bbc6c`, `__CST_ID0__`, `FOREIGN_IDENT_UNBOUND`, `BELIEFWEAVER`. Related objects with
different names do exist: `operand_invention_v1.py`, `verified_skill_crystallizer_v1.py`,
`code_polyglot_transform_and_verify_v1.py`, `incremental_semantic_graph_v1.py`,
`cow_impact_repair_engine_v1.py`, `zygote_worker_pool_v1.py`, `consistency_vs_equivalence_v1.py`.
The quoted architecture should therefore be treated as an unverified input, not as installed machinery.

Current hard benchmarks were re-read, not assumed: SWE-bench Pro private top score 61.5% on 8 Nov 2026
[5](https://www.benchleader.com/benchmarks/scale_swe_bench_pro_private);
OSWorld 2.0 has 108 long workflows, ~318 tool calls, median 1.6 h [3](https://arxiv.org/pdf/2606.29537v1);
Terminal-Bench 4.0 top score 65.15% on 19 Nov 2026 [2](https://www.vals.ai/benchmarks/terminal-bench-4).
We have no adapter, Docker harness or independent verifier for any of them, so **no score is claimed**.

## 2. Bottleneck, plan, rejected ideas

The chosen bottleneck was the measured 75.2% reach wall: a fix needs components absent from the
defective file. The existing answer is partial: `operand_invention_v1` introspects the modules the
target file imports, and `incremental_semantic_graph_v1` indexes repository symbols but does not
feed synthesis. The minimal addition is to mine components from **other modules of the same
repository**, admit them only when an observed attribute separates failing parameters from their
passing siblings, insert a real import, adjoin a guard, and let the whole test file decide.

Rejected: a larger fixed grammar (the 75.2% measurement says it buys names already supplied);
borrowing frontier model outputs (integrity violation); treating mined symbols as trusted because
they exist (the suite, not provenance, must decide); storing mined lists as knowledge (that would
be a world-fact warehouse in the store).

"Am I sure this is the smartest approach?" No — and the result below says why: the differential
precondition is often absent, so the design is not universal. It was still worth building because
it tests the exact bridge from repository structure to a verified guard without a model.

## 3. Build and hard test

The tool harvests top-level classes/functions/methods/constants from every Python module in the
target package, imports the real module in a worktree, evaluates candidate attributes on the
failing and passing inputs, and compares against the existing imported-module control at the same
60-trial cap. Two bugs were found and fixed before the recorded run: package modules under `src/`
were named `src.click` instead of `click`, and pytest ids that are values (`[b]`) were treated as
non-indexable by the inherited numeric-only indexer.

Fresh corpus: 12 one-source/one-test click commits unused by any earlier receipt. Result:
**0/12 verified** in both control and treatment, 45.2 s, zero parameters/model calls/network.
Treatment produced no candidate on any row. Diagnosis: 0/12 failing tests supplied a usable
parametrized differential to the inherited extractor — their node ids are custom multi-parameter
ids or the parametrize table is indirect. "Repo-native components" cannot be admitted when no
passing/failing value pair exists to constrain them.

## 4. Verdict and next bottleneck

Real: repository module/type harvesting works mechanically; the control/treatment harness and
flaky-test filtering work; a stale claim (344 baseline failures) and several nonexistent quoted
identifiers were corrected. Failed: repo-native mining improves nothing on this corpus (0/12).
Unproven: dual-program splicing, 16-way CoW rollouts, unified Petri-net compilation, live
SWE-bench Pro / Terminal-Bench 4.0 / OSWorld 2.0 scores, single-experience transfer.

The next bottleneck is **differential acquisition**, not component supply: obtain a real
passing/failing pair for a test whose id does not expose its parameter table. The smartest route is
to run the failing test and one minimally perturbed input in a CoW fork, read the state divergence,
and use that pair as the constraint. This reuses `zygote_worker_pool_v1` rather than adding a new
search grammar. If no contrast can be manufactured, no symbolic generator can be admitted, and the
row must be recorded as REFUSED rather than scored as a failed guess.

## 5. Limits

Producer-run; one repository; 12 real commits; no independent verifier; no live benchmark run.
The tool edits one guard only. §6 remains unmet. No merge.
