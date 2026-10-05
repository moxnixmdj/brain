from __future__ import annotations

import math

import pytest

from canonical.runtime import mysterymechanism_separable_transform_v2 as sep


def _law(x: float, z: float) -> float:
    return 2.0 * x + 3.0 * z


def _six_fit_rows():
    points = [
        (1.0, 1.0),
        (2.0, 1.0),
        (1.0, 2.0),
        (2.0, 2.0),
        (1.5, 1.2),
        (1.2, 1.7),
    ]
    return [{"x": x, "z": z, "out": _law(x, z)} for x, z in points]


def test_reserved_observation_cannot_change_structure_selection():
    fit_rows = _six_fit_rows()
    point = {"x": 1.4, "z": 1.4}

    good = sep.discover(
        fit_rows + [{**point, "out": _law(**point)}],
        bounds={"x": [1.0, 2.0], "z": [1.0, 2.0]},
        target="out",
    )
    hostile = sep.discover(
        fit_rows + [{**point, "out": _law(**point) + 1000.0}],
        bounds={"x": [1.0, 2.0], "z": [1.0, 2.0]},
        target="out",
    )

    # This is the load-bearing anti-leakage invariant: changing only the
    # reserved target cannot alter the selected transform structure or its
    # prevalidation coefficients.
    assert (
        good["selected_prevalidation"]["selection_fingerprint"]
        == hostile["selected_prevalidation"]["selection_fingerprint"]
    )
    assert good["selected_prevalidation"]["prevalidation_coefficients"] == pytest.approx(
        hostile["selected_prevalidation"]["prevalidation_coefficients"],
        rel=0.0,
        abs=1e-10,
    )
    assert good["validation_observation_used_for_library"] is False
    assert good["validation_observation_used_for_selection"] is False
    assert hostile["validation_observation_used_for_library"] is False
    assert hostile["validation_observation_used_for_selection"] is False

    assert good["prospective_validation_pass"] is True
    assert good["candidate"] is not None
    assert good["status"].startswith("PROSPECTIVELY_VALIDATED_")

    assert hostile["prospective_validation_pass"] is False
    assert hostile["candidate"] is None
    assert hostile["expression"] is None
    assert hostile["status"] == "PROSPECTIVE_VALIDATION_FAILED__EXPAND_GRAMMAR"


def test_validation_input_is_also_absent_from_candidate_library_and_selection():
    fit_rows = _six_fit_rows()
    a = sep.discover(
        fit_rows + [{"x": 1.1, "z": 1.8, "out": _law(1.1, 1.8)}],
        bounds={"x": [1.0, 2.0], "z": [1.0, 2.0]},
        target="out",
    )
    b = sep.discover(
        fit_rows + [{"x": 1.9, "z": 1.1, "out": _law(1.9, 1.1)}],
        bounds={"x": [1.0, 2.0], "z": [1.0, 2.0]},
        target="out",
    )
    assert (
        a["selected_prevalidation"]["selection_fingerprint"]
        == b["selected_prevalidation"]["selection_fingerprint"]
    )
    assert a["left_library_size"] == b["left_library_size"]
    assert a["right_library_size"] == b["right_library_size"]


def test_exact_linear_surface_survives_inner_loo_and_prospective_gate():
    rows = _six_fit_rows() + [{"x": 1.4, "z": 1.4, "out": _law(1.4, 1.4)}]
    out = sep.discover(
        rows,
        bounds={"x": [1.0, 2.0], "z": [1.0, 2.0]},
        target="out",
    )
    c = out["candidate"]
    assert c is not None
    assert c["fit_nrmse"] < 1e-8
    assert c["inner_loo_nrmse"] < 1e-7
    assert c["prospective_validation_nrmse"] < 1e-7
    for x, z in ((1.05, 1.95), (1.33, 1.66), (1.8, 1.25)):
        assert sep.predict(c, {"x": x, "z": z}) == pytest.approx(
            _law(x, z), rel=1e-7, abs=1e-7
        )
    assert out["acceptance_credit_delta"] == 0
    assert out["family_credit_delta"] == 0
    assert out["capability_credit_delta"] == 0
    assert out["ownership_credit_delta"] == 0
    assert out["private_score_claimed"] is False


def test_nonfinite_input_still_fails_closed():
    rows = _six_fit_rows() + [{"x": 1.4, "z": 1.4, "out": _law(1.4, 1.4)}]
    rows[2]["x"] = math.inf
    with pytest.raises(Exception):
        sep.discover(
            rows,
            bounds={"x": [1.0, 2.0], "z": [1.0, 2.0]},
            target="out",
        )


def test_fail_closed_solver_exposes_only_prospectively_validated_route():
    fit_rows = _six_fit_rows()
    point = {"x": 1.4, "z": 1.4}
    good_rows = fit_rows + [{**point, "out": _law(**point)}]
    bad_rows = fit_rows + [{**point, "out": _law(**point) + 1000.0}]

    good = sep.solve(
        good_rows,
        bounds={"x": [1.0, 2.0], "z": [1.0, 2.0]},
        target="out",
    )
    bad = sep.solve(
        bad_rows,
        bounds={"x": [1.0, 2.0], "z": [1.0, 2.0]},
        target="out",
    )

    assert good["status"] == "CANDIDATE_READY__PROSPECTIVE_SELECTION_SAFE__UNVERIFIED_PRIVATE_SCORE"
    assert good["route"] == "SEPARABLE_BILINEAR_PROSPECTIVE_HOLDOUT"
    assert good["candidate"] is not None
    assert good["expression"]

    assert bad["status"].startswith("FAIL_CLOSED__")
    assert bad["candidate"] is None
    assert bad["expression"] is None
