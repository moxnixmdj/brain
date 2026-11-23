# Two instrument bugs in the learning law — and what the law really says

**Authority:** NONE · `truth.achieved` stays `false` · **$0**, 0 model calls

The §3 verdict quoted the crossover at "the second or third request". Re-running the instrument
showed that number was produced by two bugs. Both are now fixed, and the honest number is worse
for my earlier claim.

---

## Bug 1 — a real effect was classified as a measurement failure

`tar -rf archive name` run when `name` already exists produces:

```
archive gains one entity, one arrived, one departed   ->  shape (1, 2, 1)
```

`classify()` had four shapes — `INERT`, `PERSIST`, `REMOVE`, `REPLACE` — and `(1,2,1)` was not
among them, so the atom was filed `UNCLASSIFIED` and counted as a failed measurement.

It is not a failure. It is an **append**: a copy is made into the archive and the *original
stays*, so the store gains an entity while the target is not consumed. Every append-only
store produces exactly this shape — an archive, a log, an event table, a commit history.

| | before | after |
|---|---|---|
| `unclassified_atoms` | 1 | **0** |

A measurement that cannot name a shape it has seen will report a working atom as a broken one.

## Bug 2 — the crossover mixed a total with a rate

```
per_request = theirs / requests_n          # 34 / 16 = 2.125   (a PER-MACHINE rate)
crossover   = adaptation / (per_request-1) # 29 / 1.125        (adaptation is a GLOBAL total)
```

29 is the sum of adaptation over four machines; 2.125 is per machine. Dividing one by the other
is not a quantity. It reported **25.78**.

The honest computation is per machine and pooled:

| machine | adaptation | learn-each | crossover |
|---|---|---|---|
| FILESYSTEM | 9 | 13 | 3.00 |
| GIT | 6 | 10 | 5.33 |
| SQLITE | 6 | 10 | 6.00 |
| TARBALL | 8 | 11 | *never — learning-each is already cheaper* |

**Pooled crossover: 4.78 requests**, not 2–3.

## What the law actually says now

```
adaptation once    29 trials (sum over 4 machines)
demonstration x4   34 trials (sum over 4 machines, 4 requests each)
```

So adapting once **is** cheaper within a machine's first four requests — by 29 to 34, about 15%.
That is a real but modest win, and it gets better with every further request on the same machine
(the cost of adaptation is paid once; demonstration is paid per request for ever).

**But the calibration is not in this system's favour.** 17 of 20 atoms cannot change the state at
all, and 4 of the remaining 3 ignore the argument they are given. On the FILESYSTEM machine the
learn-each baseline solves **all four** requests while adaptation solves the same four — the tax
is real and it buys nothing extra there.

## The correction to my own claim

I wrote that adaptation "beats learning each request from the second or third request onward".
**The measured value is 4.78**, and on one of the four machines it never breaks even within four
requests. The earlier figure came from an arithmetic error, and quoting it was a failure of the
honesty rule, not of the instrument.

What survives is the shape of the claim, not the constant: adaptation converts a per-request cost
into a per-environment cost, and it wins when a machine answers more than ~5 requests. That is a
**currency change**, exactly as the verdict said — and the constant is 4.78, not 2.

`truth.achieved` remains `false`.
