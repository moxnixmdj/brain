"""Regression for the accepted-string totality hole in Unknown-Domain V3/V4.

Both generators admit any Python str with len(beacon.strip()) >= 16, then route
that value into legacy strict UTF-8 token/randomness helpers. Unpaired surrogate
code units therefore form a reachable accepted-input counterexample to the
claimed universal emission theorem.
"""
import pytest

from canonical.runtime import unknown_domain_direct_hidden_generator_v3 as g3
from canonical.runtime import unknown_domain_direct_hidden_generator_v4 as g4


BAD_BEACON="A"*16+"\ud800"
SECRET=b"S"*32


def test_v3_accepted_beacon_can_fail_strict_utf8_encoding():
    assert len(BAD_BEACON.strip()) >= 16
    with pytest.raises(UnicodeEncodeError):
        g3._generate(
            beacon=BAD_BEACON,
            evaluator_secret=SECRET,
            namespace="V3-STRING-TOTALITY-FALSIFIER",
        )


def test_v4_accepted_beacon_can_fail_strict_utf8_encoding():
    assert len(BAD_BEACON.strip()) >= 16
    with pytest.raises(UnicodeEncodeError):
        g4._generate(
            beacon=BAD_BEACON,
            evaluator_secret=SECRET,
            namespace="V4-STRING-TOTALITY-FALSIFIER",
        )
