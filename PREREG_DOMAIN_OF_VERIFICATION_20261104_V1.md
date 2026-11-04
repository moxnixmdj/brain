# Pre-registration — a hypothesis has a domain, and it must say so

**2026-11-04 · round 14 · before implementation · authority NONE**

## Thirteen rounds never once asked this

Measured this round, before writing anything: **no module in this session reports, or even records,
the interval over which a hypothesis was checked.** `compose` returns
`['authority','branches','fits','interpretation','needs','split_at','status','why']` — no domain.
`reach`, `induce` and `recover` are the same.

The consequence is not subtle:

```
relu, trained only on x = 0,1,2   ->  return x        extrapolates to -5 as -5, true answer 0
floor(y = x), trained on x = 0,1,2 ->  return x        extrapolates to 0.5 as 0.5, true 0.0
```

Both are `DETERMINED`. Both are *correct on everything they were shown*. Both are wrong everywhere
outside the interval they were shown, and the reports say nothing that would let anyone notice.

`DETERMINED` has been read this whole session as a property of the hypothesis when it is a property
of the observations plus an unstated assumption that the world continues in the same way. That
assumption has a name — extrapolation — and it is the one thing no amount of internal consistency can
check.

## The hardest measurement is the one with no truth

Held-out prediction with a known truth function is nearly free: 42/45 in the run above, with the three
misses being exactly the domain question (`mod 2` from three points). But a creature does not get a
truth function. What it can actually compute, with no oracle at all, is:

**A hypothesis is under-written if two strictly simpler hypotheses agree on everything observed and
disagree outside it.**

That is falsifiable from the data alone, and it is the right question: not "am I right?" but "have I
distinguished myself from the simplest things that fit?"

Operationally: search the family lattice for a strictly simpler alternative that agrees on every
observation and disagrees at some probe *inside* or outside the observed range. If one exists, the
hypothesis has not earned its complexity anywhere it was tested; the disagreement point is where the
two part company and hence where the domain of validity actually ends.

## Predictions

| id | prediction | how scored |
|---|---|---|
| **D1** | `relu` from `x ∈ {0,1,2}` has a simpler rival (`y = x`) that agrees on all three, so the affine fit is reported **under-written**, with the disagreement point named. | rival found, point named |
| **D2** | `3x+1` from the same three points has **no** simpler rival, and is reported as *not* under-written even though it is equally unverified outside its range. Under-written and unsupported are different findings and must not merge. | rival absent |
| **D3** | The reported **domain of verification** is the observed interval, and any prediction outside it is flagged, not silently returned. | interval + flag |
| **D4** | `mod 2` from three points is under-written by `y = x`, which is exactly why it failed held-out prediction above — the mechanism should have said so *without* the held-out data. | same input that failed |
| **D5** | The constraint from rounds 12–13 still binds: a rival must not be a degenerate table (one parameter per point), or every hypothesis would be under-written by its own lookup table. | degenerate rival rejected |
| **D6** | **Honest negative:** a genuinely extrapolating hypothesis is not flagged backwards. `2x` from three points is under-written by... nothing simpler, and must not be flagged merely for being linear. | no spurious flag |

D6 is the one that stops this degenerating into "flag everything". A mechanism that calls every
hypothesis under-written tells the creature nothing it did not already know.

## Stop condition

If every hypothesis on every input comes back under-written, the rival search is too generous — most
likely it accepts rivals that differ only in spelling rather than in behaviour, which is the exact
error round 8 fixed for the admissible set. I would report that as a null result rather than shipping
a permanent warning.
