# An import the example added is brought where it resolves

**2026-11-12.** Base `10beb85c`. Branch `arena/f887ecaa-brain`. Follows #6699.

After #6699, 18 held-out files were still refused whole. A probe over the tracked commit lists
sorted those refusals into their real causes before anything was built: **7 of 18** fail only
because the new code needs a name the file does not provide — the very name whose `import` line
the teaching example itself added. 4 of the 7 (apache/allura, `cgi.escape -> html.escape`) need
`import html`, which any Python provides; 3 (the `math.gcd` kind) need the teacher's own
`import diofant.core.compatibility`, which other projects do not have. The remaining refusals are
of other causes and are untouched. So the round's rule wrote itself: *an import the example added
is brought along with the edit — exactly where it can be found — and refused by name where it
cannot.*

## 1. What was built

No new action and no new sentence: every taught form of `edit_by_example_v1` now carries the
example's added imports. The lesson file records them (`teaches[n]["imports"]`, name → line).

* **Only what the examples prove.** A line is carried only when the example itself added it, it is
  an absolute `import`/`from … import` (no relative imports, no `*`), and **all** examples agree on
  exactly one line for the name. Two examples that brought the same name two ways prove nothing and
  bring nothing.
* **Only where it is needed.** The line is brought only when the rewritten code uses the name and
  the file provides it nowhere. A file that already has it gets no duplicate; an import present in
  both example files is a demand on the target, as before, not a thing to bring.
* **Only where it resolves.** The module is looked up with `importlib.machinery.PathFinder`
  against the place the edit is made — the standard library or the project itself; nothing is
  imported or run to decide. Where nothing provides it, the refusal now **names the import**:
  *"the change needs `import diofant.core.compatibility`, as the examples added, and nothing named
  'diofant' can be found in this project; nothing was changed"*. Under `repeat_tried` that is exit 3
  with the file byte-identical.
* **Never over a local meaning.** A top-level binding, another import of the same name, a
  parameter or a local variable in any function enclosing an edited place keeps the refusal — the
  brought name must mean there what it meant in the example.
* The line lands after the last top-level import, else after the module docstring, else at the top.

## 2. The measurement, same tracked sets as #6699

| held_out (27 kinds, 97 files, 169 questions) | #6699 | now |
|---|---|---|
| `repeat` same / files refused | 116 / 18 | **122 / 14** |
| `repeat_tried` same (ceiling of a sufficient check) | 141 | **147** |
| statements changed that the person left alone | 0 | 0 |
| statements added that the person did not add | 0 | **4** (see below) |

The +6 answered questions are exactly the 4 allura files (one had 3 questions). The **4 added
statements** are honest residue, not wrong behavior hidden: in those files the person swapped
`import cgi` → `import html` *in place*; the engine instead brings `import html` and leaves the
now-dead `import cgi` behind — the same residue the LLM-migration literature reports for one-shot
migration (arXiv 2408.16151: "inserting unused imports"). Taking a dead import away when the
example also removed it is the next rule, not this one. The seen set is unchanged (30/69, 0/0).
The 3 diofant files stay refused with the import named; one of them (`diofant/core/numbers.py`)
lives inside the diofant project itself, where the import *would* resolve — the harness judges
files outside their checkouts, so that one refusal is partly an artifact of the harness, counted
against the engine anyway. The measuring tool itself changed: `answers()` used to reject any
output with a different statement count; it now aligns additions, and an added statement counts
against the engine unless the person added the same one.

## 3. Receipts

```
pytest -q canonical/tests/test_an_import_the_example_added_is_brought_where_it_resolves_v1.py   12 passed
pytest -q  (all six taught-action test files)                                                 257 passed
PYTHONPATH=. python3 canonical/tools/teach_actions_v1.py        11 skills, bundle 90ecd5ff… (re-taught: the
                                                                engine's source is embedded, so the sha moves)
python3 canonical/tools/edits_repeated_across_projects_v1.py measure held_out|seen             the table above
```

Two expectations of older tests changed with the behavior they pin: the `import os` case of the
widening file and the "name the file does not provide" case of the repeat file asserted the flat
refusal; the first now asserts the bring, the second uses an unresolvable name and asserts the
refusal that names it. Every refusal that still must stand (shadowing, both-ways imports, relative
imports) is still asserted.

## 4. Non-claims

Bringing an import is the whole claim: nothing is removed, renamed or re-exported, and a name used
through an alias (`import diofant as d`) is not recognized as providing `diofant`. Resolution is a
find, not a run — a module that exists but fails on import passes the check and fails at the
project's own runtime, exactly as it would for a person who typed the line. The 3 "takes a name
away" refusals of the held-out set are out of scope and untouched. `tried` remains the ceiling of a
sufficient check. No capability is registered; `truth.achieved` stays false; $0; the result-bearing
path has zero model dependency.
