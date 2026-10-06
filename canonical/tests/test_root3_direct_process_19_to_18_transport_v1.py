from canonical.runtime import root3_direct_process_19_to_18_transport_v1 as transport


def test_current_repo_transports_old_19_site_dominator_to_18():
    out = transport.verify()
    assert out["status"] == "PASS__MONOTONE_SUBSET_TRANSPORT"
    assert out["old_verified_site_count"] == 19
    assert out["current_site_count"] == 18
    assert out["new_sites"] == []
    assert out["deleted_sites"] == [[
        "canonical/runtime/bound_capabilities/archive_verify_gnu_tar.py",
        40,
        "subprocess.run",
    ]]
    assert out["shared_dominator_identical"] is True


def test_mediator_normalizer_rejects_semantic_change():
    old = "header exact 29-site subprocess universe\nALLOW"
    new = "header exact 18-site subprocess universe\nDENY"
    a, b = transport._normalize_mediator(old, new)
    assert a != b


def test_authorizer_normalizer_rejects_extra_change():
    old = 'if int(callsite.get("registry_site_count", -1)) != 19:\n    return "X"'
    new = 'if int(callsite.get("registry_site_count", -1)) != 18:\n    return "Y"'
    a, b = transport._normalize_authorizer(old, new)
    assert a != b


def test_classifier_normalizer_rejects_extra_change():
    old = "frozen as 19 exact Python process-creation\nmodifying the 19 callers\nlen(EXPECTED) != 19\nALLOW"
    new = "frozen as 18 exact Python process-creation\nmodifying the 18 callers\nlen(EXPECTED) != 18\nDENY"
    a, b = transport._normalize_classifier(old, new)
    assert a != b
