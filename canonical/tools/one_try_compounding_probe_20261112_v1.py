#!/usr/bin/env python3
"""Where does "experience it once, keep it, reuse it" actually stop? Measured on the live path.

Authority **NONE**. Producer-run measurement in a temporary directory. It registers no
capability, flips no family, reads no governance file, writes nothing into the repository, uses
no network and calls no model. `truth.achieved` stays `false`. Spend $0.

Rounds 23-25 measured compress -> admit -> replay by calling `compression_gain_v1` directly and
supplying the probe domain in the test. That is a measurement of the DECOMPRESSOR. The owner's
question ("give it an action once and it keeps it forever") is about the LIVE path, where nobody
supplies a probe domain and the caller is `MetaCircularOrganGraph.register_organ`. This tool
drives that live path and reports where the loop closes and where it does not:

  1. what the library holds after three structurally identical organs are registered through the
     live entry point (no caller probes anywhere);
  2. whether a never-seen fourth organ replays through what was actually admitted;
  3. what the same corpus does when a probe domain is DERIVED from the corpus instead of supplied
     by a human, which is the only version of the mechanism that can run unattended;
  4. whether two different organs can occupy the same library slot (identifier collision).

Every number printed here is produced by running the code, not read from a note.

Run from anywhere:
    python3 canonical/tools/one_try_compounding_probe_20261112_v1.py
    python3 canonical/tools/one_try_compounding_probe_20261112_v1.py --json out.json
"""
from __future__ import annotations

import argparse
import ast
import json
import pathlib
import sys
import tempfile
from typing import Any, Sequence

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

import canonical.swe_kernel.meta_circular_organ_graph_v1 as M  # noqa: E402
from canonical.swe_kernel import compression_gain_v1 as cg  # noqa: E402
from canonical.swe_kernel.concept_library_v1 import (  # noqa: E402
    CompoundingConceptLibrary,
    rewrite_source_with_concepts,
)

#: Four world-model organs of ONE structural family: byte-identical machinery, one dict literal
#: of per-organ data. T4 is never registered; it is the never-seen member.
T1 = [{"action": "a", "cost": 1.0, "failed": False, "delta": {"x": 2}},
      {"action": "b", "cost": 2.0, "failed": True, "delta": {"x": -1}}]
T2 = [{"action": "c", "cost": 3.5, "failed": False, "delta": {"y": 7}},
      {"action": "d", "cost": 0.5, "failed": False, "delta": {"y": 1}}]
T3 = [{"action": "f", "cost": 0.2, "failed": False, "delta": {"q": 1}},
      {"action": "g", "cost": 4.0, "failed": False, "delta": {"r": 2}}]
T4 = [{"action": "w", "cost": 2.5, "failed": False, "delta": {"k": 9}},
      {"action": "v", "cost": 7.0, "failed": True, "delta": {"m": -3}}]


def _src(transitions: Sequence[dict[str, Any]]) -> str:
    organ = M.synthesize_world_model_organ(transitions)
    assert organ is not None
    return organ.source_code


HELD_OUT_T4 = ["w", "v", "nope", "", "W"]


def _behaviour(source: str, entry: str, values: Sequence[Any]) -> list[Any]:
    ns: dict[str, Any] = {}
    exec(compile(source, "<probe>", "exec"), ns)
    fn = ns[entry]
    return [fn(v) for v in values]


