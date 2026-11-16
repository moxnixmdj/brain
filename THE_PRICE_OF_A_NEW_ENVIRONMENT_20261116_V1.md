# The price of a new environment

**Instant learning is the right unit and it is not a solution to computer use. It changes the
currency of learning from *requests* to *environments*, and the exchange rate is measured here:
about seven operations in a new machine before measuring it beats learning each request by
demonstration — after which every request costs one trial instead of two, and the agent no longer
loses requests to its own side effects. What remains unsolved is not cost. It is composition and
addressing, and both were counted.**

Date 2026-11-16 · branch `arena/fdc52fe0-brain` · authority **NONE** (producer-run sandbox) ·
receipts `canonical/verification/INSTANT_LEARNING_IN_A_NEW_ENVIRONMENT_20261116_V1.json`,
`canonical/verification/INSTANT_LEARNING_SHUFFLED_CONTROL_20261116_V1.json`

---

## 1. The claim, split into three propositions that do not share a truth value

> *"Give the model the most advanced actions, let it experience each once, and it learns them
> permanently. Give it any new environment and it learns that too. So it solves everything on a
> computer."*

| | proposition | verdict |
|---|---|---|
| **P1** | one verified experience in a **fixed** environment is enough for permanent correct reuse | **true only after the representation is told what does not matter** — measured last turn: 0 of 304 candidates survived the target's own examples with literal preconditions, 4 of 384 with one canonicalization, and one demonstration repaired 5 bugs it never saw |
| **P2** | one experience per **new environment** is enough for competence there | **true only if what is learned is the interface, not the task** — measured this turn, below |
| **P3** | therefore every problem on a computer follows | **false**: 3 of 16 requests remained unsolved, and every miss is a *kind*, not an accident |

"We already solved those perfectly" is not what this project's own receipts say. `WHAT_TRANSFERS_20261113_V1`
records one showing against four shapes — other operator form, other shape, a required `<=`, **the
same defect with other names** — and all four came back `REFUSED`. Last turn's α result is the
correction that made *one* of those four move. A mechanism that goes from 0 to 1 of 4 under a
supplied invariance is a real advance and it is not perfection.

## 2. What was measured, and where

Four machines, each a real tool over real state, each with its own reader, sharing **no** command,
no argument syntax, no identity scheme and no state format:

| machine | entities | reader |
|---|---|---|
| `FILESYSTEM` | files | the directory listing and the bytes |
| `GIT` | commits | `git log --format=%H%x09%s` |
| `TARBALL` | archive members | `tar -tf` plus `tar -xOf` per member |
| `SQLITE` | rows | `SELECT id, value FROM t ORDER BY id` |

The engine receives the machine's **atom list** (argv templates), the machine's **reader**, and
nothing else. Atom identifiers are opaque (`FS_A3`, `GIT_A1`, …); if the identifier said "create", the
identifier would be the knowledge. What an atom does is learned by executing it once and reading the
machine before and after. The effects are named in one vocabulary shared by all four machines —
`PERSIST` (one entity arrived), `REMOVE` (one left), `REPLACE` (one left, one arrived) — and the
user's requests are stated in that same vocabulary. **That shared vocabulary is the invariant;
nothing else is shared.**

## 3. The two costs, and the exchange rate

| | measurement-then-act | learn each request by demonstration |
|---|---|---|
| adaptation trials (once per machine) | **29** (36 cells exist; active probing stops when every effect has been witnessed) | 0 |
| requests solved | **13 of 16** | 11 of 16 |
| trials for the 16 requests | 44 total (29 adaptation + 15 request trials) | 34 total |
| cost per request after adaptation | **1.0** | 2.125 |

So on a **four-request** machine the demonstrator is cheaper, and it is right to be: measurement is a
fixed tax and a demonstration is not. The break-even is **≈ 26 requests across the four machines, or
≈ 6.4 requests per machine** (≈ 4.7 under a different atom order). Past that point the measuring
agent pays one trial per request for ever and the demonstrator pays ~2.1, on every request, in every
session, with nothing carried forward. A real application is not four requests; a hundred interactions
in a new tool is an ordinary afternoon, and at a hundred the demonstrator has spent ~210 trials where
the measuring agent spent 29 + 100.

**The shuffled control is the part that decides this properly.** Re-label every atom and re-order the
list (`--shuffle 7`), and the measurement regime solves **exactly the same 13 of 16, machine by
machine** — while the demonstrator's numbers move (34 → 46 trials, 11 → 12 solved). The demonstrator's
capability is a function of the order in which actions happen to be offered; the measuring agent's
capability is not. That difference is the revolution, and it is not a speed-up: it is the removal of
luck from the outcome.

## 4. Four things that are wrong with "experience each action once"

1. **One experience per action is one cell of a table.** An action's effect depends on the state it
   runs in. Measured: **5 of 18 atoms change their effect between the two state classes** — the same
   file write is `PERSIST` when the target is absent and `REPLACE` when it exists; `rm` is inert when
   the target is absent and `REMOVE` when it is present. The correct unit is **(atom × state class)**,
   which is a STRIPS operator's precondition/effect pair, not an action.
2. **Half of the offered actions cannot do anything, ever.** 17 of 36 measured cells are inert —
   **47.2%**. That is within a tenth of a percentage point of the 47.1% this tree measured
   independently on MiniWoB++ pages (`inert_action_prior_v1`), on a completely different kind of
   machine. Two independent measurements of the same law: the offered action set is roughly half
   decoration, and paying to discover that is a tax you pay once per environment instead of once per
   request.
3. **Four atoms change the world the same way no matter what they are told.** `git reset --hard` and
   `git commit --amend` affect the tip commit whatever argument you give them; `cp` duplicates
   whatever exists. Their effect is `addressable = false`. A lesson about them is a lesson about *an
   action that cannot be aimed*, and no amount of experience makes it aimable.
