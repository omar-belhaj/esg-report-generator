"""
generate_report.py
====================
Point d'entrée principal du projet, à la racine du repo. Enchaîne :
  1. (optionnel) exécution du pipeline de données Dataiku/local
  2. Génération + vérification anti-hallucination de chaque section ESRS
  3. Écriture du rapport final consommé par le dashboard Streamlit

Usage :
    python generate_report.py --annee 2025 --llm-mode mock
    python generate_report.py --annee 2025 --llm-mode ollama --ollama-model llama3.2:3b
    python generate_report.py --annee 2025 --llm-mode ollama --ollama-model llama3.2:1b
"""

import argparse
import json
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "generation"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "verification"))

from llm_client import LLMClient  # noqa: E402
from regeneration import generer_section_avec_verification  # noqa: E402

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_PROCESSED = os.path.join(PROJECT_ROOT, "data", "processed")
SECTIONS_ORDRE = ["E1", "S1", "G1"]


def main():
    parser = argparse.ArgumentParser(description="Génère le rapport ESG complet avec contrôle anti-hallucination.")
    parser.add_argument("--annee", type=int, default=2025)
    parser.add_argument("--llm-mode", type=str, default=None, help="mock / ollama / dataiku")
    parser.add_argument("--ollama-model", type=str, default=None,
                         help="Modèle Ollama à utiliser (ex. llama3.2:3b, llama3.2:1b). "
                              "Ignoré si --llm-mode n'est pas 'ollama'. Défaut : variable "
                              "d'env OLLAMA_MODEL, ou llama3.2:3b.")
    parser.add_argument("--out", type=str, default=os.path.join(DATA_PROCESSED, "rapport_final.json"))
    args = parser.parse_args()

    if args.ollama_model:
        os.environ["OLLAMA_MODEL"] = args.ollama_model

    kpis_path = os.path.join(DATA_PROCESSED, "kpis_enrichis.csv")
    if not os.path.exists(kpis_path):
        print("[INFO] Dataset enrichi introuvable, exécution du pipeline de données d'abord...")
        os.system(f"{sys.executable} {os.path.join(PROJECT_ROOT, 'dataiku_flow', 'run_pipeline.py')}")

    df_enrichi = pd.read_csv(kpis_path)
    llm_client = LLMClient(mode=args.llm_mode)

    modele_info = f" — modèle : {os.environ.get('OLLAMA_MODEL', 'llama3.2:3b')}" if llm_client.mode == "ollama" else ""
    print(f"\n=== Génération du rapport {args.annee} (mode LLM : {llm_client.mode}{modele_info}) ===\n")

    sections = []
    for pilier in SECTIONS_ORDRE:
        resultat = generer_section_avec_verification(pilier, args.annee, df_enrichi, llm_client)
        sections.append(resultat)
        badge = "✅" if resultat["statut_final"] == "verifie" else "⚠️"
        print(f"{badge} {resultat['esrs_section']} — statut : {resultat['statut_final']} "
              f"({resultat['nb_tentatives']} tentative(s))")

    rapport = {
        "annee": args.annee,
        "llm_mode": llm_client.mode,
        "entreprise": "NordTech Industries (données fictives)",
        "sections": sections,
        "kpis_bruts": df_enrichi[df_enrichi["annee"] == args.annee].to_dict(orient="records"),
    }

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(rapport, f, ensure_ascii=False, indent=2, default=str)

    n_verifie = sum(1 for s in sections if s["statut_final"] == "verifie")
    print(f"\n=== Rapport écrit dans {args.out} ({n_verifie}/{len(sections)} sections vérifiées) ===")


if __name__ == "__main__":
    main()
