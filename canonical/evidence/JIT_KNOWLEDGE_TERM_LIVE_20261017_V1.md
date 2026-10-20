# The Knowledge term runs live — 2026-10-17

The second term of the Theory had never been observed executing. It had only
been observed refusing. This is it running.

## What ran

`http.json.fetch_from_state` — reads a URL from a source file, fetches it over
HTTPS, writes the payload with provenance:

    EXECUTED  | http.json.fetch_from_state
    COMPLETED: True

Fetched live from `https://api.github.com/repos/moxnixmdj/brain`. Real
external content, not a fixture. The output carries `requested_url`,
`final_url`, `url_field_path` and the payload.

## Why this matters

Yesterday the chain stopped at a refusal:

    "evidence_units": [],
    "reason": "LIVE_RETRIEVAL_PROVENANCE_REQUIRED"

That refusal was correct, and it was the machine demanding exactly this:
content actually retrieved, with provenance attached. The Knowledge term is
now satisfied by a real fetch rather than by hand-written documents.

All three terms are now observed doing work in one loop:

| Term | Evidence |
|---|---|
| CAPABILITY | steps 1-2 of the evidence chain execute for real |
| KNOWLEDGE | live HTTPS fetch, provenance recorded, COMPLETED: True |
| SUBSTRATE | every run checkpoints |

## Bug found: a declared adapter that does not exist

`knowledge.json.fetch.external` declares:

    "adapter_module": "runtime_native_action"

No such module exists anywhere in the repository. Any chain routing through
that capability fails with:

    ADAPTER_UNLOADABLE | ModuleNotFoundError: No module named
                         'runtime_native_action'

So the capability the registry *names* as the Knowledge fetch is not the one
that works. The one that works is `http.json.fetch_from_state`, backed by
`canonical/runtime/bound_capabilities/http_json_fetch.py`.

This is why the Knowledge term appeared blocked: the entry point was wired to
a module that was never there. It was not a network problem and not a design
problem.

## Consequence

The registry should be repointed, or `runtime_native_action` supplied. Until
then any plan that routes through `knowledge.json.fetch.external` fails at the
first step, while an equivalent working capability sits unused beside it.

## Honest limit

This environment reaches only github.com, api.github.com, codeload.github.com,
registry.npmjs.org, pypi.org and files.pythonhosted.org. The fetch was real
and live, but against an allow-listed host. General web retrieval is
untested here.
