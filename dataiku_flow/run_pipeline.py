"""
run_pipeline.py
================
Exécute localement l'équivalent du flow Dataiku, recipe par recipe,
pour permettre à un reviewer de reproduire le pipeline sans instance
Dataiku. Dans le vrai projet Dataiku, ces 3 étapes sont des recipes
connectés visuellement dans le flow (voir docs/architecture.png et
dataiku_flow/README.md pour le détail du flow visuel).

Usage :
    python dataiku_flow/run_pipeline.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "recipes"))

import importlib


def main():
    print("=" * 70)
    print("PIPELINE ESG — exécution locale (équivalent flow Dataiku)")
    print("=" * 70)

    for step_module in ["01_nettoyage_kpis", "02_calcul_yoy_et_ecarts", "03_mapping_esrs"]:
        print(f"\n--- Étape : {step_module} ---")
        mod = importlib.import_module(step_module)
        mod.main()

    print("\n" + "=" * 70)
    print("Pipeline terminé. Dataset final : data/processed/kpis_enrichis.csv")
    print("=" * 70)


if __name__ == "__main__":
    main()
