# Round 29: the language was a list I typed

You asked a fourth time. Four times is not a request for another bug fix — it is a statement that my
*direction* is wrong. So this round I did not look for a defect. I looked for the thing that would
still be wrong after every defect was fixed.

## What I had been doing

Twenty-eight rounds. Every one of them found a real defect and fixed it:

| round | defect |
|---|---|
| 25 | a missing answer was reported as a missing language |
| 26 | a claim nothing could refute was called corroborated |
| 27 | the self-model was never trained |
| 28 | the self-model was trained on the answer |

All real. All inside one fixed library. That is **quality assurance on static code**, and it produces
a better static artifact, which is exactly what you said you did not want. I had optimised for the
local maximum: a tree that is impressively careful about the language it has, and unable to notice
that the language is mine.

## The question I had never asked

> **Can this system acquire a capability I did not install?**

Not "does it fix a bug in a rule I wrote." Not "does it use a table I defined more cheaply." **Does it
extend what it can express, on its own.** So I read the candidate generator looking for the boundary
between structure and authorship, and found this in `_solve_composed_table`:

```python
"""...nothing is enumerated blindly."""          # the docstring

cofactors = [("x", ...), ("2x", ...), ("x2", ...), ("const", ...)]   # four handwritten entries
for k in range(2, 13):                                                # period ≥13 unreachable
```

**The docstring warned against "a list of forms a human anticipated" and the code below it was
exactly that.** Measured consequence:

| expression | before |
|---|---|
| `T(x) + 2x` | DISAMBIGUATED_AND_CRYSTALLIZED |
| `T(x) + 3x` | HELD_OUT_REFUTED_STRUCTURE_UNDIAGNOSED |
| `T(x) + 10x` | impossible — no such entry |
| `T(x) + x` at period 13 | HELD_OUT_REFUTED_STRUCTURE_UNDIAGNOSED |

Nothing separated 2 from 3 except a Python literal I typed. **That is the language being a fixed part
of me.** A creature that can only compose with the coefficients I thought of is not acquiring
structure; it is indexing my foresight. Every round before this one was making that language more
honest. None was making it *larger*.

## The rule that replaces the list

If `y = T_k(x) + s(x)` where `T_k` has period `k`, then the k-th increment **cancels the table**:

```
D_k(x) = y(x + k) - y(x) = s(x + k) - s(x)
```

So the co-factor is not guessed. It is **whatever survives the differencing**:

- `D_k` constant → `s` is affine, slope `= D_k / k`, recovered by division
- second difference constant → `s` is quadratic, coefficient `= D₂ / 2k`, same method
- `D_k` not constant → the co-factor is something else, and the creature refuses rather than guessing

I verified the arithmetic before writing any code, over `s ∈ {2x, 3x, −2x, 7, x²}` at `k=3` and
`k=5`: the slope is recovered exactly for the linear cases, and `D_k` is correctly non-constant for
`x²` — which is what proves the test discriminates rather than assumes.

The period cap fell to the same reasoning one level up. `range(2, 13)` was a limit of my imagination
standing in for a limit of the evidence. **A block of period `k` has `k` residues, so `k` cannot
exceed the number of distinct inputs observed** — the existing residue check already refuses below
that bound, so the cap never needed to be a constant.

## Measured

| expression | before | after | held-out wrong |
|---|---|---|---|
| `T+3x` | refused | **solved** | 0/30 |
| `T+5x` | impossible | **solved** | 0/30 |
| `T−3x` | refused | **solved** | 0/30 |
| `T+10x` | impossible | **solved** | 0/30 |
| `T+7x` at period 7 | refused | **solved** | 0/30 |
| `T+2x²` | impossible | **solved** | 0/30 |
| `T+0.5x²` | impossible | **solved** | 0/30 |
| `T+x` at period 13 | refused | **solved** | 0/30 |
| `T+x` at period 17 | refused | **solved** | 0/30 |

`T+0.5x²` is the one to look at. **No list of forms I would ever have written contains 0.5.** It is
reachable only because the coefficient is computed.

## The regression that taught me the rule was working

My first rewrite removed `x*x` from the list without adding the rule that derives it, and `T(x)+x²`
went from `DISAMBIGUATED` to `HELD_OUT_REFUTED` — **a capability loss disguised as a cleanup**, and I
would have shipped it if I had not measured the old cases alongside the new ones.

That is why `TheRegressionThatTaughtTheRule` exists in the test file. The lesson is not "be careful."
The lesson is: **a generalisation that cannot reproduce the special cases it replaces is not a
generalisation, it is a deletion.** Every future round that replaces a hardcoded form must show the
old forms still work, in the same test run, or the capability loss is invisible.

## Still true, and now more clearly

This does not make the creature sentient and I will not claim it. It does not invent an *operation* —
the algebra of table-plus-cofactor is still mine, and so is the decision to difference at lag `k`. What
changed is that within that algebra, the **coefficients are no longer mine**: they are recovered from
the evidence, at any period the evidence can support, including values I could not have anticipated.

That is the difference between a fixed language and one that grows. It is a small growth, and it is
the first one that is actually growth rather than repair.

`truth.achieved: false` · `authority: NONE` · $0 · no sentience claim · no external models · no
neural weights.

## Measured state

**295 passed, 26 subtests**, one pre-existing failure that fails identically on the stashed baseline.
14 new tests, including source-level guards that fail if a handwritten co-factor list or a literal
period cap is ever reintroduced — because the comment saying one thing while the code does another is
the exact failure this round exists to end.
