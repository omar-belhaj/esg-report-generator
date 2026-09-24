"""Composant Streamlit : affichage tabulaire et graphique des KPIs bruts."""

import pandas as pd
import streamlit as st

LABELS_PILIER = {
    "E1": "🌍 E1 — Changement climatique",
    "S1": "👥 S1 — Effectifs propres",
    "G1": "⚖️ G1 — Conduite des affaires",
}


def afficher_kpis_pilier(df_pilier: pd.DataFrame, pilier: str):
    st.subheader(LABELS_PILIER.get(pilier, pilier))

    colonnes_affichees = [
        "nom_indicateur", "valeur", "unite", "variation_pct",
        "objectif_seuil", "statut_vs_objectif", "esrs_datapoint",
    ]
    colonnes_affichees = [c for c in colonnes_affichees if c in df_pilier.columns]

    df_affiche = df_pilier[colonnes_affichees].rename(columns={
        "nom_indicateur": "Indicateur",
        "valeur": "Valeur 2025",
        "unite": "Unité",
        "variation_pct": "Variation YoY (%)",
        "objectif_seuil": "Objectif",
        "statut_vs_objectif": "Statut",
        "esrs_datapoint": "Datapoint ESRS",
    })

    def _style_statut(val):
        couleurs = {"atteint": "background-color: #d4edda", "au-dessus": "background-color: #f8d7da",
                    "en-deça": "background-color: #fff3cd"}
        return couleurs.get(val, "")

    if "Statut" in df_affiche.columns:
        styler = df_affiche.style
        # pandas >= 2.1 a renommé Styler.applymap en Styler.map ; on gère les deux
        # pour rester compatible quelle que soit la version installée par l'utilisateur.
        if hasattr(styler, "map"):
            styler = styler.map(_style_statut, subset=["Statut"])
        else:
            styler = styler.applymap(_style_statut, subset=["Statut"])
        a_afficher = styler
    else:
        a_afficher = df_affiche

    st.dataframe(a_afficher, use_container_width=True, hide_index=True)
