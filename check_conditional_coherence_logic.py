#!/usr/bin/env python3
"""Coherence checking from conditional events and logical relations.

The input does not contain the atoms of Omega.  Instead, it contains Boolean
formulas for E_i and H_i and optional Boolean relations.  The program
enumerates the truth assignments of the primitive symbols, keeps only those
satisfying all relations, and groups them by the truth pattern of the
conditional events.  These groups are the logical constituents.

Boolean syntax:
    and, or, not, parentheses

Example:
    ConditionalFormula("E1|H1", "A", "H1", 0.4)
    relations=["not (A and B)", "H1 or H2"]

Dependencies:
    python -m pip install numpy scipy
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from itertools import combinations, product
from typing import Any, Mapping, Optional, Sequence

import numpy as np
from scipy.optimize import linprog


@dataclass(frozen=True)
class ConditionalFormula:
    name: str
    E: str
    H: str
    p: float


@dataclass
class LogicalConstituent:
    statuses: tuple[str, ...]
    witnesses: tuple[dict[str, bool], ...]
    q: np.ndarray
    is_c0: bool = False


@dataclass
class CoherenceStep:
    """One level of the recursive COER-P0' criterion."""

    indices: tuple[int, ...]
    names: tuple[str, ...]
    p_sub: np.ndarray
    constituents: list[LogicalConstituent]
    sigma_solvable: bool
    phi: Optional[np.ndarray] = None
    i0: tuple[int, ...] = ()
    message: str = ""


@dataclass
class CoherenceResult:
    coherent: bool
    failed_subfamily: Optional[tuple[int, ...]] = None
    failed_names: Optional[tuple[str, ...]] = None
    p_sub: Optional[np.ndarray] = None
    constituents: Optional[list[LogicalConstituent]] = None
    phi: Optional[np.ndarray] = None
    phi_indices: Optional[tuple[int, ...]] = None
    i0: Optional[tuple[int, ...]] = None
    steps: Optional[list[CoherenceStep]] = None
    message: str = ""


@dataclass
class ExtensionResult:
    """Coherent extension interval for one additional conditional event."""

    lower: float
    upper: float
    denominator_can_be_zero: bool = False
    message: str = ""
    steps: Optional[list["ExtensionStep"]] = None


@dataclass
class ExtensionStep:
    """One cycle of Steps 0--3 in the propagation algorithm."""

    cycle: int
    endpoint: float
    names: tuple[str, ...]
    constituents: list[LogicalConstituent]
    endpoint_solvable: Optional[bool] = None
    maxima: Optional[np.ndarray] = None
    reduced_names: tuple[str, ...] = ()
    action: str = ""
    bound: Optional[float] = None
    lambda_solution: Optional[np.ndarray] = None


def _parse(formula: str) -> ast.AST:
    # In the web form an empty formula denotes the sure event.
    formula = formula.strip() or "True"
    try:
        tree = ast.parse(formula, mode="eval").body
    except SyntaxError as exc:
        raise ValueError(f"Invalid Boolean formula {formula!r}: {exc}") from exc
    _validate(tree, formula)
    return tree


def _validate(node: ast.AST, formula: str) -> None:
    allowed = (
        ast.Expression,
        ast.Name,
        ast.Load,
        ast.Constant,
        ast.BoolOp,
        ast.And,
        ast.Or,
        ast.UnaryOp,
        ast.Not,
        ast.BinOp,
        ast.BitAnd,
        ast.BitOr,
        ast.Invert,
    )
    if not isinstance(node, allowed):
        raise ValueError(
            f"Unsupported syntax in Boolean formula {formula!r}: "
            f"{type(node).__name__}"
        )
    if isinstance(node, ast.Constant) and not isinstance(node.value, bool):
        raise ValueError(f"Only True/False constants are allowed: {formula!r}")
    for child in ast.iter_child_nodes(node):
        _validate(child, formula)


def _names(node: ast.AST) -> set[str]:
    return {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}


