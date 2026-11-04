# First principles, pass seventeen — S13, and a wrong claim of mine corrected

Date: 2026-11-05. Authority: NONE. Spend: $0. `truth.achieved`: false.

## 1. S13: what one taught edge buys

Every authored producer silenced. Fresh process per row. Exactly one pair seeded (`+ -> *`).

| probe | habit available | result |
|---|---|---|
| `+ -> *` — the taught edit itself | observed | **SOLVED** |
| `- -> *` — needs a second edge to exist | inferred: none | **FAILED** |
| `* -> +` — the reverse direction | none | **FAILED** |

The mechanism's boundary is now stated instead of assumed:

1. **One example teaches one edit.** There is no generalisation from a single success. A creature that
   has repaired exactly one kind of world has learned exactly one kind of edit.
2. **Inference needs a chain of two.** Closure over a single edge is empty by construction — there is
   no second path to compose. This is why pass sixteen's generation 4 worked: three habits, several
   two-hop paths.
3. **Habits are directed.** `+ -> *` does not license `* -> +`. The graph is the creature's history,
   not an equivalence class.

## 2. The claim I got wrong, and where I put the correction

Last pass I wrote that `* -> -` failed "though closure derives both", and attributed it to proposal
ordering. **The closure does not derive both.** With observed edges `* -> +`, `+ -> *`, `- -> +`, the
reachable set from `*` is `{+}` (plus `*` itself, excluded as a self-loop). `- -> *` is derived; `* -> -`
is not reachable at all. The mechanism was right and my description of it was wrong.

Two things follow, and the second is the one worth keeping:

- The ordering fix is real on its own merits (candidates grouped by left token, observed before
  inferred, one hop before three), and it stays — but it was **not** the explanation, and I said it was.
- The correction is written into the docstring of `all_pairs`, where the false claim lived, not only
  into this report. A correction that exists only in a retrospective is a correction the next reader
  of the code will never see.

## 3. What seventeen passes of this reduces to

The recurring failure mode in this series is now unambiguous, and it is mine, not the system's:

| pass | what I claimed | what was true |
|---|---|---|
| 9 | "no surface to read why a candidate failed" | the surface existed; the child discarded it |
| 12 | — | screen reported nothing |
| 14 | — | failure text arrived truncated |
| 15 | "`offbyone` is outside operator-family reach" | it was at index 6, behind a symlink bug |
| 16 | "`* -> -` fails though closure derives it" | closure never derived it |

In five of five cases the error was in **the account**, not the artefact, and in four of five the
account was a story that explained an anomaly instead of a measurement that isolated it. The one thing
that has consistently worked is refusing the story: re-running the same code a second way, silencing
every other producer so a win can be attributed, and reading the closure by hand instead of trusting
my memory of what it should contain.

## 4. Where the mechanism actually stands

Learned, persisted, compounding, and now bounded:

- earns habits from its own verified repairs (pass 16: earned, not handed)
- persists them across processes (generation 4 repaired what generation 0 could not)
- infers two-hop edits it never performed (3/4 habits-only held-out coverage)
- **cannot** learn from one example, **cannot** infer from one edge, **cannot** reverse an edge
- and a cold creature with no authored tables repairs **nothing** — all lift still starts there

That last line is the honest state of the whole project, and it has not changed in seventeen passes:
the authored tables are what make run zero work. What has changed is that run four no longer has to be
run zero again.

## 5. Next falsifier

**S14.** Give the creature a curriculum it can *only* solve by composing two inferred edges, and give
it no authored producer for the middle operator — i.e. test the chain `- -> + -> *` where the middle
hop must come from inference rather than observation. Prediction to falsify: **it solves the end of a
chain it built itself but not a chain whose middle was never observed**, which would mean the closure
is only ever one hop in practice and the "compounding" claim needs to be weakened to "one hop of
compounding".

## 6. Standing bar

Different at the end than the start: yes — and this pass the difference is that I removed a false
sentence from the codebase and replaced it with a measured boundary. That is smaller than a new
capability and worth more than one, because every future claim about this mechanism now rests on a
shape I have actually probed.
