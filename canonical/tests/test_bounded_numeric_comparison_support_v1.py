from canonical.runtime.bounded_numeric_comparison_support_v1 import classify_support,parse_comparison_claim

def rel(claim,evidence):
    return classify_support(claim,evidence,evidence_id="E")

def test_ge_true(): assert rel("Revenue growth is at least 10.","Report states Revenue growth is 12.")["relation"]=="SUPPORTS"
def test_ge_boundary(): assert rel("Revenue growth is at least 10.","Report states Revenue growth is 10.")["relation"]=="SUPPORTS"
def test_ge_false(): assert rel("Revenue growth is at least 10.","Report states Revenue growth is 9.99.")["relation"]=="CONFLICTS"
def test_le_true(): assert rel("Latency value is at most 5.","Trace states Latency value is 4.5.")["relation"]=="SUPPORTS"
def test_gt_boundary_false(): assert rel("Margin rate is more than 8.","Report states Margin rate is 8.")["relation"]=="CONFLICTS"
def test_lt_negative(): assert rel("Temperature value is less than -2.","Sensor states Temperature value is -3.")["relation"]=="SUPPORTS"
def test_exact(): assert rel("Count value is exactly 7.","Log states Count value is 7.")["relation"]=="SUPPORTS"
def test_not_exact(): assert rel("Count value is not exactly 7.","Log states Count value is 8.")["relation"]=="SUPPORTS"
def test_unrelated_key():
    x=rel("Revenue growth is at least 10.","Report states Margin rate is 12.")
    assert x["status"]=="RESOLVED" and x["relation"]=="UNRELATED"
def test_nonnumeric_evidence_unknown():
    x=rel("Revenue growth is at least 10.","Report states Revenue growth is high.")
    assert x["status"]=="UNRESOLVED" and x["claim_numeric_comparison"] is True
def test_noncomparison_claim_unknown():
    x=rel("Revenue growth is 10.","Report states Revenue growth is 12.")
    assert x["status"]=="UNRESOLVED" and x["claim_numeric_comparison"] is False
def test_comparison_parser_identity():
    x=parse_comparison_claim("Company revenue is at least 12.5.")
    assert x["entity"]=="company" and x["field"]=="revenue" and x["operator"]=="GE" and x["threshold_text"]=="12.5"