def _eval(node: ast.AST, env: Mapping[str, bool]) -> bool:
    if isinstance(node, ast.Name):
        return bool(env[node.id])
    if isinstance(node, ast.Constant):
        return bool(node.value)
    if isinstance(node, ast.BoolOp):
        values = [_eval(v, env) for v in node.values]
        if isinstance(node.op, ast.And):
            return all(values)
        return any(values)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.Not, ast.Invert)):
        return not _eval(node.operand, env)
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.BitAnd, ast.BitOr)):
        left, right = _eval(node.left, env), _eval(node.right, env)
        return (left and right) if isinstance(node.op, ast.BitAnd) else (left or right)
    raise TypeError(f"Unsupported AST node: {type(node).__name__}")


def _logical_constituents(
    events: Sequence[ConditionalFormula],
    relations: Sequence[str],
    indices: Sequence[int],
) -> list[LogicalConstituent]:
    """Build constituents and merge atom assignments with the same pattern.

    A constituent is determined by the vector of conditional-event statuses
    (true, false, or void).  Several primitive truth assignments can realize
    the same vector, so they must be represented by one constituent with
    multiple witnesses rather than by repeated constituents.
    """
    formulas = [(_parse(events[i].E), _parse(events[i].H)) for i in indices]
    relation_trees = [_parse(r) for r in relations]
    symbol_names: set[str] = set()
    for e_tree, h_tree in formulas:
        symbol_names |= _names(e_tree) | _names(h_tree)
    for relation_tree in relation_trees:
        symbol_names |= _names(relation_tree)

    symbols = sorted(symbol_names)
    groups: dict[tuple[str, ...], list[dict[str, bool]]] = {}
    for values in product((False, True), repeat=len(symbols)):
        env = dict(zip(symbols, values))
        if not all(_eval(tree, env) for tree in relation_trees):
            continue

        statuses: list[str] = []
        q: list[float] = []
        for local, (e_tree, h_tree) in enumerate(formulas):
            h_true = _eval(h_tree, env)
            e_true = _eval(e_tree, env)
            i = indices[local]
            if not h_true:
                statuses.append("void")
                q.append(float(events[i].p))
            elif e_true:
                statuses.append("true")
                q.append(1.0)
            else:
                statuses.append("false")
                q.append(0.0)

        key = tuple(statuses)
        groups.setdefault(key, []).append(env)

    constituents: list[LogicalConstituent] = []
    for statuses, witnesses in groups.items():
        q = []
        for local, status in enumerate(statuses):
            i = indices[local]
            q.append(
                1.0 if status == "true" else
                0.0 if status == "false" else
                float(events[i].p)
            )
        constituents.append(
            LogicalConstituent(
                statuses=statuses,
                witnesses=tuple(witnesses),
                q=np.asarray(q, dtype=float),
                is_c0=all(status == "void" for status in statuses),
            )
        )
    return constituents


def _sigma_constituents(
    constituents: Sequence[LogicalConstituent],
) -> list[LogicalConstituent]:
    """Return the constituents allowed in Sigma, excluding the all-void C0."""
    return [constituent for constituent in constituents if not constituent.is_c0]


def _in_convex_hull(
    p_sub: np.ndarray,
    constituents: Sequence[LogicalConstituent],
    tolerance: float,
) -> bool:
    constituents = _sigma_constituents(constituents)
    if not constituents:
        return False
    Q = np.vstack([c.q for c in constituents])
    A_eq = np.vstack([Q.T, np.ones((1, len(constituents)))])
    b_eq = np.concatenate([p_sub, np.ones(1)])
    result = linprog(
        c=np.zeros(len(constituents)),
        A_eq=A_eq,
        b_eq=b_eq,
        bounds=[(0.0, None)] * len(constituents),
        method="highs",
    )
    if not result.success or result.x is None:
        return False
    return bool(np.max(np.abs(A_eq @ result.x - b_eq)) <= tolerance)


