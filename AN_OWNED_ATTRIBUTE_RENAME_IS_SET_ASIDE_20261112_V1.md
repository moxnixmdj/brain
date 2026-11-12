# An owned attribute rename is set aside, and the second showing's injection dies

**2026-11-12.** Base `ff810a5b`. Branch `arena/4688253e-brain`. Follows #6788.

#6788 measured the second showing both ways and left one falsification standing: at two
showings, held_out gained diff 4 / extra 4, all from is_set, whose second teacher tangled its
own `self._stop → self._stop_event` rename into the kind's commit. #6788 named "reduced standing
for one-example rules" as the candidate countermeasure. **Worked from first principles, that
candidate dies before implementation:** the most damaging injected rule
(`?1.isSet -> self._stop_event.is_set`) was supported by *both* examples — their after-sides
coincided by accident of the rename. Support counting cannot see it.

The real mechanics are older than the second showing: this is the **attribute form of the
incidental rename** (#6719's variable form: "an incidental rename in the example is set aside").
The separating principle is *ownership*: a person can only rename what they assign
(`self._stop = threading.Event()` — Store context); a changed attribute nobody assigns in the
file (`isSet` → `is_set`) is a use of someone else's object — behavior, and the lesson.
`attribute_rename_undone` now mirrors `rename_undone`: when exactly one assigned attribute name
is dropped by the example's second file and exactly one appears, the new name is put back to the
old at every attribute it names, before learning reads anything. The rename vanishes from the
lesson; grouping across examples then blanks both sides (`?1.isSet -> ?1.is_set`). A pure-rename
example backs off and stays learnable as it came; a never-assigned attribute change is never
undone.

## 1. Predictions, declared before the measurement ran

Committed and pushed before any corpus run of the changed engine:

1. **held_out at 2 showings: diff 4 → 0 and extra 4 → 0** (the is_set injection dies);
   tried `same` ≥ 157.
2. **fresh at 2 showings unchanged:** strict = shown = tried = 62/0/3/0, refusals 0.
3. **seen at 2 showings unchanged:** strict 48/0/6/0 (1 refused), tried 51/0/3/0 (0 refused).
4. **One-showing tables on all three sets byte-identical** to #6778/#6788
   (fresh strict 83/6/16/13, tried 93/6/6/13·0; held_out strict 156/0/77/0, tried 196/1/36/0;
   seen strict 30/0/73/0, tried 69/2/32/0).

## 2. What landed

One run per configuration, after the declaration commit (22:47:58Z). **All four predictions held.**

| prediction | landed |
|---|---|
| 1. held_out @2: diff 4 → 0, extra 4 → 0, tried same ≥ 157 | **0 / 0 / 161 — held** |
| 2. fresh @2 unchanged (62/0/3/0, 0 refused) | **held** |
| 3. seen @2 unchanged | **held** |
| 4. one-showing tables byte-identical, all three sets | **held** |

```
fresh    at 2 showings: strict = shown = tried = 62/0/3/0, 0 refused   (95% strict)
held_out at 2 showings: strict 158/0/18/0 (4 refused)  tried 161/0/15/0 (2 refused)
seen     at 2 showings: strict 48/0/6/0 (1 refused)    tried 51/0/3/0 (0 refused)
```

**At two showings there is now not a single wrong write on any tracked set** — diff 0 and
extra 0 in every way, on fresh, held_out and seen. The one-showing tables are untouched: a
single showing still faithfully learns everything its example determines, tangles included,
exactly as pinned since #6764.

The is_set questions the injection had poisoned are now byte-matching sames: the undone second
teacher groups with the first into `?1.isSet -> ?1.is_set`, which also reaches events the
examples never named (`self.stop_request.isSet()`), exactly as the persons' edits did.

## 3. Why the declared candidate was killed before implementation

#6788 named "reduced standing for one-example rules" as the next move. Examined against the
actual failure before writing any code, it cannot work: the worst injected rule,
`?1.isSet -> self._stop_event.is_set`, was *supported by both examples* — teacher 1's after-side
read `self._stop_event.is_set()` genuinely, teacher 2's read the same by accident of its rename,
so the group spanned both examples and only the left side blanked. Support counting is blind to
a tangle that coincides with another example's honest text. Ownership is not: `_stop` is
assigned in its file, `isSet` never is. One is a name the person owns and may rename; the other
is someone else's API — behavior, the lesson itself.

## 4. Discipline

* Engine: `attribute_rename_undone`, the attribute form of `rename_undone`, wired directly
  beside it in `learn_all`; back-offs mirror the variable form (pure-rename examples come back
  as they came; never-assigned attributes are never undone; any doubt returns the text unchanged).
* 215 tests pass: 206 taught-action + 4 new attribute-form pins + 5 protocol.
* Bundle re-taught (engine source embedded); model recompiled after this report and the intent;
  verify 33/33.
* Declaration precedes measurement in branch history and push time; each configuration ran once.

## 5. Next

* Plural replacements (fresh one-showing diff 6) remain intrinsic to one showing; a project-side
  signal (the target project's own usage of the two candidates) is the only honest
  discriminator named so far.
* Extract-variable: the first reshaping whose example tangles *out* rather than in.

