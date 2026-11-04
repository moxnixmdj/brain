# Twenty-Fourth Pass: The Creature That Has Its Own Reasons

*2026-11-05. Branch `arena/3c70152b-brain`. Authority NONE. Spend $0. `truth.achieved` false.*

---

## 1. The question, sharpened

Three times the owner asked for something smarter, and the third time asked me to
"think from the deepest layer, from first principles of everything." Each time I
answered with another organ, and each organ was a better answer to the wrong
question.

So in pass twenty-four I stopped building and measured what the creature does when
nobody gives it anything.

I wrote a world with a module, a correct sibling function, one genuinely wrong line,
and a placeholder test that asserts nothing. Six cycles. The result:

```
board_changed_the_code: false
```

Then the same module with the bug *fixed*. Identical result. The creature could not
tell those two worlds apart, because it never looked at either.

**Twenty-three passes of organs, and the creature had no reason of its own to act.**
Every single mechanism built so far -- the producers, the repair loop, the
generalization gate, the competence pruner, the habits, the grammar -- begins with a
failing assertion someone else wrote. Remove that, and the organism is inert. It was
not a reasoning machine. It was a very elaborate reflex.

This is the deepest thing I have found in this series, and it is not a bug in any one
file. It is the shape of the whole design.

## 2. What was actually missing

Not a repair rule. **Absent doubt.**

A creature with no expectations has nothing to be surprised by, and a creature that
cannot be surprised has no work of its own. Every failing test it ever repaired was
work *handed* to it. The frame I had built was: *the world says something is wrong;
find out what.* The frame that was needed is: *the world says nothing; find something
to be wrong about.*

Those are not the same capability at different strengths. They are different
positions. One waits; one looks.

Concretely, the blindness was in one line. `_sense_failing_workspace_tests` -- the
organ that answers "what needs repair?" -- did this:

```python
if not test_files and not poly_tests:
    return []
```

before examining a single module. A world with no tests is a world where nothing is
owed, and the sensor returned nothing because there was nothing to return. It was
not refusing work. It had no way to represent work that had not already been
written down by somebody else.

## 3. The mechanism: notions

`canonical/swe_kernel/notions_v1.py`. A *notion* is an expectation derived from the
program's own structure, carrying the check that could refute it.

The one that matters here:

> **A function of fewer arguments is the degenerate case of one of more.**
> A square is a rectangle with equal sides. A cube is a box.

If `square_area(s) = s * s` and `rect_area(w, h) = w + h`, then
`rect_area(3, 3)` is `square_area(3)` -- the same object described two ways. It
returns 6 where the other returns 9. **Two parts of one program disagree, and nobody
was told.**

That disagreement is a falsifiable claim with a truth value, and it becomes a test:

```python
assert square_area(3) == rect_area(3, 3)
```

The creature writes that file itself, names it `test_geom.py` after the module it
indicts (which is what makes the existing repair machinery reachable at all), and the
twenty-three passes of organs finally have work that the creature generated.

Four constraints came out of measurement, not taste:

- **Notions must be refutable or they are refused.** Anything unfalsifiable
  ("this code looks messy") is not admitted. An opinion is not work.
- **Notions are allowed to be wrong.** One that fires on correct code is the normal
  cost of having expectations. The store records fire rates so a notion that fires on
  *everything* becomes visibly worthless.
- **The values come from the source**, not from me: parameter names, the constants
  already written, a grid of samples.
- **A notion that cannot be stated as an assertion is dropped.** Not guessed at.

### Measured

| world (no test file, no bug report) | notion machinery ON | OFF |
|---|---|---|
| `rect_area(w,h) -> w + h`, correct `square_area` | **fixed** -> `return w * h` | not fixed |
| `cube_volume(s) -> 6 * s`, correct `box_volume` | **fixed** -> `return s ** 3` | not fixed |
| `box_volume(l,w,h) -> l + w + h`, correct `cube_volume` | **not fixed** | not fixed |

Board 10/10. Regression set: 23 `FAILED` == baseline, no new failures.

The third row is a real failure and is discussed in section 6.

## 4. Six silent discards

The mechanism was correct on the first afternoon and invisible for the rest of it.
Every one of these produced the *identical* symptom -- no test written, no repair,
no error -- and each was found only by measuring the layer directly:

1. **`arity == 1` paired with `arity == 2`.** A cube is a degenerate *box*, and
   `cube_volume(s)` vs `box_volume(l, w, h)` skips two arguments, not one. The
   notion for that world was never constructed.
2. **`evaluate` treated "could not run" as "refuted".** `except: ok = False` meant a
   notion that declined to speak returned `fired=True`. A crash, a missing function
   and a genuine disagreement were indistinguishable on the board. Now three states:
   fired / held / declined.
