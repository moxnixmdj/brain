import hashlib

from canonical.runtime import unknown_domain_direct_candidate_v3 as c3
from canonical.runtime import unknown_domain_direct_execution_harness_v1 as harness
from canonical.runtime import unknown_domain_direct_hidden_generator_v1 as g1
from canonical.runtime import unknown_domain_direct_hidden_generator_v4 as g4
from canonical.runtime import unknown_domain_direct_hidden_generator_v5 as g5
from canonical.runtime import unknown_domain_direct_hidden_scorer_v1 as scorer


def _run(packet):
    rows=[]
    for visible,hidden in zip(packet["visible_cases"],packet["hidden_records"],strict=True):
        out=harness.execute_case(candidate_step=c3.step,case_visible=visible,hidden_record=hidden)
        assert out["scorer_result"]["pass"] is True,(visible["case_id"],out)
        rows.append(out["scorer_result"])
    assert scorer.aggregate(rows)["all_27_cases_pass"] is True


def test_v4_string_totality_counterexample_is_reachable():
    beacon="A"*16+"\ud800"
    assert len(beacon.strip())>=16
    try:
        g4._generate(beacon=beacon,evaluator_secret=b"x"*32,namespace="V4FAIL")
    except UnicodeEncodeError:
        pass
    else:
        raise AssertionError("EXPECTED_V4_STRICT_UTF8_COUNTEREXAMPLE")


def test_v5_totalizes_all_surrogate_codepoints_at_beacon_boundary():
    outputs=set()
    for cp in range(0xD800,0xE000):
        beacon="A"*16+chr(cp)
        encoded=g5._canonical_beacon(beacon)
        assert encoded.isascii()
        outputs.add(encoded)
    assert len(outputs)==0x800


def test_v5_surrogate_beacon_and_secret_matrix_passes_nonproduction_path():
    beacons=["A"*16+"\ud800","\udfff"+"B"*16,"Ω"*16,"\x00"+"C"*16]
    secrets=[b"S"*32,"T"*31+"\ud800","\udfff"+"U"*31,"λ"*32]
    for i,beacon in enumerate(beacons):
        for j,secret in enumerate(secrets):
            packet=g5._generate(
                beacon=beacon,
                evaluator_secret=secret,
                namespace=f"V5EDGE{i}{j}",
            )
            assert packet["case_count"]==27
            _run(packet)


def test_v5_preserves_v4_forced_token_collision_survival():
    original=g1._token
    try:
        g1._token=lambda *args,**kwargs:"COLLISION"
        packet=g5._generate(
            beacon="A"*16+"\ud800",
            evaluator_secret="T"*31+"\udfff",
            namespace="V5COLLIDE",
        )
        assert len({x["case_id"] for x in packet["visible_cases"]})==27
        _run(packet)
    finally:
        g1._token=original


def test_v5_large_nonproduction_sweep():
    for k in range(128):
        secret=hashlib.sha256(f"v5-secret-{k}".encode()).digest()
        beacon="V5-VERIFY-"+hashlib.sha256(f"beacon-{k}".encode()).hexdigest()[:24]
        _run(g5._generate(beacon=beacon,evaluator_secret=secret,namespace=f"V5T{k}"))


class _AdversarialStr(str):
    @property
    def __class__(self):
        raise RuntimeError("INSTANCE_CLASS_HOOK_MUST_NOT_RUN")

    def strip(self,*args,**kwargs):
        raise RuntimeError("OVERRIDDEN_STRIP_MUST_NOT_RUN")

    def encode(self,*args,**kwargs):
        raise RuntimeError("OVERRIDDEN_ENCODE_MUST_NOT_RUN")

    def __getattribute__(self,name):
        if name in {"strip","encode"}:
            raise RuntimeError("OVERRIDDEN_GETATTRIBUTE_MUST_NOT_RUN")
        return str.__getattribute__(self,name)


