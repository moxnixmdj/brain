# One trial, and what one trial actually transfers

*2026-11-16. Numbers below are produced by this tree, on real programs on a real disk, not asserted.
AUTHORITY: NONE — producer-run measurement, not independent verification.*

---

## 1. The claim, as stated

> "We already solved instant learning and instant learning in new arbitrary environments. So: give the model
> the smartest actions once, and it keeps them permanently. That solves all computer use and the most
> advanced software engineering. We were trying to make our model a sentient creature. Is this true?"

It is **half true, and the half that is true is the more valuable half** — but not for the reason the claim
gives. One trial really is enormously multiplicative. What it multiplies is a *contract*, not a trajectory.
Everything below is that distinction, measured.

## 2. What has to be true, and what is

| # | Condition for "once and forever" | Measured | Where |
|---|---|---|---|
| 1 | the demonstration must **determine** the action | **0.5469** | `SYSTEMATIC_EDIT_SUPPLY_20261116_V1` |
| 2 | the consequence must be **seen** | **0.5445** (0.6788 × 0.8021) | `ORACLE_DENSITY_20261116_V1` |
| 3 | the situation must **recur**, exactly, uncorrupted | **0.1584 / 0.0481 / 0.3114** | `SKILL_RECURRENCE`, `ACTION_REPLAY_UNDER_CHANGE` |
| 4 | an unseen situation must still be **checkable** | **0.5000 → 1.0000** | this work: `PREDICTIVE_CONTRACT_20261116_V1` |

Row 4 is the new one, and it is the row the claim actually needs. Before this work, with no recorded
consequence an agent could see only a crash or a no-op: **17 of 34** wrong actions. After one real execution
per action, on a binding it had never seen, it catches **34 of 34**, and condemns **0 of 9** correct novel
actions.

So the claim's intuition is right — one trial is worth far more than one action. The claim's *mechanism* is
wrong: what made it work is not that the action was remembered. It is that a **parameterised contract** was
extracted and could then be applied to states that did not exist when the trial happened.

## 3. The measurement

Acquire a contract on one binding (`in.txt → out.dat`). Evaluate on a **different** binding
(`payload.txt → sub/result.dat`, different bytes, different directory, never executed during acquisition),
against the same 34 mechanically derived wrong actions the density receipt used. So this is a head-to-head
against that receipt's own worst number, not a new benchmark.

| arm | what the agent has | wrong actions caught |
|---|---|---|
| no recorded consequence | nothing (crashes and no-ops only) | **0.5000** (17/34) |
| frame only | *which paths* the action creates/removes/preserves | **0.9706** (33/34) |
| frame + intervention | + the acquired input-sensitivity counterfactual | 0.9706 |
| **full** | + a content relation (declared, or derived from the trial) | **1.0000** (34/34) |

False alarms on correct novel actions: **0 of 9**. That matters more than the detection rate: a check that
catches everything by condemning everything is worthless, and the 2026 literature is full of verifiers that
pass and patches that are rejected.

**Where the capability comes from** — 19 of 34 caught by the frame or an exit code, 15 by a content relation.

That split is the finding. **The cheapest, most transferable fact about an action turned out to be which
parts of the world it is allowed to touch.** Not its bytes, not its semantics: its *frame*. It is a set of
paths, it costs nothing, and it transfers across bindings exactly.

And because that mutant family is path-heavy by construction (three of its five rules move paths), the frame
looks sufficient. It is not. On a **content-only** family — same paths, different bytes:

| content-only errors (5) | caught |
|---|---|
| frame only | **0.4** (2/5) |
| frame + intervention | 0.4 |
| full (with relation) | **0.8** (4/5) |

The single residual miss is *located*: `split -l 3` instead of `-l 2` produces the same chunk names, and the
relation "the chunks concatenate to the input" cannot see where the partition was cut. That is not hand-waving
about limits; it is one identified hole in the relation vocabulary. The fix is a stronger relation class, not
a bigger model.

Two clauses were **derived from the single execution**, not declared: `tr`'s byte map and `sed`'s literal
substitution, each validated against a perturbed input so that a coincidence could not masquerade as a
contract (which is exactly how a whole-file "substitution" — a vacuous claim that passes any output — gets
rejected). Seven were drawn from the declared class. Zero tasks were left with no clause.

The intervention added **nothing** on this space. It is reported as a null result rather than removed, because
it is the only content check that survives when the vocabulary is empty, and the ablation shows exactly the
case that would need it — which did not occur here.

## 4. The single bottleneck, now

Last measurement said: *the consequence of an action is absent from the observation* — and observation turned
out to be saturable (density 1.0 at full state, 0.7647 at names only). That bottleneck is closed for anything
whose state you can read.

The remaining one, and it is strictly larger:

> **The agent has no prospective check. It can only verify what it has already done, on a situation it has
> already been in.**

