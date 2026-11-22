# What survival of one host's knowledge would require (and what actually survives)

**Date:** 2026-11-21 · **Authority:** NONE · `truth.achieved` stays `false` · **$0**, 0 model calls, 0 parameters, 0 network
**Receipt:** `intake/RECEIPT_WHAT_TRANSFERS_TO_A_SECOND_HOST_20261121_V1.json` · **Instrument:** `canonical/tools/what_transfers_to_a_second_host_v1.py` · **Tests:** `canonical/tests/test_what_transfers_to_a_second_host_v1.py` (7 passed)
**Prior:** `intake/WHAT_IS_KNOWABLE_ABOUT_A_MACHINE_20261121_V1.md` (10 shapes, 93× retention, one host)

---

## 0. The claim being tested

The previous receipt compressed 930 observations into 10 shapes on one host and said the only
open question was whether those shapes travel. This is that test, on two hosts the shape set
had never seen:

| Host | Programs | What it is |
|---|---|---|
| **base** | 492 | the machine's `PATH`: ELF binaries, perl/sh/python scripts |
| **venv** | 13 | one interpreter and its console scripts |
| **npm-yarn** | 14 | Node/Yarn wrappers, including JS with no shebang |

**Result: the shapes travel perfectly, and they transfer almost no usable knowledge.**

---

## 1. Shapes transfer — 100 %

| Host | Shapes needed | Missing from base | Coverage |
|---|---|---|---|
| venv | 5 | **0** | 1.000 |
| npm-yarn | 3 | **0** | 1.000 |

Every shape a new host needed was already in the base set. So "the ten shapes" was not a
one-host artifact: the vocabulary `(statement kind, artifact family)` is closed across three
very different hosts.

**And that is close to worthless on its own.** A shape says *a flag list will exist*. It does
not say which flags, and it is right about "will exist" 100 % of the time while being right
about *contents* far less often:

| Key | venv precision | venv recall | npm-yarn precision | npm-yarn recall |
|---|---|---|---|---|
| artifact family (`ELF`/`SCRIPT`) | 0.250 | 1.000 | 0.325 | 1.000 |
| **producer** (shebang: `sh`, `perl`, `python3`, `env:node`) | **0.750** | 0.923 | **0.615** | 0.615 |

Recall 1.000 with precision 0.25 means the coarse key **never surprises you and is wrong three
times out of four**. Naming the producer roughly doubles precision and halves false claims —
and on the JS host it costs recall, because `env:node`, `env:pwsh` and `other` are producers the
base host had never met. **Novelty shows up as a recall hole, not as an error.**

---

## 2. The rule this forces: memory must be corroborated, not merely consistent

Banking a key on the base host means claiming: *programs with this key behave alike.* With one
member that claim is vacuous — the "dominant outcome" is just that one program's own answer,
which is exactly the per-action memory this line of work already ruled out. So a key is only
banked if **≥ 2 witnesses agree ≥ 90 %** and LOOK's flags cover ≥ 90 % of what ASK returned.

Of 19 keys on the base host:

| | count |
|---|---|
| keys seen | 19 |
| **banked** | **2** |
| refused — too few witnesses | 2 |
| refused — below the agreement floor | 10 |

The biggest key on the machine, `elf|USAGE`, has **186 members and only 80 % agreement**. The
largest ELF group is not a rule; it is a heap of 186 programs with 186 different flag sets. That
number is the honest reason there is no "general tool knowledge" to be had by grouping.

---

## 3. The finding that changes the design: LOOK is blind on the hosts that matter

| Host | Programs with *any* flag discoverable in their own bytes | LOOK's flags as a fraction of what ASK returned |
|---|---|---|
| base | **79.7 %** | **1.000** |
| venv | **7.7 %** | 0.047 |
| npm-yarn | **7.1 %** | 0.038 |

A real console script is a **241-byte stub**:

