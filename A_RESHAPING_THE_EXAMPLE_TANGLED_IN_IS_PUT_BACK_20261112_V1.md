# A reshaping the example tangled in is put back

**2026-11-12.** Base `19281c7c`. Branch `arena/5ce68cd0-brain`. Follows #6742.

#6742 fixed the first form of the tangled-commit phenomenon (an incidental rename beside the real
lesson) and named the rest "intrinsic". That label was checked this turn instead of trusted, and it
was **half wrong**: of the six kinds refusing as "adds, removes or reshapes whole statements", five
were tangles too — a person wrapped one statement in a loop, added one `@staticmethod`, split one
call, *beside* dozens of mechanical edits worth teaching. Refusing the whole example lost all of it.

## 1. What was built

`restructures_put_back` in `edit_by_example_v1`, applied to every example entering `learn_all`
(after `rename_undone`): each changed place that cannot hold a rule — `levels_of` refuses it — is
located at its innermost statement pair, put back to how the first file had it (decorators
included; `FunctionDef.lineno` excludes them, which cost `getchildren` until spans were widened),
and its span handed to the existing `unsettled` machinery: not evidence of anything, neither a
change to learn nor code left alone that could speak against a rule beside it. The reshaping is
quarantined, never taught. Still refusing, honestly: statements that came or went at the top of a
file (nothing to localize), an example that was nothing but the reshaping (nothing left to teach),
and a put-back that fails to re-parse.

This is the demonstrated-edit analogue of what imitation learning calls *extraneousness-aware*
learning (EIL, arXiv 2210.01379; SMILE, arXiv 2310.15815): learn selectively from the task-relevant
parts of an imperfect demonstration — except here the extraneous segment is identified by a sound
syntactic criterion, not a learned heuristic, and what is set aside is provably restored, not
estimated.

## 2. The measurement, same tracked sets

Declared before measuring: kinds not learned 6→small, `same` and `tried` rise, `diff` stays 0,
`extra` stays 0, seen set unchanged. Landed:

| held_out | #6742 | now |
|---|---|---|
| kinds not learned | 6 | **0** — every tracked held-out kind now learns |
| questions in reach | 179 | **233** |
| `repeat` same / diff / extra | 130 / 0 / 0 | **156 / 0 / 0** |
| `repeat_tried` same | 160 | **196** |
| refused files (strict / shown) | 14 / 3 | 14 / 3 |

The seen set did not move by one digit. Every file-level refusal left in the shown way is still
the unresolvable-import class, by design.

Across the three-turn arc (#6730 → #6742 → this): held-out `same` 122→156, `tried` 147→196, kinds
unlearned 7→0, with `diff` 0 and `extra` 0 throughout.

## 3. Receipts

```
pytest -q canonical/tests/test_a_reshaping_the_example_tangled_IN_is_put_back_v1.py   11 passed
pytest -q  (all ten taught-action test files)                                        302 passed
PYTHONPATH=. python3 canonical/tools/teach_actions_v1.py   11 skills, bundle 8edb0f99… (re-taught)
python3 canonical/tools/edits_repeated_across_projects_v1.py measure held_out|seen     the table
```

## 4. Non-claims

"Every kind learns" means every kind in the tracked corpus learns *its mechanical part*; the
reshapings themselves are quarantined, not learned — `left` grew from 49 to 77 questions precisely
because the newly-reached files contain person edits the engine honestly declines. One showing
still underdetermines restructuring itself; that boundary did not move, it was *located correctly*
this time. A top-of-file statement addition still refuses whole. `tried` remains a ceiling of a
sufficient check. truth.achieved stays false; $0; the result-bearing path has zero model
dependency.
