# THE DEEPEST STILL-OPEN DEFECT: NOTHING IS EVER COMPRESSED

2026-11-04, round 22 investigation note. Base `55d2522c` (round 21 merged as PR #6633).
Authority `NONE`. `truth.achieved` false. $0.

This note exists because round 21's own result note contained a claim I could not defend, and the
correction turned out to point at the deepest remaining layer.

---

## 1. What round 21 claimed, and the measurement that killed it

Round 21 opened a door: an unrouted problem now reaches the synthesizer. It reported **14 → 1
questions** for the same shape met twice, and I first called that "the difference between a library
and something that has been through an experience."

Then I ran the test that claim requires — does meeting one problem make a **different** problem
cheaper?

| period-5 | questions |
|---|---|
| cold, fresh creature | **24** |
| after meeting period-3 (14 q) and period-7 (34 q) | **24** |

**Flat.** Nothing transfers. 14 → 1 is a cache hit on the identical evidence shape, and a cache hit is
not learning. P4 was pre-registered as "a second work item of the same shape must be cheaper" — a
prediction satisfiable by a cache, and therefore not a test of learning at all. That is now in the
round-21 note under §3a, marked a failure of the prediction, not quietly deleted.

## 2. Why nothing transfers: the two solved programs are the same program

Ask the synthesizer for period 3, then period 5, and read what it wrote:

```python
def run(x0):                                    # period 3
    _block = (-2.0, 5.0, 1.0,)
    _n = len(_block)
    return _block[int(math.floor(x0) - math.floor(x0 / _n) * _n)]

def run(x0):                                    # period 5
    _block = (-1.0, -5.0, 2.0, -2.0, 5.0,)
    _n = len(_block)
    return _block[int(math.floor(x0) - math.floor(x0 / _n) * _n)]
```

**Byte-identical apart from the literal.** The program that does the work was not found by search; it
is emitted by a hardcoded writer for the "periodic" diagnosis. So there is no discovered structure to
share between the two problems — they differ only in a constant, and the constant cannot be abstracted.

## 3. And the abstraction machinery that should capture it never fires — measured

`register_organ` bridges every learned `SKILL` organ into the concept library `G_t`, which is the
thing that is supposed to accumulate. It brings back **zero** concepts after three distinct structures:

```
concepts before any work: 0
  p3: q=14  concepts now=0
  p5: q=24  concepts now=0
  p7: q=34  concepts now=0
```

Cause, found in `_skill_organ_to_concept_entry`:

```python
if not (len(fn.body) == 1 and isinstance(fn.body[0], ast.Return) and fn.body[0].value is not None):
    return None
```

The bridge only admits an organ whose body is **a single `return` expression**. The induced period
table's body is `Assign, Assign, Return` — three statements. Verified directly:

```
fn.body statements: 3 ['Assign', 'Assign', 'Return']
bridge predicate len(body)==1 and isinstance(Return): False
=> returns None
```

So the one mechanism in the tree for turning solved problems into reusable abstractions silently
rejects every organ the current synthesizer can produce, and reports nothing wrong. The library is
empty, `G_t` never grows, and **no amount of experience can compound** — which is exactly the flat
24 → 24 above, explained.

## 4. What the field says the answer is

I searched the live frontier rather than assert it (recorded in the round-21 intent's
`route_frontier`, sources checked across brain/inherited, official primary, registry and community):

- **DreamCoder** (Ellis et al., PLDI 2021): wake–sleep **library learning** plus a neural search
  policy. Its learned library improves solve rates by **+19.6 REGEX, +62.46 CLEVR, +29.73 LOGO** over
  the base DSL. This is the mechanism that makes experience compound, and it is what "gets smarter"
  means concretely.
- **Stitch** (Bowers et al., POPL 2023): corpus-guided top-down synthesis of abstractions. Learns
  comparably compressive libraries with **2 orders of magnitude less memory and 3–4 orders of
  magnitude less time** than DreamCoder's deductive compression. Rust crate + Python bindings.
- **LILO** (Grand et al., ICLR 2024): search–compress–document loop; adds **+42.27 / +63.43 / +43.24**
  over base DSL, and by construction refuses any abstraction that is not compressive.

The shared, load-bearing idea: **compress the corpus of solved programs into shared abstractions,
then let the abstractions be search primitives.** "Compressive" is the filter that separates a real
abstraction from a static menu of templates — the exact distinction this project keeps having to make.

## 5. So: is round 21 the smartest approach?

Round 21 was **necessary and strictly smaller than the real fix**. It was correct as far as it went —
before it, an unrecognised problem was refused by a four-item name list and two routes were dead. But
it addressed access, not learning, and it cannot make anything compound.

The deepest measured defect is them: **nothing is ever compressed.** The tree has the place where
compression belongs (`G_t`), one writer into it, and that writer's admission predicate excludes every
program the synthesizer produces. Any amount of routing, recall, or evidence-gathering on top of an
empty library cannot compound, because there is nothing in it to compound from.

## 6. The next round, stated so it can fail

Not "fill in a template", not a fifth prefix, not a tuned threshold:

1. **Make the abstraction bridge admit real programs.** An organ whose body is a sequence of
   statements has shareable structure inside it; requiring a single `return` expression is a
   formatting assumption masquerading as a safety check.
2. **Choose abstractions by compression, computed.** For a corpus of solved programs, an abstraction is
   admissible only if rewriting the corpus with it strictly reduces total description length. Anything
   that fails this is a menu entry, whatever it is called.
3. **Then re-run the same measurement that currently fails.** P4 must be re-stated so a cache cannot
   satisfy it: *a **period-12** structure never seen before must cost strictly fewer oracle
   questions after periods 3, 5 and 7 have been compressed into the library than it does cold.* A
   cache cannot pass that. If it stays flat, the round failed and will say so.

## 7. Honest limits

- The corpus that compression runs over is, right now, only the programs induced from periodic and
  affine structures. Compression over three near-identical templates will legitimately find little.
  That is a real limitation of this domain, not an excuse.
- Lower description length does not mean correct. Every abstracted organ still has to answer held-out
  targets through the oracle check the round-21 route already performs.
- `truth.achieved` false. `authority: NONE`. $0. No sentience claim. No external models, no neural
  weights, no dynamic code execution in result-bearing modules.