Why this is *the* one, from first principles rather than fashion:

- **Determinacy is not ours to move.** `0.5469`, with a published ceiling near `0.70` for a full inducer on
  real systematic edits. Spending there buys at most a few points and is trace-bounded.
- **Recurrence is not ours to move.** `0.1584` of work recurs at all; `0.0481` replays exactly. That is a
  property of the world, not of the agent.
- **Observation is now saturated.** `1.0000` under a full state; the loss is a projection choice, and the
  minimal sound projection is one feature.
- **Prospective checking was at `0.5000`** — the worst number in the whole system, on the regime that covers
  most real work: the work you have not already done.

And it is the only one of the four that closes the *asymmetry* the user named: synthesis outruns
verification, because verification has been retrospective.

## 5. Is this revolutionary, or is it what everyone already does?

Both, in different places. The honest comparison with November 2026:

- **WEVA** (EMNLP 2026) makes experience predictive with a *learned* quasi-symbolic state over entities,
  preconditions and outcomes, and regulates lookahead by predicted-versus-realised agreement. Same insight,
  different cost: it learns a representation; here the contract is *read off one execution* and holds no
  parameters at all.
- **Qwen-AgentWorld** (Jun 2026) trains a language world model across terminal, OS, code, MCP — prediction as
  a model. Elegant, and the wrong shape for us: a model large enough to predict consequences is a knowledge
  house, and "the best part is no part".
- **"Current agents fail to leverage world models as tools"** (arXiv 2601.03905, 2026): even given a
  simulator, agents rarely use it. A capability that must be *invoked* by a policy is a capability that will
  not be invoked. Here the contract is checked by construction, not by the model's discretion.
- **AgentVerify** (Apr 2026) is the cautionary result: local per-action contracts scored ~80%, while chained
  compositional assume-guarantee **collapsed to 26.67%**. So do not chain contracts and call it composition.
  Verify locally, and treat a sequence as a sequence of local checks plus a goal check.
- **Tufano et al.** (arXiv 2608.17177, Aug 2026): reasoning about pre/postconditions before writing tests
  gains **9.8 points** of bug detection. Contracts are not ceremony; they change what gets generated.

So: revolutionary in *where the contract comes from* (one execution, no parameters, no training) and in
*what it is made of* (a frame plus a relational clause, both checkable). Not revolutionary in the observation
that prediction beats reaction — that is now the consensus of 2026. The differentiator is cost: 0 parameters,
0 model calls, 0 network calls, 34 real subprocesses.

## 6. Sentience

No. And it should be said plainly, because it is the one claim in the prompt that this work cannot honour.

What has been built is a system that extracts, from one trial, a checkable model of what an action requires,
what it may touch, and what relation its output must bear to its input — and that refuses to call an
uncovered observation a pass. That is **understanding** in the only operational sense available to us: a
contract that transfers beats a trace that repeats. But it is not sentience: there is no self-model, no
valenced experience, no continuity of identity, and no measurement here would distinguish a system that
comprehends from one that satisfies these contracts perfectly. Claiming otherwise would be exactly the
self-congratulation the project forbids — a claim with no receipt.

The productive version of the ambition is narrower and testable: an agent whose model of *its own actions* is
good enough that being wrong is visible before the world pays for it. That is measurable, and it is what this
receipt measures.

## 7. What is still wrong, and what would falsify this

1. **Fidelity is not correctness.** A contract acquired from a *wrong* demonstration certifies wrongness
   forever, faithfully, and cheaply. Nothing here detects that; only an external reference can. This is the
   same boundary the observation receipt named, one level up.
2. **Transfer was measured across bindings, not across programs.** The contract knows `gzip`; it does not know
   that `bzip2` is its sibling. Generalisation to a *new program* is the open problem, and a learned world
   model is currently better at that than a derived contract. This is the real trade, stated in the receipt.
3. **The relation class is finite and was invented here.** Its holes are visible (`split -l 3`); others are
   not yet. Derivation from one trial grows the class, but does not make it complete.
4. **Sequences were not measured.** One action, one binding. Composition is where AgentVerify collapsed, and
   where OSWorld's 27-checkpoint tasks die. That is the next receipt, and it should be built as *local checks
   plus a goal check*, not as chained assume-guarantee.

Falsifiers: a class of actions whose errors survive the frame, every relation, and every counterfactual; a
correct novel action condemned by a contract that was acquired correctly; or a demonstration that a trajectory
transfers better than a contract at equal observation.

## 8. Reproduce

```
python3 canonical/swe_kernel/predictive_contract_v1.py \
  --json canonical/verification/PREDICTIVE_CONTRACT_20261116_V1.json
python3 canonical/swe_kernel/capability_law_v1.py --pinned
python3 -m pytest canonical/tests/test_predictive_contract_v1.py \
  canonical/tests/test_capability_law_v1.py -q
```
