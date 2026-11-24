# A check that nobody runs is a check that cannot be wrong

**Round:** `A_CHECK_THAT_NOBODY_RUNS_IS_A_CHECK_THAT_CANNOT_BE_WRONG_20261203_V1`
**Receipt:** `canonical/verification/A_CHECK_THAT_NOBODY_RUNS_IS_A_CHECK_THAT_CANNOT_BE_WRONG_20261203_V1.json`
**Instrument:** `canonical/tools/a_check_that_nobody_runs_is_a_check_that_cannot_be_wrong_v1.py`
**Date:** 2026-12-03 · **Model calls:** 0 · **Stored parameters:** 0 · **Network at run time:** 0

---

## 0. The headline

The last round ended by naming one unfinished thing and refusing to leave it:

> "**Repair `check_flags()` in the shipped guide.** It calls `shred --verbose` a read-only check.
> That is a one-line defect in canonical code, it is independent of every machine measured here,
> and leaving it is not an option the next round should have."

This round paid that. The defect was real and is fixed. It was also **not one line**, and the
line was not the interesting part.

| measured on this machine | before | after this round |
|---|---|---|
| flags the shipped rule certified as read-only | 2,319 | 2,297 |
| of those, that **change bytes when run** | **16** | 14 in the rule, and the 14 are refused a citation |
| pages the guide attaches a citation to | 370 | 363 |
| of those citations, **vacuous** (accept every object) | **281** | 0 handed to a destroyer |
| destroying checks reported `ACCEPTED_INERT` | **7 of 8** | 0 of 8 |
| the round's own 13 needs, verdicts | 11 held / 2 refused | **11 held / 2 refused** |

Three findings, in the order they hurt:

1. **The citation is never executed.** Every compiled step carries a `check` field taken from the
   page's own flags. Nothing reads it. `goal_holds()` runs its own programs, `edges_of()` never
   looks at `checks`, and `attempt()` does not run it either. The guide's claim that a page's
   check decides whether the input is intact is a claim about a program it never asks.
2. **When it is read, it is vacuous.** `checks[0]` is the alphabetically first flag the rule
   certified, and on 249 pages the first is `--help`. `shred --help`, `rm --help`, `truncate
   --help`, `unlink --help` are what the guide attaches to a destroying step.
3. **And the status the guide reports for a destroyed file is `ACCEPTED_INERT`.** `run()` decided
   "changed" by comparing the room's *type map* before and after. A kind is blind to an overwrite.
   `shred -v payload.txt` fills the file with random bytes, leaves a file of the same kind in the
   same name, and comes back `{"changed": false}` — "succeeded and changed nothing", for an object
   whose bytes are gone. **7 of the 8** destroying checks that were accepted were reported INERT
   this way.

The repair is three lines of substance (a forbidden vocabulary, an execution test, a digest
comparison) and one refusal. The refusal is the honest part: the citation cannot be repaired from
the page, because **3 of 87 graph edges** have any flag that can tell one object from another.

## 1. What was claimed, before anything ran

Declared in the instrument's `judged()` and copied into the receipt under
`declared_before_the_run`, twelve gates, each with a falsifier. Two could have killed the round
outright:

* **C4** — that the repair removes every writer **without naming one**. If the rule had needed
  `shred` and `split` on a list, the repair would be the blacklist the last round already argued
  is worthless on an unseen machine.
* **C9** — that the guide reports at least one destroyed object as untouched. This one is about
  the *shipped* code, so it had to be measured against a restatement of the shipped comparison,
  because by the time it was measured the tree no longer contained that comparison.

## 2. The prose test, and what a prose test is worth

Shipped rule, verbatim:

```python
return sorted({flag for flag, row in declared.items()
               if row["words"] and row["words"][0] in CHECK_VERBS and not row["arg_type"]})
```

`CHECK_VERBS = ("list", "show", "print", "display", "test", "check", "verify", "give")`.

Run every certified flag against a real object, each in its own copy of the room, and compare the
content digest of every file:

