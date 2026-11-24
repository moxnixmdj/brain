# Manufacture what the refusal asks for — and prove a fake cannot pass

**Round 9. The producer was in the program's own help text the whole time; the census had never read past the first column.**

Date: 2026-11-24 · Base: `caefcd5f` (PR #7056) · Branch: `arena/4f5cb973-brain`

---

## 1. What round 8 left open, and where the answer actually was

Round 8 closed with the next bottleneck named: **state, not reading**. 87 `UNLOADABLE`
refusals said the file was there and its *content* was the wrong kind, and substituting a
witness could not answer that, because the environment contained nothing of that kind.

The plan was to manufacture it — to have the program produce the missing artefact from its
own declarations. That plan was right about the mechanism and wrong about where the problem
was. Before a producer could be composed, a simpler defect had to surface:

**`openssl req` was not in the census at all.**

```
$ openssl --help
Standard commands
asn1parse         ca                ciphers           cmp
cms               crl               crl2pkcs7         dgst
...
req               rsa               rsautl           ...
```

That is a **columnar table**. `parse_subcommand_candidates` kept only `re.split(r"\s{2,}")[0]`
— the first column — so `req`, `genpkey`, `rsa` and everything else sitting mid-row was never
even a candidate. And behind that, `DEFAULT_MAX_SUBCOMMANDS = 24` read 24 of openssl's 147
commands; `req` sits at index 37, so even as a candidate it was cut before being asked.

Two underived numbers, one blind column read. Together they meant the operation that
**creates a certificate** was invisible to a machine with 87 refusals asking for one.

## 2. Measured

| | doors | openssl ops | openssl doors |
|---|---|---|---|
| before | 60 | 728 | 24 |
| after | **174** | **4,287** | **138** |

Zero regressions — every other program unchanged. The cost of removing the cap: **0.7 s**
for openssl to ask all 147 subcommands, and nothing measurable for any other program.
Admission is decisive and refuses prose, so the cap bought no safety either.

## 3. The manufacturer, and the guard that is the real contribution

A producer is now composed **only from flags the program printed**, checked against the
subcommand's own scope (the scope error round 7 fixed, reintroduced by me and caught by a
failing test):

```
openssl req -x509 -newkey=rsa:1024 -keyout=produced.key -out=produced.pem -days=1 -nodes -subj=/CN=produced
openssl genpkey -algorithm=RSA -out=produced.key -pkeyopt=rsa_keygen_bits:1024
```

Both exit 0 and both artefacts are accepted by consumers that were refusing
(`openssl x509` exit 1→0, `openssl pkey` exit 1→0).

But the contribution is not that it can produce a certificate. **It is that a fabricated one
cannot pass.** arXiv 2611.23305 builds probe repositories with a dependency that cannot
legitimately be obtained, and finds Repo2Run and SetupX agents almost always write a stub —
and the harnesses **mostly mark the run successful**. Rules against it in the prompt or in
CONTRIBUTING.md did not reliably stop it.

Three conditions make that impossible here:

1. **Produced, not written.** The producer is a declaration the program printed. This module
   never assembles the bytes of the thing asked for.
2. **Verified by the program.** The consumer that refused is re-run and must accept. A stub
   cannot pass: `openssl x509` rejects bytes that are not a certificate however they are named.
3. **No vanishing.** The artefact must survive and the tree must have changed.

Adversarial check, run: a stub named `produced.pem` with PEM armour and no content →
`openssl x509` exit 1, "Could not read certificate". A stub key → `openssl pkey` exit 1,
"Could not read key". **Fabricated outcomes credited: 0.**

## 4. What the manufacturer did *not* do

**It added zero doors to the fleet.** 257 refused openssl operations ask for a producible
kind (141 `key`, 92 `certificate`, 24 `parameters`), and producing the artefact made **none
of them act**:

- the 141 that ask for a `key` are `ca`, which reads its key from **`openssl.cnf`** and never
  from the file produced — the artefact is present and unused;
- the ones that do name a file need it in the form *that* operation declared, not the form the
  producer chose;
- `dhparam` needs an input it does not have, so its producer exits 1 and the status is
  `UNVERIFIED`, not credited.

The doors came from the **census repair**, which is a reading fix. Saying otherwise would be
the self-reporting this project exists to avoid.

## 5. The refusal reader repair

The `UNLOADABLE` noun capture took everything after the verb, so
`Could not open file or uri for loading certificate from in.txt` yielded the kind
`file or uri for`, and `Could not read certificate from in.txt` yielded `certificate from in`
— fragments no producer can be found for. The kind is the noun the locative preposition hangs
off: cut at `from`/`into`/`at`, drop the program's own loader words, keep the last noun. 601
refusals now yield real kinds instead of phrases.

## 6. §3 verdict, updated

| claim | verdict now |
|---|---|
| The unknown is missing knowledge | **FALSE, twice over.** Rounds 7–9 have moved 60 → 174 doors on a fixed fleet with **zero** fetched facts. Every gain came from a string the machine already had. |
| The bottleneck is capability or model size | **FALSE.** It is *reading*: a blind column, an underived cap of 24, a noun captured from the wrong clause. |
| Instant learning works | **PARTIALLY TRUE, and now testable.** What persists is `kind → declared producer → did the consumer accept`. That is not the action; it is the term. |
| Manufacturing the missing term solves state | **FALSE as measured.** The artefact is necessary and insufficient: `ca` needs a *config*, not a file. State is deeper than one artefact. |

## 7. The next bottleneck

`openssl ca` reads its key from **`openssl.cnf`** — a *configuration* the environment must
contain, describing which files mean what. That is the next layer of state: not one artefact,
but a **contract between the program and the filesystem**, which the program also documents.
The same move applies one level up: read the config the program says it needs, and produce
*that* from the program's own declared defaults.

## 8. Limits

- The manufacturer adds no fleet doors; its numbers are the guard and the direct consumer
  tests, not a door count.
- Three producible kinds only (`certificate`, `key`, `parameters`); everything else is
  `NO_DECLARED_PRODUCER`, never a guess.
- `ca`'s config dependency is real and unmodelled.
- Authority `NONE`, sandbox only, independent verification **OPEN**. No benchmark result is
  claimed: this round measured the census and the guard, not a task suite.
