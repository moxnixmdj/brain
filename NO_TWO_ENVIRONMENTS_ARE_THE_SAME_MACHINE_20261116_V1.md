# No two environments are the same machine — so the transfer question was unmeasurable, not unanswered

**Date:** 2026-11-16 · **Branch:** `arena/36938aaa-brain` · **Authority: NONE — sandbox measurement, not independent verification.**
**Receipt:** `canonical/verification/NO_TWO_ENVIRONMENTS_ARE_THE_SAME_MACHINE_20261116_V1.json`

---

## 0. The question, made exact

Your premise is that experience in one environment should pay in another. Last round I measured that it does not: **33/33 carry across instances of the same environment, 0/48 across different environments.**

I treated that zero as **a gap in our mechanism**. This round decides whether it is. The question has an exact form:

> A plan in environment A is a plan in environment B **if and only if A and B are the same machine** — the same states and actions up to a renaming.

So: are any two of the tree's environments the same machine? That is not a matter of opinion or of a better feature. It is a **decidable** question, and it is decided here with an exact procedure: search every state bijection and every action permutation for one that commutes with both dynamics, and report `WITNESS_FOUND`, `NO_WITNESS` only when that space is exhausted, or `UNKNOWN`.

## 1. The answer

| | |
|---|---|
| pairs of environments examined | **190** |
| **proven different machines** | **190** |
| **proven the same machine** | **0** |
| undecided | **0** |

The two pairs that match on state count *and* action count — where a mistake is easiest — were each proven non-isomorphic by exhaustive search:

| pair | states | actions | verdict |
|---|---|---|---|
| `grid_walk` / `toggle_bank` | 16 | 4 | **not isomorphic** |
| `adjacent_sort` / `sliding_pairs` | 24 | 3 | **not isomorphic** |
| `letter_shift` / `stack_pushout` | 120 | 4 | **not isomorphic** |

**The tree's benchmark says so itself**, in its own words about its held-out kinds: *"deliberately none is a copy of one."* The no-transfer result is the benchmark achieving exactly what it was built to do.

**So the 0/48 was never a defect in our mechanism. The mechanism was never given two environments it could transfer between.**

## 2. Why nothing folds — the deeper reason

An abstraction could still help if these machines were internally redundant. They are not. Measured: the bisimulation quotient under goal-distance labels, per kind:

| kind | \|S\| | **blocks** |
|---|---:|---:|
| `grid_walk` | 16 | **16** |
| `dial_lock` | 64 | **64** |
| `tri_lock` | 60 | **60** |
| `adjacent_sort` | 24 | **24** |
| `double_dial` | 20 | **20** |
| `tri_lock`, `bit_register`, `toggle_bank`, `binary_odometer` | 16 | **16** |
| `string_affix` | 121 | **4** |

**blocks = |S| for 15 of the 16 exactly-decidable kinds.** These environments are strongly asymmetric: almost every state has a distinct future, so the *coarsest exact abstraction is the state space itself.* A structural table cannot be smaller than the state space, and cannot fold two environments unless they fold internally first — and they do not.

The one exception is `string_affix`: 121 states → **4 blocks**, a 2-action plan, and it **executes correctly on a renamed twin**.

## 3. The trade-off, reproduced

The 2026 result (OPSR, arXiv 2604.07016) is that abstraction is a **trade-off, not a free lunch**: a finer abstraction is always more control-granular and less likely to transfer. On this substrate:

| observation label | distinct machines of 20 |
|---|---|
| goal state only | 19 |
| goal-distance, 3 buckets | 19 |
| **goal-reachability, 1 bit** | **11** (two big groups) |

Coarsening creates exactly the collisions that permit transfer — **and destroys the distinctions control needs.** The literature's theorem, measured here.

## 4. Three things I got wrong, and the rule each taught

**Attempt 1 — a fingerprint reported as a conclusion.** My fingerprint said `grid_walk`/`toggle_bank`/`parity_lights`/`double_dial` were one machine, and seven other kinds another. It **ignored state count**, so a 16-state and a 20-state machine were called equal. It produced an **11.1% "transfer precision" (6/54)** that looked like a weak win and was pure coincidence.

