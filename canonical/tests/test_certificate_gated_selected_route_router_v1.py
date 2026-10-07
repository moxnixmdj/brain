import pytest

from canonical.runtime.certificate_gated_selected_route_router_v1 import (
    AdmissionReceipt,
    RouterFailClosed,
    select_certified_route,
)


def receipt(*, admitted=True, context="ctx", cell="c1", route="r1", a="1", q="2", r="3"):
    return AdmissionReceipt(
        context_digest=context,
        cell_id=cell,
        route_id=route,
        route_blob_sha=r * 40,
        adequacy_certificate_blob_sha=q * 40,
        admission_certificate_blob_sha=a * 40,
        admitted=admitted,
    )


def test_returns_only_positive_context_bound_receipt():
    x = select_certified_route(
        actual_context_digest="ctx",
        receipts=[
            receipt(admitted=False, a="0"),
            receipt(admitted=True, a="2", route="r2"),
            receipt(admitted=True, a="1", route="r1"),
        ],
    )
    assert x.admitted is True
    assert x.context_digest == "ctx"
    assert x.route_id == "r1"


def test_fail_closed_when_no_positive_receipt_matches_actual_context():
    with pytest.raises(RouterFailClosed, match="NO_CERTIFIED_ROUTE_FOR_ACTUAL_CONTEXT"):
        select_certified_route(
            actual_context_digest="ctx",
            receipts=[receipt(context="other"), receipt(admitted=False)],
        )


def test_tie_break_is_deterministic_and_content_addressed():
    rs = [
        receipt(a="b", q="1", r="1", route="later"),
        receipt(a="a", q="f", r="f", route="earlier"),
    ]
    x1 = select_certified_route(actual_context_digest="ctx", receipts=rs)
    x2 = select_certified_route(actual_context_digest="ctx", receipts=reversed(rs))
    assert x1 == x2
    assert x1.route_id == "earlier"


def test_malformed_or_duplicate_receipts_fail_closed():
    bad = AdmissionReceipt("ctx", "c", "r", "not-a-sha", "2" * 40, "3" * 40, True)
    with pytest.raises(RouterFailClosed, match="ROUTE_BLOB_SHA_INVALID"):
        select_certified_route(actual_context_digest="ctx", receipts=[bad])

    good = receipt()
    with pytest.raises(RouterFailClosed, match="DUPLICATE_RECEIPT"):
        select_certified_route(actual_context_digest="ctx", receipts=[good, good])


def test_non_boolean_admission_fails_closed():
    bad = receipt(admitted="false")
    with pytest.raises(RouterFailClosed, match="ADMISSION_MUST_BE_LITERAL_BOOL"):
        select_certified_route(actual_context_digest="ctx", receipts=[bad])
