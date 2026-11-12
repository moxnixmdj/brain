"""Names a standard library kept under a second name when the first was deprecated.

Why this file exists, and what it is not
----------------------------------------
The organ refuses a change whose shown call had a different number of arguments at another call
site, and it is right to: a function replaced by a different function may not take the same
arguments. `yaml.load(h)` becoming `yaml.safe_load(h)` is exactly that case, and a test in this repo
holds it as one.

But some names are not different functions. They are the *same* function under an old name that was
deprecated and kept so old code would keep working: `assertEquals` is `assertEqual`,
`assertRaisesRegexp` is `assertRaisesRegex`, `logger.warn` is `logger.warning`. For those, the
reason the check exists does not apply -- a call does not have to take the arguments the old name's
only showing happened to pass, because the callee never changed.

Why this cannot be worked out from the two names
------------------------------------------------
It was tried, and it fails. `self.assertEquals -> self.assertEqual` and `yaml.load ->
yaml.safe_load` are the *same shape*: one attribute renamed on one object, nothing else different.
Neither is a re-export (`yaml.load is yaml.safe_load` is false), neither keeps the same docstring,
and no structural reading tells them apart. Structure says "something was renamed"; it cannot say
whether the thing on the right behaves like the thing on the left. So this is knowledge, and it is
recorded here as knowledge rather than inferred at the point of use.

Why this list is honest to ship
-------------------------------
It is short, it is checkable, and every entry is a removal the standard library announced. It is
deliberately a *closed* list of deprecations, not a growing map of "renames that turned out fine" --
an entry may only be added for a name the library itself documents as an alias of another. That
boundary is what stops this becoming a table of guesses.
"""

from __future__ import annotations

#: (the old name, the name it is an alias of, where that is written down).
#:
#: The object is deliberately NOT part of the key. The deprecation appears as `self.assertEquals`
#: on one project's class and as `self.assertRaisesRegexp` on another, and the alias is a property
#: of the *name*, not of the object it is read from. Keying on the object would silently miss every
#: spelling the record did not happen to contain.
#:
#: Every entry is a name the owning library documents as a deprecated alias AND that delegates:
#: unittest's aliases are installed by `deprecated_func(*args, **kwargs)`, and `Logger.warn` is
#: `def warn(self, msg, *args, **kwargs): ...; self.warning(msg, *args, **kwargs)`. Both therefore
#: forward *every* argument, which is what makes "the same function, so it takes what it always
#: took" true rather than assumed. An entry whose replacement has a fixed parameter list would not
#: qualify, however plainly the documentation called it a rename.
ALIASES: tuple[tuple[str, str, str], ...] = (
    # unittest, deprecated in 3.1/3.2/3.5 and removed under bpo-45162, slated for 3.12.
    # Source: docs.python.org/3.1/library/unittest.html "Deprecated aliases", and the
    # 3.12 What's New removal list.
    ("assertEquals", "assertEqual", "unittest docs, deprecated aliases"),
    ("assertNotEquals", "assertNotEqual", "unittest docs, deprecated aliases"),
    ("assertAlmostEquals", "assertAlmostEqual", "unittest docs, deprecated aliases"),
    ("assertNotAlmostEquals", "assertNotAlmostEqual", "unittest docs, deprecated aliases"),
    ("assertRegexpMatches", "assertRegex", "unittest docs, deprecated aliases"),
    ("assertNotRegexpMatches", "assertNotRegex", "unittest docs, deprecated aliases"),
    ("assertRaisesRegexp", "assertRaisesRegex", "unittest docs, deprecated aliases"),
    ("failUnlessEqual", "assertEqual", "unittest docs, deprecated aliases"),
    ("failIfEqual", "assertNotEqual", "unittest docs, deprecated aliases"),
    ("failUnlessAlmostEqual", "assertAlmostEqual", "unittest docs, deprecated aliases"),
    ("failIfAlmostEqual", "assertNotAlmostEqual", "unittest docs, deprecated aliases"),
    ("failUnless", "assertTrue", "unittest docs, deprecated aliases"),
    ("failIf", "assertFalse", "unittest docs, deprecated aliases"),
    ("failUnlessRaises", "assertRaises", "unittest docs, deprecated aliases"),
    ("assert_", "assertTrue", "unittest docs, deprecated aliases"),
    # logging: `Logger.warn` warns and then calls `self.warning(msg, *args, **kwargs)`.
    ("warn", "warning", "logging docs, Logger.warn deprecated"),
)


def alias_of(old: str, new: str) -> bool:
    """True when `old` and `new` are two names of the same thing, one kept for compatibility."""
    return any(old == was and new == now for was, now, _ in ALIASES)


def where(old: str, new: str) -> str | None:
    """The record that makes `alias_of(old, new)` true, so a refusal can point at it."""
    for was, now, source in ALIASES:
        if old == was and new == now:
            return source
    return None
