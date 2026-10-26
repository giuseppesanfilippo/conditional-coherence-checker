#!/usr/bin/env python3
"""Web interface for coherence checking of conditional assessments.

Run with:
    streamlit run web_coherence_app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

# Allow the app to be launched from any working directory.
OUTPUT_DIR = Path(__file__).resolve().parent
if str(OUTPUT_DIR) not in sys.path:
    sys.path.insert(0, str(OUTPUT_DIR))

from check_conditional_coherence_logic import (  # noqa: E402
    ConditionalFormula,
    check_coherence,
    coherent_extension_interval,
)
from ckc_examples import load_ckc_examples  # noqa: E402


st.set_page_config(
    page_title="Coherence checker",
    page_icon="∴",
    layout="wide",
)


DEFAULT_EVENTS = [
    {"name": "E1|H1", "E": "A", "H": "H1", "p": 0.40},
    {"name": "E2|H2", "E": "B", "H": "H2", "p": 0.60},
]
DEFAULT_RELATIONS = "not (A and B)\nH1 or H2"


def _load_available_ckc_examples() -> dict:
    directories = (
        OUTPUT_DIR / "examples",
        OUTPUT_DIR.parent / "examples",
    )
    examples = {}
    for directory in directories:
        examples.update(load_ckc_examples(directory))
    return examples


CKC_EXAMPLES = _load_available_ckc_examples()


def _event(name: str, E: str, H: str, p: float) -> dict:
    return {"name": name, "E": E, "H": H, "p": p}


def _event_label(E: str, H: str) -> str:
    """Build the read-only label used for a conditional event."""
    return f"{E.strip() or 'True'}|{H.strip() or 'True'}"


# Exact coherent instantiations of the rules discussed in the papers.
# Strict conclusions such as "Some S is P" are represented by a positive
# illustrative value (for example, 0.5).
EXAMPLES = {
    "Custom input": {
        "description": "Enter your own conditional events and relations.",
        "events": DEFAULT_EVENTS,
        "relations": DEFAULT_RELATIONS,
    },
    "Weak contraposition (with background H)": {
        "description": (
            "P(B|A and H)=1, P(not B|H)=0.8, therefore "
            "P(not A|not B and H)=1."
        ),
        "events": [
            _event("B|A and H", "B", "A and H", 1.0),
            _event("not B|H", "not B", "H", 0.8),
            _event("not A|not B and H", "not A", "not B and H", 1.0),
        ],
        "relations": "",
    },
    "Weak contraposition (without background H)": {
        "description": (
            "P(B|A)=1, P(not B)=0.8, therefore P(not A|not B)=1."
        ),
        "events": [
            _event("B|A", "B", "A", 1.0),
            _event("not B", "not B", "True", 0.8),
            _event("not A|not B", "not A", "not B", 1.0),
        ],
        "relations": "",
    },
    "Weak transitivity (Barbara)": {
        "description": (
            "P(P|M)=1, P(M|S)=1, P(S|S or M)=0.5, therefore P(P|S)=1."
        ),
        "events": [
            _event("P|M", "P", "M", 1.0),
            _event("M|S", "M", "S", 1.0),
            _event("S|(S or M)", "S", "S or M", 0.5),
            _event("P|S", "P", "S", 1.0),
        ],
        "relations": "",
    },
    "Figure I — Barbara (AAA)": {
        "description": "Every M is P; every S is M; therefore every S is P.",
        "events": [
            _event("P|M", "P", "M", 1.0),
            _event("M|S", "M", "S", 1.0),
            _event("S|(S or M)", "S", "S or M", 0.5),
            _event("P|S", "P", "S", 1.0),
        ],
        "relations": "",
    },
    "Figure I — Barbari (AAI)": {
        "description": "Every M is P; every S is M; some S is P.",
        "events": [
            _event("P|M", "P", "M", 1.0),
            _event("M|S", "M", "S", 1.0),
            _event("S|(S or M)", "S", "S or M", 0.5),
            _event("P|S", "P", "S", 1.0),
        ],
        "relations": "",
    },
    "Figure I — Darii (AII)": {
        "description": "Every M is P; some S is M; some S is P.",
        "events": [
            _event("P|M", "P", "M", 1.0),
            _event("M|S", "M", "S", 0.6),
            _event("S|(S or M)", "S", "S or M", 0.5),
            _event("P|S", "P", "S", 0.8),
        ],
        "relations": "",
    },
    "Figure I — Celarent (EAE)": {
        "description": "No M is P; every S is M; therefore no S is P.",
        "events": [
            _event("P|M", "P", "M", 0.0),
            _event("M|S", "M", "S", 1.0),
            _event("S|(S or M)", "S", "S or M", 0.5),
            _event("P|S", "P", "S", 0.0),
        ],
        "relations": "",
    },
    "Figure I — Celaront (EAO)": {
        "description": "No M is P; every S is M; some S is not P.",
        "events": [
            _event("P|M", "P", "M", 0.0),
            _event("M|S", "M", "S", 1.0),
            _event("S|(S or M)", "S", "S or M", 0.5),
            _event("not P|S", "not P", "S", 1.0),
        ],
        "relations": "",
    },
    "Figure I — Ferio (EIO)": {
        "description": "No M is P; some S is M; some S is not P.",
        "events": [
            _event("P|M", "P", "M", 0.0),
            _event("M|S", "M", "S", 0.6),
            _event("S|(S or M)", "S", "S or M", 0.5),
            _event("not P|S", "not P", "S", 0.7),
        ],
        "relations": "",
    },
    "Figure II — Camestres (AEE)": {
        "description": "Every P is M; no S is M; therefore no S is P.",
        "events": [
            _event("M|P", "M", "P", 1.0),
            _event("M|S", "M", "S", 0.0),
            _event("S|(S or P)", "S", "S or P", 0.5),
            _event("P|S", "P", "S", 0.0),
        ],
        "relations": "",
    },
    "Figure II — Camestrop (AEO)": {
        "description": "Every P is M; no S is M; some S is not P.",
        "events": [
            _event("M|P", "M", "P", 1.0),
            _event("M|S", "M", "S", 0.0),
            _event("S|(S or P)", "S", "S or P", 0.5),
            _event("not P|S", "not P", "S", 1.0),
        ],
        "relations": "",
    },
    "Figure II — Baroco (AOO)": {
        "description": "Every P is M; some S is not M; some S is not P.",
        "events": [
            _event("M|P", "M", "P", 1.0),
            _event("not M|S", "not M", "S", 0.6),
            _event("S|(S or P)", "S", "S or P", 0.5),
            _event("not P|S", "not P", "S", 0.6),
        ],
        "relations": "",
    },
    "Figure II — Cesare (EAE)": {
        "description": "No P is M; every S is M; therefore no S is P.",
        "events": [
            _event("M|P", "M", "P", 0.0),
            _event("M|S", "M", "S", 1.0),
            _event("S|(S or P)", "S", "S or P", 0.5),
            _event("P|S", "P", "S", 0.0),
        ],
        "relations": "",
    },
    "Figure II — Cesaro (EAO)": {
        "description": "No P is M; every S is M; some S is not P.",
        "events": [
            _event("M|P", "M", "P", 0.0),
            _event("M|S", "M", "S", 1.0),
            _event("S|(S or P)", "S", "S or P", 0.5),
            _event("not P|S", "not P", "S", 1.0),
        ],
        "relations": "",
    },
    "Figure II — Festino (EIO)": {
        "description": "No P is M; some S is M; some S is not P.",
        "events": [
            _event("M|P", "M", "P", 0.0),
            _event("not M|S", "not M", "S", 0.6),
            _event("S|(S or P)", "S", "S or P", 0.5),
            _event("not P|S", "not P", "S", 0.6),
        ],
        "relations": "",
    },
    "Figure III — Darapti (AAI)": {
        "description": "Every M is P; every M is S; some S is P.",
        "events": [
            _event("P|M", "P", "M", 1.0),
            _event("S|M", "S", "M", 1.0),
            _event("M|(S or M)", "M", "S or M", 0.5),
            _event("P|S", "P", "S", 0.5),
        ],
        "relations": "",
    },
    "Figure III — Datisi (AII)": {
        "description": "Every M is P; some M is S; some S is P.",
        "events": [
            _event("P|M", "P", "M", 1.0),
            _event("S|M", "S", "M", 0.6),
            _event("M|(S or M)", "M", "S or M", 0.5),
            _event("P|S", "P", "S", 0.5),
        ],
        "relations": "",
    },
    "Figure III — Disamis (IAI)": {
        "description": "Some M is P; every M is S; some S is P.",
        "events": [
            _event("P|M", "P", "M", 0.6),
            _event("S|M", "S", "M", 1.0),
            _event("M|(S or M)", "M", "S or M", 0.5),
            _event("P|S", "P", "S", 0.6),
        ],
        "relations": "",
    },
    "Figure III — Felapton (EAO)": {
        "description": "No M is P; every M is S; some S is not P.",
        "events": [
            _event("P|M", "P", "M", 0.0),
            _event("S|M", "S", "M", 1.0),
            _event("M|(S or M)", "M", "S or M", 0.5),
            _event("not P|S", "not P", "S", 0.5),
        ],
        "relations": "",
    },
    "Figure III — Ferison (EIO)": {
        "description": "No M is P; some M is S; some S is not P.",
        "events": [
            _event("P|M", "P", "M", 0.0),
            _event("not S|M", "not S", "M", 0.6),
            _event("M|(S or M)", "M", "S or M", 0.5),
            _event("not P|S", "not P", "S", 0.6),
        ],
        "relations": "",
    },
    "Figure III — Bocardo (OAO)": {
        "description": "Some M is not P; every M is S; some S is not P.",
        "events": [
            _event("not P|M", "not P", "M", 0.6),
            _event("S|M", "S", "M", 1.0),
            _event("M|(S or M)", "M", "S or M", 0.5),
            _event("not P|S", "not P", "S", 0.6),
        ],
        "relations": "",
    },
}


# Propagation examples from the Annals paper.  Here the conclusion is kept
# separate from the premises so that it can be passed to Algorithm 1 as the
# further conditional event.
EXTENSION_EXAMPLES = {
    "Custom extension": {
        "description": "Use the current assessment and enter a new target below.",
        "events": DEFAULT_EVENTS,
        "relations": DEFAULT_RELATIONS,
        "target": _event("E_new|H_new", "", "", 0.0),
        "formula": "",
    },
    "Annals — Figure I propagation": {
        "description": (
            "Premises (C|B, B|A, A|(A or B)); target C|A. "
            "Theorem PROPWTFIGI."
        ),
        "events": [
            _event("C|B", "C", "B", 0.60),
            _event("B|A", "B", "A", 0.70),
            _event("A|(A or B)", "A", "A or B", 0.80),
        ],
        "relations": "",
        "target": _event("C|A", "C", "A", 0.0),
        "formula": r"""
        z'=
        \begin{cases}
        0, & t=0,\\
        \max\left\{0,xy-\dfrac{(1-t)(1-x)}{t}\right\}, & t>0,
        \end{cases}
        \qquad
        z''=
        \begin{cases}
        1, & t=0,\\
        \min\left\{1,(1-x)(1-y)+\dfrac{x}{t}\right\}, & t>0.
        \end{cases}
        """,
    },
    "Annals — Figure II propagation": {
        "description": (
            "Premises (B|C, not B|A, A|(A or C)); target not C|A. "
            "Theorem PROPF2."
        ),
        "events": [
            _event("B|C", "B", "C", 0.90),
            _event("not B|A", "not B", "A", 0.80),
            _event("A|(A or C)", "A", "A or C", 0.80),
        ],
        "relations": "",
        "target": _event("not C|A", "not C", "A", 0.0),
        "formula": r"""
        [z',z'']=
        \begin{cases}
        [0,1], & t\leq x+yt\leq 1,\\
        \left[\dfrac{x+yt-1}{tx},1\right], & x+yt>1,\\
        \left[\dfrac{t-x-yt}{t(1-x)},1\right], & x+yt<t.
        \end{cases}
        """,
    },
    "Annals — Figure III propagation": {
        "description": (
            "Premises (C|B, A|B, B|(A or B)); target C|A. "
            "Theorem PROPF3."
        ),
        "events": [
            _event("C|B", "C", "B", 0.40),
            _event("A|B", "A", "B", 0.90),
            _event("B|(A or B)", "B", "A or B", 0.70),
        ],
        "relations": "",
        "target": _event("C|A", "C", "A", 0.0),
        "formula": r"""
        z'=
        \begin{cases}
        0, & t(x+y-1)\leq 0,\\
        \dfrac{t(x+y-1)}{1-t(1-y)}, & t(x+y-1)>0,
        \end{cases}
        \qquad
        z''=
        \begin{cases}
        1, & t(y-x)\leq 0,\\
        1-\dfrac{t(y-x)}{1-t(1-y)}, & t(y-x)>0.
        \end{cases}
        """,
    },
}


def _initialise_state() -> None:
    if "event_count" not in st.session_state:
        st.session_state.event_count = len(DEFAULT_EVENTS)
    for index, event in enumerate(DEFAULT_EVENTS):
        defaults = {
            f"name_{index}": event["name"],
            f"E_{index}": event["E"],
            f"H_{index}": event["H"],
            f"p_{index}": event["p"],
        }
        for key, value in defaults.items():
            st.session_state.setdefault(key, value)
    st.session_state.setdefault("relations", DEFAULT_RELATIONS)
    st.session_state.setdefault("example_choice", "Custom input")
    st.session_state.setdefault("extension_example_choice", "Custom extension")
    st.session_state.setdefault(
        "ckc_example_choice",
        next(iter(CKC_EXAMPLES), ""),
    )
    st.session_state.setdefault("extension_name", "E_new|H_new")
    st.session_state.setdefault("extension_E", "")
    st.session_state.setdefault("extension_H", "")
    st.session_state.setdefault("extension_formula", "")


def _add_event() -> None:
    index = st.session_state.event_count
    st.session_state.event_count += 1
    st.session_state[f"name_{index}"] = f"E{index + 1}|H{index + 1}"
    st.session_state[f"E_{index}"] = ""
    st.session_state[f"H_{index}"] = ""
    st.session_state[f"p_{index}"] = 0.5


def _remove_event() -> None:
    if st.session_state.event_count > 1:
        st.session_state.event_count -= 1


def _remove_event_at(index: int) -> None:
    """Remove one event and shift all following rows up."""
    count = st.session_state.event_count
    if count <= 1 or not 0 <= index < count:
        return
    fields = ("name", "E", "H", "p")
    for row in range(index, count - 1):
        for field in fields:
            st.session_state[f"{field}_{row}"] = st.session_state[
                f"{field}_{row + 1}"
            ]
    for field in fields:
        st.session_state.pop(f"{field}_{count - 1}", None)
    st.session_state.event_count = count - 1


def _move_event(index: int, direction: int) -> None:
    """Move one event one row up or down."""
    other = index + direction
    count = st.session_state.event_count
    if not 0 <= index < count or not 0 <= other < count:
        return
    for field in ("name", "E", "H", "p"):
        key = f"{field}_{index}"
        other_key = f"{field}_{other}"
        st.session_state[key], st.session_state[other_key] = (
            st.session_state[other_key],
            st.session_state[key],
        )


def _load_selected_example() -> None:
    example = EXAMPLES[st.session_state.example_choice]
    events = example["events"]
    st.session_state.event_count = len(events)
    for index, event in enumerate(events):
        st.session_state[f"name_{index}"] = event["name"]
        st.session_state[f"E_{index}"] = event["E"]
        st.session_state[f"H_{index}"] = event["H"]
        st.session_state[f"p_{index}"] = event["p"]
    st.session_state.relations = example["relations"]


def _load_extension_example() -> None:
    example = EXTENSION_EXAMPLES[st.session_state.extension_example_choice]
    events = example["events"]
    st.session_state.event_count = len(events)
    for index, event in enumerate(events):
        st.session_state[f"name_{index}"] = event["name"]
        st.session_state[f"E_{index}"] = event["E"]
        st.session_state[f"H_{index}"] = event["H"]
        st.session_state[f"p_{index}"] = event["p"]
    st.session_state.relations = example["relations"]
    target = example["target"]
    st.session_state.extension_name = target["name"]
    st.session_state.extension_E = target["E"]
    st.session_state.extension_H = target["H"]
    st.session_state.extension_formula = example["formula"]


def _load_ckc_example() -> None:
    example = CKC_EXAMPLES[st.session_state.ckc_example_choice]
    events = example.events
    st.session_state.event_count = len(events)
    for index, event in enumerate(events):
        st.session_state[f"name_{index}"] = event["name"]
        st.session_state[f"E_{index}"] = event["E"]
        st.session_state[f"H_{index}"] = event["H"]
        st.session_state[f"p_{index}"] = event["p"]
    st.session_state.relations = example.relations
    st.session_state.extension_E = example.target["E"]
    st.session_state.extension_H = example.target["H"]
    st.session_state.extension_formula = example.formula


def _read_events() -> list[ConditionalFormula]:
    result = []
    for index in range(st.session_state.event_count):
        event_E = st.session_state[f"E_{index}"].strip()
        event_H = st.session_state[f"H_{index}"].strip()
        result.append(
            ConditionalFormula(
                name=_event_label(event_E, event_H),
                E=event_E,
                H=event_H,
                p=float(st.session_state[f"p_{index}"]),
            )
        )
    return result


def _show_constituents(constituents) -> None:
    rows = []
    regular_number = 1
    for constituent in constituents:
        if constituent.is_c0:
            label = "C0"
            used_in_sigma = "No — all-void constituent"
        else:
            label = f"C{regular_number}"
            regular_number += 1
            used_in_sigma = "Yes"
        rows.append(
            {
                "constituent": label,
                "status pattern": " / ".join(constituent.statuses),
                "q": tuple(float(value) for value in constituent.q),
                "number of witnesses": len(constituent.witnesses),
                "witness assignment": str(constituent.witnesses[0]),
                "used in Σ": used_in_sigma,
            }
        )
    st.dataframe(rows, hide_index=True, use_container_width=True)


def _show_step(step, step_number: int) -> None:
    title = f"Step {step_number}: {', '.join(step.names)}"
    with st.expander(title, expanded=step_number == 1):
        st.write(f"Subassessment: {', '.join(step.names)}")
        if step.sigma_solvable:
            st.write("System Σ: solvable")
        else:
            st.error("System Σ: not solvable")
        if step.message:
            st.caption(step.message)

        if step.phi is not None:
            rows = []
            for local, value in enumerate(step.phi):
                rows.append(
                    {
                        "event": step.names[local],
                        "M'_j": float(value),
                    }
                )
            st.write("Theorem quantities")
            st.dataframe(rows, hide_index=True, use_container_width=True)
            st.caption(f"I₀' = {tuple(index + 1 for index in step.i0)}")

        st.write("Logical constituents")
        st.caption("C0 is the all-void constituent and is excluded from Σ.")
        st.caption(
            "Truth assignments with the same status pattern are grouped into "
            "one constituent; the table shows how many witnesses it has."
        )
        if step.constituents:
            _show_constituents(step.constituents)
        else:
            st.info("No logical constituents satisfy the supplied relations.")


def _show_result(result) -> None:
    if result.coherent:
        st.success("The assessment is coherent.")
    else:
        st.error("The assessment is incoherent.")

    st.write(result.message)

    if result.failed_names:
        st.write("Critical subassessment:", ", ".join(result.failed_names))

    if result.steps:
        st.subheader("Recursive coherence check")
        for step_number, step in enumerate(result.steps, start=1):
            _show_step(step, step_number)


def _show_extension_result(result, known_formula: str = "") -> None:
    st.success(
        "Coherent extension interval: "
        f"[{result.lower:.6f}, {result.upper:.6f}]"
    )
    st.write(result.message)
    if abs(result.lower - result.upper) <= 1e-9:
        st.info("The coherent extension is unique.")
    elif result.lower == 0.0 and result.upper == 1.0:
        st.info("The available assessment gives no informative bound.")

    if known_formula:
        st.subheader("Known analytical bounds for this example")
        st.caption("Here x, y and t denote the probabilities of the premises shown above.")
        st.latex(known_formula)

    st.subheader("Extension algorithm trace")
    st.caption(
        "Each expander is one cycle of Algorithm 1. C0 is displayed for reference "
        "but is excluded from the linear system."
    )
    for step in result.steps or []:
        endpoint_label = "lower endpoint z=0" if step.endpoint == 0.0 else "upper endpoint z=1"
        with st.expander(f"Cycle {step.cycle}: {endpoint_label}", expanded=False):
            st.write("Family in Step 0: " + ", ".join(step.names))
            st.write("Step 0: logical constituents")
            st.caption(
                "Equal status patterns have already been merged; the witness "
                "count records the underlying truth assignments."
            )
            _show_constituents(step.constituents)

            if step.endpoint_solvable:
                st.write("Step 1: endpoint system is solvable.")
            else:
                st.write("Step 1: endpoint system is not solvable.")

            if step.lambda_solution is not None:
                sigma_constituents = [
                    constituent
                    for constituent in step.constituents
                    if not constituent.is_c0
                ]
                lambda_rows = []
                for number, (constituent, value) in enumerate(
                    zip(sigma_constituents, step.lambda_solution), start=1
                ):
                    lambda_rows.append(
                        {
                            "constituent": f"C{number}",
                            "status pattern": " / ".join(constituent.statuses),
                            "lambda": float(value),
                        }
                    )
                bound_symbol = "z'" if step.endpoint == 0.0 else "z''"
                st.write(f"Lambda vector associated with {bound_symbol}")
                st.caption(
                    "The displayed coefficients are the lambdas for C1, ..., Cm; "
                    "C0 is excluded from Sigma."
                )
                st.dataframe(
                    lambda_rows, hide_index=True, use_container_width=True
                )

            if step.maxima is None:
                if step.endpoint == 0.0:
                    st.latex(
                        r"\Lambda'=(\lambda'_1,\ldots,\lambda'_m),\qquad "
                        r"z' = \min\sum_{\substack{r:\,C_r\subseteq E_{n+1}H_{n+1}}}\lambda'_r"
                    )
                else:
                    st.latex(
                        r"\Lambda''=(\lambda''_1,\ldots,\lambda''_m),\qquad "
                        r"z'' = \max\sum_{\substack{r:\,C_r\subseteq E_{n+1}H_{n+1}}}\lambda''_r"
                    )
                st.write(f"{step.action} Bound obtained: {step.bound:.6f}.")
            else:
                st.write("Step 3: maxima M_j over the endpoint solution set")
                rows = [
                    {"event": name, "M_j": float(value)}
                    for name, value in zip(step.names, step.maxima)
                ]
                st.dataframe(rows, hide_index=True, use_container_width=True)
                if step.reduced_names:
                    st.write(
                        step.action
                        + " Reduced subfamily: "
                        + ", ".join(step.reduced_names)
                        + "."
                    )
                else:
                    st.write(f"{step.action} Bound: {step.bound:.6f}.")


_initialise_state()

st.title("Coherence checking for conditional events")
st.caption(
    "Enter formulas for E and H. Primitive Boolean symbols are inferred "
    "automatically; all relations must hold."
)

st.subheader("Load an example")
st.selectbox(
    "Example",
    tuple(EXAMPLES),
    key="example_choice",
)
st.caption(EXAMPLES[st.session_state.example_choice]["description"])
st.button("Load selected example", on_click=_load_selected_example)

st.subheader("Load an extension example")
st.selectbox(
    "Extension example",
    tuple(EXTENSION_EXAMPLES),
    key="extension_example_choice",
)
st.caption(
    EXTENSION_EXAMPLES[st.session_state.extension_example_choice]["description"]
)
st.button("Load selected extension example", on_click=_load_extension_example)

if CKC_EXAMPLES:
    st.subheader("Load a legacy .ckc example")
    st.selectbox(
        "CKC example",
        tuple(CKC_EXAMPLES),
        key="ckc_example_choice",
    )
    st.caption(CKC_EXAMPLES[st.session_state.ckc_example_choice].description)
    st.button("Load selected .ckc example", on_click=_load_ckc_example)

st.subheader("Conditional events")
header = st.columns([1.3, 2.0, 2.0, 1.0, 0.55, 0.55, 0.8])
for column, label in zip(
    header, ["Event (E|H)", "E", "H", "p", "", "", ""]
):
    column.markdown(f"**{label}**")

st.info(
    "Suggestions: use True for a sure event and False for an impossible "
    "event. Empty E or H is also interpreted as True."
)

for index in range(st.session_state.event_count):
    columns = st.columns([1.3, 2.0, 2.0, 1.0, 0.55, 0.55, 0.8])
    columns[0].text(
        _event_label(
            st.session_state[f"E_{index}"],
            st.session_state[f"H_{index}"],
        )
    )
    columns[1].text_input(
        "E",
        key=f"E_{index}",
        help="Use True for a sure event and False for an impossible event. Empty means True.",
        label_visibility="collapsed",
    )
    columns[2].text_input(
        "H",
        key=f"H_{index}",
        help="Use True for a sure conditioning event and False for an impossible one. Empty means True.",
        label_visibility="collapsed",
    )
    columns[3].number_input(
        "p",
        min_value=0.0,
        max_value=1.0,
        step=0.01,
        format="%.6f",
        key=f"p_{index}",
        label_visibility="collapsed",
    )
    columns[4].button(
        "↑",
        key=f"move_up_{index}",
        help="Move this event up",
        disabled=index == 0,
        on_click=_move_event,
        args=(index, -1),
    )
    columns[5].button(
        "↓",
        key=f"move_down_{index}",
        help="Move this event down",
        disabled=index == st.session_state.event_count - 1,
        on_click=_move_event,
        args=(index, 1),
    )
    columns[6].button(
        "Remove",
        key=f"remove_event_{index}",
        help="Remove this event",
        disabled=st.session_state.event_count <= 1,
        on_click=_remove_event_at,
        args=(index,),
    )

button_columns = st.columns([1, 1, 4])
button_columns[0].button("Add event", on_click=_add_event)
button_columns[1].button("Remove last event", on_click=_remove_event)

st.subheader("Logical relations")
st.text_area(
    "One relation per line",
    key="relations",
    height=90,
    help="Syntax: and, or, not, and parentheses. Example: not (A and B)",
)

if st.button("Check coherence", type="primary"):
    try:
        events = _read_events()
        relations = tuple(
            relation.strip()
            for relation in st.session_state.relations.splitlines()
            if relation.strip()
        )
        _show_result(check_coherence(events, relations))
    except Exception as error:  # Streamlit should show input errors in the page.
        st.error(f"Input error: {error}")

st.subheader("Compute a coherent extension")
st.caption(
    "Enter one additional conditional event E|H. The app computes the closed "
    "interval [z', z''] of all values that preserve coherence."
)

extension_columns = st.columns([2.0, 2.0])
extension_columns[0].text_input(
    "E",
    key="extension_E",
    help="Use True for a sure event and False for an impossible event. Empty means True.",
)
extension_columns[1].text_input(
    "H",
    key="extension_H",
    help="Use True for a sure conditioning event and False for an impossible one. Empty means True.",
)
st.caption(
    "Target event (read-only): "
    + _event_label(st.session_state.extension_E, st.session_state.extension_H)
)

if st.button("Compute coherent extension"):
    try:
        events = _read_events()
        relations = tuple(
            relation.strip()
            for relation in st.session_state.relations.splitlines()
            if relation.strip()
        )
        base_result = check_coherence(events, relations)
        if not base_result.coherent:
            raise ValueError(
                "The current assessment is incoherent. Compute an extension "
                "only after the existing assessment is coherent."
            )
        target_E = st.session_state.extension_E.strip()
        target_H = st.session_state.extension_H.strip()
        target = ConditionalFormula(
            name=_event_label(target_E, target_H),
            E=target_E,
            H=target_H,
            p=0.0,
        )
        extension = coherent_extension_interval(events, target, relations)
        _show_extension_result(extension, st.session_state.extension_formula)
    except Exception as error:
        st.error(f"Extension error: {error}")
