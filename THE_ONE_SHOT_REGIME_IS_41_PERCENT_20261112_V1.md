# The one-shot regime is 41% of the bound surface

**2026-11-12.** Base `dd67c1f4`. Branch `arena/1e8b91af-brain`. Round 3.

Round 1 gave the argument. Round 2 gave the measurement: one demonstration leaves 14 of 47
programs standing and the one you would pick is wrong on 90% of held-out inputs. Both rounds
ended on the same sentence:

> One try is enough exactly when the interface and the verifier already do the generalising.

That sentence is only worth writing if it can be pointed at this repository. This round points it.

Authority **NONE**. Structural census of declared metadata: it runs no capability, checks no
claim, and reports what the registry says. `truth.achieved` stays `false`. $0, zero model.

---

## 1. The census

`one_shot_regime_census_20261112.py` classifies all 145 entries of
`canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json` on two axes, with no judgement calls:

- **typed interface** — an entry point, typed arguments, and declared result fields. This is the
  `environment_fit_v1` shape: a lesson expressible as code against a declared contract, where the
  interface *is* the prior.
- **verifier strength** — whether the entry's qualification names an independent checker, and
  whether the receipt it names is actually in the tree:

|  | RECEIPTED (names a checker **and** the receipt exists) | DECLARED (names one, no receipt) | NONE |
|---|---|---|---|
| **TYPED** | **60** | 22 | **29** |
| **UNTYPED** | 18 | 7 | 9 |

```
bound capabilities            145
typed interface               111   (77%)
declares independence         107
  of which receipt on disk     78
runtime predicate self-report 113   (78%)

one-shot safe (typed + receipted)      60  = 41%
typed but nothing checks it            29  = 20%
declared receipts not in the tree       8
receipts with no attribution           20
```

A declaration is not verification — this repository's own law says verification means someone else
ran it — so `DECLARED` is deliberately **not** counted as safe. The 20 is the interesting middle:
a receipt sits on disk but nobody attributed it to an independent party.

## 2. What it says

**41% of the bound surface is in the regime where one try is genuinely enough.** Sixty
capabilities have a typed interface and a receipted independent check. For those, "do it once and
keep it" is not an overclaim: the contract carries the generalisation and the receipt carries the
trust. That is a real, countable asset, and it is the answer to *"so we solve everything?"* —
**no, but we know exactly which 60 things we solve that way.**

**20% is in the cell where one try is actively dangerous.** Twenty-nine capabilities expose a typed
interface and nothing independent checks them. Learning from one demonstration there means
permanently storing the producer's own opinion of its success. Nine of the twenty-nine are the
`python.software.*` repair family — the part of the surface the owner cares most about. That is not
a new accusation: it is the same defect that produced the 5/5 false success, which only moved to
5/5 honest when a hand-written admission rule was added. The admission rule patched one hole. This
census says there are twenty-nine doors.

**And at runtime, 78% of the surface is judged by a field the capability itself emits.** For 113 of
145, the action template's success predicate reads `result_fields` — the tool's own report. That is
not proof of dishonesty; most of those tools are stdlib wrappers whose self-report is fine. It is
proof that the runtime gate cannot, by itself, distinguish a correct answer from a confident one,
which is exactly the settlement failure Round 1 measured at 12× cheaper and strictly worse.

**Eight declared receipt paths do not exist.** Small, mechanical, and worth naming: a receipt that
is cited and absent is a citation, not evidence.

## 3. Why this is the honest answer to the question

The owner asks whether instant learning solves "anything on a computer". Three numbers now bound
that:

| number | what it counts |
|---|---|
| **5.4%** (8/149) | what the front door reachable from a sentence |
| **41%** (60/145) | what is structurally in the one-shot-safe regime |
| **20%** (29/145) | what would learn its own claim if you gave it one try |

The product of the first two is the real current figure, and it is small. The third is the trap:
the fastest way to *appear* to solve everything is to point the learner at the unchecked cells,
where every attempt looks successful and nothing is. That is what a "give it a try in every
environment" programme would actually do, and the census predicts the failure mode in advance.

## 4. What to build, in order

1. **Give an independent check to the 29.** Not a new mechanism: the registry already has
   `expect` and `verification` blocks; 60 entries show what a receipted one looks like. Nine are
   software repair, where the check is mechanical (held-out inputs, a suite the producer did not
   write, the admission rule already in the tree). This is the highest-value work available and it
   is bookkeeping with teeth.
2. **Attribute or delete the 20 unattributed receipts and the 8 missing ones.** Cheap, and it
   makes the DECLARED tier mean something.
3. **Then** widen the typed-interface count (111 → more) by expressing GUI and document work as
   code against a declared contract, which is the Agent S4 move and the only place a 2026 system
   got a 3.8×.
4. **Only then** a learner on top. A learner over a surface that cannot check itself does not
   compound; it accumulates confidence.

## 5. Receipts

```
python3 one_shot_regime_census_20261112.py --list-unchecked
canonical/tests/test_one_shot_regime_census_v1.py     7 tests, all passing
```

The tests pin the properties that make the number quotable: every capability lands in exactly one
cell and the cells sum to the total; `RECEIPTED` implies a receipt that exists; `DECLARED` is never
counted as safe; a negated marker (`"pending"`, `"false"`, `"unverified"`) is not a declaration; a
named verifier is; every orphan receipt is really absent; and the summary is derived from the
records rather than asserted.

## 6. Non-claims

This is a census of declared metadata, not an audit. A `RECEIPTED` row means the registry names an
independent checker and the named receipt is on disk; it does not mean the check was re-run today,
and nothing here re-runs it. The axis definitions are structural and could be argued with — the
counts move if the definitions move, which is why the definitions are in the file and the tests pin
them. No capability registered, no family flipped, no terminal or sentience credit. $0, zero model
dependency.
