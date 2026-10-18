"""Type-directed sampling of valid arguments for any bound capability.

`capability_type_surface_v1` tells us, for every capability, the type of every input slot
(67/67 signatures, 163 slots, 13 types, zero unknowns). What it does not do is *produce* a
value of a given type. This module is the inverse of the surface's parsers: given a signature,
it samples arguments that `capability_type_surface_v1.check()` accepts.

Why this is the load-bearing piece, from first principles:

- ONE-SHOT PLAN V4 asks each spec to pass `min_instances: 500` fresh instances. Across ~40
  specs that is ~20,000 instances. Hand-writing them is the slow path; sampling them is a loop.
- A capability is only a capability for *unseen instances of a declared input class*
  (TRUE_CAPABILITY_TEST_LAW_V1). A sampler over the declared types is literally the machine
  that manufactures unseen instances.
- With instances available, oracles can be *mined from observation* (invariant mining over
  input/output pairs) rather than hand-authored, which is the only model-free way to get an
  independent oracle.

This is the QuickCheck/Hypothesis idea applied at the capability level: types in, valid
instances out. Zero model, zero dependency.

Every path this module hands out is created inside a caller-supplied workspace, because the
bound adapters reject anything outside the repository (PATH_OUTSIDE_REPOSITORY).
"""
from __future__ import annotations

import json
import random
import string
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import capability_type_surface_v1 as ts

SCHEMA = "PROJECT_BRAIN_TYPE_DIRECTED_SAMPLER_V1"

_WORDS = ("alpha", "bravo", "charlie", "delta", "echo", "foxtrot", "golf", "hotel",
          "india", "juliet", "kilo", "lima", "mike", "november", "oscar", "papa")


def _word(rng: random.Random) -> str:
    return rng.choice(_WORDS)


def _text(rng: random.Random, n: int = 3) -> str:
    return " ".join(_word(rng) for _ in range(n))


# --------------------------------------------------------------------------------------
# per-type samplers.  Each returns a value the surface's _accepts() will approve.
# --------------------------------------------------------------------------------------

def _s_number(rng: random.Random, ws: Path, slot: str = "") -> float:
    return round(rng.uniform(-1000.0, 1000.0), rng.choice([0, 1, 2]))


def _s_number_list(rng: random.Random, ws: Path, slot: str = "") -> list[float]:
    return [_s_number(rng, ws) for _ in range(rng.randint(1, 5))]


def _s_pair_list(rng: random.Random, ws: Path, slot: str = "") -> list[list[float]]:
    """(pixel, value) anchors, never scalars.

    Two constraints come from the surface, not from taste:
    - pairs, not numbers -- x_ticks was mistyped NUMBER_LIST for months, which is why
      chart.raster.scene_graph.v1 was selected and then could not execute;
    - at least 3 anchors -- calibrate_axis needs three points to fit an axis, so the surface
      rejects len < 3. Sampling 2 was my bug, not the surface's.
    """
    return [[round(rng.uniform(0, 1000), 1), round(rng.uniform(-100, 100), 2)]
            for _ in range(rng.randint(3, 6))]


def _s_bool(rng: random.Random, ws: Path, slot: str = "") -> bool:
    return rng.choice([True, False])


def _s_string(rng: random.Random, ws: Path, slot: str = "") -> str:
    return _word(rng)


def _s_json_text(rng: random.Random, ws: Path, slot: str = "") -> str:
    obj: dict[str, Any] = {_word(rng): rng.choice([_s_number(rng, ws), _text(rng, 1), _s_bool(rng, ws)])
                           for _ in range(rng.randint(1, 3))}
    return json.dumps(obj, sort_keys=True)


def _s_kv(rng: random.Random, ws: Path, slot: str = "") -> dict[str, Any]:
    return {_word(rng): _s_number(rng, ws) for _ in range(rng.randint(1, 3))}