```python
#!/tmp/brainvenv/bin/python3
import re, sys
from _pytest.config import _console_main
...
    sys.exit(_console_main())
```

No flags in its bytes, no usage text, nothing. 11 of 12 venv programs are this shape. On the
base host the previous receipt measured 91 % residency — *"the knowledge was never missing"*. On
these hosts the knowledge is missing from the artifact and lives in an import it does not name.
**Residency was a property of that host, not a law about computers.**

That is why the selector asked: **ASK 12 / LOOK 1 on the venv, ASK 13 / LOOK 1 on npm-yarn**. It
activated zero banked keys on either host, so `memory_activation_precision` is `null` — not 0.0.
No activation means no claim; the earlier draft scored it as 0.0, which would have been an
invented failure.

---

## 4. Contents do not transfer at all

Statement *text* banked from the base host appeared on a new host **0 times**:

| Host | programs reusing a text prediction | predicted kinds realised | text exactly right |
|---|---|---|---|
| venv | 0 | 0 | 0 |
| npm-yarn | 0 | 0 | 0 |

So the answer to *"should we save his experience"* is now measured twice over: save the
**structure** (which kinds of statement a producer's programs make), never the strings. The
strings are the machine's; re-reading them costs 6.8 ms.

---

## 5. What he should do, in one sentence per step

> **Look first** (6.3 s for 284 MB) → **ask only what the bytes did not settle** (6.8 ms each) →
> **verify the claim against the parser** (that is where 2 self-contradictions per 90 probes live)
> → **bank structure only when ≥ 2 witnesses agree ≥ 90 %** → **re-measure discoverability on
> every new host**, because it is a property of *that* host, not of computers.

Steps 1–3 are a total pass and cost ~5 s. Step 4 is what stops the memory from becoming a
library of one-off facts. Step 5 is the one that would have been missed without this receipt.

---

## 6. What is real and what is not

**Real (measured here):**
- Shapes are portable across three hosts: 0 missing, 100 % coverage.
- The producer key is strictly sharper than artifact family on both new hosts (0.75 vs 0.25, 0.615 vs 0.325).
- A corroboration rule is load-bearing: it banks **2 of 19** keys, and without it a single
  perfectly-agreeing witness would have been banked as a rule.
- LOOK's power is host-specific: 79.7 % discoverable on base, **7.1 % on npm-yarn**. Asking is
  the correct action there, not a fallback.

**Not real (and not claimed):**
- **Three hosts are not a universe.** They are all Linux, one machine, one OS. The honest next
  falsifier is a genuinely different OS (macOS, Windows), where the artifact families themselves
  change — `Mach-O`, `.exe` with resources, PowerShell cmdlets.
- **The base host is privileged.** 79.7 % discoverability is high because Debian binaries embed
  their usage text. A host of container images or generated wrappers would look like the venv.
- **Banking 2 keys is a small, honest number.** It says the vocabulary is portable and the
  payload is not; it does not say the payload can never be made portable.
- **Nothing here touches GUI state, hidden application state, or long-horizon workflows** — still
  the reason the frontier sits near 20.6 % binary on OSWorld 2.0.
- `truth.achieved` remains **false**. No §6 claim.

---

## 7. The next falsifier (one, not a list)

Take these two bankable keys to a **different operating system**, not another directory on this
one. Prediction: artifact families change (`Mach-O`, PE, cmdlet metadata), so the family key
collapses — and the producer key survives only if "producer" is a portable notion. If it does
survive, the memory is genuinely portable structure. If it does not, the honest conclusion is
that knowledge must be re-derived per host at ~5 s a host, and that re-derivation *is* the
algorithm — the best part is still no part.

---

*Every number above is in `intake/RECEIPT_WHAT_TRANSFERS_TO_A_SECOND_HOST_20261121_V1.json`,
reproducible with `python3 canonical/tools/what_transfers_to_a_second_host_v1.py`.*
