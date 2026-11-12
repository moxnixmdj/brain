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

**P1 FALSIFIED. P2 FALSIFIED. P3 HELD. P4 HELD.** Recorded, not erased.

Every corpus number is byte-identical to T33 — the mechanism caused no corpus
movement in either direction:

| set @showings | strict same/diff/left/extra (ref) | tried same/diff/left/extra (ref) |
|---|---|---|
| fresh @1 | 83/6/16/13 (1) | 93/6/6/13 (0) |
| held_out @1 | 156/0/77/0 (14) | 196/1/36/0 (3) |
| seen @1 | 30/0/73/0 (1) | 69/2/32/0 (0) |
| fresh @2 | 62/0/3/0 (0) | 62/0/3/0 (0) |
| held_out @2 | 158/0/18/0 (4) | 161/0/15/0 (2) |
| seen @2 | 48/0/6/0 (1) | 51/0/3/0 (0) |

Why P1 fell. Two errors in the declaration, both found by re-diagnosis after
the run:

1. **Set mis-mapping.** utcnow lives in *seen*, yaml_safe_load in *seen*,
   mpl_get_cmap in *fresh* — not all in held_out as declared. P2 was therefore
   aimed at the wrong table from the start.
2. **The real pair disagrees in substance, not just in imports.** Example 1
   rewrites `datetime.utcnow()` → `datetime.now(datetime.UTC)`; example 2
   rewrites it → `datetime.now(timezone.utc)` *and* tangles in an unrelated
   `st.dataframe(use_container_width=True → width="stretch")` edit. The import
   set-aside worked exactly as built — utcnow's refusal changed from the
   spurious "same code was left alone elsewhere" (import dissent read as lesson
   dissent) to the true "the rules worked out from the examples do not
   reproduce example 2" (the two people did different things). No import
   mechanism can or should bridge two different replacement texts; writing
   either variant would contradict one example. **This refusal is correct.**

What survives falsification: the principle and the mechanism are right and
pinned by unit tests (clean import widening end-to-end; forced import dissent
dropped without poisoning the lesson). On this corpus no kind at two showings
was blocked *only* by imports — the one suspected kind was also blocked by a
genuine disagreement the old refusal message had masked. The mechanism's
measurable value here is diagnostic honesty (the refusal now names the real
cause) plus zero-regression generality for future corpora where import-only
dissent does occur.

## What this does not claim

Pure-addition reshapings (yaml_safe_load, set_daemon) are untouched and still
refuse (T35 ground). mpl_get_cmap stays refused on purpose (needs-gate).
utcnow stays refused on purpose (the examples disagree). The honest frame
stands: the 8.13x
figure is cached exact recall; there is no any-action-once capability and no
sentience; improvement comes only from mechanisms like this one — declared,
measured once, and kept honest when a prediction falsifies.
