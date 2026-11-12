# One showing is literal; two showings are general

**2026-11-12.** Base `2540a6ed`. Branch `arena/6f3845ae-brain`. Round 13.

Every round until now answered the question on the file-question learner, which is a toy. This round
answers it on the surface the owner actually wants: **changing code.** The mechanism is already in
the tree, under a name nobody would guess —
`canonical/swe_kernel/taught_actions/edit_by_example_v1.py`. An example is a file before and the
same file after. Nobody writes the change down as a program; the learner works it out as rewrite
rules and repeats it on another file.

Shown the same defect at four shapes it never saw:

```
rule from ONE showing   ['product == None -> product is None']
rule from TWO showings  ['?1 == None -> ?1 is None']

unseen sites of the same defect                           4
edited after ONE showing                                  1
refused after ONE showing, naming the form                3
edited after TWO showings                                 4
```

One showing produced a rule about **the exact name it saw**. `invoice.paid == None`, `g() == None`,
`x == None` were all refused — "nothing in the file has the form the examples changed". A second
showing, at a *different* place, is what produces `?1 == None`, and then all four are edited.

**That is the whole answer, on the surface that matters, in one table.** Not "one demonstration
generalises" — one demonstration *memorises*, and the second different one generalises.

Authority **NONE**. The shipped learner ran in-process on synthetic source. Writes no file, starts no
process, $0, zero model dependency.

## 1. Why the second showing is not just "more of the same"

Look at what the second showing does on a file with a dangerous call:

```python
import yaml

def settings(h):
    return yaml.load(h)

def theirs(h):
    return yaml.load(h, Loader=yaml.FullLoader)
```

Shown once — `yaml.load → yaml.safe_load` — the learner **refuses**:

```
line 9 of the file has yaml.load called with 1 argument and the keyword Loader;
the examples ... [nothing is changed]
```

That refusal is the difference between a tool and a foot-gun. The module's own notes record the
alternative: on real commits, this rule rewrote `yaml.safe_load(stream, Loader=...)` and broke code
the new function does not accept.

Shown twice — the second example changes a plain call and *leaves a `Loader=` call alone* — the rule
becomes `yaml.load(?1) → yaml.safe_load(?1)` and the learner edits the plain call while leaving the
dangerous one untouched **without being asked**. The second showing did not add information about
`yaml`; it added information about **what not to touch**.

That is the part no amount of "try it once and keep it" supplies, and it is why the two
demonstrations are not interchangeable with one repeated twice: the second is valuable exactly
because it is *different*, including in what it leaves alone.

## 2. The ceiling, again, in the same shape as round 9

```
line 1 of the example adds, removes or reshapes whole statements;
only a change inside one expression or one simple statement can be learned
```

Add a statement, rename a function, introduce a branch — refused. The learnt space is a fixed
algebra of *expression-level rewrites*, and examples select within it. This is the identical finding
as the word learner's fourteen parts and the repair loop's bounded AST mutations:

> **Every working learning mechanism in this tree is selection inside a fixed operator space.
> Code sets the space; examples choose a point in it.**

Three independent mechanisms, three different domains, one structure. That is no longer a guess
about how these systems behave — it is the design of the only three things in this repository that
learn from demonstration.

## 3. What to do with this

1. **Never ship a demonstration-based rule from one example.** Not because it will fail loudly — it
   will *succeed* on the code that looks like the example, and refuse elsewhere, which reads as
   "working but limited" while it is actually "memorised". Two examples, deliberately different, is
   the unit.
2. **Choose the second example for what it leaves alone**, not for what it changes. The `Loader`
   case is the archetype: the second example's value was entirely in the code it did not touch.
3. **Extend the algebra in code when a lesson is refused for its shape.** "adds, removes or reshapes
   whole statements" is a boundary a written part can move; a thousand demonstrations cannot.
4. **This is the fast path to the owner's goal.** Coding capability here is not bought with
   environments or with one-shot experience; it is bought with (a) wider learned algebras and (b)
   second examples chosen adversarially. Both are engineering, both are cheap, and both are already
   half-built in `swe_kernel/taught_actions/`.

## 4. Receipts

```
python3 one_showing_is_literal_two_showings_are_general_probe_20261112.py --list
python3 -m pytest -q canonical/tests/test_one_showing_is_literal_two_showings_are_general_v1.py   9 passed
```

## 5. Non-claims

One family of edit, one synthetic corpus, the shipped learner unmodified. Nothing here measures
performance on a real repository, and nothing here is a benchmark or acceptance claim. The four
"unseen sites" are four shapes of one defect, not a population. No capability registered, no file
written, `truth.achieved` false, $0, zero model dependency.