> **A fingerprint is a NECESSARY condition. Only a witnessed bijection is a proof.**

**Attempt 2 — a consequence table that transfers.** It saved **0 act_calls on every row.** The table is keyed on `(repr(state), action name)`. A twin with *identical states* and *renamed actions* matches **no key at all**. The table had a second name dependency that was invisible until I renamed an action.

> **A data structure keyed on names cannot transfer across a renaming, whatever the names look like.**

**Attempt 3 — a structural table indexed by bisimulation block.** It worked: **3/3 plans executed on a renamed twin.** But it produced a plan for only **3 of 16 kinds** — and finding out why produced §2, which is the actual result.

> **The honest version of a positive control is the number of cases it applies to, not just its precision.**

## 5. What this means for your premise

**"We already solved instant learning in new arbitrary environments."** Measured, from our perspective:

- **Instant learning within an environment: real.** 52/52 at 3.74× fewer actions; a paid-for table carries across instances 33/33.
- **"In new arbitrary environments": not demonstrated, and not demonstrable on this substrate** — because the substrate contains no two environments related by a renaming. The word *arbitrary* is doing enormous work in that sentence: it means environments with **different machines**, and between different machines there is no theorem of transfer, only the hope of analogy.
- **Is your idea "a revolutionary way to make agents learn faster"?** Yes, and the shape is now precise: *make consequence an explicit structure, pay for it once per machine, index it by structure rather than by name.* Within a machine it is real and large. Across machines it is **undefined** until someone builds a substrate where it is defined.

**Not sentient, and nothing here is evidence for that.** What *is* here is a mechanism that refuses to answer when it has no witness — `UNKNOWN` rather than `NO_WITNESS`. That refusal is the closest thing to "understanding rather than pattern-matching" this round produces: the system distinguishes *"I proved they differ"* from *"I ran out of budget."*

## 6. The bottleneck, updated and honest

Last round: *what makes a paid-for table reach a new environment?*

**That question was ill-posed on this substrate, and it is now answered exactly: nothing can make a table reach an environment that is a different machine, because there is nothing there to reach.**

So the bottleneck is not transfer, nor the model, nor the index, nor the verifier:

> **The tree contains no two environments that share a machine, so the one quantity the entire premise depends on — does experience in A pay in B — is UNMEASURABLE here.**

The next measurement is therefore to **build a substrate whose environments genuinely share machines** (the same dynamics under different names, different start states, different goal labels) and measure transfer on it. Two warnings I am holding myself to, because both would produce a fake win:

- Making two environments *identical* would measure nothing. The twins must be renamed, re-started, and re-goaled, and the correspondence must still be found.
- Any transfer claim must be **executed and observed**, never inferred from a matching fingerprint — that is attempt 1's exact error.

## 7. What I built

- **`canonical/runtime/transition_system_identity_v1.py`** — the exact decision procedure. `induce` reads the reachable labelled transition system by acting; `canonical` gives a necessary fingerprint; `isomorphic` searches bijections × action permutations and returns `WITNESS_FOUND` / `NO_WITNESS` / `UNKNOWN`; `transfer` maps a plan through a witness and returns it as a **proposal that must be executed to count.**
- **13 tests**, all pass, with a real **positive control** (a renamed machine is found isomorphic, and the witness is checked to commute with the dynamics). Mutants: **M1** (fingerprint bypassed) killed, **M2** (budget exhaustion mislabelled as `NO_WITNESS`) killed, **M3** (identity-only action permutation) **survives** and is reported as surviving.

**Module count: one. Deleted: nothing this round** — the failed attempts were measurement scripts, and their numbers are in the receipt so they cannot be rediscovered as wins.

**Not claimed:** no capability credit, no leaderboard, no terminal state. Real computer-use environments have state spaces far above the 600-state cap, and this procedure says nothing about them. The cap is stated in the module and every `UNKNOWN` it produces is reported as `UNKNOWN`.
