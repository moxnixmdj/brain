from __future__ import annotations

from canonical.runtime.finality_gate_v2 import (
    closure_certificate_digest,
    control_receipt_digest,
    environment_receipt_digest,
    isolation_receipt_digest,
    replay_receipt_digest,
    route_binding_digest,
    verify_finality,
)


def h(ch):
    return (ch * 64)[:64]


def item(name, identity, verifier):
    row = {
        "name": name,
        "identity_sha256": identity,
        "owned_or_sealed": True,
        "right_to_use": True,
        "independently_verified": True,
        "verifier_id": verifier,
    }
    row["control_receipt_sha256"] = control_receipt_digest(row)
    return row


def closure(kind, route_root, rows, verifier):
    row = {
        "closure_kind": kind,
        "route_root_sha256": route_root,
        "item_identity_sha256": sorted(x["identity_sha256"] for x in rows),
        "complete": True,
        "independently_verified": True,
        "verifier_id": verifier,
        "method_id": "fixed-point-" + kind,
        "result_sha256": h("8" if kind == "dependency" else "9"),
    }
    row["receipt_sha256"] = closure_certificate_digest(row)
    return row


def state():
    manifest = h("a")
    root = h("b")
    binding = {
        "active_manifest_sha256": manifest,
        "route_root_sha256": root,
        "independently_verified": True,
        "verifier_id": "route-binding-verifier",
        "result_sha256": h("c"),
    }
    binding["receipt_sha256"] = route_binding_digest(binding)

    deps = [item("lib", h("d"), "dep-control-verifier")]
    effects = [item("runtime", h("e"), "effect-control-verifier")]
    dep_cert = closure("dependency", root, deps, "dep-closure-verifier")
    eff_cert = closure("effect", root, effects, "effect-closure-verifier")

    env = {
        "zero_ambient_authority": True,
        "general_network_available": False,
        "environment_image_sha256": h("f"),
        "launcher_policy_sha256": h("1"),
        "independently_verified": True,
        "verifier_id": "environment-verifier",
    }
    env["receipt_sha256"] = environment_receipt_digest(env)

    isolation = {
        "performed": True,
        "donor_root_sha256": h("2"),
        "post_isolation_route_root_sha256": root,
        "independently_verified": True,
        "verifier_id": "isolation-verifier",
        "result_sha256": h("3"),
    }
    isolation["receipt_sha256"] = isolation_receipt_digest(isolation)

    def replay(rid, carrier, verifier, result):
        row = {
            "replay_id": rid,
            "carrier_id": carrier,
            "verifier_id": verifier,
            "active_manifest_sha256": manifest,
            "route_root_sha256": root,
            "dependency_closure_receipt_sha256": dep_cert["receipt_sha256"],
            "effect_closure_receipt_sha256": eff_cert["receipt_sha256"],
            "environment_receipt_sha256": env["receipt_sha256"],
            "isolation_receipt_sha256": isolation["receipt_sha256"],
            "pass": True,
            "independently_verified": True,
            "result_sha256": result,
        }
        row["receipt_sha256"] = replay_receipt_digest(row)
        return row

    return {
        "active_manifest_sha256": manifest,
        "route_root_sha256": root,
        "route_root_binding": binding,
        "dependency_closure": deps,
        "dependency_closure_certificate": dep_cert,
        "effect_closure": effects,
        "effect_closure_certificate": eff_cert,
        "replay_environment": env,
        "donor_isolation": isolation,
        "clean_room_replays": [
            replay("r1", "carrier-a", "replay-verifier-a", h("4")),
            replay("r2", "carrier-b", "replay-verifier-b", h("5")),
        ],
    }


def assert_reason(mutator, expected):
    s = state()
    mutator(s)
    out = verify_finality(s)
    assert out["pass"] is False, out
    assert out["reason"] == expected, out


def test_valid_finality_certificate_has_no_terminal_authority():
    out = verify_finality(state())
    assert out["pass"] is True, out
    assert out["d_finality"] is True
    assert out["terminal_authority"] is False
    assert out["terminal_credit_delta"] == 0


