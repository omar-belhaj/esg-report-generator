"""Composant Streamlit : badge ✅ vérifié / ⚠️ à corriger."""

import streamlit as st


def afficher_badge_verification(statut: str):
    if statut == "verifie":
        st.markdown(
            "<div style='text-align:right'><span style='background-color:#d4edda;"
            "color:#155724;padding:4px 10px;border-radius:12px;font-size:0.85em;"
            "font-weight:600;'>✅ Vérifié</span></div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            "<div style='text-align:right'><span style='background-color:#fff3cd;"
            "color:#856404;padding:4px 10px;border-radius:12px;font-size:0.85em;"
            "font-weight:600;'>⚠️ À corriger</span></div>",
            unsafe_allow_html=True,
        )
