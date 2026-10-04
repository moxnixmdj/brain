from canonical.runtime import livebench_union25_channel_factorization_v1 as f


def test_exact_21_to_5_plus_3_factorization():
    out=f.verify()
    assert out["hard_signature_count"]==21
    assert out["global_chassis_count"]==5
    assert out["count_overlay_count"]==3
    assert out["exact_factorization_identity"]=="21 = 8 + 4 + 4 + 4 + 1"
    assert out["signatures_per_chassis"]=={
        "CONSTRAINED_SINGLETON":1,
        "ENGLISH_LOWER":4,
        "ENGLISH_UPPER":4,
        "NEUTRAL":8,
        "RESPONSE_LANGUAGE":4,
    }


def test_factorization_is_bijective():
    for sig in f.expected_factorized_signatures():
        chassis,overlays=f.factor_signature(sig)
        assert f.reconstruct(chassis,overlays)==sig


def test_conflict_deleted_cross_channels():
    assert f.K not in f.CHASSIS_ALLOWED_OVERLAYS["RESPONSE_LANGUAGE"]
    assert f.C not in f.CHASSIS_ALLOWED_OVERLAYS["ENGLISH_UPPER"]
    assert f.C not in f.CHASSIS_ALLOWED_OVERLAYS["ENGLISH_LOWER"]
