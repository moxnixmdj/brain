#!/usr/bin/env python3
"""Which change to try first, counted from the same fixes that gave the changes.

Why this exists
---------------
Measured 2026-11-12 (canonical/verification/EXPERT_FIXES_DOSE_RESPONSE_20261112_V1.json): the
edit-kind learner (edit_kind_learning_v1), shown 2,864 real fixes once each, repairs 55 of 100
bugs it never saw within 200 candidates; shown 1,000 of them it repairs 56. More lessons reach
further and bury what they reach: the published fix is among the candidates of 46 bugs and among
the first 200 of 34, and the middle bug has 30,000 candidates.

The learner orders candidates by votes. Every lesson votes one over the number of candidates its
operator makes, and an operator that keeps the whole statement of its fix counts like one that
keeps nothing of it. How far each kind of operator can be trusted was never asked.

This module asks the lessons. Each lesson is taken in turn as a bug nobody has fixed: the
operators read off the OTHER lessons are tried on its first program, and it is counted whether
its second program is among the candidates an operator makes. The count is kept by the kind of
operator (what it does, how open it is, how much of what stood around the change it keeps), by
how many lessons gave the operator, and by how many candidates it makes in that program. While a
lesson is the bug, the lessons of its own group (the same task, say) are left out, so that a
near copy of its fix among the lessons does not make the operators look better than they are on
a program from elsewhere.

For a new program the counts give, for every operator that fits it, a chance that the fix is
among the operator's candidates. A candidate's share of that chance is the chance over the
number of candidates; the candidates are ordered by their shares. Nothing here accepts a
candidate: the caller's tests do. And nothing here is set by hand except how the counts are
grouped and smoothed (SUPPORT_EDGES, MADE_EDGES, SHRINK), which was fixed before any count was made.

It is the ranking step of Getafix (Bader et al., OOPSLA 2019), where a fix pattern is ranked by
how it fared on earlier fixes, with the fare counted leave-one-group-out.
"""
from __future__ import annotations

import ast
import warnings
from typing import Any, Callable, Iterator, Mapping, Sequence

from canonical.runtime import edit_kind_learning_v1 as kinds

SCHEMA = "BRAIN_EDIT_KIND_CHOICE_V1"

SUPPORT_EDGES = (1, 2, 3, 5, 10, 30)          # lessons that gave an operator: 1, 2, 3-4, 5-9, 10-29, 30 and more
MADE_EDGES = (1, 2, 3, 6, 11, 31, 101)        # candidates it makes in the program: 1, 2, 3-5, 6-10, 11-30, 31-100, more
SHRINK = 20.0                                 # a count is drawn towards the coarser count as if 20 cases stood behind that one
SUM, MOST = "sum", "most"                     # how the shares of several operators for one candidate are put together


def bucket(value: int, edges: Sequence[int]) -> int:
    """The index of the last edge that is not above `value` (0 when the value is below them all)."""
    at = 0
    for index, edge in enumerate(edges):
        if value >= edge:
            at = index
    return at


def kind_of(operator: kinds.Operator) -> str:
    """What an operator does, how open it is, how much of its surroundings it keeps."""
    return f"{operator.what}/{operator.openness}/{operator.surroundings}"


class Counts:
    """For operators that fitted a program: how often, and how often the fix was among their candidates."""

    def __init__(self) -> None:
        self.cells: dict[str, list[int]] = {}      # "kind|support bucket|made bucket" -> [fitted, held the fix]
        self.programs = 0
        self.programs_with_the_fix_among_the_candidates = 0

    def add(self, kind: str, support: int, made: int, held: bool) -> None:
        cell = self.cells.setdefault(f"{kind}|{bucket(support, SUPPORT_EDGES)}|{bucket(made, MADE_EDGES)}", [0, 0])
        cell[0] += 1
        cell[1] += 1 if held else 0

    def take(self, other: "Counts") -> None:
        for key, (fitted, held) in other.cells.items():
            cell = self.cells.setdefault(key, [0, 0])
            cell[0] += fitted
            cell[1] += held
        self.programs += other.programs
        self.programs_with_the_fix_among_the_candidates += other.programs_with_the_fix_among_the_candidates

    def as_dict(self) -> dict[str, Any]:
        return {"programs": self.programs, "programs_with_the_fix_among_the_candidates": self.programs_with_the_fix_among_the_candidates,
                "cells": {key: list(self.cells[key]) for key in sorted(self.cells)}}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Counts":
        counts = cls()
        counts.programs = int(data["programs"])
        counts.programs_with_the_fix_among_the_candidates = int(data["programs_with_the_fix_among_the_candidates"])
        for key, (fitted, held) in data["cells"].items():
            if len(key.split("|")) != 3 or held > fitted or held < 0:
                raise ValueError(f"not a count: {key!r} {fitted} {held}")
            counts.cells[key] = [int(fitted), int(held)]
        return counts


def fitting(lessons: kinds.Lessons, source: str, *, group_of: Callable[[str], Any] | None = None, without_group: Any = None,
            at_most: int = kinds.MAX_CANDIDATES_OF_ONE) -> Iterator[tuple[str, kinds.Operator, list[str], list[str]]]:
    """Every operator that makes candidates in this program: (its text, the operator, the lessons
    that gave it, its candidates). With `group_of`, lessons of the group `without_group` do not
    count, and an operator only they gave is passed over. Nothing when the program cannot be read."""
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            place = kinds.Place(source)
    except (SyntaxError, ValueError, RecursionError):
        return
    for text, operator in lessons.operators.items():
        givers = lessons.given_by[text]
        if group_of is not None:
            givers = [name for name in givers if group_of(name) != without_group]
        if not givers:
            continue
        made = kinds.candidates(operator, place, at_most)
        if made:
            yield text, operator, givers, made


