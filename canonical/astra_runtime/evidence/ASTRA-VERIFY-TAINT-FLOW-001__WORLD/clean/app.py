"""No external bytes reach a shell."""

import os


def handle():
    count = 3
    os.system("echo %d" % count)