def measure() -> dict[str, Any]:
    out: dict[str, Any] = {"schema": "ONE_TRY_COMPOUNDING_PROBE_V1", "authority": "NONE"}
    sources = [_src(t) for t in (T1, T2, T3)]
    unseen = _src(T4)

    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)

        # ---- 1. the LIVE path: three registrations, no caller-supplied probe domain anywhere
        lib = CompoundingConceptLibrary(root / "live.json")
        graph = M.MetaCircularOrganGraph(root / "live_graph.json", concept_library=lib)
        for i, src in enumerate(sources):
            graph.register_organ(
                M.synthesize_world_model_organ((T1, T2, T3)[i], name=f"wm{i}")
            )
        live_entries = [
            {"concept_id": c.concept_id, "family": c.family,
             "mdl_gain_bytes": c.mdl_gain_bytes, "corpus_sites": c.corpus_sites}
            for c in lib.concepts()
        ]
        live_replay = rewrite_source_with_concepts(unseen, lib)
        # ---- 1b. the CURVE: what one more experience buys, on the live path, with no caller
        # probes. This is the owner's question asked as arithmetic rather than as prose: after k
        # registrations, how many abstractions exist and does a never-seen member replay?
        curve = []
        with tempfile.TemporaryDirectory() as tmp2:
            lib_c = CompoundingConceptLibrary(pathlib.Path(tmp2) / "curve.json")
            graph_c = M.MetaCircularOrganGraph(
                pathlib.Path(tmp2) / "curve_graph.json", concept_library=lib_c
            )
            for k, src in enumerate(sources, start=1):
                graph_c.register_organ(
                    M.synthesize_world_model_organ((T1, T2, T3)[k - 1], name=f"curve{k}")
                )
                entries = lib_c.concepts()
                replay = graph_c.concept_library and rewrite_source_with_concepts(unseen, lib_c)
                curve.append({
                    "organs_registered": k,
                    "library_entries": len(entries),
                    "abstractions": sum(1 for c in entries if c.family),
                    "never_seen_replay": "REWRITTEN" if replay else "REFUSED",
                    "never_seen_program_bytes": (
                        cg.description_bytes("def predict(" + replay.rsplit("def predict(", 1)[-1])
                        if replay else None
                    ),
                })
        out["curve"] = curve

        out["live_path"] = {
            "organs_registered": 3,
            "library_entries": live_entries,
            "abstractions_admitted": sum(1 for e in live_entries if e["family"]),
            "raw_slots": len(getattr(lib, "_concepts", {}) or {}),
            "never_seen_replay": "REWRITTEN" if live_replay else "REFUSED",
            # The PROGRAM's bytes. The shared helper is counted separately below: it is stored
            # once for the whole family, and folding it into one program would make reuse look
            # like a loss on that program while the family is what got cheaper.
            "never_seen_program_bytes": (
                cg.description_bytes(live_replay.rsplit("def predict(", 1)[0] and
                                     "def predict(" + live_replay.rsplit("def predict(", 1)[-1])
                if live_replay else None
            ),
            "never_seen_total_bytes_with_helper": (
                cg.description_bytes(live_replay) if live_replay else None
            ),
            "never_seen_cold_bytes": cg.description_bytes(unseen),
        }

    # ---- 2. what the mechanism does when the probe domain is DERIVED, not supplied
    corpus = list(sources) + [unseen]
    derived = _derive_probe_domain(corpus)
    derived_used = "DERIVED" if derived else "NONE"
    res_derived = cg.compress_corpus(sources, probes=derived) if derived else None
    res_supplied = cg.compress_corpus(sources, probes=_human_domain())
    out["probe_domain"] = {
        "derived_from_corpus": derived_used,
        "derived_probe_count": len(derived),
        "admitted_with_derived_probes": (
            [(a["concept_id"], a["gain_bytes"], a["family"]) for a in res_derived["abstractions"]]
            if res_derived else []
        ),
        "refusals_with_derived_probes": res_derived["refusals"] if res_derived else [],
        "admitted_with_human_supplied_probes": [
            (a["concept_id"], a["gain_bytes"], a["family"]) for a in res_supplied["abstractions"]
        ],
    }

    # ---- 3. identifier collision: two structurally different organs, one library slot
    with tempfile.TemporaryDirectory() as tmp:
        lib2 = CompoundingConceptLibrary(pathlib.Path(tmp) / "collide.json")
        ids = []
        for i, src in enumerate(sources):
            entry = M._skill_organ_to_concept_entry(
                M.make_organ(stratum=M.SKILL, name=f"c{i}", task_signature="wm",
                             entrypoint="predict", source_code=src),
                corpus_sources=[src],
            )
            if entry is not None:
                ids.append(entry.concept_id)
                lib2.admit_verified_concept(entry)
        out["identifier_collision"] = {
            "entries_offered": len(ids),
            "distinct_concept_ids": len(set(ids)),
            "slots_after_admission": len(getattr(lib2, "_concepts", {}) or {}),
            "distinct_organs_lost": max(0, len(set(sources)) - len(getattr(lib2, "_concepts", {}) or {})),
        }

    # ---- 4. replay correctness of whatever the derived-probe path round-trips
    if res_derived and res_derived["abstractions"]:
        a = res_derived["abstractions"][0]
        with tempfile.TemporaryDirectory() as tmp:
            lib3 = CompoundingConceptLibrary(pathlib.Path(tmp) / "replay.json")
            _admit(lib3, a)
            report = cg.rewrite_source_with_abstractions(unseen, lib3, probes=derived)
            out["derived_replay"] = {
                "rewritten": report is not None,
                "bytes_before": report["bytes_before"] if report else cg.description_bytes(unseen),
                "bytes_after": report["bytes_after"] if report else None,
                "behaviour_mismatches": _mismatches(report, unseen, HELD_OUT_T4),
            }
    else:
        out["derived_replay"] = {"rewritten": False, "behaviour_mismatches": 0}
    return out