def _s_argv(rng: random.Random, ws: Path, slot: str = "") -> list[str]:
    return [rng.choice(["python", "-B", "pytest", _word(rng)])
            for _ in range(rng.randint(1, 4))]


# --------------------------------------------------------------------------------------
# content-aware file generation
#
# Type-validity is not semantic validity. A PATH_FILE holding three random words satisfies
# _accepts(PATH_FILE, ...) and is nevertheless useless: json.query.jq raises JSONDecodeError
# on it, and every python-repair capability raises on it too, because they need real JSON and
# real Python. Measured on the first sweep: 26 of 70 capabilities failed every instance, and
# essentially all of those failures were this, not type errors.
#
# So the file's CONTENT is inferred from the slot name. The slot names are not free-form --
# they are the adapter's actual parameter names (json_path, yaml_path, python_source,
# markdown_path), which is why this works at all.
# --------------------------------------------------------------------------------------

_JSON_DOC = '{{"records": [{{"id": {i}, "name": "{w}", "value": {v}}}]}}'
_YAML_DOC = "alpha: {i}\nbeta:\n  - {i}\n  - {i2}\nname: {w}\n"
_CSV_DOC = "id,name,value\n{i},{w},{v}\n{i2},{w2},{v2}\n"
_PY_MODULE = "def {fn}(a, b):\n    return a + b\n\n\ndef {fn2}(x):\n    return x * 2\n"
_PY_TEST = ("import {mod}\n\n\ndef test_{fn}_adds():\n"
            "    assert {mod}.{fn}(1, 2) == 3\n\n\ndef test_{fn2}_doubles():\n"
            "    assert {mod}.{fn2}(4) == 8\n")
_MANIFEST = '{{"files": ["a.txt", "b.txt"], "root": ".", "name": "{w}"}}'


def _content_for(slot: str, rng: random.Random) -> tuple[str, str]:
    """Return (suffix, content) appropriate to what `slot` actually names."""
    s = (slot or "").lower()
    w, w2 = _word(rng), _word(rng)
    i, i2 = rng.randrange(1000), rng.randrange(1000)
    v, v2 = round(rng.uniform(-100, 100), 2), round(rng.uniform(-100, 100), 2)
    fn, fn2 = _word(rng), _word(rng)
    if "yaml" in s or "yml" in s:
        return ".yaml", _YAML_DOC.format(i=i, i2=i2, w=w)
    if "json" in s or "manifest" in s:
        doc = _MANIFEST.format(w=w) if "manifest" in s else _JSON_DOC.format(i=i, w=w, v=v)
        return ".json", doc
    if "csv" in s or "records" in s:
        return ".csv", _CSV_DOC.format(i=i, w=w, v=v, i2=i2, w2=w2, v2=v2)
    if "markdown" in s or s.endswith("_md") or s == "md":
        return ".md", f"# {w}\n\n{_text(rng, 6)}\n\n- {w2}\n"
    if "test" in s or "corpus" in s:
        return ".py", _PY_TEST.format(mod="subject", fn=fn, fn2=fn2)
    if "python" in s or "source" in s or s.endswith("_py") or "module" in s:
        return ".py", _PY_MODULE.format(fn=fn, fn2=fn2)
    if "html" in s or "page" in s:
        return ".html", f"<html><body><h1>{w}</h1><p>{_text(rng, 5)}</p></body></html>"
    if "pdf" in s:
        return ".pdf", "%PDF-1.4\n% sampled placeholder\n"
    if "png" in s or "image" in s or "screenshot" in s:
        return ".png", ""
    return ".txt", _text(rng, 4)


def _new_file(rng: random.Random, ws: Path, slot: str) -> Path:
    ws.mkdir(parents=True, exist_ok=True)
    suffix, content = _content_for(slot, rng)
    p = ws / f"{slot or 'f'}{rng.randrange(1 << 30)}{suffix}"
    p.write_text(content, encoding="utf-8")
    return p


