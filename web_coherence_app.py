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

def _event(name: str, E: str, H: str, p: float) -> dict:
    return {"name": name, "E": E, "H": H, "p": p}


# Exact coherent instantiations of the rules discussed in the papers.
# Strict conclusions such as "Some S is P" use a positive illustrative value.
EXAMPLES = {
    "Custom input": {
        "description": "Enter your own conditional events and relations.",
        "events": DEFAULT_EVENTS,
        "relations": DEFAULT_RELATIONS,
    },
    "Weak contraposition (with background H)": {
        "description": "P(B|A and H)=1, P(not B|H)=0.8, therefore P(not A|not B and H)=1.",
        "events": [
            _event("B|A and H", "B", "A and H", 1.0),
            _event("not B|H", "not B", "H", 0.8),
            _event("not A|not B and H", "not A", "not B and H", 1.0),
        ],
        "relations": "",
    },
    "Weak contraposition (without background H)": {
        "description": "P(B|A)=1, P(not B)=0.8, therefore P(not A|not B)=1.",
        "events": [
            _event("B|A", "B", "A", 1.0),
            _event("not B", "not B", "True", 0.8),
            _event("not A|not B", "not A", "not B", 1.0),
        ],
        "relations": "",
    },
    "Weak transitivity (Barbara)": {
        "description": "P(P|M)=1, P(M|S)=1, P(S|S or M)=0.5, therefore P(P|S)=1.",
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
        "events": [_event("P|M", "P", "M", 1.0), _event("M|S", "M", "S", 1.0), _event("S|(S or M)", "S", "S or M", 0.5), _event("P|S", "P", "S", 1.0)],
        "relations": "",
    },
    "Figure I — Barbari (AAI)": {
        "description": "Every M is P; every S is M; some S is P.",
        "events": [_event("P|M", "P", "M", 1.0), _event("M|S", "M", "S", 1.0), _event("S|(S or M)", "S", "S or M", 0.5), _event("P|S", "P", "S", 1.0)],
        "relations": "",
    },
    "Figure I — Darii (AII)": {
        "description": "Every M is P; some S is M; some S is P.",
        "events": [_event("P|M", "P", "M", 1.0), _event("M|S", "M", "S", 0.6), _event("S|(S or M)", "S", "S or M", 0.5), _event("P|S", "P", "S", 0.8)],
        "relations": "",
    },
    "Figure I — Celarent (EAE)": {
        "description": "No M is P; every S is M; therefore no S is P.",
        "events": [_event("P|M", "P", "M", 0.0), _event("M|S", "M", "S", 1.0), _event("S|(S or M)", "S", "S or M", 0.5), _event("P|S", "P", "S", 0.0)],
        "relations": "",
    },
    "Figure I — Celaront (EAO)": {
        "description": "No M is P; every S is M; some S is not P.",
        "events": [_event("P|M", "P", "M", 0.0), _event("M|S", "M", "S", 1.0), _event("S|(S or M)", "S", "S or M", 0.5), _event("not P|S", "not P", "S", 1.0)],
        "relations": "",
    },
    "Figure I — Ferio (EIO)": {
        "description": "No M is P; some S is M; some S is not P.",
        "events": [_event("P|M", "P", "M", 0.0), _event("M|S", "M", "S", 0.6), _event("S|(S or M)", "S", "S or M", 0.5), _event("not P|S", "not P", "S", 0.7)],
        "relations": "",
    },
    "Figure II — Camestres (AEE)": {
        "description": "Every P is M; no S is M; therefore no S is P.",
        "events": [_event("M|P", "M", "P", 1.0), _event("M|S", "M", "S", 0.0), _event("S|(S or P)", "S", "S or P", 0.5), _event("P|S", "P", "S", 0.0)],
        "relations": "",
    },
    "Figure II — Camestrop (AEO)": {
        "description": "Every P is M; no S is M; some S is not P.",
        "events": [_event("M|P", "M", "P", 1.0), _event("M|S", "M", "S", 0.0), _event("S|(S or P)", "S", "S or P", 0.5), _event("not P|S", "not P", "S", 1.0)],
        "relations": "",
    },
    "Figure II — Baroco (AOO)": {
        "description": "Every P is M; some S is not M; some S is not P.",
        "events": [_event("M|P", "M", "P", 1.0), _event("not M|S", "not M", "S", 0.6), _event("S|(S or P)", "S", "S or P", 0.5), _event("not P|S", "not P", "S", 0.6)],
        "relations": "",
    },
    "Figure II — Cesare (EAE)": {
        "description": "No P is M; every S is M; therefore no S is P.",
        "events": [_event("M|P", "M", "P", 0.0), _event("M|S", "M", "S", 1.0), _event("S|(S or P)", "S", "S or P", 0.5), _event("P|S", "P", "S", 0.0)],
        "relations": "",
    },
    "Figure II — Cesaro (EAO)": {
        "description": "No P is M; every S is M; some S is not P.",
        "events": [_event("M|P", "M", "P", 0.0), _event("M|S", "M", "S", 1.0), _event("S|(S or P)", "S", "S or P", 0.5), _event("not P|S", "not P", "S", 1.0)],
        "relations": "",
    },
    "Figure II — Festino (EIO)": {
        "description": "No P is M; some S is M; some S is not P.",
        "events": [_event("M|P", "M", "P", 0.0), _event("not M|S", "not M", "S", 0.6), _event("S|(S or P)", "S", "S or P", 0.5), _event("not P|S", "not P", "S", 0.6)],
        "relations": "",
    },
    "Figure III — Darapti (AAI)": {
        "description": "Every M is P; every M is S; some S is P.",
        "events": [_event("P|M", "P", "M", 1.0), _event("S|M", "S", "M", 1.0), _event("M|(S or M)", "M", "S or M", 0.5), _event("P|S", "P", "S", 0.5)],
        "relations": "",
    },
    "Figure III — Datisi (AII)": {
        "description": "Every M is P; some M is S; some S is P.",
        "events": [_event("P|M", "P", "M", 1.0), _event("S|M", "S", "M", 0.6), _event("M|(S or M)", "M", "S or M", 0.5), _event("P|S", "P", "S", 0.5)],
        "relations": "",
    },
    "Figure III — Disamis (IAI)": {
        "description": "Some M is P; every M is S; some S is P.",
        "events": [_event("P|M", "P", "M", 0.6), _event("S|M", "S", "M", 1.0), _event("M|(S or M)", "M", "S or M", 0.5), _event("P|S", "P", "S", 0.6)],
        "relations": "",
    },
    "Figure III — Felapton (EAO)": {
        "description": "No M is P; every M is S; some S is not P.",
        "events": [_event("P|M", "P", "M", 0.0), _event("S|M", "S", "M", 1.0), _event("M|(S or M)", "M", "S or M", 0.5), _event("not P|S", "not P", "S", 0.5)],
        "relations": "",
    },
    "Figure III — Ferison (EIO)": {
        "description": "No M is P; some M is S; some S is not P.",
        "events": [_event("P|M", "P", "M", 0.0), _event("not S|M", "not S", "M", 0.6), _event("M|(S or M)", "M", "S or M", 0.5), _event("not P|S", "not P", "S", 0.6)],
        "relations": "",
    },
    "Figure III — Bocardo (OAO)": {
        "description": "Some M is not P; every M is S; some S is not P.",
        "events": [_event("not P|M", "not P", "M", 0.6), _event("S|M", "S", "M", 1.0), _event("M|(S or M)", "M", "S or M", 0.5), _event("not P|S", "not P", "S", 0.6)],
        "relations": "",
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
    st.session_state.setdefault("extension_name", "E_new|H_new")
    st.session_state.setdefault("extension_E", "")
    st.session_state.setdefault("extension_H", "")


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

st.subheader("Load an example")
st.selectbox(
    "Example",
    tuple(EXAMPLES),
    key="example_choice",
)
st.caption(EXAMPLES[st.session_state.example_choice]["description"])
st.button("Load selected example", on_click=_load_selected_example)


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


st.subheader("Compute a coherent extension")
st.caption(
    "Enter one additional conditional event E|H. The app computes the closed "
    "interval [z', z''] of all values that preserve coherence."
)

extension_columns = st.columns([1.3, 2.0, 2.0])
extension_columns[0].text_input("Name", key="extension_name")
extension_columns[1].text_input(
    "E",
    key="extension_E",
    help="Use True for a sure event and False for an impossible event.",
)
extension_columns[2].text_input(
    "H",
    key="extension_H",
    help="Use True for a sure conditioning event and False for an impossible one.",
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
        target = ConditionalFormula(
            name=st.session_state.extension_name.strip() or "E_new|H_new",
            E=st.session_state.extension_E.strip(),
            H=st.session_state.extension_H.strip(),
            p=0.0,
        )
        extension = coherent_extension_interval(events, target, relations)
        st.success(
            "Coherent extension interval: "
            f"[{extension.lower:.6f}, {extension.upper:.6f}]"
        )
        st.write(extension.message)
        if abs(extension.lower - extension.upper) <= 1e-9:
            st.info("The coherent extension is unique.")
        elif extension.lower == 0.0 and extension.upper == 1.0:
            st.info("The available assessment gives no informative bound.")
    except Exception as error:
        st.error(f"Extension error: {error}")