def count_program(counts: Counts, lessons: kinds.Lessons, before: str, after: str, *, group_of: Callable[[str], Any] | None = None,
                  without_group: Any = None) -> dict[str, int] | None:
    """One lesson taken as a bug: every operator of the other lessons that fits `before`, and
    whether `after` is among its candidates. None, and nothing counted, when either cannot be read."""
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            fix = ast.unparse(ast.parse(after))
            ast.parse(before)
    except (SyntaxError, ValueError, RecursionError):
        return None
    fitted = held = 0
    for _, operator, givers, made in fitting(lessons, before, group_of=group_of, without_group=without_group):
        has_it = fix in made
        counts.add(kind_of(operator), len(givers), len(made), has_it)
        fitted += 1
        held += 1 if has_it else 0
    counts.programs += 1
    counts.programs_with_the_fix_among_the_candidates += 1 if held else 0
    return {"operators_that_fitted": fitted, "operators_that_held_the_fix": held}


class Table:
    """The chance that the fix is among the candidates of an operator that fits, read off the counts.
    The finest count is drawn towards the coarser ones: all operators; the kind; the kind and how
    many candidates; the kind, how many candidates and how many lessons."""

    def __init__(self, counts: Counts, shrink: float = SHRINK) -> None:
        self.shrink = float(shrink)
        self.levels: list[dict[tuple, list[int]]] = [{}, {}, {}, {}]
        for key, (fitted, held) in counts.cells.items():
            kind, support, made = key.split("|")
            for level, at in enumerate(((), (kind,), (kind, int(made)), (kind, int(made), int(support)))):
                cell = self.levels[level].setdefault(at, [0, 0])
                cell[0] += fitted
                cell[1] += held
        fitted, held = self.levels[0].get((), [0, 0])
        self.overall = held / fitted if fitted else 0.0

    def chance(self, kind: str, support: int, made: int) -> float:
        support, made = bucket(support, SUPPORT_EDGES), bucket(made, MADE_EDGES)
        chance = self.overall
        for level, at in ((1, (kind,)), (2, (kind, made)), (3, (kind, made, support))):
            fitted, held = self.levels[level].get(at, (0, 0))
            chance = (held + self.shrink * chance) / (fitted + self.shrink)
        return chance


def shares(lessons: kinds.Lessons, source: str, table: Table | None = None, *,
           at_most: int = kinds.MAX_CANDIDATES_OF_ONE) -> dict[str, tuple[float, float, float]]:
    """For every candidate program: (the learner's own sum of votes, its share with the lessons added up, the
    largest share a single operator gives it).

    An operator's chance, over the candidates it makes, is each candidate's share through that
    operator. For the sum, the chance is first divided among the lessons that gave the operator,
    every lesson counts once for a candidate, with the largest share it has for it, and the lessons
    are added up: the learner's own voting, with the counted chance where it has a one. Without a
    table both shares are 0."""
    rows: dict[str, dict[str, list[float]]] = {}
    most: dict[str, float] = {}
    for _, operator, givers, made in fitting(lessons, source, at_most=at_most):
        vote = 1.0 / len(made)
        share = table.chance(kind_of(operator), len(givers), len(made)) / len(made) if table is not None else 0.0
        each = share / len(givers)
        for candidate in made:
            if share > most.get(candidate, -1.0):
                most[candidate] = share
            row = rows.setdefault(candidate, {})
            for lesson in givers:
                held = row.get(lesson)
                if held is None:
                    row[lesson] = [vote, each]
                else:
                    if held[0] < vote:
                        held[0] = vote
                    if held[1] < each:
                        held[1] = each
    return {candidate: (sum(pair[0] for pair in row.values()), sum(pair[1] for pair in row.values()), most[candidate])
            for candidate, row in rows.items()}


def ordered(found: Mapping[str, tuple[float, float, float]], how: str | None) -> list[tuple[str, float, dict[str, float]]]:
    """The candidates, the likeliest first: (text, share, {"votes": the learner's sum of votes}).
    `how` is SUM or MOST; None gives the learner's own order. Equal shares: the learner's votes
    decide, then the shorter text, then the text."""
    if how not in (None, SUM, MOST):
        raise ValueError(f"how must be {SUM!r}, {MOST!r} or None")
    at = {None: 0, SUM: 1, MOST: 2}[how]
    out = [(candidate, numbers[at], {"votes": numbers[0]}) for candidate, numbers in found.items()]
    out.sort(key=lambda item: (-item[1], -item[2]["votes"], len(item[0]), item[0]))
    return out


def ranking(lessons: kinds.Lessons, source: str, table: Table | None = None, *, how: str = SUM,
            at_most: int = kinds.MAX_CANDIDATES_OF_ONE) -> list[tuple[str, float, dict[str, float]]]:
    """Candidate programs for this one, the likeliest first. Without a table the order is the learner's own."""
    if how not in (SUM, MOST):
        raise ValueError(f"how must be {SUM!r} or {MOST!r}")
    return ordered(shares(lessons, source, table, at_most=at_most), how if table is not None else None)
