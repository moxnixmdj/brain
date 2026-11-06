# Unified model gap analysis (read-only)

Scripts and outputs that label every tracked Python file once, so the scattered
parts of the project can be seen in one place. Nothing here changes the compiled
model (`../BRAIN_UNIFIED_MODEL_V1.json`) or its verifier.

## Coverage of the compiled model

The compiler covers a file in two ways (see `canonical/runtime/compile_brain_unified_model_v1.py`):

- as a `source_index` row: 1,948 `canonical/runtime` modules that are not capabilities;
- as a capability's `provenance.source_path`: 215 files.

Non-test Python files: 2,850. Covered: 2,163. Uncovered: 687 (`out/real_gap_summary.json`).

## Labels

- `out/module_labels.csv`: one label for each of the 5,297 tracked `.py` files (`module_labels.py`).
- `out/real_gap_labels.csv`: one label for each of the 687 uncovered non-test files (`label_real_gap.py`).
- `out/outside_runtime_review.csv`: the 175 uncovered files outside `canonical/runtime`, sorted by whether a tracked record names them (`review_outside_runtime.py`).

Labels that are weak and need a human check:

- `CURRENT` means "highest version number in a family, or a single-version file." It is not verified to be the live version. In 17 multi-version families, an older version is imported and the newest is not (`out/current_vs_imported_summary.json`).
- `RETIRE_CANDIDATE` and `USED` come from a coarse, name-based import check.
- `REFERENCED_BY_RECORD` means the path appears in a tracked non-Python file. It doesn't show the reference is current.

## Rerun order

```
python3 canonical/unified_model/gap/version_families.py
python3 canonical/unified_model/gap/current_vs_imported.py
python3 canonical/unified_model/gap/runtime_triage.py      # needs out/gap_classified.csv
python3 canonical/unified_model/gap/classify_gap.py
python3 canonical/unified_model/gap/module_labels.py
python3 canonical/unified_model/gap/real_gap.py
python3 canonical/unified_model/gap/label_real_gap.py
python3 canonical/unified_model/gap/review_outside_runtime.py
```

`model_gap.py` and `triage.py` are the earlier steps: the first compares the index with the tree, and the second groups honest-suite failures from a junit file.

## Not done

- Folding these labels into the compiled model needs a change to the compiler. That needs owner approval.
- Value scoring needs owner-approved weights (draft in `/home/user/ledger/SCHEMA.md`, which is outside the repo and not durable).
- Test outcomes are not joined to these labels yet. The honest-suite run from before the environment reset was not completed.
