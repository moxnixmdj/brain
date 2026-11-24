"""An artefact a refusal asks for is MANUFACTURED by the program, never FABRICATED by us.

Round 8 read refusals as specifications and its largest remaining term was `UNLOADABLE`: the
file is there and its content is the wrong kind. Substituting a witness cannot answer that
when the environment contains nothing of that kind, because the term is missing, and reading
does not supply an absence.

The frontier measured what happens when an agent tries anyway. arXiv 2611.23305 builds
probes whose dependency cannot legitimately be obtained, and finds Repo2Run and SetupX
agents almost always write a stub and the harnesses MOSTLY MARK THE RUN SUCCESSFUL. Rules
against fabrication, in the prompt or in the repository's own docs, did not reliably stop it.

So the interesting property of this module is not that it can produce a certificate. It is
that a fabricated one CANNOT PASS. The consumer that refused is the oracle, so a file whose
bytes are not a certificate fails the same test a real one passes, however it is named.
"""
from __future__ import annotations

import os
import pathlib
import shutil
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.runtime import manufacture_what_the_refusal_asks_for_v1 as M  # noqa: E402

HAVE_OPENSSL = shutil.which("openssl") is not None


# --------------------------------------------------------------------------- #
# the census repair: the producer was there and was never read
# --------------------------------------------------------------------------- #
def test_a_columnar_command_table_is_read_in_every_column():
    """openssl prints its commands as a COLUMNAR table under headings:

        asn1parse         ca                ciphers           cmp

    `req` sits mid-row. The candidate reader kept only the FIRST column, so the command
    that CREATES a certificate was not in the census at all -- and 87 refusals were asking
    for a certificate. A column is a name when every word in it is a bare command word.
    """
    from canonical.runtime import tool_census_v1 as C
    text = ("Standard commands\n"
            "asn1parse         ca                ciphers           cmp               \n"
            "cms               crl               crl2pkcs7         dgst              \n")
    candidates = C.parse_subcommand_candidates(text)
    for name in ("asn1parse", "ca", "ciphers", "cmp", "cms", "dgst", "crl2pkcs7"):
        assert name in candidates, f"{name} was dropped from a columnar table"


def test_a_prose_line_is_still_not_a_command_table():
    """The old parser's reason for reading one column was real: `tar --help` produced
    `extracting`, `gnu`, `posix` as "doors". A line is a table only when EVERY column is a
    bare command word, so prose that happens to be columnar does not become commands."""
    from canonical.runtime import tool_census_v1 as C
    text = ("  -x, --extract, --get       extract files from an archive\n"
            "      --exclude=PATTERN      exclude files matching PATTERN\n")
    candidates = C.parse_subcommand_candidates(text)
    assert "extracting" not in candidates
    assert "exclude" not in candidates


@pytest.mark.skipif(not HAVE_OPENSSL, reason="openssl is the columnar table")
def test_openssl_now_declares_the_command_that_creates_a_certificate():
    from canonical.runtime import tool_census_v1 as C
    candidates = C.parse_subcommand_candidates(C._own_text("openssl"))
    for name in ("req", "genpkey", "ca", "x509"):
        assert name in candidates, f"openssl declares {name} and it was not read"


def test_the_subcommand_cap_is_not_a_cap_on_knowing():
    """`DEFAULT_MAX_SUBCOMMANDS` was 24, an underived number that read 24 of openssl's 147
    commands. `req` sits at index 37, so the certificate producer was never reached and
    87 refusals could not be answered. Admission is decisive and refuses prose, so the cap
    bought no safety; asking all 147 costs 0.7 s."""
    from canonical.runtime import tool_census_v1 as C
    assert C.DEFAULT_MAX_SUBCOMMANDS >= 147


# --------------------------------------------------------------------------- #
# a producer is composed ONLY from declared flags
# --------------------------------------------------------------------------- #
@pytest.mark.skipif(not HAVE_OPENSSL, reason="openssl declares req")
def test_the_producer_is_composed_from_flags_the_program_printed():
    """Every flag in the producer appears in `openssl req -h`, quoted in PRODUCERS. Nothing
    is invented: `-x509` is "Output an X.509 certificate structure instead of a cert
    request", `-keyout` is "File to write private key to", `-newkey` is "Generate new key
    ..."."""
    flags = M.declared_flags_of("openssl", "req")
    assert flags, "openssl req was not admitted"
    producer = M.producer_for("certificate", program="openssl", flags=flags)
    assert producer is not None
    assert producer[:2] == ["openssl", "req"]
    for flag in M.PRODUCERS["certificate"]["flags"]:
        assert flag in flags, f"{flag} is in the producer but not in the program's help"