def _solve_sigma(
    p_sub: np.ndarray,
    constituents: Sequence[LogicalConstituent],
    tolerance: float,
):
    """Solve Sigma and return one feasible lambda, or None.

    Sigma is

        Q.T lambda = p,
        sum(lambda) = 1,
        lambda >= 0.

    Here Q contains the constituent points q_k.  The solution set is the
    set called S in the theorem.
    """
    constituents = _sigma_constituents(constituents)
    if not constituents:
        return None
    Q = np.vstack([c.q for c in constituents])
    A_eq = np.vstack([Q.T, np.ones((1, len(constituents)))])
    b_eq = np.concatenate([p_sub, np.ones(1)])
    result = linprog(
        c=np.zeros(len(constituents)),
        A_eq=A_eq,
        b_eq=b_eq,
        bounds=[(0.0, None)] * len(constituents),
        method="highs",
    )
    if not result.success or result.x is None:
        return None
    if np.max(np.abs(A_eq @ result.x - b_eq)) > tolerance:
        return None
    return result.x


def coherent_extension_interval(
    events: Sequence[ConditionalFormula],
    target: ConditionalFormula,
    relations: Sequence[str] = (),
    tolerance: float = 1e-9,
) -> ExtensionResult:
    """Compute the coherent extension interval using Algorithm 1.

    This is the Step 0--3 propagation algorithm stated in the Annals paper:
    test the endpoint (``z=0`` or ``z=1``), optimize when that endpoint is
    impossible, and recursively reduce to the indices whose conditioning
    events have zero maximum mass.
    """
    _validate_events(events)
    _validate_events([target])
    original_events = list(events)
    extension_steps: list[ExtensionStep] = []
    cycle_counter = 0

    def _cycle(selected_indices: tuple[int, ...], endpoint: float):
        nonlocal cycle_counter
        cycle_counter += 1
        selected_events = [original_events[i] for i in selected_indices]
        cycle_events = selected_events + [target]
        local_indices = tuple(range(len(cycle_events)))
        all_constituents = _logical_constituents(
            cycle_events, relations, local_indices
        )
        constituents = _sigma_constituents(all_constituents)
        if not constituents:
            raise ValueError("The extension system has no admissible constituent.")

        trace = ExtensionStep(
            cycle=cycle_counter,
            endpoint=endpoint,
            names=tuple(event.name for event in cycle_events),
            constituents=all_constituents,
        )
        extension_steps.append(trace)

        m = len(constituents)
        previous_count = len(selected_events)
        previous_p = np.asarray(
            [event.p for event in selected_events], dtype=float
        )
        previous_rows = []
        for local in range(previous_count):
            h = np.asarray(
                [status != "void" for status in (c.statuses[local] for c in constituents)],
                dtype=float,
            )
            eh = np.asarray(
                [status == "true" for status in (c.statuses[local] for c in constituents)],
                dtype=float,
            )
            previous_rows.append(eh - previous_p[local] * h)

        target_h = np.asarray(
            [c.statuses[-1] != "void" for c in constituents], dtype=float
        )
        target_eh = np.asarray(
            [c.statuses[-1] == "true" for c in constituents], dtype=float
        )
        previous_matrix = (
            np.vstack(previous_rows)
            if previous_rows
            else np.empty((0, m), dtype=float)
        )

        # Step 1: test the endpoint in system (6), including normalization.
        endpoint_matrix = np.vstack(
            [
                previous_matrix,
                target_eh - endpoint * target_h,
                np.ones((1, m)),
            ]
        )
        endpoint_rhs = np.concatenate(
            [np.zeros(previous_count + 1), np.ones(1)]
        )
        endpoint_solution = linprog(
            c=np.zeros(m),
            A_eq=endpoint_matrix,
            b_eq=endpoint_rhs,
            bounds=[(0.0, None)] * m,
            method="highs",
        )
        trace.endpoint_solvable = bool(endpoint_solution.success)
        if not endpoint_solution.success:
            # Step 2: normalize on the new conditioning event and optimize
            # the mass of E_{n+1} H_{n+1}.
            optimization_matrix = np.vstack([previous_matrix, target_h])
            optimization_rhs = np.concatenate(
                [np.zeros(previous_count), np.ones(1)]
            )
            objective = target_eh if endpoint == 0.0 else -target_eh
            optimized = linprog(
                c=objective,
                A_eq=optimization_matrix,
                b_eq=optimization_rhs,
                bounds=[(0.0, None)] * m,
                method="highs",
            )
            if not optimized.success:
                raise ValueError(
                    "The linear program for the coherent extension "
                    "could not be solved."
                )
            value = float(optimized.fun if endpoint == 0.0 else -optimized.fun)
            trace.lambda_solution = np.asarray(optimized.x, dtype=float)
            trace.bound = value
            trace.action = (
                "Step 2: endpoint is infeasible; optimize the target numerator "
                "with target-conditioning mass normalized to one."
            )
            return value, "Step 2"

        # Step 3: maximize each conditioning-event mass over the endpoint
        # solution set and identify I0.
        maxima = []
        for local in range(previous_count + 1):
            conditioning = np.asarray(
                [status != "void" for status in (c.statuses[local] for c in constituents)],
                dtype=float,
            )
            maximum = linprog(
                c=-conditioning,
                A_eq=endpoint_matrix,
                b_eq=endpoint_rhs,
                bounds=[(0.0, None)] * m,
                method="highs",
            )
            if not maximum.success:
                raise ValueError("Unable to compute the Step 3 maxima.")
            maxima.append(float(-maximum.fun))
        trace.maxima = np.asarray(maxima, dtype=float)

        target_max = maxima[-1]
        if target_max > tolerance:
            trace.lambda_solution = np.asarray(endpoint_solution.x, dtype=float)
            trace.bound = endpoint
            trace.action = (
                "Step 3: target conditioning event has positive maximum mass; "
                "the endpoint is accepted."
            )
            return endpoint, "Step 3"

        zero_previous = tuple(
            selected_indices[local]
            for local, maximum in enumerate(maxima[:-1])
            if maximum <= tolerance
        )
        if not zero_previous:
            trace.lambda_solution = np.asarray(endpoint_solution.x, dtype=float)
            trace.bound = endpoint
            trace.action = (
                "Step 3: only the target conditioning event has zero maximum "
                "mass; the endpoint is accepted."
            )
            return endpoint, "Step 3"
        if zero_previous == selected_indices:
            raise ValueError("The extension algorithm did not reduce the subfamily.")
        trace.reduced_names = tuple(original_events[i].name for i in zero_previous)
        trace.action = (
            "Step 3: reduce to the subfamily whose conditioning events have "
            "zero maximum mass, then restart at Step 0."
        )
        return _cycle(zero_previous, endpoint)

    lower, lower_step = _cycle(tuple(range(len(original_events))), 0.0)
    upper, upper_step = _cycle(tuple(range(len(original_events))), 1.0)
    lower = float(np.clip(lower, 0.0, 1.0))
    upper = float(np.clip(upper, 0.0, 1.0))
    if lower > upper + tolerance:
        raise ValueError("The computed extension interval is inconsistent.")
    return ExtensionResult(
        lower=lower,
        upper=upper,
        denominator_can_be_zero=(lower == 0.0 and upper == 1.0),
        message=(
            "Algorithm 1 completed: lower bound via "
            f"{lower_step}, upper bound via {upper_step}."
        ),
        steps=extension_steps,
    )


