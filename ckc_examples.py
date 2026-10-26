"""Importer for the legacy .ckc example files.

The old checker stores Boolean formulas as Lisp-like S-expressions and
stores an interval for every conditional probability.  This module translates
the logical relations to the Python Boolean syntax accepted by the web app.
Imprecise source assessments are made precise by using their midpoint.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CKCExample:
    """One imported legacy example, ready for the Streamlit form."""

    title: str
    source_name: str
    events: list[dict[str, Any]]
    relations: str
    target: dict[str, Any]
    formula: str
    description: str


def _tokenize(text: str) -> list[str]:
    return re.findall(r"\(|\)|[^\s()]+", text)


def _read_one(tokens: list[str], position: int) -> tuple[Any, int]:
    if position >= len(tokens):
        raise ValueError("Unexpected end of CKC expression.")
    token = tokens[position]
    if token != "(":
        if token == ")":
            raise ValueError("Unexpected closing parenthesis in CKC expression.")
        return token, position + 1

    result: list[Any] = []
    position += 1
    while position < len(tokens) and tokens[position] != ")":
        item, position = _read_one(tokens, position)
        result.append(item)
    if position >= len(tokens):
        raise ValueError("Unclosed parenthesis in CKC expression.")
    return result, position + 1


def _read_many(text: str) -> list[Any]:
    tokens = _tokenize(text)
    expressions = []
    position = 0
    while position < len(tokens):
        expression, position = _read_one(tokens, position)
        expressions.append(expression)
    return expressions


def _sections(text: str) -> dict[str, str]:
    matches = list(re.finditer(r"^\[([^\]]+)\]\s*$", text, re.MULTILINE))
    sections: dict[str, str] = {}
    for number, match in enumerate(matches):
        end = matches[number + 1].start() if number + 1 < len(matches) else len(text)
        sections[match.group(1).strip().lower()] = text[match.end() : end]
    return sections


def _safe_name(raw: str) -> str:
    name = re.sub(r"[^A-Za-z0-9_]", "_", raw)
    if not name:
        name = "event"
    if name[0].isdigit():
        name = f"v_{name}"
    return name


class _FormulaConverter:
    def __init__(self, declared_symbols: list[str]):
        self._names: dict[str, str] = {}
        for symbol in declared_symbols:
            self._name(symbol)

    def _name(self, raw: str) -> str:
        key = raw.upper()
        if key == "NIL":
            return "True"
        if key not in self._names:
            self._names[key] = _safe_name(raw)
        return self._names[key]

    def formula(self, expression: Any) -> str:
        if isinstance(expression, str):
            return self._name(expression)
        if not expression:
            return "True"
        operator = str(expression[0]).upper()
        arguments = expression[1:]
        if operator == "NOT":
            return f"not ({self.formula(arguments[0])})"
        if operator in {"AND", "OR"}:
            connective = " and " if operator == "AND" else " or "
            return "(" + connective.join(self.formula(item) for item in arguments) + ")"
        return "(" + " and ".join(self.formula(item) for item in expression) + ")"

    def equivalence(self, left: Any, right: Any) -> str:
        left_formula = self.formula(left)
        right_formula = self.formula(right)
        return (
            f"(({left_formula}) and ({right_formula})) or "
            f"((not ({left_formula})) and (not ({right_formula})))"
        )

    def relation(self, expression: Any) -> str:
        if not isinstance(expression, list) or not expression:
            return self.formula(expression)
        operator = str(expression[0]).upper()
        arguments = expression[1:]
        if operator == "PARTITION":
            members = (
                arguments[0]
                if len(arguments) == 1 and isinstance(arguments[0], list)
                else arguments
            )
            formulas = [self.formula(item) for item in members]
            at_least_one = "(" + " or ".join(formulas) + ")"
            at_most_one = " and ".join(
                f"not ({formulas[i]} and {formulas[j]})"
                for i in range(len(formulas))
                for j in range(i + 1, len(formulas))
            )
            return f"({at_least_one} and {at_most_one})" if at_most_one else at_least_one
        if operator == "IDENTITY":
            return self.equivalence(arguments[0], arguments[1])
        if operator == "INC":
            return (
                f"(not ({self.formula(arguments[0])}) or "
                f"({self.formula(arguments[1])}))"
            )
        if operator == "IMP_CONG":
            return f"not ({self.formula(arguments[0])})"
        return self.formula(expression)


def _number(value: Any) -> float:
    return float(Fraction(str(value)))


def _parse_file(path: Path) -> CKCExample:
    sections = _sections(path.read_text(encoding="utf-8-sig"))
    declared_symbols = [
        expression
        for expression in _read_many(sections.get("events", ""))
        if isinstance(expression, str)
    ]
    converter = _FormulaConverter(declared_symbols)

    relations = [
        converter.relation(expression)
        for expression in _read_many(sections.get("relations", ""))
    ]

    probabilities = []
    for expression in _read_many(sections.get("cond. probabilities", "")):
        if not isinstance(expression, list) or len(expression) < 3:
            continue
        pair = expression[0]
        if not isinstance(pair, list) or len(pair) != 2:
            continue
        lower = _number(expression[1])
        upper = _number(expression[2])
        probabilities.append(
            {
                "E": converter.formula(pair[0]),
                "H": converter.formula(pair[1]),
                "lower": lower,
                "upper": upper,
            }
        )

    events = []
    for item in probabilities:
        midpoint = (item["lower"] + item["upper"]) / 2.0
        events.append(
            {
                "name": f"{item['E']}|{item['H']}",
                "E": item["E"],
                "H": item["H"],
                "p": midpoint,
            }
        )

    target = {"name": "", "E": "", "H": ""}
    new_event = _read_many(sections.get("new event", ""))
    if new_event and isinstance(new_event[0], list) and len(new_event[0]) == 2:
        target["E"] = converter.formula(new_event[0][0])
        target["H"] = converter.formula(new_event[0][1])
        target["name"] = f"{target['E']}|{target['H']}"

    bounds = _read_many(sections.get("lowerupper", ""))
    lower_upper = None
    if bounds and isinstance(bounds[0], list) and len(bounds[0]) >= 2:
        lower_upper = (_number(bounds[0][0]), _number(bounds[0][1]))

    interval_count = sum(
        abs(item["lower"] - item["upper"]) > 1e-12 for item in probabilities
    )
    if interval_count:
        assessment_note = (
            f" {interval_count} source assessment(s) were imprecise and have "
            "been made precise using their midpoints."
        )
    else:
        assessment_note = " All stored conditional assessments are precise."

    formula = ""
    if lower_upper is not None:
        formula = (
            rf"\left[z',z''\right]="
            rf"\left[{lower_upper[0]:.12g},\,{lower_upper[1]:.12g}\right]"
        )

    return CKCExample(
        title=f"CKC — {path.stem}",
        source_name=path.name,
        events=events,
        relations="\n".join(relations),
        target=target,
        formula=formula,
        description=f"Imported from {path.name}.{assessment_note}",
    )


def load_ckc_examples(directory: Path) -> dict[str, CKCExample]:
    """Load all CKC files in a directory, ignoring malformed files."""
    examples: dict[str, CKCExample] = {}
    if not directory.is_dir():
        return examples
    for path in sorted(directory.glob("*.ckc")):
        try:
            example = _parse_file(path)
        except (OSError, ValueError, IndexError, TypeError):
            continue
        examples[example.title] = example
    return examples
