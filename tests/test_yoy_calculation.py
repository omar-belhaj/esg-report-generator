"""
test_yoy_calculation.py
=========================
Tests du recipe 02 (calcul YoY et écarts vs objectifs).

Lancer avec : pytest tests/test_yoy_calculation.py -v
"""

import importlib
import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "dataiku_flow", "recipes"))

# Le nom de fichier "02_calcul_yoy_et_ecarts.py" commence par un chiffre et
# n'est donc pas importable via `import ...` classique : on passe par importlib.
_module = importlib.import_module("02_calcul_yoy_et_ecarts")
calculer_yoy = _module.calculer_yoy


def _df_test():
    return pd.DataFrame([
        {"kpi_id": "X", "pilier": "E1", "esrs_datapoint": "E1-6", "nom_indicateur": "Test",
         "annee": 2023, "valeur": 100.0, "unite": "u", "objectif_seuil": 80.0,
         "sens_amelioration": "baisse", "perimetre": "Groupe"},
        {"kpi_id": "X", "pilier": "E1", "esrs_datapoint": "E1-6", "nom_indicateur": "Test",
         "annee": 2024, "valeur": 90.0, "unite": "u", "objectif_seuil": 80.0,
         "sens_amelioration": "baisse", "perimetre": "Groupe"},
        {"kpi_id": "X", "pilier": "E1", "esrs_datapoint": "E1-6", "nom_indicateur": "Test",
         "annee": 2025, "valeur": 75.0, "unite": "u", "objectif_seuil": 80.0,
         "sens_amelioration": "baisse", "perimetre": "Groupe"},
    ])


def test_premiere_annee_sans_n1():
    df = calculer_yoy(_df_test())
    ligne_2023 = df[df["annee"] == 2023].iloc[0]
    assert pd.isna(ligne_2023["valeur_n1"])
    assert pd.isna(ligne_2023["variation_pct"])


def test_variation_pct_calculee_correctement():
    df = calculer_yoy(_df_test())
    ligne_2024 = df[df["annee"] == 2024].iloc[0]
    # (90 - 100) / 100 * 100 = -10.0
    assert ligne_2024["variation_pct"] == pytest.approx(-10.0)


def test_statut_objectif_atteint_quand_sens_baisse_et_valeur_sous_seuil():
    df = calculer_yoy(_df_test())
    ligne_2025 = df[df["annee"] == 2025].iloc[0]
    # valeur=75, objectif=80, sens='baisse' -> 75 <= 80 -> atteint
    assert ligne_2025["statut_vs_objectif"] == "atteint"


def test_statut_au_dessus_quand_sens_baisse_et_valeur_superieure_au_seuil():
    df = calculer_yoy(_df_test())
    ligne_2023 = df[df["annee"] == 2023].iloc[0]
    # valeur=100, objectif=80, sens='baisse' -> 100 > 80 -> au-dessus
    assert ligne_2023["statut_vs_objectif"] == "au-dessus"


def test_statut_en_deca_quand_sens_hausse_et_valeur_inferieure_au_seuil():
    df_source = _df_test().copy()
    df_source["sens_amelioration"] = "hausse"
    df = calculer_yoy(df_source)
    ligne_2023 = df[df["annee"] == 2023].iloc[0]
    # valeur=100, objectif=80, sens='hausse' -> 100 >= 80 -> atteint
    assert ligne_2023["statut_vs_objectif"] == "atteint"
