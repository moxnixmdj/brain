# A name the examples already imported is brought, and its alias follows the renamed uses

**2026-11-12.** Base `df7faf2f`. Branch `arena/bbc362d9-brain`. Follows #6764.

The fresh-set measurement of #6764 left exactly one gap it called *reachable*: the three
`smart_str` refusals, where the needed name was already imported in the teacher's own file, so the
lesson knew its origin and refused anyway. This turn is the engine move #6764's report declared as
next: **bring a needed name from the examples' own imports**. Working it to the ground exposed a
second, deeper half of the same gap, and both halves are now engine capabilities:

1. **Bring from the examples' standing imports.** When the new code needs a name no example
   *added* a line for, but every example file imports it from one unambiguous absolute place, the
   lesson now synthesizes the bring line itself (`from django.utils.encoding import smart_str`)
   from the recorded origin. It is skipped where the rewrite's own import places will bind the
   name, and the resolution gate still decides whether it may enter a project.
2. **The import alias follows the renamed uses.** The actual refused files
   (`import_export/widgets.py`, three forks) import the old name *among others*:
   `from django.utils.encoding import force_text, smart_text`. The teacher's whole-line import
   rewrite cannot reach that line, and pasting a parallel import would not be what any person
   does — the persons renamed the one alias where it stands. The engine now does exactly that,
   as the statement-level sibling of the existing `renames_to_add` (where a renamed *import*
   pulls stray *reads* along, the new `aliases_to_follow` lets renamed *reads* pull their
   *import alias* along). It fires only when everything is certain: every read of the old name
   sits inside a place being rewritten, the new name is free, exactly one line binds the old
   one, and the lesson knows the origin module matches.

## 1. Declared predictions, and what the measurement did to them

Declared before re-measuring (fresh re-measures are tracked-set regression checks; the one-shot
pre-registered draw was consumed in #6764 and is not revised):

| prediction | landed |
|---|---|
| fresh tried refusals 3 → 0 | **0 — held** |
| fresh tried `same` rises | **90 → 93 — held** |
| fresh `diff` frozen at 6 | **6 — held** |
| fresh `extra` frozen at 13 | **13 — held** |
| held_out strict `same` ≥ 156, `diff`/`extra` 0 | **156/0/0 — held** |
| seen unchanged | **unchanged — held** |

Full tables after the change:

```
fresh     strict 83/6/16/13 (1 refused)   shown 84/6/15/13 (0)   tried 93/6/6/13 (0 refused)
held_out  strict 156/0/77/0 (14 refused)  shown 156/0/77/0 (3)   tried 196/1/36/0 (3)
seen      strict 30/0/73/0  (1 refused)   shown 30/0/73/0  (0)   tried 69/2/32/0  (0)
```

The first attempt — synthesis alone, with a conservative skip when the file already imports from
the module — moved nothing: the three files then failed `names_still_hold`, because skipping the
bring leaves `smart_str` genuinely unbound. That diagnosis is what surfaced the alias-following
half. The falsified interim prediction (that synthesis alone would clear the refusals) stands
recorded here: the real mechanics of the gap were one level deeper than #6764's report named.

## 2. What the person did, and what the engine now does

Teacher (`dbca-wa/prs`): `from django.utils.encoding import smart_text` →
`... import smart_str`, uses renamed. Target (`django-import-export`, 3 forks):

```
before:  from django.utils.encoding import force_text, smart_text
person:  from django.utils.encoding import force_str, smart_str
engine:  from django.utils.encoding import force_text, smart_str
```

The engine renames the one alias its lesson covers and the uses with it — the file is correct and
imports resolve. `force_text → force_str` is a *different* lesson no example in this kind shows;
the engine's line is counted `left`/`different` against the person's at that line, exactly as the
honesty of the measure demands, while all renamed uses byte-match (`same` +3).

## 3. The canonical test that encoded the old limit

`test_an_import_changed_together_with_its_uses_is_repeated_when_every_use_is_covered` asserted
that `from m import other, old_name` + a covered call must **refuse** ("the calls are not changed
on their own"). The spirit of that assertion — never break the file — is preserved by stronger
means: the alias follows, so the calls are *not* changed on their own. The test now asserts the
full person-shaped rewrite `from m import other, new_name`. The demand-only test of the bring
family likewise now asserts the successful bring from the examples' standing imports.

## 4. Discipline

* 206/206 taught-action tests pass (two rewritten to the new, stronger expectations).
* Bundle re-taught (engine source is embedded): sha `ccc8b31b…`, 11 skills.
* Unified model recompiled after this report and the intent were written; verify 33/33.
* Guards unchanged; `aliases_to_follow` is gated by the same `names_still_hold`,
  resolution, and single-binding certainties as everything else — anything less certain leaves
  the line alone.

## 5. Next

* A second showing against the intent tangle (`extra` 13) — the only honest way to separate the
  lesson from the teacher's other habits.
* Extract-variable: the first reshaping whose example tangles *out* rather than in.
