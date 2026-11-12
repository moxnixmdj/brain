#!/usr/bin/env python3
"""Nine blind facts become decidable; one stays blind honestly.

PREDICTIONS -- written 2026-11-12 BEFORE the confirmatory run, on branch
`arena/156d21d6-brain` at base `05c9d45ff`. Environment recon done first (git on
PATH; pypi egress verified by the audit's TCP convention; PIL absent; tesseract
absent), so each prediction names both the decision and the machine it is about.

P1  `git.repository.available` -> True, how=path_executable (git binary present).
P2  `pypi.live_metadata.available` -> True, how=pypi_tcp_reachable, evidence pypi.org.
P3  `pypi.selection.available` -> True, how=pypi_tcp_reachable (same route; the
    adapter still fail-closes on the caller's data when it runs).
P4  `structured.release_claim.available` -> True, how=network_tcp_reachable (the
    claim arrives over HTTP; the route is the machine-level precondition).
P5  All five chart facts -> DECIDED (how=subsystem_probed), value False on this
    machine, evidence names BOTH missing pieces: module:PIL and executable:tesseract.
    Absence is information -- the fact is no longer indistinguishable from
    "I have no idea".
P6  `source.candidate.provenance.verified` STAYS UNDECIDABLE__NOT_ESTABLISHED.
    No capability produces it, and a file-existence scan would fabricate
    "verified" -- sensing it dishonestly is worse than leaving it blind.
P7  Registry totals move to {PROVIDED: 100, SENSED: 24, BLIND: 1}; exactly one
    blind fact (P6's); 2 capabilities still blocked (the two source ones);
    143/145 fully decidable now (was 135 with BLIND 11 pins stale at 10).
P8  Front-door fate shift: the three capabilities whose premises became True no
    longer reject with PRECONDITION_NOT_TRUE_OF_WORLD (git -> ACTION_FAILED past
    the premise gate; pypi -> ACTION_FAILED; web.release -> AMBIGUOUS); the four
    chart capabilities reject with the premise answered False (named evidence),
    and the two source capabilities remain premise-blocked by the honest blind.
P9  Fail-closed unchanged: an unknown `.available` fact stays
    UNDECIDABLE__NOT_ESTABLISHED (never guessed).

Environment-pinned like the network-sensor test before it: if a future machine
ships PIL and tesseract, P5's value flips to True by the same instrument and
these pins are updated to the machine's truth, not silently.
"""
from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.runtime import world_probe_v1 as WP  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "canonical" / "runtime" / "BOUND_CAPABILITY_REGISTRY_V1.json"


def _probe(fact: str) -> dict:
    return WP.probe_effect(fact, goal="", goal_paths=(), root=str(ROOT))


def test_p1_git_repository_route_decided_by_the_git_binary() -> None:
    r = _probe("git.repository.available")
    assert r["how"] == "path_executable"
    assert r["true"] is True


def test_p2_p3_pypi_route_decided_by_the_scoped_tcp_probe() -> None:
    for fact in ("pypi.live_metadata.available", "pypi.selection.available"):
        r = _probe(fact)
        assert r["how"] == "pypi_tcp_reachable", fact
        assert r["true"] is True, fact
        assert r["evidence"] == "pypi.org"


def test_p4_release_claim_rides_the_network_route() -> None:
    r = _probe("structured.release_claim.available")
    assert r["how"] == "network_tcp_reachable"
    assert r["true"] is True


def test_p5_chart_facts_decided_with_named_missing_pieces() -> None:
    for fact in ("chart.query.x_value.available", "chart.query.y_value.available",
                 "chart.series.label.available",
                 "chart.question.binary_phase_solvus.available",
                 "chart.question.legend_linear_intersection.available"):
        r = _probe(fact)
        assert r["how"] == "subsystem_probed", fact
        assert r["true"] is False, fact
        assert "module:PIL" in r["evidence"], fact
        assert "executable:tesseract" in r["evidence"], fact


def test_p6_the_one_honestly_blind_fact_stays_blind() -> None:
    r = _probe("source.candidate.provenance.verified")
    assert r["how"] == "UNDECIDABLE__NOT_ESTABLISHED"
    assert r["true"] is False


def test_p7_registry_totals_after_the_nine_closures() -> None:
    caps = json.loads(REGISTRY.read_text(encoding="utf-8"))["capabilities"]
    provided = set()
    for entry in caps.values():
        for fact in entry.get("provides") or []:
            provided.add(str(fact))
    facts = sorted({str(f) for e in caps.values() for f in (e.get("requires") or [])})
    tally = {"PROVIDED": 0, "SENSED": 0, "BLIND": 0}
    blind = []
    for fact in facts:
        if fact in provided:
            tally["PROVIDED"] += 1
            continue
        r = _probe(fact)
        if r["how"] == "UNDECIDABLE__NOT_ESTABLISHED":
            tally["BLIND"] += 1
            blind.append(fact)
        else:
            tally["SENSED"] += 1
    assert tally == {"PROVIDED": 100, "SENSED": 24, "BLIND": 1}
    assert blind == ["source.candidate.provenance.verified"]
    blocked = [
        cid for cid, e in caps.items()
        if {str(x) for x in (e.get("requires") or [])} & set(blind)
    ]
    assert sorted(blocked) == ["source.authority.identity.ror",
                               "source.evidence.extract.objective_grounded.stdlib"]
    assert len(caps) - len(blocked) == 143


def test_p8_front_door_fate_shift_for_the_true_premises() -> None:
    from canonical.runtime import grounded_action_v1 as GA
    caps = json.loads(REGISTRY.read_text(encoding="utf-8"))["capabilities"]
    kw = {cid: " ".join((caps[cid].get("keywords") or [])[:6]) for cid in caps}

    # Premises now True: past the premise gate, into binding/execution fates.
    for cid, allowed in (
        ("git.repository.operate.v1", {"ACTION_FAILED"}),
        ("pypi.provenance.audit_live_artifact", {"ACTION_FAILED"}),
        ("web.release.verify.independent_http", {"AMBIGUOUS", "ACTION_FAILED"}),
    ):
        out = GA.act(kw[cid], root=str(ROOT), registry=caps, bridge=False,
                     memory=False)
        assert out.get("status") in allowed, (cid, out.get("status"))

    # Premises now honestly False: rejected, but with the subsystem probed --
    # the check can name what the machine lacks instead of shrugging.
    for cid in ("chart.raster.curve_value_query.v1",
                "chart.raster.curve_x_at_y_query.v1",
                "chart.read.binary_phase_solvus.v1",
                "chart.read.legend_linear_intersection.v1"):
        out = GA.act(kw[cid], root=str(ROOT), registry=caps, bridge=False,
                     memory=False)
        assert out.get("status") in {"UNRESOLVED", "PRECONDITION_NOT_TRUE_OF_WORLD"}, \
            (cid, out.get("status"))


def test_p9_fail_closed_unchanged_for_unknown_facts() -> None:
    r = _probe("warp.drive.available")
    assert r["how"] == "UNDECIDABLE__NOT_ESTABLISHED"
    assert r["true"] is False
