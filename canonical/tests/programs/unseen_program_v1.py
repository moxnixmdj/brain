"""A program in a dialect no fixture uses, to test that the mechanism reads a document.

Nothing here was tuned against: the help style is `SUBCOMMANDS` with no `USAGE:` line, flags are
declared under a bare `-h, --help   show this text` heading with `REQUIRED` as a trailing word,
and the pages carry **no EXAMPLES** -- which is the ordinary shape of a real subcommand's help and
the case the planner was weakest on.

Run it directly: `python canonical/tests/programs/unseen_program_v1.py`.
"""
import subprocess, sys, pathlib, tempfile, os
sys.path.insert(0,'/home/user/brain')
from canonical.runtime import require_survey_plan_v1 as R

PROGRAM = r'''#!/usr/bin/env python3
import sys
PAGES = {
"": """vaultctl -- secrets and certificate management for a service mesh

SUBCOMMANDS
    secret        read and write secrets
    cert          issue and inspect certificates
    policy        access policy rules

Run `vaultctl <group> -h` for the group's subcommands.
""",
"secret": """secret -- read and write secrets

SUBCOMMANDS
    get           print the value of one secret
    put           store a new value under a name
    rotate        re-issue the value of an existing secret
    list          print every secret name in a namespace
""",
"secret get": """print the value of one secret

-h, --help          show this text
    --name VALUE        the secret's name                      REQUIRED
    --namespace VALUE   the namespace it lives in               REQUIRED
    --reveal BOOL       print the plaintext rather than a hash
""",
"secret put": """store a new value under a name

-h, --help          show this text
    --name VALUE        the secret's name                      REQUIRED
    --namespace VALUE   the namespace it lives in               REQUIRED
    --from-file PATH    read the value from this file
    --value TEXT        the value itself
""",
"secret rotate": """re-issue the value of an existing secret

-h, --help          show this text
    --name VALUE        the secret's name                      REQUIRED
    --namespace VALUE   the namespace it lives in               REQUIRED
""",
"secret list": """print every secret name in a namespace

-h, --help          show this text
    --namespace VALUE   the namespace to list                   REQUIRED
    --prefix TEXT       only names starting with this
""",
"cert": """cert -- issue and inspect certificates

SUBCOMMANDS
    issue         request a certificate for a hostname
    inspect       print a certificate's subject and expiry
""",
"cert issue": """request a certificate for a hostname

-h, --help          show this text
    --host VALUE        the hostname the certificate is for    REQUIRED
    --days INT          how long it should be valid for
    --ca VALUE          the signing authority to use
""",
"cert inspect": """print a certificate's subject and expiry

-h, --help          show this text
    --host VALUE        the hostname the certificate is for    REQUIRED
""",
"policy": """policy -- access policy rules

SUBCOMMANDS
    allow         permit a principal to read a secret
    revoke        remove a permission
""",
"policy allow": """permit a principal to read a secret

-h, --help          show this text
    --principal VALUE   who is being allowed                    REQUIRED
    --secret VALUE      the secret they may read                REQUIRED
    --namespace VALUE   the namespace it lives in               REQUIRED
""",
"policy revoke": """remove a permission

-h, --help          show this text
    --principal VALUE   who is losing the permission            REQUIRED
    --secret VALUE      the secret in question                  REQUIRED
""",
}
args = [a for a in sys.argv[1:] if a not in ("-h", "--help")]
key = " ".join(args)
sys.stdout.write(PAGES.get(key, PAGES.get(args[0] if args else "", PAGES[""])))
'''

d = pathlib.Path(tempfile.mkdtemp())
exe = d / "vaultctl"
exe.write_text(PROGRAM); exe.chmod(0o755)

CASES = [
    # The page's own verb. A request that says "get" -- the word the document uses for this
    # operation -- plans exactly right: `secret get --name db-password --namespace production`.
    # The same request saying "read" plans `secret put`, because read and get are different
    # tokens in the act class and nothing in these pages links them. That limit is real and is
    # recorded in the research document rather than fitted with weights.
    ('Get the secret named "db-password" from the "production" namespace.',
     ["secret","get","--name","db-password","--namespace","production"]),
    ('Issue a certificate for the host "api.example.com" valid for 90 days.',
     ["cert","issue","--host","api.example.com","--days","90"]),
    ('List every secret name in the "staging" namespace.',
     ["secret","list","--namespace","staging"]),
    ('Allow the principal "analytics-svc" to read the secret "warehouse-key" in the "data" namespace.',
     ["policy","allow","--principal","analytics-svc","--secret","warehouse-key","--namespace","data"]),
    ('Inspect the certificate for "api.example.com".',
     ["cert","inspect","--host","api.example.com"]),
    ('Rotate the secret "api-token" in the "production" namespace.',
     ["secret","rotate","--name","api-token","--namespace","production"]),
]

ok = 0
for request, want in CASES:
    out = R.require_survey_plan(str(exe), request, probes=22)
    got = list(out["plans"][0]["argv"][1:]) if out["plans"] else []
    good = got == want
    ok += good
    print(("ok  " if good else "FAIL"), request[:56])
    if not good:
        print("      want:", want)
        print("      got: ", got)
print(f"\n{ok}/{len(CASES)} on a program the planner has never seen")
