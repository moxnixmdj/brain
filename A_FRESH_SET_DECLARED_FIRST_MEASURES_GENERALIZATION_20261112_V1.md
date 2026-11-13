# A fresh set, declared first, measures generalization

**2026-11-12.** Base `5df74130`. Branch `arena/fc6ffba9-brain`. Follows #6749.

With all 27 tracked held-out kinds learning, the only honest question left was the one the owner
keeps asking: *does it generalize?* The corpus's own protocol answers it: kinds are declared
before commits are looked at. So this turn ran the engine's first **pre-registered, final-test-once
generalization measurement** (the protocol the evaluation literature now names exactly that:
arXiv 2412.03700, arXiv 2608.26170): sixteen new kinds written into `KINDS["fresh"]`, committed and
**pushed publicly at 20:20:48Z before `collect fresh` ran**, collection walked GitHub's answers
mechanically, and `measure fresh` ran once. No engine code changed in this turn.

## 1. Declared predictions, and what the test did to them

Declared with the kinds, before any commit was seen: `diff` = 0, `extra` = 0, ≥ 8 of 16 kinds
learn, `same` ≥ 40% of strict questions.

| fresh (9 measurable kinds, 42 files, 105 questions) | declared | landed |
|---|---|---|
| kinds that learn | ≥ 8 | **9 of 9 measurable** (12 found commits; 3 teacher-only; 4 found nothing) |
| strict `same` | ≥ 40% | **83/105 = 79%** |
| `diff` | 0 | **6 — falsified** |
| `extra` | 0 | **13 — falsified** |

The two misses decompose into exactly two named phenomena, both diagnosed to the line:

* **`extra` 13, all one kind (fail_unless):** the teacher's real commit was a *multi-kind cleanup* —
  beside `failUnless→assertTrue` it also converted `assertEquals→assertEqual`. The engine learned
  everything the example determines (by design, and faithfully); the held-out humans applied
  narrower judgment about which cleanup belonged in their commit. One showing cannot distinguish
  "the lesson" from "the teacher's other habits" — only a second showing could, by keeping the
  rules both examples support. The repeated edits are *correct migrations*; `extra` counts
  faithfulness to the demonstration against conformance to the person. The old sets never
  exercised this because their teachers happened to be single-minded.
* **`diff` 6, all one kind (np_object):** the ecosystem offers **two valid replacements**
  (`np.object`→`object`, as the teacher chose, and →`np.object_`, as the persons chose). The
  engine followed its teacher; no one-showing learner can know the other project's preference.
* The three `smart_str` refusals name a reachable gap: the needed name was already imported in the
  teacher's own file, so the lesson knows its origin — a bring-from-the-example's-imports rule is
  the next engine turn's candidate.
* `mpl_get_cmap` went almost entirely to `left`: the modern form is a call→subscript reshape plus
  an import change — the engine honestly declined what one showing underdetermines.

## 2. What this says

Generalization to never-seen kinds largely held: 79% of questions byte-matched the human on first
contact, every measurable kind learned. And the fresh wild immediately surfaced the two boundaries
the curated sets could not: demonstrations are tangled *in intent*, not just in syntax, and some
migrations are genuinely plural. Both now have names, lines, and counts instead of being unknown.

## 3. Receipts

```
git log: declaration commit pushed 20:20:48Z; collect fresh ran after; measure fresh ran once
pytest -q canonical/tests/test_a_generalization_set_is_declared_before_it_is_collected_v1.py  4 passed
python3 canonical/tools/edits_repeated_across_projects_v1.py measure fresh    the table above
teach_actions --check: same_as_tracked_bundle true (no engine change this turn)
```

## 4. Non-claims

The fresh numbers are one draw of GitHub's commit search on one day, kept mechanically; they are
not a distribution. `tried` on fresh (90/105, 3 refusals) remains a ceiling of a sufficient check.
The two falsified predictions are left falsified — no post-hoc engine patch rode this turn, per
the no-post-hoc-protocol-changes discipline. truth.achieved stays false; $0; the result-bearing
path has zero model dependency.