4. **The projection that makes effects portable is blind to some effects.** `mv` preserves content, so
   under the content projection it is `INERT` — a real effect, invisible. One atom in this experiment
   is exactly that, and the receipt names it. You cannot have full portability and full completeness
   for free; you choose which blindness you can afford.

## 5. What is genuinely not solved — and it is not cost

Three of sixteen requests were refused, and each refusal is a *class*:

- **The surface cannot express the effect.** `git` can only rewrite or remove the **tip** commit, not
  an arbitrary one, so "replace the content of entity X" and "remove entity X" are refused by the
  reader — for every agent, at every budget. Surface expressivity is a property of the machine, not of
  the learner.
- **The effect needs composition.** An archive has no "replace a member's content" atom; replacing is
  *delete then append*. The measuring agent found no single atom with that effect and reported
  `UNREACHABLE__NO_MEASURED_ATOM_HAS_THIS_EFFECT` — correct, and it is the wall.
- **Demonstration loses requests to its own side effects.** In one machine the demonstrator deleted the
  very entity it was supposed to update, then could not recover inside the same request. Measurement
  tells you the effect *before* you spend the state; demonstration spends the state to find out.

So the missing part is a **composer over measured effects** — planning with preconditions and effects
instead of picking one atom. That is a small thing to say and a large thing to build, and part of it
already exists in this tree (`predicate_world_abstraction_v1`, `operator_semantics_v1`,
`hierarchical_skill_library_v1`) — it should be joined to this measurement, not rebuilt beside it.

## 6. Is this revolutionary, compared with how agents learn now?

**Yes, and precisely where.** Current agents get better by paying per task, in every environment,
for ever — either by demonstrations, by rollouts, or by weight updates that compress the distribution
of tasks they have seen. This pays **per environment, once**, in a currency the environment cannot
fake (its own state, read before and after), and then every request in that environment costs one
trial. The 2026 literature agrees on the constants and disagrees on nothing that matters here:
`OSExpert` (arXiv 2603.07978) needed explicit exploration of an environment's unit functions to get
any transfer to unseen UIs at all, and measured existing computer-use agents at 0–10% success without
it; `MacArena` (arXiv 2606.06560) showed Linux→macOS rankings inverting by 26.5 points, i.e. the
surface does not transfer; Voyager's skills transferred to a new world **because the underlying API
was the same**. That last sentence is the whole law: **experience transfers when the interface
transfers, and the invariant that makes it transfer is the effect, not the command.**

**And no, in the sense the sentence "so we solve everything on a computer" needs.** The tax is per
machine and a general computer has unboundedly many machines, so the total is
`O(machines × adaptation) + O(requests)`. That is a change of currency from requests to environments.
It is the right change — it is the only one that makes cost sub-linear in usage — and it is not zero.

## 7. Sentience, and the weights

Nothing in this file is evidence of a sentient creature, and it would be dishonest to let the
architecture imply one. What is built is a **procedure acquirer**: it measures what actions do,
stores (precondition class → effect), acts through the effect vocabulary, and is judged by a reader it
cannot forge. That is a mechanism for capability. If sentience is the goal, then the honest status is:
no test in this tree measures it, this mechanism does not create it, and any sentence claiming it
would be exactly the kind of unverified claim the laws of this repository forbid.

On parameters: this system has **zero learned parameters**, which is the only way "every bit must be
calculated" is satisfiable. Its content is (a) theorems — α-equivalence, the shape of a state delta;
(b) measurements — the effect table, one cell per (atom × state class); (c) a verifier — the machine's
own reader. No knowledge house, no pre-training, no distillation, nothing to waste compute on. "The
best part is no part" is satisfied in the strongest available sense: the part that is *not* there is
the parameter tensor, and the part that is there is a table whose every bit came from an execution.

## 8. The single bottleneck, restated once more

> Last turn: **the size of the hypothesis space is the vocabulary; its reach per demonstration is the
> invariant set.**
> This turn: for computer use, the invariant is the **effect vocabulary**, the vocabulary is the
> **(atom × state class) table**, and the binding constraint is neither of those. It is **composition**.

Every remaining failure here is a composition or an addressing gap, not a measurement gap. Fix
composition — plan over measured preconditions and effects, verify each step with the reader, and
refuse when the surface cannot express the effect — and the same adaptation tax buys whole workflows
instead of single atoms. That is the next single thing, and it is the only one on this evidence that
moves capability rather than cost.

## 9. Non-claims

- Four CLI/database surfaces, not four GUI applications: there is no display in this sandbox. The law
  is the same; the adaptation constant on a screen is much larger — which makes the exchange rate
  *better* for measurement and the tax bigger, both at once.
- 18 atoms, 16 requests, one corpus of four machines. This is a cost law with measured constants, not
  a benchmark score, and no benchmark is claimed or improved.
- Producer-run, authority **NONE**, no independent verification, no terminal or capability credit.
- Zero model dependency, zero network at run time, zero spend. Every verdict is the machine's own
  reader before and after the command; a command that prints "ok" and changes nothing is `INERT` and
  is tested to be.

## 10. Reproduce

```
python3 canonical/tools/instant_learning_in_a_new_environment_v1.py \
  --out /tmp/inst.jsonl --receipt /tmp/inst_receipt.json
python3 canonical/tools/instant_learning_in_a_new_environment_v1.py \
  --out /tmp/inst_shuf.jsonl --receipt /tmp/inst_shuf_receipt.json --shuffle 7
python3 -m pytest canonical/tests/test_instant_learning_in_a_new_environment_v1.py -q
```
