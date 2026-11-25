# Hidden capabilities, lifted into the model and the runtime — 24 November 2026

The claim was that we had solved things under non-obvious names and that the
unified model did not know it. That is true, and it was measurable. This records
what was hiding, what now reaches the model and the runtime, and what still
cannot be claimed.

## 1. The blind spot was structural, not accidental

Three layers each looked complete and each excluded the same population:

* **The receipt lane's `discover()` walks the registries.** A module must own a
  bound or extended-registry row before it can be probed. Nothing that was never
  declared can ever be probed, so nothing that was never declared can ever earn
  the evidence that would admit it. The population was unreachable by
  construction, not rejected on merit.
* **`source_index` walks only `canonical/runtime`.** Measured: 506 of the 626
  discovered surfaces live elsewhere — `canonical/tools` 322, `canonical/swe_kernel`
  94, `execution_guard` 25, 46 at the repository root.
* **Nothing enumerated the tree by invocation shape.** Whether a module can be
  called at all is a property of its AST — `run(args, root) -> dict`, or a
  `main`/`__main__` entry — and no artefact asked that question.

## 2. What the census found

`canonical/tools/harvest_hidden_capabilities_v1.py`, over 3,463 Python modules
(excluding tests, `__pycache__`, `tmp` and vendored trees):

| measure | count |
| --- | --- |
| modules parsed | 3,464 |
| contract shape (`run(args, root)`) | 308 |
| program shape (`main` / `__main__`) | 1,187 |
| importable library, no invocation shape | 1,918 |
| already declared (by id **or** by source path) | 850 |
| declared by capability id but never linked by path | 19 |
| **discovered, undeclared, executable** | **626** |

The 19 matter: a module can name its capability in its own docstring header and
still be absent from any path index, because the bound registry records
`adapter_module` and resolves the file by stem. Counting those as hidden would
have inflated the headline by 3%; they are excluded.

Distribution of the 626 by location: `canonical/tools` 322, `canonical/swe_kernel`
94, `canonical/runtime` 120 (75 program + 45 contract), `execution_guard` 25,
46 at the root, 19 across `intake`, `scripts`, `verification`, `canonical/experiments`.

They are not trivia. Among them: `bound_capabilities/jq_query.py` (bounded jq),
`numeric_expression_sympy.py` (typed symbolic arithmetic),
`chart_positioned_ocr_axis_binding_v1.py` (positioned OCR → chart axes),
`docx_verify_ooxml_intent.py` (DOCX content vs creation intent),
`concrete_execution_oracle.py` and `crosshair_contract_oracle.py` (two independent
oracles), `python_change_impact_testselect.py` (diff → minimal test set),
`git_bisect_regression.py`, `swe_kernel/computer_use_agent_v1.py`,
`swe_kernel/egraph_and_deductive_synthesizer_v1.py`,
`swe_kernel/real_commit_repair_v1.py`.
None of them was in the compiled model as anything you could call.

## 3. What changed

* **The model** (`compile_brain_unified_model_v1.py`) now emits a
  `harvested_capabilities` section: 621 rows (626 minus the 5 the compiler
  resolves as an admitted capability's adapter), each with path, `sha256`,
  invocation shape, entrypoint, any capability id the module declares about
  itself, declared inputs and result fields, and routing triggers. Counts
  appear alongside the admitted ones (`harvested_capabilities`,
  `harvested_contract_surfaces`, `harvested_program_surfaces`,
  `harvested_admitted`). Every row carries `admitted: false`,
  `capability: false`, `admission_state: DISCOVERED_NOT_ADMITTED`.
  The rows are re-derived from the tree on every compile, so a stale census
  cannot outlive its files, and the archive digest covers them.
* **The runtime** has an entry: `canonical/runtime/harvested_capability_runtime_v1.py`.
  Given an id (or a path) and the arguments the module documents, it executes
  the module through `capability_receipt_lane_v1.execute_and_receipt` — the
  project's only executor — and returns `{status, observed, receipt_path,
  admitted: false, model_calls: 0}`. A surface that cannot run returns
  `REFUSED` with a reason instead of a fabricated result.
* **The lane** gained one additive parameter, `probe_args`, so a caller that
  already knows the invocation can supply it. Default remains `None`, so every
  receipt the lane issued before issues identically.
* **The front door** (`UnifiedModel`) exposes `harvested_surfaces()` and
  `find_harvested(id)`. `route()` and `solve()` are untouched: a discovered
  surface is never routed to, because routing is a capability claim.
* **The verifier** has a new category, `HARVESTED_SURFACE` (5 cases): rows
  exist, every row's `sha256` matches its live file, no row claims admission or
  collides with an admitted id or path, every row is routable, and the route
  file exists. Full run: **38/38 PASS**.

## 4. Measured execution, not claims

Blind execution is not the mechanism, and the census says so instead of assuming
it. On a sample of 80 contract surfaces invoked with `{}`: **7 returned a dict;
73 refused with a typed reason** — `MISSING_REQUIRED_ARGUMENTS`,
`PATH_INVALID:None`, `INPUT_FILE_MISSING`, `ORACLE_TARGET_MISSING`,
`BROWSER_URL_INVALID`, or a structured `{"capability": ..., "error": true}` body.
These are adapters validating their inputs, not broken modules.

With their documented inputs, they run. Executed through the runtime tonight:

| surface | inputs | result |
| --- | --- | --- |
| `bound_capabilities/jq_query.py` | real JSON + jq filter | `output_verified: true`, output `b` (correct), receipt issued |
| `bound_capabilities/concrete_execution_oracle.py` | source + sample | executed, `status: NO_POSTCONDITION_PARSED` (honest: no postcondition in the snippet) |
| `python_test_corpus_discovery_v1.py` | none | refused — no structured result |
| `python_change_impact_testselect.py` | source root + changed paths | refused — needs a real diff argument |
| `numeric_expression_sympy.py` | — | cannot run here: `sympy` is not installed in this sandbox |

Every successful call wrote a producer receipt into
`canonical/astra_runtime/evidence/` and staged an additive entry in
`CAPABILITY_RECEIPT_PROJECTION_V1.json`.

## 5. What this does not claim, and the next bottleneck

* **Not admission.** The loader requires a different identity to re-run each
  receipt with signed GitHub OIDC claims. This work produces the candidates that
  lane could never see; it cannot verify itself, and the verifier fails the build
  if any harvested row claims otherwise.
* **Not "all 621 execute".** Two of five sampled adapters ran with the inputs at
  hand; the rest need *their* inputs. The next bottleneck is mechanical input
  synthesis per documented contract — the same job `declared_probe_args` does for
  registry entries, which has nothing to read for a surface with no row. That is
  the honest next build, and it is a smaller problem than it looks: 41 of the 622
  are contracts whose inputs are already written down in their own docstrings.
* **Not terminal authority.** Sandbox measurement only.

## 6. Reading this against the frontier

From `CAPABILITY_VERSUS_FRONTIER_20261124_V1.md`, our weakest line was "ours is
small and self-defined". This changes that picture in one specific way: the
surface we own was never 447 descriptors. It is 447 admitted plus 621 discovered,
and the discovered half includes oracles, OCR, symbolic arithmetic, test
selection, bisection and document verification that were simply unindexed. It
does not raise the 2/89 blind-repair rate. It removes the excuse that we did not
know what we had.