```
certified: 2,319 (program, flag) pairs      runs: 4,638      changed bytes: 16
ln --verbose        shred --verbose        split --verbose
stream -help        stream -im6 -version   wdctl --oneline      (and 10 spellings)
```

`shred -v`'s page says *"show progress"*. Its first prose word is `show`. It takes no argument. So
it is a read-only check by the shipped rule, and it destroys the object it is given.

The one-line fix — add `-v` to a forbidden list — would have worked on this machine and nowhere
else. That is the same argument the last round made against a written kind table, and it applies
to the fix as much as to the defect.

## 3. The citation: three separate defects in one slot

**It is never run.** `compile_step` attaches `page["checks"][:1]`; `goal_holds()` decides the goal
by running `tar -tf`, `gzip -t`, `sha256sum`, `grep -F`. The published check is a receipt field.

**It is vacuous.** Measured by running each cited flag against every object in the room: **281 of
370** accept every object, and therefore say nothing about the object they are attached to. The
most common is `--help`, on **249** pages. On the four destroying pages the citation is exactly
`rm --help`, `shred --help`, `truncate --help`, `unlink --help`.

**It cannot tell which object was acted on.** Put the right object and a decoy of the same kind,
made by the same producer, in one room:

| check | on the right object | on the decoy | verdict |
|---|---|---|---|
| `gzip -t payload.txt.gz` | 0 | 0 (`other.txt.gz`) | **blind** |
| `tar -tf right.tar` | 0 | 0 (`decoy.tar`) | **blind** |
| `unzip -t right.zip` | 0 | 0 (`decoy.zip`) | **blind** |
| `python -c "json.load(...)"` | 0 | 0 (`decoy.json`) | **blind** |

**8 of 8** probes accept the file the action never touched. The last round found this for one
check and worked around it by giving a need two requirements; this round shows the workaround was
a local dodge, not a repair.

## 4. The repair, and the number that says it is not enough

`check_flags()` now refuses a **destroyer by name** and a flag whose page uses the **vocabulary of
a write** (`remove`, `overwrite`, `truncate`, `split`, `shuffle`, …). Then
`certified_checks()` **runs** each surviving candidate against a real room and keeps only those
that leave every byte where it was. And `run()` compares a **content digest**, not a kind map, so
a destroyed file is a change.

Removed: **22** of 2,319 — the 16 that changed bytes plus six help pages of destroyers. Named:
zero programs in the execution rule.

Then the question that decides whether the repair is worth anything: **of the citations that
survive, how many can separate one object from another?**

```
survivors measured: 439        discriminate: 8        accept everything: 206    accept nothing: 225
the 8 are gzip --list/--test/-l/-t and zcat --list/--test/-l/-t
```

**3 of 87 edges** in the graph have any such flag available; the programs that offer one are
`gzip` and `zcat`. A repair that demanded discrimination would leave 84 edges with no citation at
all. So the citation slot cannot be filled from a page's own flags, and the honest move is to
fill it from **the room** — the object the step actually produced, and a digest of it — which
this round specifies and does not build.

## 5. `ACCEPTED_INERT` for a destroyed file

The sharpest result, and it is about the *status*, not the citation:

```
shipped comparison (kinds):    shred -v payload.txt  ->  accepted: True, changed: False
attempt() therefore:                                     ACCEPTED_INERT
bytes of payload.txt:                                    random, original text gone
reported:                                                "succeeded and changed nothing"
```

`run()` took `before = typed(root)`, `after = typed(root)` and reported `changed = before != after`.
A type map is `{name: kind}`. `shred` preserves both. Of the 8 destroying checks that were
accepted, **7** came back `ACCEPTED_INERT` and one `ACCEPTED_CHANGED` (it left a new file behind).
After the digest repair: **8 of 8** `ACCEPTED_CHANGED`, **0** still INERT.

This is the last round's own finding — *a kind is blind to an overwrite* — promoted from a
measurement about typing to a defect in the status the guide gives an operator. The guide spent a
round proving a kind map cannot see an overwrite, and then used a kind map to decide whether an
action changed anything.

