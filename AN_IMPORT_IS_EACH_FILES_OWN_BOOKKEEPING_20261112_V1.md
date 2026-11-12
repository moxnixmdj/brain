# An import is each file's own bookkeeping

Date: 2026-11-12 (T34). Engine: `canonical/swe_kernel/taught_actions/edit_by_example_v1.py`.
Base: main `0d888623` (post-#6805, carries T33 `attribute_rename_undone`).

## The refusal this closes

After T33, four kinds still refuse at two showings on held_out. Diagnosed each:

| kind | refusal | diagnosis |
|---|---|---|
| utcnow | "same code was left alone ... elsewhere" | example 1 keeps `from datetime import datetime` untouched; example 2 widens the same line to `..., timezone`. The code-level lesson agrees perfectly; only the **import lines** dissent. |
| yaml_safe_load | "adds/removes/reshapes whole statements" | example adds a new `_make_safe_yaml` def beside the in-place lesson — pure-addition reshaping, NOT an import problem. Out of scope here (T35). |
| set_daemon | "adds/removes/reshapes whole statements" | same shape: mass additions beside `setDaemon(True)→daemon=True`. Out of scope (T35). |
| mpl_get_cmap | needs-gate | `matplotlib` not importable in the target — a **correct** refusal. Must stay. |

## The principle

A from-import line is not part of the lesson — it is each file's own bookkeeping
about where its names come from. Two examples whose code-level edits agree can
legitimately disagree on their import lines, because each file already had
different imports before the person arrived. So:

1. **Set-aside:** when a cross-example rule group fails and every place on both
   sides is an import statement, the group is dropped silently — no import rule
   is learned, and no refusal poisons the code-level lesson.
2. **Standing bring:** what the rewritten code *needs* is established per target.
   If a learned rule's standing name (e.g. `timezone`) is not defined, imported,
   or provided in the target, and the target owns exactly one plain from-import
   line of the right module with the name free, that line is extended
   (`from datetime import date, datetime` → `..., datetime, timezone`).
   Ambiguity (zero or several candidate lines, name taken, aliased/starred
   imports) still refuses — the engine never guesses.

Mechanism: import-only failing groups skipped in the `rules` loop;
new `aliases_to_add(text, places, fail_at)` chained in `written()` after
`renames_to_add` + `aliases_to_follow`.

Pinned by 2 new tests in
`canonical/tests/test_an_import_the_example_added_is_brought_where_it_resolves_v1.py`
(217 engine tests total, 215 pass here; the 2 non-passing are the
namespace-sandbox door tests that fail on the clean base of this machine
before any T34 change — pre-existing environment, green in CI).

## Predictions — declared before the measurement run

Measured after this declaration is pushed: one run per configuration,
`--showings 1` and `--showings 2`, on fresh / held_out / seen. No re-draws.

P1. **utcnow learns at two showings.** The "same code was left alone" refusal
    for utcnow disappears on held_out @2; its targets are answered, not refused.
P2. **held_out @2 strict refusals drop below 4** (T33: 4) and strict correct
    rises above 158 (T33: 158). yaml_safe_load, set_daemon, mpl_get_cmap remain
    refusals — the first two are a different (T35) mechanism, the third is a
    correct needs-gate.
P3. **Zero wrong writes at two showings everywhere stays.** @2 wrong = 0 on
    strict and tried for all three sets (T33: 0 across the board).
P4. **No one-showing regression.** @1 wrong does not rise on any set
    (T33 strict wrong: fresh 6, held_out 0, seen 0); @1 strict correct does not
    fall (fresh 83, held_out 156, seen 30). The standing-bring step may convert
    some @1 misses into matches; it must not create new wrong writes.

## Results (filled after the single measurement run)

_pending_

## What this does not claim

Pure-addition reshapings (yaml_safe_load, set_daemon) are untouched and still
refuse. mpl_get_cmap stays refused on purpose. The honest frame stands: the 8.13x
figure is cached exact recall; there is no any-action-once capability and no
sentience; improvement comes only from mechanisms like this one — declared,
measured once, and kept honest when a prediction falsifies.