def _human_domain() -> list[Any]:
    """The domain a human supplies in the tests: every real action id plus unknowns."""
    return sorted({str(t["action"]) for table in (T1, T2, T3) for t in table}) + ["zzz", ""]


def _derive_probe_domain(sources: Sequence[str]) -> list[Any]:
    """Probe inputs derived from the corpus itself -- the only version that runs unattended."""
    return cg.derive_probe_domain(sources)


def _admit(lib: CompoundingConceptLibrary, abstraction: dict[str, Any]) -> None:
    from canonical.swe_kernel.concept_library_v1 import ConceptEntry

    lib.admit_verified_concept(ConceptEntry(
        concept_id=str(abstraction["concept_id"]),
        arity=int(abstraction["arity"]),
        param_names=tuple(abstraction["param_names"]),
        body_expr="",
        body_stmts=cg.helper_body_stmts(abstraction),
        domain_kind="any",
        mdl_gain_bytes=int(abstraction["gain_bytes"]),
        corpus_sites=int(abstraction["sites"]),
        verified_hits=1,
        family=str(abstraction.get("family") or ""),
    ))


def _mismatches(report: dict[str, Any] | None, unseen: str, values: Sequence[Any]) -> int:
    if report is None:
        return 0
    prelude = "\n".join(str(h).rstrip() + "\n" for h in report["helpers"].values())
    cold = _behaviour(unseen, "predict", values)
    warm = _behaviour(prelude + str(report["source"]), "predict", values)
    return sum(1 for a, b in zip(cold, warm) if a != b)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", type=pathlib.Path, default=None)
    args = parser.parse_args(list(argv) if argv is not None else None)

    result = measure()
    live = result["live_path"]
    print("one-try compounding probe  --  authority NONE, producer-run, temp dirs only\n")
    print("LIVE PATH (register_organ -> concept library -> wake replay, no caller probes)")
    print(f"  organs registered                             {live['organs_registered']}")
    print(f"  library entries                               {len(live['library_entries'])}")
    print(f"  abstractions admitted (family set)            {live['abstractions_admitted']}")
    print(f"  never-seen organ replay                       {live['never_seen_replay']}")
    print(f"  never-seen program bytes                      "
          f"{live['never_seen_cold_bytes']} cold"
          + (f" -> {live['never_seen_program_bytes']} warm"
             f" (+ shared helper, total {live['never_seen_total_bytes_with_helper']})"
             if live['never_seen_program_bytes'] else ""))
    print()
    print("CURVE (each row = one more organ experienced, never-seen member replayed after it)")
    print("  organs  library  abstractions  never-seen replay  bytes")
    for row in result["curve"]:
        print(f"  {row['organs_registered']:>6}  {row['library_entries']:>7}  "
              f"{row['abstractions']:>13}  {row['never_seen_replay']:>17}  "
              f"{row['never_seen_program_bytes'] or '-'}")
    print()
    pd = result["probe_domain"]
    print("PROBE DOMAIN")
    print(f"  derived from the corpus                       {pd['derived_from_corpus']}"
          f" ({pd['derived_probe_count']} probes)")
    print(f"  admitted with derived probes                  {len(pd['admitted_with_derived_probes'])}")
    print(f"  admitted with human-supplied probes           {len(pd['admitted_with_human_supplied_probes'])}")
    if pd["refusals_with_derived_probes"]:
        print(f"  refusal when derived                          "
              f"{[r['reason'] for r in pd['refusals_with_derived_probes']]}")
    print()
    ic = result["identifier_collision"]
    print("IDENTIFIER")
    print(f"  entries offered / distinct ids / slots        "
          f"{ic['entries_offered']} / {ic['distinct_concept_ids']} / {ic['slots_after_admission']}")
    print(f"  distinct organs lost to one slot              {ic['distinct_organs_lost']}")
    print()
    dr = result["derived_replay"]
    print("DERIVED-PROBE REPLAY")
    print(f"  rewritten                                     {dr['rewritten']}")
    if dr["rewritten"]:
        print(f"  bytes                                         {dr['bytes_before']} -> {dr['bytes_after']}")
    print(f"  behaviour mismatches on held-out inputs       {dr['behaviour_mismatches']}")

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(result, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        print("\nWROTE", args.json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
