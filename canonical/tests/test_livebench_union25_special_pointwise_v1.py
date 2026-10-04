from canonical.runtime import livebench_union25_archetypes_v1 as u
from canonical.runtime import livebench_union25_special_pointwise_v1 as special


def c(iid, **slots):
    return {"instruction_id": iid, "slots": slots, "parameter_complete": True}


def build(ids, *, language="en", comma_repeat=False):
    out = []
    for iid in ids:
        if iid == u.EXIST:
            out.append(c(iid, keywords=["alpha", "beta"]))
        elif iid == u.FORBIDDEN:
            out.append(c(iid, forbidden_words=["gamma", "delta"]))
        elif iid == u.REPEAT:
            prefix = (
                "Write a compact note, please."
                if comma_repeat
                else "Write a compact note."
            )
            out.append(c(iid, prompt_to_repeat=prefix))
        elif iid == u.LANGUAGE:
            out.append(c(iid, language=language, language_name="English"))
        else:
            out.append(c(iid))
    return out


def test_exact_union25_special_delta_partition():
    out = special.verify_structural_closure()
    assert out["special_delta_structure_count"] == 17
    assert out["route_counts"] == {
        "CONSTRAINED_SINGLETON": 1,
        "REPEAT_PROMPT": 4,
        "TWO_RESPONSES": 12,
    }
    assert out["language_two_structure_count"] == 4
    assert out["nonlanguage_special_structure_count"] == 13
    assert out["remaining_union25_extra_structures_after_special_delta"] == 13614


def test_all_nonlanguage_special_delta_structures_construct():
    structures = special.enumerate_extra_special_structures()
    for ids in structures:
        if u.LANGUAGE in ids:
            continue
        out = special.solve_special(build(ids))
        assert out["status"] == "CANDIDATE_POINTWISE_OPTIMAL_SPECIAL_DELTA", (
            ids,
            out,
        )
        assert out["theoretical_max_pass_count"] == len(ids)
        assert out["requires_exact_language_postvalidation"] is False


def test_all_repeat_no_comma_comma_prefixes_have_exact_one_loss_plan():
    structures = [
        ids
        for ids in special.enumerate_extra_special_structures()
        if u.route(ids) == "REPEAT_PROMPT"
    ]
    assert len(structures) == 4
    for ids in structures:
        out = special.solve_special(build(ids, comma_repeat=True))
        assert out["status"] == "CANDIDATE_POINTWISE_OPTIMAL_SPECIAL_DELTA"
        assert out["sacrificed_instruction_ids"] == [u.REPEAT]
        assert out["theoretical_max_pass_count"] == len(ids) - 1
        assert "," not in out["response"]


def test_four_language_two_structures_construct_for_every_pinned_language():
    structures = [
        ids
        for ids in special.enumerate_extra_special_structures()
        if u.TWO in ids and u.LANGUAGE in ids
    ]
    assert len(structures) == 4
    assert len(special.single.LANGUAGE_SAMPLES) == 30
    for ids in structures:
        for code in special.single.LANGUAGE_SAMPLES:
            out = special.solve_special(build(ids, language=code))
            assert out["status"] == "CANDIDATE_POINTWISE_OPTIMAL_SPECIAL_DELTA", (
                ids,
                code,
                out,
            )
            assert out["theoretical_max_pass_count"] == len(ids)
            assert out["requires_exact_language_postvalidation"] is True
            assert out["language_code"] == code
            left, right = out["response"].split("******")
            assert left.strip()
            assert right.strip()
            assert left.strip() != right.strip()
            if u.NO_COMMA in ids:
                assert "," not in out["response"]
            if u.TITLE in ids:
                assert "<<" in out["response"] and ">>" in out["response"]


def test_active15_only_is_rejected():
    out = special.solve_special([c(u.TWO)])
    assert out["status"] == "FAIL_CLOSED"
    assert "ACTIVE15_ONLY_NOT_THIS_SOLVER" in out["error"]
