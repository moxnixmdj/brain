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

*(filled in after the single measurement run, below)*