def _theorem_step(
    events: Sequence[ConditionalFormula],
    relations: Sequence[str],
    indices: tuple[int, ...],
    tolerance: float,
    steps: list[CoherenceStep],
):
    """One recursive application of Theorem COER-P0'."""
    constituents = _logical_constituents(events, relations, indices)
    p_sub = np.asarray([events[i].p for i in indices], dtype=float)
    if _solve_sigma(p_sub, constituents, tolerance) is None:
        steps.append(
            CoherenceStep(
                indices=indices,
                names=tuple(events[i].name for i in indices),
                p_sub=p_sub,
                constituents=constituents,
                sigma_solvable=False,
                message="The system Sigma is not solvable.",
            )
        )
        return CoherenceResult(
            coherent=False,
            failed_subfamily=indices,
            failed_names=tuple(events[i].name for i in indices),
            p_sub=p_sub,
            constituents=constituents,
            steps=steps,
            message="The system Sigma is not solvable.",
        )

    # Phi_j(lambda) is the total lambda-mass of constituents on which H_j
    # is true.  To obtain M'_j=max_{lambda in S'} Phi_j(lambda), take
    # S'=S and solve one LP maximization for each j.
    sigma_constituents = _sigma_constituents(constituents)
    Q = np.vstack([c.q for c in sigma_constituents])
    H = np.asarray(
        [[status != "void" for status in c.statuses] for c in sigma_constituents],
        dtype=float,
    )
    A_eq = np.vstack([Q.T, np.ones((1, len(sigma_constituents)))])
    b_eq = np.concatenate([p_sub, np.ones(1)])
    maxima = []
    for local_j in range(len(indices)):
        result = linprog(
            c=-H[:, local_j],
            A_eq=A_eq,
            b_eq=b_eq,
            bounds=[(0.0, None)] * len(sigma_constituents),
            method="highs",
        )
        if not result.success:
            return CoherenceResult(
                coherent=False,
                failed_subfamily=indices,
                failed_names=tuple(events[i].name for i in indices),
                p_sub=p_sub,
                constituents=constituents,
                message="Unable to maximize Phi_j over the solution set of Sigma.",
            )
        maxima.append(float(-result.fun))

    phi = np.asarray(maxima)
    zero_local = tuple(
        local_j for local_j, value in enumerate(phi) if value <= tolerance
    )
    zero_global = tuple(indices[local_j] for local_j in zero_local)

    steps.append(
        CoherenceStep(
            indices=indices,
            names=tuple(events[i].name for i in indices),
            p_sub=p_sub,
            constituents=constituents,
            sigma_solvable=True,
            phi=phi,
            i0=zero_global,
            message="System Sigma is solvable.",
        )
    )

    if not zero_local:
        return CoherenceResult(
            coherent=True,
            constituents=constituents,
            phi=phi,
            phi_indices=indices,
            i0=(),
            steps=steps,
            message="Sigma is solvable and I0' is empty; the assessment is coherent.",
        )

    if zero_global == indices:
        message = (
            "System Sigma is solvable only through solutions with zero mass "
            "on every conditioning event (M'_j=0 for all j). Therefore no "
            "admissible solution exists and the assessment is incoherent."
        )
        steps[-1].message = message
        return CoherenceResult(
            coherent=False,
            failed_subfamily=indices,
            failed_names=tuple(events[i].name for i in indices),
            p_sub=p_sub,
            constituents=constituents,
            phi=phi,
            phi_indices=indices,
            i0=zero_global,
            steps=steps,
            message=message,
        )

    # The theorem requires coherence of P0' on the indices I0'.
    reduced = _theorem_recursive(
        events, relations, tuple(zero_global), tolerance, steps
    )
    if reduced.coherent:
        return CoherenceResult(
            coherent=True,
            constituents=constituents,
            phi=phi,
            phi_indices=indices,
            i0=zero_global,
            steps=steps,
            message=(
                "Sigma is solvable and the recursively extracted assessment "
                "P0' is coherent."
            ),
        )
    return CoherenceResult(
        coherent=False,
        failed_subfamily=reduced.failed_subfamily,
        failed_names=reduced.failed_names,
        p_sub=reduced.p_sub,
        constituents=reduced.constituents,
        phi=phi,
        phi_indices=indices,
        i0=zero_global,
        steps=steps,
        message=(
            "Sigma is solvable, but the assessment P0' indexed by I0' "
            "is incoherent."
        ),
    )


