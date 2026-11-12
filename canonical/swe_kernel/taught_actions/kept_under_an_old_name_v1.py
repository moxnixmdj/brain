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

#: (the object the old name is read from, the old name, the name it is an alias of).
#: The object is spelled as code reads it, `self` included, because `self.assertEquals` and
#: `self.assertRaisesRegexp` are how the deprecation actually appears; `None` means any object,
#: used only where the old name was never anything but the alias.
ALIASES: tuple[tuple[str | None, str, str], ...] = (
    # unittest: deprecated aliases, removed in 3.12, aliased back for 3.11 (bpo-45162).
    (None, "assertEquals", "assertEqual"),
    (None, "assertNotEquals", "assertNotEqual"),
    (None, "assertAlmostEquals", "assertAlmostEqual"),
    (None, "assertNotAlmostEquals", "assertNotAlmostEqual"),
    (None, "assertRegexpMatches", "assertRegex"),
    (None, "assertNotRegexpMatches", "assertNotRegex"),
    (None, "assertRaisesRegexp", "assertRaisesRegex"),
    (None, "failUnlessEqual", "assertEqual"),
    (None, "failIfEqual", "assertNotEqual"),
    (None, "failUnlessAlmostEqual", "assertAlmostEqual"),
    (None, "failIfAlmostEqual", "assertNotAlmostEqual"),
    (None, "failUnless", "assertTrue"),
    (None, "failIf", "assertFalse"),
    (None, "failUnlessRaises", "assertRaises"),
    (None, "assert_", "assertTrue"),
    # logging: `Logger.warn` was deprecated in favour of `Logger.warning`.
    (None, "warn", "warning"),
)


def alias_of(old: str, new: str) -> bool:
    """True when `old` and `new` are two names of the same thing, one kept for compatibility."""
    return any(old == was and new == now for _, was, now in ALIASES)


def known_rename(pattern_name: str, template_name: str) -> bool:
    """True when a rule that only renames `pattern_name` to `template_name` is a compatibility alias.

    Only a rename is ever considered: `alias_of` is asked about the pair, and the caller has already
    checked that nothing but the written name differs between the two patterns.
    """
    return alias_of(pattern_name, template_name)
