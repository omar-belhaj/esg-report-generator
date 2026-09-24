"""
generate_sections.py
=====================
Pour chaque pilier ESRS (E1, S1, G1) et une année de reporting donnée :
  1. Sélectionne les KPIs enrichis correspondants (data/processed/kpis_enrichis.csv)
  2. Construit le prompt (system + user) à partir des templates
  3. Appelle le LLM (via LLMClient)
  4. Retourne un objet structuré {section, texte_genere, kpis_utilises}

Ce module ne fait PAS la vérification anti-hallucination : voir
verification/cross_checker.py, orchestré par generate_report.py.

Usage :
    python generation/generate_sections.py --annee 2025
"""

import argparse
import json
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from llm_client import LLMClient  # noqa: E402

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_PROCESSED = os.path.join(PROJECT_ROOT, "data", "processed")
PROMPTS_DIR = os.path.join(os.path.dirname(__file__), "prompts")

SECTIONS_ORDRE = ["E1", "S1", "G1"]
LABELS_PILIER = {
    "E1": "E1 - Changement climatique",
    "S1": "S1 - Effectifs propres",
    "G1": "G1 - Conduite des affaires",
}


def charger_prompt_template(nom_fichier: str) -> str:
    with open(os.path.join(PROMPTS_DIR, nom_fichier), encoding="utf-8") as f:
        return f.read()


def formater_tableau_kpis(df_pilier: pd.DataFrame) -> str:
    """Formate les KPIs d'un pilier en lignes texte lisibles par un LLM (et par le parser mock)."""
    lignes = []
    for _, row in df_pilier.iterrows():
        ligne = f"- {row['nom_indicateur']} : {row['valeur']:g} {row['unite']}"
        if pd.notna(row.get("variation_pct")):
            ligne += f" (variation vs {int(row['annee']) - 1} : {row['variation_pct']:+.2f}%)"
        if pd.notna(row.get("statut_vs_objectif")):
            ligne += f" [statut vs objectif : {row['statut_vs_objectif']}]"
        lignes.append(ligne)
    return "\n".join(lignes)


def formater_contexte(df_pilier: pd.DataFrame) -> str:
    lignes = []
    for _, row in df_pilier.iterrows():
        if pd.notna(row.get("texte_contexte")):
            lignes.append(f"- [{row['nom_indicateur']}] {row['texte_contexte']}")
    return "\n".join(lignes) if lignes else "(aucun contexte qualitatif disponible pour cette section/année)"


def construire_prompt_utilisateur(pilier: str, annee: int, df_pilier: pd.DataFrame) -> str:
    template = charger_prompt_template("section_template.txt")
    return template.format(
        esrs_section=LABELS_PILIER[pilier],
        annee=annee,
        annee_precedente=annee - 1,
        tableau_kpis=formater_tableau_kpis(df_pilier),
        contexte_qualitatif=formater_contexte(df_pilier),
    )


def generer_section(pilier: str, annee: int, df_enrichi: pd.DataFrame, llm_client: LLMClient) -> dict:
    df_pilier = df_enrichi[(df_enrichi["pilier"] == pilier) & (df_enrichi["annee"] == annee)].copy()
    if df_pilier.empty:
        raise ValueError(f"Aucune donnée trouvée pour le pilier {pilier} / année {annee}.")

    system_prompt = charger_prompt_template("system_prompt.txt")
    user_prompt = construire_prompt_utilisateur(pilier, annee, df_pilier)

    texte_genere = llm_client.complete(system_prompt, user_prompt)

    return {
        "pilier": pilier,
        "esrs_section": LABELS_PILIER[pilier],
        "annee": annee,
        "texte_genere": texte_genere,
        "kpis_utilises": df_pilier.to_dict(orient="records"),
        "prompt_utilisateur": user_prompt,
        "system_prompt": system_prompt,
    }


def generer_rapport_complet(annee: int, llm_mode: str = None) -> list:
    df_enrichi = pd.read_csv(os.path.join(DATA_PROCESSED, "kpis_enrichis.csv"))
    llm_client = LLMClient(mode=llm_mode)

    sections = []
    for pilier in SECTIONS_ORDRE:
        section = generer_section(pilier, annee, df_enrichi, llm_client)
        sections.append(section)
        print(f"[OK] Section générée : {LABELS_PILIER[pilier]} ({len(section['texte_genere'])} caractères)")

    return sections


def main():
    parser = argparse.ArgumentParser(description="Génère les sections narratives ESRS à partir des KPIs enrichis.")
    parser.add_argument("--annee", type=int, default=2025)
    parser.add_argument("--llm-mode", type=str, default=None, help="mock / ollama / dataiku (défaut: variable LLM_MODE ou 'mock')")
    parser.add_argument("--out", type=str, default=os.path.join(DATA_PROCESSED, "sections_generees.json"))
    args = parser.parse_args()

    sections = generer_rapport_complet(args.annee, llm_mode=args.llm_mode)

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(sections, f, ensure_ascii=False, indent=2, default=str)

    print(f"\n[OK] {len(sections)} sections écrites dans {args.out}")


if __name__ == "__main__":
    main()
