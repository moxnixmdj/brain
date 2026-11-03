# The optimal plan — V9, after the item the plan wanted to build turned out to be already half-built

**2026-11-03.** Supersedes `OPTIMAL_PLAN_20261103_V8.md` where measurement changed it. Both of
V8's reachable items are now **landed**: P1 (`a3d5a29`) and P3 (`b3a777a`). This document is about
what is actually left, and it **demotes P4** — which V8 ranked second — because the mechanism is
already in the kernel and the version V8 proposed to build would have deleted a capability that
currently works.

Authority: **NONE.** No capability, ownership, benchmark, terminal or sentience credit follows.
`truth.achieved` stays `false`. Model dependency 0. Spend $0.

---

## 0. Banked (do not re-plan)

| item | state | evidence |
|---|---|---|
| P1 — a declared `TEST_SUITE` must be a contract oracle | **LANDED** `a3d5a29` | gate deleted → 4/6 gate tests fail; 167 focused tests; guard 17/17; production 6/6 unchanged |
| P3 — a missing parser must refuse, not silently narrow | **LANDED** `b3a777a` | report deleted → 1/5 fails; 150 focused tests; production 6/6 unchanged; guard 17/17 |
| All 12 live refusals priced | **MEASURED** | capability 7 (all one cause), selection 1, fixture 4 |
| The confinement carrier is host-blocked | **MEASURED** | `unshare -n` EPERM; no cgroup delegation; no bwrap/nsjail/docker |

---

## 1. What I got wrong in V8, and how I found out

V8 ranked **P4 — "consult `rule_expiry` at recall"** as the second-cheapest win. I started to build
it, and the first thing I did was read the recall path. It is already there:
`verified_skill_crystallizer_v1.py:1214-1230` audits rules against `rule_expiry_v1` on **every
recall** and skips `STALE` ones at line 1330.

So the honest correction is: **the wire exists.** What V8 actually wanted was one line deeper, and
that one line is a trap. Measured on the shipped store
(`canonical/astra_runtime/tmp/verified_skills_v1.sqlite`), in a copy, today:

```
rule_expiry_v1.audit → {'FRESH': 0, 'STALE': 0, 'UNKNOWN': 5}
   all five: NO_WORLD_FINGERPRINT_RECORDED
```

The kernel skips `STALE` only (line 1330, `stale_ids`). `rule_expiry_v1`'s own docstring says
**`UNKNOWN` is "treated exactly like STALE, because unknown provenance fails closed"**. If the
kernel obeyed the module's stated default, **the shipped store would stop serving every rule it
ships.** That is not a hardening; it is the deletion of an owned capability, and it would look like
a security improvement while doing it.

Worse, the store **cannot transition those rules to `FRESH`**: `reverify()` requires the rule's own
training example, and the shipped bundle's rule keys are
`['created_ts', 'domain', 'error_class', 'language', 'provenance', 'rule', 'skeleton_fp', 'skill_id',
'verified_hits']` — **no training example**. The rules would be `UNKNOWN` forever.

And one more: a successful recall **increments `verified_hits` but never stamps the world**. So a
rule can be re-proven by execution and remain permanently unprovenanced.

That is the real P4, and it is smaller, safer, and the opposite of what V8 proposed.

---

## 2. The plan

### P4′ (next) — stamp the world when a rule is *proven*, not only when it is taught

One capability currently producing nothing: `now_world_fingerprint` is a parameter of
`recall_and_apply_verified` that **no production caller passes**, and a verified hit does not stamp.

- **Deliverable:** in `_commit_verified_hit`, after a contract-oracle verified hit, call
  `rule_expiry_v1.record_taught(db_path, skill_id)` — the rule has just reproduced its lesson in
  *this* world, which is exactly what the stamp means.
- **Success criterion:** a rule taught in world A, re-proven in world B by a real suite, then moved
  back to world A, is freshly stamped and `FRESH` in B; and a `STALE` rule that cannot run is still
  skipped. Both directions, or the stamp is meaningless.
- **What it deliberately does NOT do:** change what `UNKNOWN` means. That decision belongs to the
  owner and to the module's own docstring, and it cannot be taken while the only way to reach
  `FRESH` is a training example the store does not have.
- **Risk:** low. It only adds stamps. **Progress class:** `VERIFIED_INTEGRATION_OF_OWNED_CAPABILITY`.

### P5 (the real frontier) — feed production misses to the version-space diagnoser

Unchanged from V8, and now the only item with synthesis content. `rule_scope_learning_v1` and
`select_probe` own the mathematics; nothing consumes a production miss. The measured flags-off path
produces exactly three such misses and the flags-on path produces none — a falsification of the
current scope, sitting unused.

- **Success criterion:** with broadening flags off, the store moves `SCOPE_STATEMENT` →
  `SCOPE_OPERATOR` **because an executed probe failed**, and then recalls the three cases it used to
  miss, with the four `<=`-is-correct controls preserved.
- **Risk:** high — it changes what the system believes about itself. Gate it on an executed
  counterexample, never on inference.

### P6 — the seven confinement refusals: still `BLOCKED_ON_HOST`, still not code

Seven of twelve live refusals are one cause, and V8's host measurement stands: no network
namespace, no cgroup delegation, no bwrap/nsjail/docker. The honest deliverable is the qualification
harness plus the requirements as an executable preflight, run where a carrier can exist. **Do not
weaken the guard to move the number.**

### The decision that is not mine to take

`rule_expiry_v1` says `UNKNOWN` == `STALE`. The only store shipped with this repository is 100%
`UNKNOWN`. Those two facts cannot both be right. Either:

1. the carrier teaches and stamps at ship time (so the shipped store is `FRESH`), or
2. the owner relaxes `UNKNOWN` for rules whose contract records a `TEST_SUITE` page and which
   re-verify on first use, or
3. the shipped store is deliberately retired.

A2 is the option that fits: after P4′, a rule that has been re-proven by a real suite carries a
stamp, so the population of `UNKNOWN` rules shrinks by execution rather than by declaration. I have
not implemented any of the three. **This is an owner decision and I am putting it in front of you
rather than picking it.**

---

## 3. Ranked

| rank | item | reachable here | effect | risk |
|---|---|---|---|---|
| 1 | P4′ stamp on verified hit | **yes** | turns "proven" into a recorded fact; unblocks the expiry story | low |
| 2 | P5 miss → scope | **yes** | the only real synthesis frontier | high |
| 3 | P6 carrier qualification harness | **no — host-blocked** | 7/12 refusals | n/a |
| — | V8's P4 as written ("treat UNKNOWN like STALE") | yes but **would delete the shipped capability** | negative | — |
| — | front-door learner connection | gated on a person | — | — |

---

## 4. Non-claims

The 6/6 in §0 is a non-blind constructed benchmark by the author of the plan, not an independent
qualification. The `UNKNOWN` measurement is over a **copy** of the shipped store, on this host; a
different host may stamp differently. Both landed items are **unadmitted**: V22 prewrite admission,
recursive OBS, blocker lease and independent verification are still missing, and none of them can be
manufactured by an agent.