3. **The constructor assigned a literal over its own argument.** `self.arity = 0`
   instead of `self.arity = arity`. Every notion carried arity zero.
4. **A regex anchored to prose.** `_notion_to_assertion` matched the literal string
   `(x, x)`. When the subject changed to `(equal args)`, the regex stopped matching
   and *every* notion was dropped.
5. **`explain` returned `[]` for fewer than two arguments.** The row naming the
   failing function itself -- `cube_volume(3)` produced 6, owed 27 -- was the one row
   no hypothesis could ever be derived from.
6. **`consistent` rejected every name absent from the binary-operator table.** So
   `cube` -- the correct explanation -- was recorded, ranked, and then dropped as
   inconsistent.

This is now the dominant failure mode of the whole project: **not a wrong answer, a
silently discarded one.** Six occurrences in one pass, on top of four in the previous
one. A capability that is present and unreachable is worse than one that is absent,
because it produces the confident report "measured: false".

## 5. Where the pairing rule came from

I got the pairing wrong three times, and the sequence is the honest content of this
section.

**First:** pair every function with every other. This produced
`square_area(x) == 2 * rect_perimeter(x, x)` -- an area against twice a perimeter.
It fires on correct code, no edit can satisfy it, and on the board it **vetoed a real
repair**: the correct `return w * h` was rejected because this noise expectation
remained violated. A bad notion is not harmless. It makes the creature worse.

**Second:** filter on shared literal constants. Wrong in the other direction --
`s * s` and `w * h` share no literal, so this threw away the one notion that
identifies the bug.

**Third:** a numeric near-miss test -- "two descriptions of one quantity agree on
most inputs and differ on a few." This cannot work, and the reason is worth stating
plainly: a *defect* that happens to be right at one sample (`w + h == w * h` at 2)
and a *category error* that crosses at one sample (`16 == 2 * (4 + 4)`) look
identical. Without a specification, arithmetic alone cannot tell them apart.

What works is the program's **own declaration**: functions that compute the same
quantity share a word in their names. `square_area` and `rect_area` both say *area*.
`square_area` and `rect_perimeter` have no word in common.

This is not the authored table the owner rejected. It is not a list of known
formulas, and it encodes no case: it reads the identifiers the source already wrote
and asks whether two functions are talking about the same thing. But it is a form of
reading, and it inherits the limit in section 6.

## 6. The limit, stated honestly

**Notions find internal inconsistency. They cannot find a self-consistent lie.**

The mechanism compares two parts of one program. It knows nothing about what the
program is *for*. Concretely:

- A module where the only wrong function has no sibling to disagree with is invisible.
  If `rect_area` were the only function in the file, there would be no notion.
- **S35 is exactly this failure.** `box_volume(l, w, h) -> l + w + h` against a
  correct `cube_volume(s) -> 6 * s`: the notion fires (they disagree), a test is
  written and fails -- and the creature's own interpretive layer reads the evidence
  the wrong way round. Given `cube_volume(3) = 18` and `box_volume(3,3,3) = 6`, it
  concludes that `box_volume` is the one that is wrong, because 6 is what `3 * 3`
  gives. The evidence says *these two disagree*; it does not say which one to
  believe, and the creature picked the wrong side. It produced a plausible, wrong
  edit.
- A program that is internally consistent and wrong about the world is invisible.
  A `rect_area` that returns `w * h` when the business wants a triangle is not a bug
  this creature can ever see.

I am not going to close that gap by adding a producer. To see a self-consistent lie
you need a specification from outside the program, and inventing one from the code's
own structure is not derivation -- it is guessing with extra steps.

What I can say is that the creature now has a position it did not have: **it can be
surprised by its own code.** That is a necessary condition for a mind, and it was
absent for twenty-three passes while every other measure went up.

## 7. What changed in the claim

Before this pass, the accurate description of the system was:

> A repair engine that acts on failing assertions, with a large and growing library of
> edit producers.

That was not what the owner asked for, and no amount of producers was going to make
it so. After this pass:

> A system that derives expectations from the structure of a program, writes the
> tests those expectations imply, is surprised when its own code contradicts itself,
> and repairs it -- with no failing test, no bug report, and no instruction.

Two measurements support the second description and one refutes an overstatement of
it. Claims of progress in this project are only allowed to be backed by capability
that changed while the code did not; both "fixed" rows above are the creature
encountering a world it had never seen and doing work nobody assigned.

Board 10/10. Regression set unchanged. Authority NONE. Spend $0. `truth.achieved`
false -- and now the sentence means something, because for the first time the
creature can tell when something is wrong without being told.
