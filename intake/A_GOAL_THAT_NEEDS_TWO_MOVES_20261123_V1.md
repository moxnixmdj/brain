# A goal that needs two moves

**Round 5. A goal no single door satisfies is planned as a sequence of measured move
classes, and the plan is refuted against the real tree — in both orders.**

Date: 2026-11-23 · Base: `866e778f` (PR #7052) · Branch: `arena/a504fc78-brain`

---

## 1. The wall this round inherits

Round 4's receipt names it in its own words: *the join answers which door for ONE move;
a goal needing several moves in order is unanswered.*

`perfect_algorithm_v1.plan()` returns `REFUSED__GOAL_NEVER_OBSERVED`, and its reason is
structural rather than a missing branch. Reaching a goal state requires *recognising* it,
and recognising it requires having stood in it. A goal expressed as one more state can
only be answered by search that has already visited that state.

## 2. The obvious plan, and the measurement that killed it

Call the search the tree already has. Two planners exist.

**`capability_planner.plan_capabilities`** is a correct A* with preconditions, effects and
costs, and twenty modules already use it. Its transition is add-only:

```python
new_facts = frozenset(set(facts) | set(cap.provides))
```

No capability can take anything away. Handed a goal that needs both a compression and a
copy:

```
initial  plain:a          goal  archived:a AND copy:a
gzip     requires plain:a  provides archived:a
cp       requires plain:a  provides copy:a
```

it returns `['gzip', 'cp']`. Run for real:

```
gzip -q a.txt      -> a.txt GONE
cp a.txt copy.txt  -> cp: cannot stat 'a.txt': No such file or directory
```

The plan is not suboptimal. It is **impossible**. A planner without a delete list cannot
see that a step destroyed a precondition of a later step.

**`consequence_table_v1.learn_and_solve`** has no such trouble: it plans over whole
states, which carry deletes naturally. It also reports its own price, honestly, over 52
satisfiable instances:

```
probes   0   1   2   4   8  16  32  64  unbound
solved   0   1   5   8  21  28  36  46     52
```

Zero prior experience solves nothing, because a whole state does not transfer to a world
with different filenames in it. That is the user's standing objection — *environments
always change* — stated as a measurement.

So neither existing piece does the round-5 job. The gap between them is what this round
built.

| piece | transfers across worlds | honours deletes | goal must be observed |
|---|---|---|---|
| `shortest_plan` / `consequence_table` | no (whole states) | yes | **yes** |
| `capability_planner` | yes | **no (add-only)** | no |
| **this round** | yes | yes | no |

## 3. The unit: a class of move, with a precondition

Round 4 already had the right unit for one move — a relation signature, measured by
running the door, containing no path, no argv, no content. What it did not have was a
**precondition**: a signature is a delta, and a delta does not say what a state *was*.
`{'IDENT': CHANGED}` is true of `mv here there` and of `mv there here`, so deltas cannot
be sequenced.

The observation that unblocks it: one relation in the signature is already a
precondition. `LOT: RETAINED` says content could be read afterwards — therefore content
was there to begin with. `moved()` drops it as “unchanged”, which is exactly right when
*choosing* a door and exactly wrong when *sequencing* one. The same value does two jobs,
and only the second needs it kept.

That makes a measured signature a small set of conditions on a state, and conditions
generalise where states do not:

```
rm      LOT PARTIAL, CARD DECREASED     needs readable content; loses one of them
cp      CARD INCREASED                  needs readable content; adds a name
mv      CARD SAME, IDENT CHANGED        needs readable content; keeps the count
gzip    CARD SAME, LOT RETAINED         needs readable content; keeps it one layer down
```

The plan carries four relation dimensions, each **owned by exactly one relation**:

| dimension | owner | why it must exist |
|---|---|---|
| `NAMES` | `CARD` | the count of names — but not enough alone: `cp` and `touch` both raise it |
| `READABLE` | `LOT` | separates a copy from an empty file; `CARD` cannot |
| `CONTENTS` | derived from `READABLE` | a copy adds a *name*, not a content |
| `REMOVED` | `CARD` falling | a goal may be about **history**, not just the final state |

Every effect is *derived* from the signature by one rule per relation; nothing is fitted.

## 4. What was measured

Receipt: `canonical/verification/A_GOAL_THAT_NEEDS_TWO_MOVES_20261123_V1.json`.

| measurement | result |
|---|---|
| doors measured | **23** |
| distinct classes | **4** |
| goal satisfiable by one door, in any of 3 worlds | **0** |
| plan found | **one 2-class plan, identical in all 3 worlds** |
| executed forward, on disk | **holds in 3/3** |
| executed in reverse, on disk | **fails in 3/3** |
| unreachable goal | **refused**, naming the missing fact |
| model calls · parameters · time | **0 · 0 · 1.1 s** |

The goal, stated before any plan was made and identical in every world:

> remove the subject's name, and lose nothing doing it — as many readable names
> afterwards as there were before.

No single measured move meets it. `rm` falls the count. `cp` never removes a name. `mv`
removes one and creates one, so the count holds — but a rename is not a cleanup and
`REMOVED` does not count it.

Executed for real in `TWO_NAMES_ONE_CONTENT`:

```
plan:        cp, then rm
forward:     after = [COPY, in.gz, in.json]   one name vanished, 0 contents lost  ✓
reverse:     after = [in.gz, in.json]         rm left nothing to copy            ✗
```

## 5. Nine designs measured and killed

Each of these was believed, built, and then killed by a number. They are in the receipt
(`what_was_wrong_first`) because a defect that lives only in a chat log gets made again.

1. **An add-only plan** — `['gzip','cp']`, impossible on disk (§2).
2. **The `moved()` subset as input** — it drops `LOT: RETAINED`, which *was* the
   precondition, so a rename became applicable to an empty world.
3. **`CARD` alone as the state** — `cp` and `touch` both raise it by one.
4. **A delete subtracting both `READABLE` and `CONTENTS`** — one loss counted twice, so
   `cp; rm` reported zero readable names while the content sat readable in the copy.
5. **A goal of `{REMOVED≥1, READABLE≥1}`** — `rm` met it outright in a world holding a
   duplicate content, so no sequence was needed.
6. **A goal of `{REMOVED≥1, READABLE≥1, NAMES≥3}`** — still met by `rm` in a world
   already holding four names. The same escape, one world over.
7. **Two doors executed against different files** — the census binds `cp` to `in.json`
   and `rm` to `in.txt`, so the sequence copied one file and deleted another.
8. **`len(after) < len(before)` as the removal test** — a copy adds a name and a delete
   removes one, so a net zero hid a real removal.
9. **A refusal control of “three readable names”** — reachable by `cp` twice; the planner
   rightly planned it and the control proved nothing.

## 6. A round-4 defect found by re-measuring

Round 4's receipt reports *54 census rows = 4 programs*. Re-run, seeding the way round 4
seeded:

```
round_4_seed_rows_by_tool: {gzip: 33, rm: 21}
round_4_distinct_programs_with_rows: 2
```

The census binds `cp` and `mv` to `in.json`. Round 4 seeded only `in.txt`/`in.gz`, so
both doors aborted on a missing operand — and an aborted door produces no row. **The two
doors a person would actually reach for contributed nothing, and the count of programs
was reported as four.** Round 5 seeds `in.json` and they appear: 2 `cp` rows, 2 `mv` rows.

This does not overturn round 4's stability or held-out numbers, which were measured on
the rows that did exist. It does mean round 4's *coverage* was two programs, not four.

## 7. Honest limits

- The plan is shortest in **move count**, not cost. No wall-clock or money model.
- Classes come from four programs. A class no program here implements cannot be planned
  with, and the planner **refuses** rather than inventing it.
- `CONTENTS`/`READABLE` are clamped by `NAMES`, so a world where a name outlives its
  content must be stated with `world(readable=...)`; the planner will not discover it.
- A `touch`-shaped operation shares the copy's signature and is mis-modelled as a copy.
  No signature over these six relations separates them — stated, not papered over.
- **A goal is still stated by the caller** as dimensions. Nothing here reads a request in
  words and produces that statement. That is the next wall, not a solved problem.
- Producer-run sandbox only. **No independent identity has re-run any of it.**

## 8. The web, and what it confirms

Every recent hybrid planner — DUPLEX, PDDLCoder, Agent+P, LLM-DP — puts a **model** at
the exact step this round refuses to: translating observations into a planning domain.
Their bottleneck is the translation; ours is measured instead. The framing that matches
best is that a door which changes nothing *here* is a **precondition failure, not an
absence** — which is precisely what §3 turns into a `requires()`. DUPLEX is explicit that
the LLM should not plan, only extract; this round removes the extraction too, for the
narrow class of moves where execution already measured the answer.

## 9. What is not claimed

`truth.achieved` stays **false**. What is real: a goal no single door satisfies is
planned as a sequence of measured classes and refuted against the real tree in both
orders, in three unrelated worlds. What is not: reading a request in words, any goal
about meaning, cost-aware planning, any benchmark score, and independent verification —
which remains **OPEN**.