def _theorem_recursive(
    events: Sequence[ConditionalFormula],
    relations: Sequence[str],
    indices: tuple[int, ...],
    tolerance: float,
    steps: list[CoherenceStep],
) -> CoherenceResult:
    if not indices:
        return CoherenceResult(coherent=True, message="Empty terminal subassessment.")
    return _theorem_step(events, relations, indices, tolerance, steps)


def check_coherence_by_theorem(
    events: Sequence[ConditionalFormula],
    relations: Sequence[str] = (),
    tolerance: float = 1e-9,
) -> CoherenceResult:
    """Check coherence using Theorem COER-P0'.

    At each recursion level the program:

    1. constructs the logical constituents;
    2. solves Sigma;
    3. computes M'_j=max_{lambda in S} Phi_j(lambda) by linear programming;
    4. forms I0'={j:M'_j=0};
    5. recursively checks P0'.
    """
    _validate_events(events)
    steps: list[CoherenceStep] = []
    return _theorem_recursive(
        events, relations, tuple(range(len(events))), tolerance, steps
    )


def _validate_events(events: Sequence[ConditionalFormula]) -> None:
    if not events:
        raise ValueError("At least one conditional event is required.")
    for event in events:
        if not (0.0 <= event.p <= 1.0):
            raise ValueError(f"p must lie in [0,1]: {event.name}")