class _AdversarialBytes(bytes):
    @property
    def __class__(self):
        raise RuntimeError("INSTANCE_CLASS_HOOK_MUST_NOT_RUN")

    def __bytes__(self):
        raise RuntimeError("OVERRIDDEN_BYTES_MUST_NOT_RUN")

    def __buffer__(self,*args,**kwargs):
        raise RuntimeError("OVERRIDDEN_BUFFER_MUST_NOT_RUN")

    def __len__(self):
        raise RuntimeError("OVERRIDDEN_LEN_MUST_NOT_RUN")

    def __getitem__(self,*args,**kwargs):
        raise RuntimeError("OVERRIDDEN_GETITEM_MUST_NOT_RUN")

    def __iter__(self):
        raise RuntimeError("OVERRIDDEN_ITER_MUST_NOT_RUN")


class _FakeStr:
    @property
    def __class__(self):
        return str

    def __str__(self):
        raise RuntimeError("FAKE_STR_COERCION_MUST_NOT_RUN")


class _FakeBytes:
    @property
    def __class__(self):
        return bytes

    def __bytes__(self):
        raise RuntimeError("FAKE_BYTES_COERCION_MUST_NOT_RUN")


def _expect_generator_error(fn,code):
    try:
        fn()
    except g1.UnknownDomainGeneratorError as exc:
        assert str(exc)==code
    else:
        raise AssertionError("EXPECTED_UNKNOWN_DOMAIN_GENERATOR_ERROR:"+code)


def test_v5_totality_includes_genuine_str_and_bytes_subclasses_without_instance_hooks():
    beacon=_AdversarialStr("A"*16+"\ud800")
    secret_text=_AdversarialStr("S"*31+"\udfff")
    assert g5._is_genuine_runtime_instance(beacon,str) is True
    packet=g5._generate(
        beacon=beacon,
        evaluator_secret=secret_text,
        namespace="V5SUBCLASS",
    )
    assert packet["case_count"]==27
    _run(packet)

    secret_bytes=_AdversarialBytes(b"B"*32)
    assert g5._is_genuine_runtime_instance(secret_bytes,bytes) is True
    assert g5._secret_bytes_total(secret_bytes)==b"B"*32


def test_v5_rejects_isinstance_class_spoof_proxies_before_payload_descriptors():
    fake_str=_FakeStr()
    fake_bytes=_FakeBytes()

    # CPython consults an instance __class__ attribute for isinstance(), which is
    # exactly why isinstance is not a sound payload-domain authority here.
    assert isinstance(fake_str,str) is True
    assert isinstance(fake_bytes,bytes) is True

    assert g5._is_genuine_runtime_instance(fake_str,str) is False
    assert g5._is_genuine_runtime_instance(fake_bytes,bytes) is False

    _expect_generator_error(
        lambda:g5._canonical_beacon(fake_str),
        "POST_FREEZE_BEACON_INVALID",
    )
    _expect_generator_error(
        lambda:g5._secret_bytes_total(fake_str),
        "EVALUATOR_SECRET_INVALID",
    )
    _expect_generator_error(
        lambda:g5._secret_bytes_total(fake_bytes),
        "EVALUATOR_SECRET_INVALID",
    )


def test_runtime_type_gate_cannot_be_spoofed_by_instance_class_property():
    assert g5.RUNTIME_TYPE_GATE=="TYPE_OBJECT_MRO_MEMBERSHIP_VIA_TYPE_BASE_DESCRIPTOR"
    for value,base in (
        ("x",str),
        (_AdversarialStr("x"),str),
        (b"x",bytes),
        (_AdversarialBytes(b"x"),bytes),
    ):
        assert g5._is_genuine_runtime_instance(value,base) is True
    assert g5._is_genuine_runtime_instance(_FakeStr(),str) is False
    assert g5._is_genuine_runtime_instance(_FakeBytes(),bytes) is False
