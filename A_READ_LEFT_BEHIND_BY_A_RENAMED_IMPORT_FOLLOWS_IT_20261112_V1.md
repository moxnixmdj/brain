# A read left behind by a renamed import follows it

**2026-11-12.** Base `8439f609`. Branch `arena/f0beac73-brain`. Follows #6719.

Three held-out refusals were left, all of one shape: the example renames an imported name **on the
import line itself** (`from django.utils.encoding import force_text` → `force_str`, Django 4's
documented direct replacement) and shows one call; the file to edit reads the old name in forms the
example never showed — another argument, a second argument, a bare reference. The teacher's shown
argument starts from an import, so no reading can widen to those forms, and the engine refused each
whole file: *"takes the name 'force_text' away ... line 341 still uses it."*

The refusal was protecting a file that is already lost: after the demonstrated import edit, every
leftover read of the old name is a certain NameError. There is no sound completion except following
the renamed definition — which is what all three people did. So that is now the rule, and it is the
rule the 2026 rename tooling applies when a *person* asks for a rename (resolved references, never
text; refuse on shadowing); here it fires only when an example demonstrated the map.

## 1. What was built

`renames_to_add` in `edit_by_example_v1`: when a rewritten import line is an `ImportFrom` of the
same module with the same number of names and a bound name changed, the old→new map is read off
the line, and every read of the old name that no rule reaches becomes a one-name rewrite riding
the same edit. Nothing follows where the map is unsure:

* two renames that disagree on the name — nothing follows;
* a new name the file already binds — nothing follows (the refusal stands rather than re-bind);
* an old name something else in the file also binds — nothing follows, and the rules themselves
  already decline the call, because the name no longer cleanly means the import;
* a read a function rebinds locally — skipped, and the refusal stands for it;
* strings, attributes, relative imports — never touched.

The pass is unconditional in `written`, so a lesson that remembers a tried file with a followed
read still replays byte-for-byte (pinned by test). One old parametrized expectation moved: the
refused "bare read after an import rename" case is now the positive; the refusal that stands in
its place is the locally-shadowed read.

## 2. The measurement, same tracked sets

Declared before measuring: held-out repeat 122→125, refused 14→11 and 6→3, tried 147→150, extra
stays 0, seen unchanged. Landed exactly:

| held_out (27 kinds, 97 files, 169 questions) | #6719 | now |
|---|---|---|
| `repeat` same / files refused | 122 / 14 | **125 / 11** |
| `repeat_tried` same (ceiling of a sufficient check) | 147 | **150** |
| statements touched that the person left alone | 0 | 0 |

Two of the three files come out **byte-identical** to the person (laxy, pgweb). The third differs
only where the person wrote a try/except compatibility import; the engine's plain rename is the
statement the person also changed, so nothing is counted against either. Every refusal left in the
shown/tried ways is now of one class: the three diofant files whose teacher import resolves only
inside its own project, each refused naming the import. The seen set did not move by one digit.

## 3. Receipts

```
pytest -q canonical/tests/test_a_read_left_behind_by_a_renamed_import_follows_it_v1.py   11 passed
pytest -q  (all eight taught-action test files)                                        280 passed
PYTHONPATH=. python3 canonical/tools/teach_actions_v1.py     11 skills, bundle ab4366dc… (re-taught)
python3 canonical/tools/edits_repeated_across_projects_v1.py measure held_out|seen       the table
```

## 4. Non-claims

The map is read from one import line, positionally, same module, same count — a reordered import
list or a split line yields no map and keeps the refusal. The rename follows the *binding*, not
the runtime object: a module that re-exports the old name elsewhere is out of sight, exactly as it
is for every text-free rename tool. The locally-shadowed read keeps a refusal that is strictly
overcautious (the local binding would survive), inherited and unchanged. `tried` remains the
ceiling of a sufficient check; the 3 unresolvable-import refusals remain by design. No capability
is registered; `truth.achieved` stays false; $0; the result-bearing path has zero model dependency.
