# Enrollment gate: what the root can actually dispatch

- registry rows: live 145, snapshot 146, extended 2321, projection 321, pending bindings 18 → merged 2490 | admitted by `load_verified_registry`: **462**
- provides vocabulary 683, requires vocabulary 125
- rows dispatched as the declared native kind `runtime_native_action`: 2 (no adapter file expected; listed, not counted as a defect)
- `OWNED_FAMILY_ROUTES` (fact): ownership-matrix route modules, 4 named, INVENTORY_ONLY__NOT_DISPATCH_SHAPE 3, RECEIPTED__NO_INDEPENDENT_VERIFICATION 1 -- an inventory row is not enrollment; only ADMITTED means the root can dispatch it
- harness-certified capabilities: 11 — registry-bound 11, pending binding only 0 (), unenrolled 0
- **clean: False**

| defect class | count | what it means for 'one model' |
|---|---|---|
| `DANGLING_ADAPTER` | 0 | the dispatch table names code that is not in the tree |
| `MISSING_VERIFICATION_RECEIPT` | 3 | admission rule 2 is cited but the evidence file is gone |
| `UNSATISFIABLE_REQUIRES` | 25 | a planner can never satisfy these preconditions from registered work |
| `UNENROLLED_CERTIFIED_CAPABILITY` | 0 | the strongest measurements are not dispatchable and not even queued |
| `FAMILY_ROUTE_FILE_MISSING` | 0 | an owned capability family cites a route module that is not in the tree |
| `REGISTRY_VS_SNAPSHOT_DIVERGENCE` (fact, not a defect) | 35 | by design: the snapshot is a floor and the merge is a union, so divergence cannot delete a row -- it is drift to read, not a defect to block |

`MISSING_VERIFICATION_RECEIPT`:

- code.multilanguage.parse.tree_sitter.v1 -> canonical/verification/HARDCORE_VERIFY_CODE_MULTILANGUAGE_PARSE_TREE_SITTER_V1_V1.json
- software.hardcore.kernel.orchestrate.v1 -> canonical/verification/HARDCORE_VERIFY_SOFTWARE_HARDCORE_KERNEL_ORCHESTRATE_V1_V1.json
- software.synthesis.grid_induction.v1 -> canonical/verification/HARDCORE_VERIFY_SOFTWARE_SYNTHESIS_GRID_INDUCTION_V1_V1.json

`UNSATISFIABLE_REQUIRES`:

- archive.tar_gz.available
- artifact.file.available
- candidate.response_or_fields.available
- chart.query.x_value.available
- chart.query.y_value.available
- chart.question.binary_phase_solvus.available
- chart.question.legend_linear_intersection.available
- chart.series.label.available
- git.repository.available
- image.file.available
- manifest.json.available
- markdown.file.available
- network.http.available
- node.runtime.available
- pdf.file.available
- pdf.file.image_only.available
- pypi.live_metadata.available
- pypi.selection.available
- raw_task.text.available
- source.candidate.provenance.verified
- structured.json.available
- structured.release_claim.available
- trades.json.available
- typed.scalar.inputs.available
- yaml.file.available
