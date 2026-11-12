# A dead import the example also removed is taken away

**2026-11-12.** Base `65578066`. Branch `arena/235fa916-brain`. Follows #6709.

#6709 ended with four counted-against-the-engine statements on the held-out set: in the four
apache/allura files the person swapped `import cgi` for `import html` in place; the engine brought
`import html` and left the dead `import cgi` behind — the same residue the migration literature
reports for one-shot migration. This round takes that line away, on the same ground the bring
stood on: **the example itself removed exactly that import as part of exactly this change.**

Tools that remove unused imports blind dare it only for the standard library — autoflake's default,
"other modules may have side effects that make them unsafe to remove automatically." A demonstration
is stronger than a guess: a person removed this line alongside this edit and kept the result.

## 1. What was built

* **Learned, never guessed.** `Shown` now keeps the import lines the example removed
  (`removed_lines`), exactly as it keeps the added ones; a rule takes a name away only when every
  example removed one same line for it. Two examples that removed the name two ways take nothing.
  Only absolute imports binding exactly one name count; relative imports and `import a, b` never do.
* **Taken only where everything is certain.** After the edit has passed every existing check, the
  line goes only when the file holds exactly that statement, on lines of its own, without a comment,
  sharing its lines with nothing, and the finished file reads or writes the name nowhere
  (`imports_taken_away`). Anything less certain leaves the line where it is.
* **Never a refusal.** Keeping an import is never wrong the way removing a used one would be, so
  this rule has no refusal class: where the conditions fail, the file simply keeps the line — the
  behavior every round before this one had.
* The lesson says it: `teaches[n]["takes away"] = {"cgi": "import cgi"}`; old lessons are untouched.

## 2. The measurement, same tracked sets

Declared before measuring: held-out `extra` 4 → 0, every other number of #6709 unchanged.

| held_out (27 kinds, 97 files, 169 questions) | #6709 | now |
|---|---|---|
| `repeat` same / files refused | 122 / 14 | 122 / 14 |
| `repeat_tried` same (ceiling of a sufficient check) | 147 | 147 |
| statements changed/removed that the person left alone | 0 | **0** |
| statements added/removed the person did not match | 4 | **0** |

Exactly that. In the four allura files the only difference from the person is now the *position*
of `import html` (the person wrote it where `import cgi` stood; the engine appends after the last
import) — statement for statement they agree. The seen set is unchanged (30/69, 0 extra), i.e. the
engine never removed an import any person kept. The measuring tool changed with the behavior:
`answers()` used to read an engine deletion as "left alone"; it now counts a removed statement
against the engine unless the person changed or removed that statement too, and an added statement
may also match what the person put at a place they changed. Under the stricter counting the old
engine scores extra 4 — the new one scores extra 0 under the rules its predecessor was judged by
and under the stricter ones.

## 3. Receipts

```
pytest -q canonical/tests/test_a_dead_import_the_example_also_removed_is_taken_away_v1.py   12 passed
pytest -q  (all seven taught-action test files)                                           269 passed
PYTHONPATH=. python3 canonical/tools/teach_actions_v1.py      11 skills, bundle c5b8c9a8… (re-taught:
                                                              the engine's source is embedded)
python3 canonical/tools/edits_repeated_across_projects_v1.py measure held_out|seen          the table
```

No prior test changed: a kept import was never asserted anywhere an example had removed it.

## 4. Non-claims

The three force_str refusals remain: their blocker is a use the rules cannot reach (*"takes the
name 'force_text' away ... line 341 still uses it"*), a rule-widening problem, not an import one.
The removal check is syntactic presence of the name, so a file reading the module through
`globals()` or `getattr` tricks would lose its import — exactly as it would under the person's own
edit in the examples, and no such file exists in either measured set. A module imported only for
its side effects is removed only if the examples' author removed it too — the demonstration is
trusted over the fear, and that trust is the whole rule. `tried` remains the ceiling of a
sufficient check. No capability is registered; `truth.achieved` stays false; $0; the result-bearing
path has zero model dependency.
