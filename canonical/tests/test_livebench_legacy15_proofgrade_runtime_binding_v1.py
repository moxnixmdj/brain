import zipfile

import pytest

from canonical.runtime import livebench_legacy15_exact_postvalidator_v1 as post
from canonical.runtime import livebench_legacy15_hermetic_nltk_binding_v1 as hermetic


def c(iid, **slots):
    return {
        "instruction_id": iid,
        "slots": slots,
        "parameter_complete": True,
    }


def test_non_nltk_active15_contract_does_not_require_runtime_artifacts(monkeypatch):
    sentinel_registry = {"sentinel": object()}
    monkeypatch.setattr(
        post,
        "load_pinned_registry",
        lambda _root: (sentinel_registry, {"status": "SOURCE_BOUND"}),
    )
    registry, binding = post.load_proofgrade_registry(
        "/synthetic/livebench",
        [c("keywords:forbidden_words", forbidden_words=["omega"])],
    )
    assert registry is sentinel_registry
    assert binding["proofgrade_runtime_dependencies_bound"] is True
    assert binding["runtime"]["status"] == "NOT_REQUIRED__NO_NLTK_DEPENDENT_ACTIVE15_CHECKER"


@pytest.mark.parametrize(
    "contract",
    [
        c("length_constraints:number_words", num_words=100, relation="at least"),
        c("length_constraints:number_sentences", num_sentences=2, relation="less than"),
    ],
)
def test_nltk_dependent_contract_fails_closed_without_pinned_artifacts(contract):
    with pytest.raises(
        post.ExactPostvalidationError,
        match="PROOFGRADE_NLTK_BINDING_REQUIRED",
    ):
        post.load_proofgrade_registry(
            "/synthetic/livebench",
            [contract],
        )


def test_nltk_binding_is_inherited_before_source_registry(monkeypatch):
    calls = []

    def fake_runtime(wheel, data):
        calls.append(("runtime", str(wheel), str(data)))
        return {"status": "PASS__SYNTHETIC_HERMETIC_RUNTIME"}

    def fake_source(root):
        calls.append(("source", str(root)))
        return ({"x": object()}, {"status": "PASS__SYNTHETIC_SOURCE"})

    monkeypatch.setattr(post.hermetic_nltk, "verify_and_bind", fake_runtime)
    monkeypatch.setattr(post, "load_pinned_registry", fake_source)

    _registry, binding = post.load_proofgrade_registry(
        "/livebench",
        [c("length_constraints:number_words", num_words=100, relation="at least")],
        nltk_wheel_path="/artifacts/nltk.whl",
        nltk_data_root="/artifacts/nltk_data",
    )
    assert calls[0][0] == "runtime"
    assert calls[1][0] == "source"
    assert binding["runtime"]["status"] == "PASS__SYNTHETIC_HERMETIC_RUNTIME"
    assert binding["source"]["status"] == "PASS__SYNTHETIC_SOURCE"


def test_data_archive_binding_detects_extracted_drift(tmp_path):
    category = tmp_path / "tokenizers"
    category.mkdir()
    archive = category / "punkt.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("punkt/english.pickle", b"exact-bytes")

    extracted = category / "punkt" / "english.pickle"
    extracted.parent.mkdir()
    extracted.write_bytes(b"exact-bytes")

    expected = hermetic._git_blob_sha(archive)
    checked = hermetic._verify_data_archive_and_extraction(
        tmp_path,
        "tokenizers",
        "punkt.zip",
        expected,
    )
    assert checked == 1

    extracted.write_bytes(b"drift")
    with pytest.raises(hermetic.HermeticNLTKError, match="EXTRACTED_FILE_DRIFT"):
        hermetic._verify_data_archive_and_extraction(
            tmp_path,
            "tokenizers",
            "punkt.zip",
            expected,
        )