def check_coherence(
    events: Sequence[ConditionalFormula],
    relations: Sequence[str] = (),
    tolerance: float = 1e-9,
) -> CoherenceResult:
    """Check coherence using Theorem COER-P0'.

    Relations are formulas that must be true.  A relation can use any
    primitive Boolean symbol occurring in E, H, or another relation.
    """

    return check_coherence_by_theorem(events, relations, tolerance)


def check_coherence_by_all_subfamilies(
    events: Sequence[ConditionalFormula],
    relations: Sequence[str] = (),
    tolerance: float = 1e-9,
) -> CoherenceResult:
    """Reference implementation checking every non-empty subfamily."""

    _validate_events(events)

    n = len(events)
    for size in range(1, n + 1):
        for indices in combinations(range(n), size):
            constituents = _logical_constituents(events, relations, indices)
            p_sub = np.asarray([events[i].p for i in indices], dtype=float)
            if not _in_convex_hull(p_sub, constituents, tolerance):
                return CoherenceResult(
                    coherent=False,
                    failed_subfamily=tuple(indices),
                    failed_names=tuple(events[i].name for i in indices),
                    p_sub=p_sub,
                    constituents=constituents,
                    message="The assessment is incoherent on this subfamily.",
                )

    return CoherenceResult(
        coherent=True,
        message="The assessment is coherent on every tested subfamily.",
    )


def print_result(result: CoherenceResult) -> None:
    print(result.message)
    if result.coherent:
        if result.phi is not None:
            print("M'_j values:", result.phi)
        if result.i0 is not None:
            print("I0':", result.i0)
        return
    if result.phi is not None:
        print("M'_j values:", result.phi)
    if result.i0 is not None:
        print("I0':", result.i0)
    print("Subfamily:", ", ".join(result.failed_names or ()))
    print("Assessment:", result.p_sub)
    print("Logical constituents:")
    for number, constituent in enumerate(result.constituents or [], start=1):
        print(f"  C{number}: statuses={constituent.statuses}, q={constituent.q}")
        print(f"      witness assignment: {constituent.witnesses[0]}")


if __name__ == "__main__":
    # Example: no atoms are supplied.  The relations define which truth
    # assignments are logically possible.
    events = [
        ConditionalFormula("E1|H1", "A", "H1", 0.40),
        ConditionalFormula("E2|H2", "B", "H2", 0.60),
    ]
    relations = [
        "not (A and B)",
        "H1 or H2",
    ]
    print_result(check_coherence(events, relations))
