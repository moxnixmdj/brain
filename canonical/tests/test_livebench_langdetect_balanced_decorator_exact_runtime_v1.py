import hashlib
from pathlib import Path

from langdetect.detector_factory import DetectorFactory, PROFILES_DIRECTORY

from canonical.runtime import livebench_langdetect_balanced_decorator_invariance_v1 as r


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def _module_path(module) -> Path:
    return Path(module.__file__).resolve()


def test_pinned_langdetect_109_source_bytes_match():
    import langdetect.detector as detector
    import langdetect.detector_factory as detector_factory
    import langdetect.utils.ngram as ngram
    import langdetect.utils.unicode_block as unicode_block

    assert _git_blob_sha(_module_path(detector)) == r.PINNED_DETECTOR_BLOB
    assert _git_blob_sha(_module_path(detector_factory)) == r.PINNED_DETECTOR_FACTORY_BLOB
    assert _git_blob_sha(_module_path(ngram)) == r.PINNED_NGRAM_BLOB
    assert _git_blob_sha(_module_path(unicode_block)) == r.PINNED_UNICODE_BLOCK_BLOB


def _factory():
    f = DetectorFactory()
    f.load_profile(PROFILES_DIRECTORY)
    f.set_seed(0)
    return f


def _feature_stream(factory: DetectorFactory, text: str):
    d = factory.create()
    d.append(text)
    d.cleaning_text()
    return d._extract_ngrams()


def test_exact_pinned_langdetect_feature_stream_is_identical():
    f = _factory()
    cases = 0
    for code, sample in sorted(r.LANGUAGE_SAMPLES.items()):
        base = sample + " " + sample
        base_features = _feature_stream(f, base)
        assert base_features
        for p in range(5):
            for h in range(5):
                if p == 0 and h == 0:
                    continue
                decorated = r.decorate_losslessly(
                    base, placeholders=p, highlights=h
                )
                assert _feature_stream(f, decorated) == base_features
                cases += 1
    assert cases == 720


def test_exact_livebench_checker_bytes_and_decorator_counts():
    from instruction_following_eval import instructions as lb

    assert _git_blob_sha(Path(lb.__file__).resolve()) == r.PINNED_INSTRUCTIONS_BLOB

    for p in range(1, 5):
        c = lb.PlaceholderChecker("detectable_content:number_placeholders")
        c.build_description(num_placeholders=p)
        out = r.decorate_losslessly(
            "alpha beta", placeholders=p, highlights=0
        )
        assert c.check_following(out)

    for h in range(1, 5):
        c = lb.HighlightSectionChecker("detectable_format:number_highlighted_sections")
        c.build_description(num_highlights=h)
        out = r.decorate_losslessly(
            "alpha beta", placeholders=0, highlights=h
        )
        assert c.check_following(out)


def test_exact_response_language_checker_is_decorator_causally_invariant():
    from instruction_following_eval import instructions as lb

    # langdetect is stochastic by default. Fixing the source-supported seed
    # isolates the causal question: can the decorator itself change detection?
    DetectorFactory.seed = 0
    try:
        passed = 0
        for code, sample in sorted(r.LANGUAGE_SAMPLES.items()):
            base = sample + " " + sample
            checker = lb.ResponseLanguageChecker("language:response_language")
            checker.build_description(language=code)
            base_result = checker.check_following(base)
            assert base_result, code
            for p, h in ((1, 0), (4, 0), (0, 1), (0, 4), (4, 4)):
                decorated = r.decorate_losslessly(
                    base, placeholders=p, highlights=h
                )
                assert checker.check_following(decorated) == base_result
                passed += 1
        assert passed == 150
    finally:
        DetectorFactory.seed = None
