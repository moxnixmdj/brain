# The census was wrong, the acquisition is real, and the law has now held three times

**2026-11-12.** Base `79df0c78`. Branch `arena/56406da4-brain`. Round 9.

Round 8 ended by promoting *binding* to the top of the work list on the strength of a census:
61 rows `NOT_BINDABLE` against 9 `BLOCKED_BY_UNKNOWN`. The same document named the error that
produced it — *"I measured what stopped a capability first and called it what stops it"* — and then
committed it again one paragraph later. This round measures whether the census itself is valid, and
it is not.

Authority **NONE**. One machine, no independent verifier, $0, zero model dependency.
`truth.achieved` stays `false`. No capability registered. Registry read, never written.

---

## 1. The census was measuring my sentences, not the machine

The census feeds each capability its own **keywords**. On two rows, with a real sentence instead:

| Capability | Keyword soup | A real sentence |
|---|---|---|
| `text.file.write` | not selected | routed to **`image.extract.ocr.tesseract`** and blocked on a missing OCR tool |
| `json.query.jq` | `NOT_BINDABLE: ['jq_filter']` | routed to **`yaml.to_json.yq`**, `VERIFIED_ACTION` |

`text.file.write` was never blocked by the machine. It was blocked because five keywords are not a
request, and the front door — correctly — could not tell what to do with them.

**So round 8's 61 is an upper bound on machinery defects, not a count of them, and probably a loose
one.** The retraction is the substance of this round. A census that does not control the input cannot
rank the machinery, and I built one and drew a conclusion from it.

## 2. What did work: acquisition

The one lever that produced a verified action, held in my hands, reproduced:

```
yaml.to_json.yq   ACTION_FAILED  Blocker:BOUND_APT_METADATA_NOT_FOUND:yq
        ↓   /usr/bin/python3 -m pip install --user --break-system-packages yq pyyaml
yaml.to_json.yq   VERIFIED_ACTION
```

No root (uid 1001), no `sudo`, no dpkg lock, no apt metadata. **`pip --user --break-system-packages`
put `yq` and `pyyaml` on a box where apt could not.** That is a real +1 in the terminal census
(33 → 34 `VERIFIED_ACTION`), reproduced across two runs.

Two traps inside that result, both mine:

- **The first "success" was an artifact.** I ran `PATH=/tmp/venv/bin:$PATH python3 …`, which resolves
  to `/tmp/venv/bin/python3` — a different interpreter that could `import yaml`. The control run used
  `/usr/bin/python3`, which could not. I read a difference between two pythons as a difference
  between two PATHs. **Every result here re-run under `/usr/bin/python3`.**
- **`pip --user` is refused by PEP 668** on this image; `--break-system-packages` is what makes it
  work, and that flag is a *decision*, not a detail — it deliberately overrides the OS's own
  protection. It is defensible for a user-scoped install on a disposable box and not obviously
  defensible anywhere else. Recording it as a measurement, not a recommendation.

## 3. What did not work: teaching a blind sensor its blind spot

The presence probe `_adapter_required_modules` scans an adapter's imports and asks the machine
whether those modules actually exist. That is the right idea — *test for features, not versions*.
It is blind in a specific way: **8 of the 11 apt-sourced entries expose no statically visible module
at all**, including

```
docx.document.create.python_docx   adapter=python_document_builder   apt=['python3-docx']
json.query.jq                      adapter=jq_query                  apt=['jq']
```

`python_document_builder` reaches for its library through `importlib.import_module(name)` where
`name` arrives as an argument, so no static scan can ever see it. The template, meanwhile, states it
as a literal: `'module': 'docx'`. The information is one field away from the scanner.

So I ran the counterfactual — patch the scanner to read the template's literal module, re-run:

| Capability | Before the patch | After the patch |
|---|---|---|
| `docx.document.create.python_docx` | `BOUND_APT_METADATA_NOT_FOUND` | `DOCUMENT_SPEC_UNRESOLVED` |
| `docx.document.create_from_json_record` | `JSON_DOCX_SPEC_UNRESOLVED` | `JSON_DOCX_SPEC_UNRESOLVED` |
| `professional.artifact.visual_observer.v1` | not selected | not selected |