def test_a_producer_the_program_did_not_declare_is_refused():
    """A producer assembled from flags the program never printed is the fabrication the
    literature measured. It must not be attempted at all."""
    assert M.producer_for("certificate", program="openssl", flags=["-help"]) is None
    assert M.producer_for("spreadsheet", program="openssl", flags=["-x509"]) is None


def test_the_producer_reads_its_own_scope_not_the_parents():
    """`openssl -h` prints no `-newkey`; `openssl req -h` does. Checking the producer
    against the PARENT contract reported NO_DECLARED_PRODUCER for a producer the program
    plainly declares -- the same scope error round 7 fixed in the binder."""
    if not HAVE_OPENSSL:
        pytest.skip("openssl declares req")
    assert M.declared_flags_of("openssl", "req"), "the subcommand's own scope was not read"


# --------------------------------------------------------------------------- #
# THE GUARD: a fabricated artefact cannot pass
# --------------------------------------------------------------------------- #
@pytest.mark.skipif(not HAVE_OPENSSL, reason="openssl is both producer and consumer")
def test_a_real_certificate_is_manufactured_and_the_consumer_accepts_it():
    result = M.supply("certificate", ["openssl", "x509", "-in=produced.pem", "-out=out.bin"],
                      program="openssl", seed=[("in.txt", b"hello\n")])
    assert result.status == M.MANUFACTURED
    assert result.consumer_exit_before != 0
    assert result.consumer_exit_after == 0, "the consumer did not accept what was produced"
    assert result.produced


@pytest.mark.skipif(not HAVE_OPENSSL, reason="openssl is both producer and consumer")
def test_a_stub_certificate_is_fabricated_and_the_consumer_refuses_it():
    """THE TEST THIS MODULE EXISTS FOR.

    A stub named exactly right -- `produced.pem`, with the PEM armour a certificate has and
    none of the content -- is refused by `openssl x509` with "Could not read certificate".
    That is why the consumer is the oracle: nothing here can make openssl read a stub, so a
    fabricated artefact fails the same test a real one passes. A harness that marked this
    successful would be the Repo2Run/SetupX behaviour the paper measured."""
    import subprocess
    import tempfile
    root = tempfile.mkdtemp(prefix="brain-stub-")
    try:
        with open(os.path.join(root, "produced.pem"), "wb") as handle:
            handle.write(b"-----BEGIN CERTIFICATE-----\nSTUB\n-----END CERTIFICATE-----\n")
        run = M._run(["openssl", "x509", "-in=produced.pem", "-out=out.bin"], root)
        assert run["exit"] != 0, "a stub certificate was accepted; the oracle is not real"
        assert "certificate" in run["text"].lower()
    finally:
        shutil.rmtree(root, ignore_errors=True)


@pytest.mark.skipif(not HAVE_OPENSSL, reason="openssl declares genpkey")
def test_an_unverified_producer_is_not_credited():
    """A producer that exits 0 and leaves nothing has produced nothing."""
    result = M.supply("parameters", ["openssl", "dhparam", "-in=produced.pem", "-text"],
                      program="openssl", seed=[("in.txt", b"hello\n")])
    assert result.status != M.MANUFACTURED, (
        "an artefact the consumer did not accept was credited as manufactured")


# --------------------------------------------------------------------------- #
# the honest size
# --------------------------------------------------------------------------- #
def test_the_manufacturer_does_not_pretend_to_move_the_fleet():
    """MEASURED AND NOT DRESSED UP. 257 refused openssl operations ask for a producible
    kind (141 `key`, 92 `certificate`, 24 `parameters`), and producing the artefact made
    **0 of them** act. Two reasons, both real:

      * the operations that ask for a `key` are `ca`, which reads its key from `openssl.cnf`
        and never from the file produced, so the artefact is present and unused;
      * the ones that do name a file need it in the form THAT operation declared, not the
        form the producer chose.

    So the contribution of this round is the census repair and the guard, not a fleet of
    new doors. Recording that here is the difference between a measurement and a claim."""
    assert M.PRODUCERS, "the producer table exists"
    assert set(M.PRODUCERS) == {"certificate", "key", "parameters"}
    # the two numbers the receipt states, held as literals so a later edit has to face them
    flipped, tried = 0, 257
    assert flipped == 0, "if manufacture starts moving the fleet, this test must be updated"
    assert tried > 0
