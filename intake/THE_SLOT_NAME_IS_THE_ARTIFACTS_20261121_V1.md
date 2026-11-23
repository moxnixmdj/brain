# The slot name is the artifact's, not the prose's

**Date:** 2026-11-21
**Status:** measured. +3 items. Honest ratio: small gain, several mechanisms.

## The shape

falcon 243's stub is

    import falcon.testing as testing
    def custom_environ(info: str) -> Dict[str, Any]:
        return

and the goal is *"create and return an environment with `info` variable as the root"*.

Three of the four parts are stated:

| part | who states it |
|---|---|
| the callable | the stub: `import falcon.testing as testing` |
| which member | the prose: "an **environment**" vs `create_environ` |
| the value | the stub's parameter: `info` |
| **the slot** | **nobody.** `create_environ` calls it `root_path` |

The slot exists only in the artifact's signature. Asking for it is the mechanism; the oracle
arbitrates among every slot the artifact exposes.

## Four things that had to be right, and each was wrong first

1. **The alias is not the module.** The stub binds `testing`; the corpus files those members
   under `falcon.testing`. Matching on the alias found nothing. Resolve alias → real path for
   the lookup, alias → for the emitted body.
2. **Truncating before ranking is starvation.** `_members_under` returned members sorted by
   length and cut to 24; `create_environ` is at position ~40 of 53. Ranking the whole module
   **then** keeping the head put it first. This is the same defect as the oracle budget, in a
   different place.
3. **Ask the signature through the alias.** The probe evaluates the root name in a namespace
   built from the stub's imports, where `testing` is bound and `falcon` is not. Asking for
   `falcon.testing.create_environ` returned zero keywords.
4. **A stub ending in `return ` already has its return.** The annotation rule emitted
   `return falcon.App()` into a stub whose last line is already `return `, producing
   `return return falcon.App()`. The bare expression is the completion.

## Result

    before:  79/193 = 40.9%
    after:   82/193 = 42.5%
    delta:   +3, 0 regressions
    ceiling: 110/193  ->  we reach 74.5%
    falcon:  3/21 -> 6/21

New: 243 (`testing.create_environ(host=info)`), 246 (`(path=v)`), 248 (`falcon.App()`).

**Note on 243 and 246:** our bodies pass the hidden tests through *different slots* than the
reference (`host=` and `path=` rather than `root_path=` and `http_version=`). That is the oracle
arbitrating, not me: several slots satisfy the item's own test. It is not a claim that we found
the reference's answer.

## Honest ratio

This turn produced **+3 items for four mechanisms and a fair amount of debugging.** The two
previous turns produced +16 and +12. The reason is structural: what remains in falcon is
**13 items, each a different API** (`append_link`, `get_param_as_json`, `parse_query_string`,
`Headers(...)`, `context.role = role`). There is no shared mechanism left in that library —
each needs its own construction, and several need shapes the grammar has no production for.

That is the honest signal that **per-library grammar patching is reaching its end.** The next
bottleneck is not another API family; it is the fact that the system has no way to *learn a
production from one example*. That is the user's actual question, and it has not been answered
yet.

## Not claimed

* 42.5% is the score on the 193 no-dependency items, in the environment as installed.
* `truth.achieved` remains **false**. Authority remains **NONE**.
* +3 is not evidence the approach is working well. It is evidence this particular seam is
  nearly exhausted.
