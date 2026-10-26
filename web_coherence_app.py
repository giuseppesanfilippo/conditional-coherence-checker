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
)


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


def _read_events() -> list[ConditionalFormula]:
    result = []
    for index in range(st.session_state.event_count):
        result.append(
            ConditionalFormula(
                name=st.session_state[f"name_{index}"].strip(),
                E=st.session_state[f"E_{index}"].strip(),
                H=st.session_state[f"H_{index}"].strip(),
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


_initialise_state()

st.title("Coherence checking for conditional events")
st.caption(
    "Enter formulas for E and H. Primitive Boolean symbols are inferred "
    "automatically; all relations must hold."
)

st.subheader("Conditional events")
header = st.columns([1.3, 2.0, 2.0, 1.0])
for column, label in zip(header, ["Name", "E", "H", "p"]):
    column.markdown(f"**{label}**")

st.info(
    "Suggestions: use True for a sure event and False for an impossible "
    "event."
)

for index in range(st.session_state.event_count):
    columns = st.columns([1.3, 2.0, 2.0, 1.0])
    columns[0].text_input("Name", key=f"name_{index}", label_visibility="collapsed")
    columns[1].text_input(
        "E",
        key=f"E_{index}",
        help="Use True for a sure event and False for an impossible event.",
        label_visibility="collapsed",
    )
    columns[2].text_input(
        "H",
        key=f"H_{index}",
        help="Use True for a sure conditioning event and False for an impossible one.",
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

button_columns = st.columns([1, 1, 4])
button_columns[0].button("Add event", on_click=_add_event)
button_columns[1].button("Remove event", on_click=_remove_event)

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
