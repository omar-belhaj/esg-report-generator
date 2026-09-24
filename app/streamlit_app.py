"""
streamlit_app.py
==================
Dashboard principal du projet esg-report-generator.

Affiche, pour chaque section ESRS (E1/S1/G1) :
  - les KPIs bruts (tableau + statut vs objectif)
  - le texte narratif généré par le LLM
  - le badge de vérification anti-hallucination (✅ / ⚠️) et son détail

Permet de relancer la génération (avec choix du mode LLM) et d'exporter le
rapport final en PDF ou Word.

Lancer avec :
    streamlit run app/streamlit_app.py
"""

import json
import os
import subprocess
import sys

import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.dirname(__file__))
from components.kpi_view import afficher_kpis_pilier  # noqa: E402
from components.narrative_view import afficher_section_narrative  # noqa: E402
from components.kpi_editor import afficher_editeur_kpis  # noqa: E402

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_PROCESSED = os.path.join(PROJECT_ROOT, "data", "processed")
RAPPORT_PATH = os.path.join(DATA_PROCESSED, "rapport_final.json")

st.set_page_config(page_title="ESG Report Generator — NordTech Industries", page_icon="🌱", layout="wide")


@st.cache_data(show_spinner=False)
def charger_rapport(path: str, _mtime: float):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main():
    st.title("🌱 ESG Report Generator")
    st.caption(
        "Génération assistée par LLM des sections narratives d'un rapport de durabilité "
        "aligné ESRS, avec contrôle anti-hallucination sur chaque chiffre cité. "
        "**Données 100% fictives** (projet portfolio)."
    )

    with st.sidebar:
        st.header("⚙️ Génération du rapport")
        annee = st.selectbox("Exercice", options=[2025], index=0)

        OPTIONS_LLM = {
            "mock (démo, instantané)": ("mock", None),
            "llama3.2:3b (Ollama, local)": ("ollama", "llama3.2:3b"),
            "llama3.2:1b (Ollama, local, plus léger)": ("ollama", "llama3.2:1b"),
        }
        choix_llm = st.selectbox(
            "Mode de génération LLM",
            options=list(OPTIONS_LLM.keys()),
            help=(
                "mock : gabarit déterministe, sans rien à installer, résultat instantané.\n"
                "llama3.2:3b / llama3.2:1b : vraie génération via Ollama en local "
                "(nécessite Ollama installé — https://ollama.com — et le modèle "
                "téléchargé au préalable avec `ollama pull <modèle>`). "
                "Le 1b est plus léger et plus rapide sur une machine modeste."
            ),
        )
        llm_mode, ollama_model = OPTIONS_LLM[choix_llm]

        if st.button("🔄 (Re)générer le rapport", use_container_width=True):
            with st.spinner("Génération et vérification anti-hallucination en cours..."):
                cmd = [sys.executable, os.path.join(PROJECT_ROOT, "generate_report.py"),
                       "--annee", str(annee), "--llm-mode", llm_mode]
                if ollama_model:
                    cmd += ["--ollama-model", ollama_model]
                result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                st.success("Rapport généré avec succès.")
                st.cache_data.clear()
            else:
                st.error("Échec de la génération. Détail :")
                st.code(result.stderr or result.stdout)

        st.divider()
        st.markdown("**Export du rapport**")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📄 PDF", use_container_width=True):
                _exporter("pdf")
        with col2:
            if st.button("📝 Word", use_container_width=True):
                _exporter("docx")

    if not os.path.exists(RAPPORT_PATH):
        st.warning("Aucun rapport généré pour l'instant. Cliquez sur **(Re)générer le rapport** dans la barre latérale.")
        st.stop()

    rapport = charger_rapport(RAPPORT_PATH, os.path.getmtime(RAPPORT_PATH))

    # --- Résumé global ---
    sections = rapport["sections"]
    n_verifie = sum(1 for s in sections if s["statut_final"] == "verifie")
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Exercice", rapport["annee"])
    col_b.metric("Sections vérifiées", f"{n_verifie}/{len(sections)}")
    col_c.metric("Mode LLM utilisé", rapport.get("llm_mode", "n/a"))

    st.divider()

    df_kpis = pd.DataFrame(rapport["kpis_bruts"])

    tab_narratif, tab_kpis, tab_edition = st.tabs(
        ["📖 Rapport narratif", "📊 KPIs bruts", "✏️ Éditer les KPIs"]
    )

    with tab_narratif:
        for section in sections:
            afficher_section_narrative(section)
            st.divider()

    with tab_kpis:
        for pilier in ["E1", "S1", "G1"]:
            df_pilier = df_kpis[df_kpis["pilier"] == pilier]
            if not df_pilier.empty:
                afficher_kpis_pilier(df_pilier, pilier)
                st.write("")

    with tab_edition:
        afficher_editeur_kpis(llm_mode, ollama_model)


def _exporter(format_: str):
    script = "export_pdf.py" if format_ == "pdf" else "export_docx.py"
    out_file = f"rapport_esg.{format_}"
    out_path = os.path.join(DATA_PROCESSED, out_file)
    with st.spinner(f"Génération du fichier {format_.upper()}..."):
        result = subprocess.run(
            [sys.executable, os.path.join(PROJECT_ROOT, "app", "export", script),
             "--in", RAPPORT_PATH, "--out", out_path],
            capture_output=True, text=True,
        )
    if result.returncode == 0 and os.path.exists(out_path):
        with open(out_path, "rb") as f:
            st.sidebar.download_button(
                f"⬇️ Télécharger le {format_.upper()}", data=f.read(),
                file_name=out_file, use_container_width=True,
            )
    else:
        st.sidebar.error(f"Échec de l'export {format_.upper()}.")
        st.sidebar.code(result.stderr or result.stdout)


if __name__ == "__main__":
    main()