def test_route_binding_tamper_fails():
    assert_reason(
        lambda s: s["route_root_binding"].update({"result_sha256": h("9")}),
        "ROUTE_ROOT_BINDING_SELF_DIGEST_MISMATCH",
    )


def test_unowned_dependency_fails_even_with_recomputed_receipt():
    def mutate(s):
        row = s["dependency_closure"][0]
        row["owned_or_sealed"] = False
        row["control_receipt_sha256"] = control_receipt_digest(row)
    assert_reason(mutate, "UNOWNED_OR_UNCONTROLLED_RESOURCE")


def test_control_receipt_tamper_fails():
    assert_reason(
        lambda s: s["dependency_closure"][0].update({"verifier_id": "changed"}),
        "CLOSURE_ITEM_CONTROL_RECEIPT_MISMATCH",
    )


def test_dependency_completeness_item_set_mismatch_fails():
    def mutate(s):
        cert = s["dependency_closure_certificate"]
        cert["item_identity_sha256"] = []
        cert["receipt_sha256"] = closure_certificate_digest(cert)
    assert_reason(mutate, "CLOSURE_CERTIFICATE_ITEM_SET_MISMATCH")


def test_closure_certificate_tamper_fails():
    assert_reason(
        lambda s: s["effect_closure_certificate"].update({"result_sha256": h("7")}),
        "CLOSURE_CERTIFICATE_SELF_DIGEST_MISMATCH",
    )


def test_environment_network_escape_fails():
    def mutate(s):
        env = s["replay_environment"]
        env["general_network_available"] = True
        env["receipt_sha256"] = environment_receipt_digest(env)
    assert_reason(mutate, "ZERO_AMBIENT_REPLAY_ENVIRONMENT_UNPROVED")


def test_environment_receipt_tamper_fails():
    assert_reason(
        lambda s: s["replay_environment"].update({"launcher_policy_sha256": h("7")}),
        "REPLAY_ENVIRONMENT_SELF_DIGEST_MISMATCH",
    )


def test_isolation_must_bind_post_isolation_route_root():
    def mutate(s):
        row = s["donor_isolation"]
        row["post_isolation_route_root_sha256"] = h("9")
        row["receipt_sha256"] = isolation_receipt_digest(row)
    assert_reason(mutate, "DONOR_ISOLATION_UNPROVED")


def test_isolation_receipt_tamper_fails():
    assert_reason(
        lambda s: s["donor_isolation"].update({"result_sha256": h("9")}),
        "DONOR_ISOLATION_SELF_DIGEST_MISMATCH",
    )


def test_replays_require_two_distinct_carriers():
    def mutate(s):
        row = s["clean_room_replays"][1]
        row["carrier_id"] = "carrier-a"
        row["receipt_sha256"] = replay_receipt_digest(row)
    assert_reason(mutate, "CLEAN_ROOM_CARRIER_DIVERSITY_INSUFFICIENT")


def test_replays_require_two_distinct_verifiers():
    def mutate(s):
        row = s["clean_room_replays"][1]
        row["verifier_id"] = "replay-verifier-a"
        row["receipt_sha256"] = replay_receipt_digest(row)
    assert_reason(mutate, "CLEAN_ROOM_VERIFIER_DIVERSITY_INSUFFICIENT")


def test_replay_must_bind_exact_effect_closure_receipt():
    def mutate(s):
        row = s["clean_room_replays"][0]
        row["effect_closure_receipt_sha256"] = h("9")
        row["receipt_sha256"] = replay_receipt_digest(row)
    assert_reason(mutate, "CLEAN_ROOM_REPLAY_BINDING_INVALID")


def test_replay_receipt_tamper_fails():
    assert_reason(
        lambda s: s["clean_room_replays"][0].update({"result_sha256": h("9")}),
        "CLEAN_ROOM_REPLAY_SELF_DIGEST_MISMATCH",
    )


def test_duplicate_replay_id_fails():
    def mutate(s):
        row = s["clean_room_replays"][1]
        row["replay_id"] = "r1"
        row["receipt_sha256"] = replay_receipt_digest(row)
    assert_reason(mutate, "CLEAN_ROOM_REPLAY_ID_DUPLICATE")