def _s_path_file(rng: random.Random, ws: Path, slot: str = "") -> str:
    return str(_new_file(rng, ws, slot))


def _s_path_dir(rng: random.Random, ws: Path, slot: str = "") -> str:
    ws.mkdir(parents=True, exist_ok=True)
    d = ws / f"{(slot or 'd')[:12]}{rng.randrange(1 << 30)}"
    d.mkdir(parents=True, exist_ok=True)
    # a source root for the python-repair cluster must contain real python and real tests
    if "source" in (slot or "").lower() or "root" in (slot or "").lower():
        fn, fn2 = _word(rng), _word(rng)
        (d / "subject.py").write_text(_PY_MODULE.format(fn=fn, fn2=fn2), encoding="utf-8")
        (d / "test_subject.py").write_text(_PY_TEST.format(mod="subject", fn=fn, fn2=fn2),
                                           encoding="utf-8")
    return str(d)


def _s_path_output(rng: random.Random, ws: Path, slot: str = "") -> str:
    ws.mkdir(parents=True, exist_ok=True)
    suffix, _ = _content_for(slot, rng)
    # an output must not exist yet; keep the declared type so parsers downstream accept it
    return str(ws / f"o{rng.randrange(1 << 30)}{suffix}")


def _s_path_list(rng: random.Random, ws: Path, slot: str = "") -> list[str]:
    return [_s_path_file(rng, ws, slot) for _ in range(rng.randint(1, 3))]


_SAMPLERS = {
    ts.NUMBER: _s_number,
    ts.NUMBER_LIST: _s_number_list,
    ts.PAIR_LIST: _s_pair_list,
    ts.BOOL: _s_bool,
    ts.STRING: _s_string,
    ts.JSON_TEXT: _s_json_text,
    ts.KV: _s_kv,
    ts.ARGV: _s_argv,
    ts.PATH_FILE: _s_path_file,
    ts.PATH_DIR: _s_path_dir,
    ts.PATH_OUTPUT: _s_path_output,
    ts.PATH_LIST: _s_path_list,
}


class SamplingFailure(RuntimeError):
    pass


def sample_args(signature: Mapping[str, str], rng: random.Random, workspace: Path) -> dict[str, Any]:
    """Sample one valid argument mapping for `signature` (slot -> type name).

    Raises SamplingFailure if a slot's type has no sampler. UNKNOWN has none by design --
    the surface accepts nothing for UNKNOWN, so a slot typed UNKNOWN is a real defect in the
    registry and must stay loud rather than be papered over with a guess.
    """
    out: dict[str, Any] = {}
    for slot, want in signature.items():
        fn = _SAMPLERS.get(want)
        if fn is None:
            raise SamplingFailure("NO_SAMPLER_FOR_TYPE:" + str(want) + ":" + str(slot))
        out[slot] = fn(rng, workspace, slot)
    return out


def sample_many(signature: Mapping[str, str], n: int, rng: random.Random,
                workspace: Path) -> list[dict[str, Any]]:
    """Sample `n` independent argument mappings."""
    return [sample_args(signature, rng, workspace) for _ in range(n)]


def sample_and_check(signature: Mapping[str, str], n: int, rng: random.Random,
                     workspace: Path) -> dict[str, Any]:
    """Sample `n` mappings and run every one through the surface's own `check()`.

    The surface is the authority on validity, not this module: sampling is a hypothesis,
    `check()` is the verdict. Reporting the disagreement rate is the whole point -- if the
    sampler ever emits something `check()` rejects, the sampler is wrong, not the surface.
    """
    rows = sample_many(signature, n, rng, workspace)
    bad = 0
    for args in rows:
        if ts.check(signature, args):
            bad += 1
    return {
        "schema": SCHEMA,
        "n": n,
        "slots": dict(signature),
        "accepted": n - bad,
        "rejected": bad,
        "accept_rate": (n - bad) / n if n else 0.0,
    }