## 6. What the repair did not change

Re-running the shipped round's own instrument after the repair:

```
programs_read 446, edges 87, needs 13, goals_held 11, held_out 2, refused 2, repairs_attempted 0
G1..G7 all MET
```

Identical to `1da0b549`, need for need, gate for gate. That is not a paradox: the citation and the
`changed` flag are not read by `edges_of()` or by `goal_holds()`. **The defects could persist
precisely because nothing downstream depended on them.** A defect that changes no number is the
kind that survives a round which checks its numbers.

## 7. Where this loses

* **None of the 13 needs took a wrong object.** The blindness in §3 is latent: it is measured on a
  room built to expose it, and it did not corrupt any verdict in the shipped round. What it means
  is that the guide's citation could not have caught such a step, not that one occurred.
* **The `changed` repair changes a status nothing in the round reads.** The 13 needs are still
  decided by `goal_holds()`. A repaired status is a repaired *report*, and the report is what an
  operator acts on — but it is not a repaired verdict.
* **The which-object probes are four artifact kinds** (gzip, tar, zip, json) read from this
  machine's pages. A kind with no decoy here is not measured.
* **The 22 removed flags are a measurement of this machine.** The rule is execution plus the
  page's vocabulary, and the vocabulary is English; a page that says "expunge" instead of
  "remove" passes the vocabulary test and is caught only if it writes bytes.
* **The `--help`/`--version` family remains certifiable.** It is read-only, so the execution rule
  keeps it. It is also vacuous. `check_flags()` is now honest about what it certifies; the
  *citation* still picks `tar --block-number` for `tar`, which is real but useless. Only a
  room-derived citation fixes that, and this round did not build one.

## 8. What is real and what is not

**Real.** The shipped rule certified 16 byte-mutating flags, one of them a destroyer it also
cited on every step that page compiles. 281 of 370 citations accepted every object in the room and
249 were `--help`. 8 of 8 cited-check probes accepted a decoy the action never touched. 7 of 8
accepted destroyers were reported `ACCEPTED_INERT`. All four are executed measurements with the
counts in the receipt.

**Not real.** That the guide's verdicts were wrong. They were not; the 13 needs reproduce exactly.
That a repaired citation now witnesses an action. It does not — 3 of 87 edges have a flag capable
of it. That `check_flags()` is fixed and done. It is fixed for *destroyers*, and its output is
still the wrong place to look for a witness.

## 9. The three things the next round inherits

1. **Fill the citation from the room.** A step's check should be *the object the step produced,
   compared against what the goal named* — not a flag from the page. The instrument already has
   the pieces (`created`, `_digest`, `goal_holds`); what is missing is a check value derived from
   the action rather than from prose.
2. **The last round's thin machine, again.** Obligations 1 and 2 from `A_TYPE_YOU_WROTE_…` are
   still open: argument-carrying witnesses measured on the thin machine, and transfer to a room
   whose producers were chosen after the rule was frozen. This round did not touch either.
3. **Measure the status, not only the verdict.** Every round so far has verified the goal. None
   has verified that what the guide *tells the operator* about a step is true. §5 found seven lies
   in one status field of one program; the same audit has not been run over `REFUSED_*`.

## 10. Reproduce it

```bash
python3 canonical/tools/a_check_that_nobody_runs_is_a_check_that_cannot_be_wrong_v1.py \
  --receipt /tmp/receipt.json        # ~100 s, 4,638 check runs
python3 -m pytest canonical/tests/test_a_check_that_nobody_runs_is_a_check_that_cannot_be_wrong_v1.py
```

The second run of the same tool is a workflow,
`.github/workflows/a-check-that-nobody-runs-is-a-check-that-cannot-be-wrong-20261203.yml`, which
re-measures the receipt on a clean machine and fails if any declared gate has moved.

---

*A check that is not run cannot be wrong, and that is not a virtue — it is the reason a repository
can carry 2,319 read-only checks, cite one of them on every step it compiles, and never find out
that the one it cites on `shred` is the flag that shreds.*
