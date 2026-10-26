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


def _show_result(result) -> None:
    if result.coherent:
        st.success("L'assessment è coerente.")
    else:
        st.error("L'assessment è incoerente.")

    st.write(result.message)

    if result.failed_names:
        st.write("Sottoassessment critico:", ", ".join(result.failed_names))

    if result.phi is not None:
        st.subheader("Quantità del teorema")
        rows = []
        indices = result.phi_indices or tuple(range(len(result.phi)))
        for local, value in enumerate(result.phi):
            index = indices[local] if local < len(indices) else local
            rows.append({"indice": index + 1, "M'_j": value})
        st.dataframe(rows, hide_index=True, use_container_width=True)
        i0 = tuple(index + 1 for index in (result.i0 or ()))
        st.caption(f"I₀' = {i0}")

    if result.constituents:
        st.subheader("Costituenti logici")
        rows = []
        for number, constituent in enumerate(result.constituents, start=1):
            rows.append(
                {
                    "costituente": f"C{number}",
                    "stati": " / ".join(constituent.statuses),
                    "q": tuple(float(value) for value in constituent.q),
                    "valutazione testimone": str(constituent.witnesses[0]),
                }
            )
        st.dataframe(rows, hide_index=True, use_container_width=True)


_initialise_state()

st.title("Verifica della coerenza di eventi condizionati")
st.caption(
    "Inserire le formule di E e H. Gli atomi primitivi vengono individuati "
    "automaticamente; le relazioni devono essere vere."
)

st.subheader("Eventi condizionati")
header = st.columns([1.3, 2.0, 2.0, 1.0])
for column, label in zip(header, ["Nome", "E", "H", "p"]):
    column.markdown(f"**{label}**")

for index in range(st.session_state.event_count):
    columns = st.columns([1.3, 2.0, 2.0, 1.0])
    columns[0].text_input("Nome", key=f"name_{index}", label_visibility="collapsed")
    columns[1].text_input("E", key=f"E_{index}", label_visibility="collapsed")
    columns[2].text_input("H", key=f"H_{index}", label_visibility="collapsed")
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
button_columns[0].button("Aggiungi evento", on_click=_add_event)
button_columns[1].button("Rimuovi evento", on_click=_remove_event)

st.subheader("Relazioni logiche")
st.text_area(
    "Una relazione per riga",
    key="relations",
    height=90,
    help="Sintassi: and, or, not, parentesi. Esempio: not (A and B)",
)

if st.button("Verifica coerenza", type="primary"):
    try:
        events = _read_events()
        relations = tuple(
            relation.strip()
            for relation in st.session_state.relations.splitlines()
            if relation.strip()
        )
        _show_result(check_coherence(events, relations))
    except Exception as error:  # Streamlit should show input errors in the page.
        st.error(f"Errore nei dati inseriti: {error}")
