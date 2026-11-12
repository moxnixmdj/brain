# THE SECOND FAMILY: the compression mechanism generalises — measured

**2026-11-12.** Round 25. Base `83c2f6d0` (Round 24 merged). Authority `NONE`. `truth.achieved`
stays `false`. $0 incremental spend. Zero model dependency (pure stdlib AST work).

Rounds 23/24 measured compress → admit → license → replay for ONE family (periodic-table
lookup) and honestly pinned that the mechanism had not been shown to generalise. This round
asked the generalization question with the smallest possible change and measured the answer.

---

## 1. The prediction, written before the confirmatory run

> Three world-model organs — machinery byte-identical across organs, one dict literal of
> per-organ data — compress into ONE admitted abstraction with measured gain and the family
> recognised from structure; a NEVER-seen fourth world-model organ, synthesized cold, replays
> through it strictly smaller with behaviour preserved on held-out action ids.

## 2. The measurement

| step | result |
|---|---|
| lifter generalisation | every constant-collection literal (tuple/list/set/dict, recursively literal) lifts as ONE parameter — the tuple rule, generalised |
| admission economics | 2 sites: `NOT_COMPRESSIVE` (refused); **3 sites: gain = 103 bytes**, family `keyed_table_lookup` recognised from the `.get` + None-branch structure — the same 3-site economics as the periodic family, measured independently |
| never-seen 4th world model (cold) | **394 → 277 description bytes (30% smaller)** through the wake replay |
| behaviour | 0 mismatches on held-out action ids including unknowns (`'zzz'`, `''`), non-strings (`0.5`, `None`, tuples) |
| machinery ownership | `table.get`, the None-branch, and the schema constants are gone from the program — they live in the library |

The mechanism is no longer one-family. Two structurally-recognised families (periodic-table,
keyed-table) now compress, admit, and replay under the same measured discipline, with the same
refusal semantics.

## 3. What was built

**`_LiftConstants`** — the tuple rule generalised to every constant collection, recursively
(dict-of-dicts lifts as one parameter, which is exactly a world-model's table). Two exclusions
are load-bearing and pinned:
- `None`/`True`/`False` are **structural singletons, not data** (`row is None`,
  `out['known'] = True` are the machinery itself). Lifting them measured out as self-defeating:
  the abstraction grew a parameter every site passed as the same singleton, and the schema dict
  shredded into per-key parameters. A table whose data genuinely contains booleans refuses to
  lift wholesale — an honest refusal until a caller argues otherwise with a measured corpus.

**Helper renderer** — indents EVERY line of each statement. The old renderer prefixed only the
first line, so any multi-line statement (`if row is None:` with a body) rendered as a
SyntaxError that the fail-closed try swallowed and reported as "no shape". Single-line corpora
(rount 23's tables) had hidden this since the beginning.

**Probe-grid honesty, both gates** — a grid the original answers IDENTICALLY on every input
verifies nothing; it is the gate a forged abstraction would sail through. Both admission
(`compress_corpus`) and replay (`rewrite_source_with_abstractions`) now measure discrimination
(≥ 2 distinct outputs on the originals) and refuse `PROBE_GRID_NON_DISCRIMINATING` otherwise.
`compress_corpus` takes caller `probes`: domains the numeric grid cannot see (string-keyed
tables) must be probed with real domain inputs.

**The bridge's honest scope, stated** — the bridge stays SKILL-only and correctly admits
nothing it cannot probe: it has no domain knowledge, so under the vacuity gate a string-domain
organ offered through it refuses (`PROBE_GRID_NON_DISCRIMINATING`) instead of shipping an
unchecked abstraction. The second family enters the library through a caller that supplies real
domain probes (measured in the test). Wiring organ-declared domain probes into the bridge is
named next-round work, not silently skipped.

## 4. The crystallization-time question, killed with arithmetic

Round 24 named "emit abstraction calls during crystallization" as the next round. Killed before
implementation: organs must stay self-contained (pure source, no external bindings), so an
emitted call form must embed the helper — measured, that totals ~262 description bytes against
the cold form's 179 for a 12-value table. Emission only pays with a runtime-binding execution
contract (library prelude bound at organ execution), which changes the execution contract of
every downstream organ consumer — an architectural decision, not a round-sized change. Recorded
here so the arithmetic survives; the replay path (Round 24) already delivers the byte win at the
system level: library once + minimal forms beats N fat organs from the third organ, the same
economics admission already enforces.

## 5. What this changes about the honest answers

- "Is this revolutionary mechanism general or a one-family trick?" — **measured: general across
  two families**, with the generalisation being one idea (constant collections are data), not
  per-family machinery.
- The compounding loop is now family-generic in all four arrows: compress, admit, license
  (still periodic-only, honestly), replay.
- Unchanged: cross-KIND compounding remains the pinned negative; `truth.achieved` is false; no
  family flipped; the licensing of evidence policies remains periodic-only.

## 6. Honest limits

- The keyed-table family is recognised structurally (`.get` on a bare name + a None-branch) —
  one writer's shape. Other writer families (perceptors, policies) are unmeasured this round.
- The second family enters the library via domain-probed compression in tests; the bridge
  automation for non-numeric domains is named next-round work.
- The full-suite run in this sandbox carries the repo's documented environment bucket (missing
  `PIL`, `cadquery`, and other third-party modules — 29 collection errors pre-existing, not
  from this change); every suite that collects and touches the changed modules passes.
- One machine, producer-run, disposable state. $0. No sentience claim.

## 7. Next round this points at

1. **Organ-declared domain probes** — organs carry their evidence inputs in metadata; the bridge
   then admits string-domain organs through the same measured gate (closes the bridge's honest
   gap without weakening it).
2. **Perceptor/policy corpora** — measure whether the writer's remaining families compress under
   the generalised lifter (the third-family question, same cheap discipline).
3. **The learning-to-learn benchmark, re-run** — the pinned NO_COMPOUNDING verdict was measured
   against feature-bucket policies; the library now holds reusable machinery. Whether that
   changes the verdict is a pre-registrable, cache-proof question.
