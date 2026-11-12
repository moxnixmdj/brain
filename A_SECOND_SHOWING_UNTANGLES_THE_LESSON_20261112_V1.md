# A second showing untangles the lesson from the teacher's other habits

**2026-11-12.** Base `8238d637`. Branch `arena/0e163c42-brain`. Follows #6778.

The pre-registered fresh set of #6764 left two intrinsic one-showing boundaries standing: the
**intent tangle** (`extra` 13 — one fail_unless teacher whose commit was a multi-kind cleanup,
and one showing cannot separate the lesson from the teacher's other habits) and **plural
replacements** (`diff` 6 — np_object, where the ecosystem offers two valid targets). #6764 and
#6778 both declared the same next move: *a second showing*.

The engine has carried the mechanism since #6686, pinned in its own words: *"several examples
are read as one … code any example left alone speaks against a rule that fits it."* The 2026
literature prescribes exactly this consolidation — reliable skill evolution must capture patterns
across multiple trajectories, not individual behaviors (arXiv 2606.11435), and stored skills help
mainly where procedures must be exact unless they are abstracted across experiences
(arXiv 2608.03874). What the repository has never done is **measure** multi-showing teaching on
the tracked corpus. This turn adds `--showings N` to the measure harness (teachers are the first
N commits of a kind, read as one lesson; their files never appear as targets; default 1 is
byte-identical to the old protocol) and runs the declared measurement.

## 1. Predictions, declared before the measurement ran

Written and committed to this file before `measure --showings 2` was executed on any set. The
second teacher of each kind has not been looked at.

1. **fresh at 2 showings: `extra` = 0.** All 13 one-showing extras are the fail_unless intent
   tangle. The doctrine predicts the second example's untouched code kills the tangled rules.
   This is the risked claim: it fails if the second fail_unless example happens to contain no
   code the tangled rules fit.
2. **fresh at 2 showings: tried refusals = 0.**
3. **fresh at 2 showings: every `different` comes from np_object.** Plural replacements are
   intrinsic: a same-kind second showing repeats the teacher-side choice and cannot reveal the
   other project's preference.
4. **held_out and seen at 2 showings: `diff` = 0 and `extra` = 0 in every way.** The safety
   claim: a second showing may widen correctly or narrow, but never writes a wrong line.
5. **Regression: at 1 showing, all three sets reproduce the #6778 tables byte for byte**
   (fresh strict 83/6/16/13, tried 93/6/6/13 with 0 refusals; held_out strict 156/0/77/0,
   tried 196/1/36/0; seen strict 30/0/73/0, tried 69/2/32/0).

Kinds with fewer than 3 commits drop out of a 2-showing run by construction (fresh keeps 8 of
9 measurable kinds — basestring has only 2 commits; totals therefore shrink and are reported
as their own table, never as a revision of the one-showing numbers).

## 2. What landed

One run per configuration, after the declaration commit was pushed (22:09:35Z).

| prediction | landed |
|---|---|
| 1. fresh at 2 showings `extra` = 0 | **0 — held** (13 → 0: the fail_unless tangle died) |
| 2. fresh at 2 showings tried refusals = 0 | **0 — held** |
| 3. every fresh `different` from np_object | **held vacuously — diff fell to 0** |
| 4. held_out and seen at 2 showings diff = extra = 0 | **seen held (0/0); held_out FALSIFIED: diff 4, extra 4** |
| 5. one-showing regression, three sets byte-identical | **held** |

```
fresh    at 2 showings: 8 kinds (1 not learned), 24 files, 65 questions
         strict = shown = tried = 62 same / 0 diff / 3 left / 0 extra / 0 refused
held_out at 2 showings: 27 kinds (1 not learned), 94 files, 176 questions
         strict 154/4/18/4 (4 refused)   tried 157/4/15/4 (2 refused)
seen     at 2 showings: 14 kinds (2 not learned), 31 files, 54 questions
         strict 48/0/6/0 (1 refused)     tried 51/0/3/0 (0 refused)
```

**Fresh strict same-rate rose from 79% (83/105) at one showing to 95% (62/65) at two** — on
never-seen kinds, under the harness's teachers-never-targets rule. The `left` collapse (16 → 3)
means the second example's differing places widened the blanks exactly as the doctrine says.

## 3. The falsification, diagnosed to the line

All 4 diff + 4 extra at two showings are **one kind, is_set**. The second is_set teacher
(`fiefdx/MyNote`) tangled its own bug fix into the kind's commit: besides `isSet() → is_set()`
it renamed `self._stop → self._stop_event` (its comment: shadowing `threading.Thread._stop`
had made `'Event' object is not callable`). The first teacher's file never contained a
`self._stop` — so no example's untouched code could speak against the rename rules, and they
survived into the lesson, renaming other projects' `self._stop` events (which the persons did
not do) and even widening into `?1.isSet -> self._stop_event.is_set`.

So the measured law is symmetric, and sharper than the hope:

* a second showing **removes** tangle where any example's untouched code speaks against it
  (fresh: the second fail_unless teacher's file contained `assertEquals` calls left alone —
  extra 13 → 0);
* a second showing **injects** tangle where only the new teacher carries a habit and no other
  example has code of that form at all (held_out: is_set 0 → 4+4).

The doctrine *"code any example left alone speaks against a rule that fits it"* behaved
exactly as written; what is now measured is its boundary: **silence is not dissent.** An
example that has no code of a rule's form neither supports nor opposes it.

Five kinds also refuse to learn at two showings (mpl_get_cmap, set_daemon, yaml_safe_load,
utcnow + one more conflicting pair): the engine's conflict gates ("the same code was left
alone, or changed another way"; "adds, removes or reshapes whole statements") refuse rather
than guess when the second example disagrees in shape. Those kinds drop out instead of
writing anything — refusal, not damage.

## 4. What this answers, and the next reachable move

The owner's question — can the model learn the smartest actions from one exposure,
permanently? — now has a two-sided number: one showing generalizes at 79% strict on
never-seen kinds; a **vetted** second showing lifts it to 95%; an **unvetted** second showing
can inject the new teacher's habits. More exposures are not monotonic improvement; they are
monotonic only in what the examples jointly witness.

Next reachable engine move, now named with evidence: **a rule shown by only one of several
examples should carry its one-example standing into the rewrite** — e.g. enter a target only
when the target's own project check or another example corroborates it, while rules every
example supports keep full standing. That is a declared-first engine turn of its own; nothing
was patched post hoc this turn.

## 5. Discipline

* Harness: `--showings N` (default 1 byte-identical; teachers never targets; small kinds drop).
* 5/5 protocol tests (one new, pinning the showings semantics); 206/206 taught-action tests;
  engine untouched; bundle expected byte-identical and verified so.
* Declaration commit precedes the measurement in branch history and in push time.

