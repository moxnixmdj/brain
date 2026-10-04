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


class _HostileStr(str):
    def strip(self,*args,**kwargs):
        raise RuntimeError("HOSTILE_STRIP_DISPATCH")
    def encode(self,*args,**kwargs):
        raise RuntimeError("HOSTILE_ENCODE_DISPATCH")
    def __str__(self):
        raise RuntimeError("HOSTILE_STR_DISPATCH")


class _HostileBytes(bytes):
    def __bytes__(self):
        raise RuntimeError("HOSTILE_BYTES_DISPATCH")
    def __len__(self):
        raise RuntimeError("HOSTILE_LEN_DISPATCH")


def test_v5_bypasses_hostile_str_subclass_virtual_methods():
    beacon=_HostileStr("A"*16+"\ud800")
    secret=_HostileStr("S"*31+"\udfff")
    canonical=g5._canonical_beacon(beacon)
    assert type(canonical) is str
    assert canonical.startswith("UDIRV5-BEACON-HEX|")
    raw=g5._secret_bytes_total(secret)
    assert type(raw) is bytes
    assert len(raw)>=32
    packet=g5._generate(beacon=beacon,evaluator_secret=secret,namespace="V5HOSTILESTR")
    assert packet["case_count"]==27
    _run(packet)


def test_v5_materializes_hostile_bytes_subclass_via_buffer_protocol():
    secret=_HostileBytes(b"S"*32)
    raw=g5._secret_bytes_total(secret)
    assert type(raw) is bytes
    assert raw==b"S"*32
    packet=g5._generate(beacon="B"*16,evaluator_secret=secret,namespace="V5HOSTILEBYTES")
    assert packet["case_count"]==27
    _run(packet)


def test_v5_rejects_short_hostile_str_by_base_strip_semantics():
    short=_HostileStr("   short   ")
    try:
        g5._canonical_beacon(short)
    except g1.UnknownDomainGeneratorError as exc:
        assert str(exc)=="POST_FREEZE_BEACON_INVALID"
    else:
        raise AssertionError("EXPECTED_SHORT_HOSTILE_STR_REJECTION")