**The blocker moved; it did not go away.** No capability that was failing began working.

And the reason is visible in the first row of the table above: `docx` **was already importable** —
`pip` installed it, `import docx` succeeds — and the capability still failed on
`DOCUMENT_SPEC_UNRESOLVED`. Granting the scanner perfect sight would have bought a capability that
cannot parse its own argument. The sensor was never the constraint.

## 4. The law, with three confirmations

> **A blocker is the obstacle whose removal makes the thing work. Anything found by a census is a
> symptom.**

- **Round 8:** close all 9 blind premises → 3 become selected → **0 work**.
- **Round 8, same document:** promote binding on 61 rows → the 61 were **my sentences** (§1).
- **Round 9:** give the presence probe perfect sight → **0 work**.

Three counterfactuals, three nulls. Every blocker I have found by counting has dissolved when I
removed it. The counterfactual is not a nicety; it is the only instrument in this exercise that has
ever falsified anything, and it has never once confirmed a census.

## 5. So what is the real limiting factor?

Not the sensors. Not the binder. Not the registry's argument lists. Those are all *cheap* to fix and
*inert* to fix, which is why three rounds of fixing them changed nothing measurable.

The measurements say the limiting factor is **the distance between a request and a callable
interface**, and it has three parts that this round did not touch:

1. **A sentence must name its inputs.** `file.copy.v1` correctly answers
   `PATH_NOT_STATED_IN_THE_SENTENCE` when the sentence names no path. That refusal is right, and no
   amount of machinery work removes it — only a caller that says what it means.
2. **A box must hold the tool.** Proven: +1, rootless, six seconds. This is the cheapest lever in the
   system and the only one that produced a verified action today.
3. **An interface must be able to state what it needs.** 8 of 11 apt entries cannot; but fixing that
   buys nothing until (1) holds.

The order matters: **(1) before (2) before (3)** — because (3) is inert without (1), and (2) is
trivial once (1) is satisfied.

## 6. Answering the owner

**"What is wrong?"** My measurement, twice. The machinery is in better shape than the last two rounds
reported: 34 of 64 exercised capabilities verify on this box *right now*, after nothing but `pip`.

**"Why can't we just give it the most advanced actions?"** We can, and today's answer is narrower
than last round's: the actions are mostly already there and mostly already work. What fails is
supplying a specific request — a path, a filter, a module — which is the caller's job and cannot be
engineered away inside the capability.

**"Am I right or wrong?"** Right that the mechanism works and that one experience can be enough.
Wrong that the remaining work is large: three rounds of me hunting a big structural defect found
nothing that survived a counterfactual. The remaining work looks **small and caller-shaped**, which
is the better news.

**"Sentient creature."** Unchanged and unmeasured. The one thing this round adds is negative and
about me: I drew a firm conclusion from a census whose inputs I never controlled, then named the
error, then repeated it in the same document. The law in §4 is written about the machine and it is
just as true about the person holding the pen.

## 7. Receipts and non-claims

- `census_vs_counterfactual_20261112.py` — the retraction measurement, the acquisition probe and the
  sensor counterfactual, re-runnable on any box.
- `canonical/tests/test_census_vs_counterfactual_v1.py` — pins the acquisition result (+1, rootless),
  the probe's blind spot (8 of 11) and the counterfactual null.
- Terminal census on this box, `/usr/bin/python3`, after acquisition: **34 `VERIFIED_ACTION`,
  30 `ACTION_FAILED`**, 4 no keywords.

**Not claimed:** that the 30 remaining failures are machinery defects — §1 shows some are my
sentences. Not claimed: that every remaining failure has the same shape; I counterfactualised three
of them, not thirty. Not claimed: that `pip --user --break-system-packages` is a safe general policy.
`--break-system-packages` overrides a protection the OS put there on purpose.

**Still owed from round 6:** the four-row `requires` diff
(`image.qr.generate.qrencode`, `image.code.decode.zbarimg`,
`sqlite.table.create_from_json_records`, `sqlite.table.verify_against_json_records`) — proposed, never
applied; the registry is CODEOWNERS-protected.
