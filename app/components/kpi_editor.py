"""
kpi_editor.py
==============
Onglet d'édition interactive des KPIs sources (data/raw/kpis_esg.csv).

Principe : le CSV reste la source de vérité canonique du projet (cohérent
avec l'usage réel — les KPIs ESG viennent de systèmes sources, pas de
saisie manuelle en production), mais l'utilisateur peut modifier des
valeurs directement dans le dashboard pour une démonstration interactive :
la modification est écrite dans le CSV, puis le pipeline de données et la
génération du rapport sont relancés automatiquement.

Seules les colonnes de VALEUR (`valeur`, `objectif_seuil`) sont éditables.
Les colonnes structurelles (kpi_id, pilier, esrs_datapoint, annee...) restent
en lecture seule : ce sont les clés de jointure avec le contexte qualitatif
et le référentiel de mapping ESRS (data/raw/contexte_qualitatif.csv et
mapping_esrs.csv) — les modifier romprait ces correspondances silencieusement.
Pour la même raison, l'ajout ou la suppression de lignes est désactivé
(num_rows="fixed") : une nouvelle ligne de KPI n'aurait ni contexte ni
mapping associé.
"""

import os
import subprocess
import sys

import pandas as pd
import streamlit as st

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
KPIS_RAW_PATH = os.path.join(PROJECT_ROOT, "data", "raw", "kpis_esg.csv")

COLONNES_EDITABLES = ["valeur", "objectif_seuil"]
COLONNES_STRUCTURELLES = [
    "kpi_id", "pilier", "esrs_datapoint", "nom_indicateur",
    "annee", "unite", "sens_amelioration", "perimetre",
]


def afficher_editeur_kpis(llm_mode: str, ollama_model: str = None):
    st.markdown("### ✏️ Éditer les KPIs sources")
    st.caption(
        "Modifiez une ou plusieurs valeurs ci-dessous, puis cliquez sur "
        "**Sauvegarder et régénérer le rapport**. Les colonnes grisées "
        "(identifiant, pilier, code ESRS, année...) sont en lecture seule : "
        "elles servent de clé de jointure avec le contexte qualitatif et le "
        "mapping ESRS, et les modifier casserait ces correspondances. "
        "L'ajout/la suppression de ligne est désactivé pour la même raison."
    )

    if not os.path.exists(KPIS_RAW_PATH):
        st.error(f"Fichier source introuvable : {KPIS_RAW_PATH}")
        return

    df = pd.read_csv(KPIS_RAW_PATH)

    df_edite = st.data_editor(
        df,
        use_container_width=True,
        hide_index=True,
        num_rows="fixed",
        disabled=COLONNES_STRUCTURELLES,
        key="editeur_kpis",
    )

    col_bouton, col_espace = st.columns([1, 3])
    with col_bouton:
        sauvegarder = st.button(
            "💾 Sauvegarder et régénérer le rapport",
            type="primary", use_container_width=True,
        )

    if not sauvegarder:
        return

    modifications = _detecter_modifications(df, df_edite)
    if not modifications:
        st.info("Aucune modification détectée par rapport au fichier source.")
        return

    with st.expander(f"📝 {len(modifications)} modification(s) détectée(s)", expanded=True):
        for m in modifications:
            st.markdown(
                f"- **{m['kpi_id']}** ({m['annee']}) — `{m['colonne']}` : "
                f"{m['ancienne']} → {m['nouvelle']}"
            )

    df_edite.to_csv(KPIS_RAW_PATH, index=False)

    with st.spinner("Réexécution du pipeline de données et régénération du rapport..."):
        resultat_pipeline = subprocess.run(
            [sys.executable, os.path.join(PROJECT_ROOT, "dataiku_flow", "run_pipeline.py")],
            capture_output=True, text=True,
        )
        if resultat_pipeline.returncode != 0:
            st.error("Échec du pipeline de données. Le fichier source a été modifié mais le "
                      "rapport n'a pas pu être régénéré.")
            st.code(resultat_pipeline.stderr or resultat_pipeline.stdout)
            return

        resultat_rapport = subprocess.run(
            [sys.executable, os.path.join(PROJECT_ROOT, "generate_report.py"),
             "--annee", "2025", "--llm-mode", llm_mode]
            + (["--ollama-model", ollama_model] if ollama_model else []),
            capture_output=True, text=True,
        )
        if resultat_rapport.returncode != 0:
            st.error("Échec de la génération du rapport après mise à jour des KPIs.")
            st.code(resultat_rapport.stderr or resultat_rapport.stdout)
            return

    st.success("KPIs mis à jour, pipeline relancé et rapport régénéré avec succès.")
    st.cache_data.clear()
    st.rerun()


def _detecter_modifications(df_original: pd.DataFrame, df_edite: pd.DataFrame) -> list:
    """Compare les deux DataFrames colonne par colonne (sur les colonnes
    éditables uniquement) et retourne la liste des cellules modifiées."""
    modifications = []
    for idx in df_original.index:
        for col in COLONNES_EDITABLES:
            ancienne = df_original.at[idx, col]
            nouvelle = df_edite.at[idx, col]
            valeurs_valides = pd.notna(ancienne) and pd.notna(nouvelle)
            if valeurs_valides and ancienne != nouvelle:
                modifications.append({
                    "kpi_id": df_original.at[idx, "kpi_id"],
                    "annee": df_original.at[idx, "annee"],
                    "colonne": col,
                    "ancienne": ancienne,
                    "nouvelle": nouvelle,
                })
    return modifications
