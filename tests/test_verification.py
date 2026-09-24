"""
test_verification.py
======================
Tests du cœur anti-hallucination : number_extractor + cross_checker.

Lancer avec : pytest tests/test_verification.py -v
"""

import os
import sys

import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "verification"))

from number_extractor import extraire_nombres, exclure_annees_isolees  # noqa: E402
from cross_checker import verifier_section  # noqa: E402


@pytest.fixture
def df_enrichi():
    path = os.path.join(os.path.dirname(__file__), "..", "data", "processed", "kpis_enrichis.csv")
    if not os.path.exists(path):
        pytest.skip("data/processed/kpis_enrichis.csv absent — lancez d'abord dataiku_flow/run_pipeline.py")
    return pd.read_csv(path)


# ----------------------------------------------------------------------
# number_extractor
# ----------------------------------------------------------------------

def test_extraction_nombre_simple():
    nombres = extraire_nombres("La valeur est de 4820 tCO2eq.")
    assert len(nombres) == 1
    assert nombres[0].valeur_normalisee == 4820.0


def test_extraction_grand_nombre_sans_separateur():
    """Régression : un grand nombre sans séparateur de milliers ne doit pas
    être tronqué (ex. 25800 ne doit pas devenir 258)."""
    nombres = extraire_nombres("La consommation atteint 25800 MWh.")
    assert len(nombres) == 1
    assert nombres[0].valeur_normalisee == 25800.0


def test_extraction_avec_separateur_milliers():
    nombres = extraire_nombres("La consommation atteint 25 800 MWh.")
    assert len(nombres) == 1
    assert nombres[0].valeur_normalisee == 25800.0


def test_extraction_pourcentage_negatif():
    nombres = extraire_nombres("Une baisse de -13.45% a été observée.")
    assert len(nombres) == 1
    assert nombres[0].valeur_normalisee == -13.45
    assert nombres[0].est_pourcentage is True


def test_extraction_virgule_decimale_francaise():
    nombres = extraire_nombres("Le taux s'établit à 9,74%.")
    assert len(nombres) == 1
    assert abs(nombres[0].valeur_normalisee - 9.74) < 1e-6


def test_exclusion_annees_isolees():
    nombres = extraire_nombres("En 2025, la valeur a atteint 4820 tCO2eq.")
    filtres = exclure_annees_isolees(nombres, annees_valides={2023, 2024, 2025})
    valeurs = [n.valeur_normalisee for n in filtres]
    assert 2025.0 not in valeurs
    assert 4820.0 in valeurs


# ----------------------------------------------------------------------
# cross_checker — cas positif (texte correct)
# ----------------------------------------------------------------------

def test_texte_correct_est_verifie(df_enrichi):
    texte = (
        "Les émissions de gaz à effet de serre du Scope 1 s'établissent à "
        "4820 tCO2eq en 2025, en baisse de 9.74% par rapport à 2024."
    )
    rapport = verifier_section("E1", 2025, texte, df_enrichi)
    assert rapport.statut == "verifie"


# ----------------------------------------------------------------------
# cross_checker — cas négatif (chiffre halluciné)
# ----------------------------------------------------------------------

def test_chiffre_invente_est_detecte(df_enrichi):
    texte = (
        "Les émissions ont chuté de 99.9% cette année, un record absolu "
        "jamais atteint par une entreprise du secteur."
    )
    rapport = verifier_section("E1", 2025, texte, df_enrichi)
    assert rapport.statut == "a_corriger"
    valeurs_rejetees = [v["valeur_brute"] for v in rapport.to_dict()["chiffres_non_verifies"]]
    assert any("99.9" in v for v in valeurs_rejetees)


def test_valeur_correcte_mais_mauvaise_unite_ou_arrondi_grossier_est_detectee(df_enrichi):
    """Une valeur proche mais significativement différente (ex. mauvais arrondi
    ou confusion d'échelle) doit être rejetée, pas silencieusement acceptée."""
    texte = "Les émissions Scope 1 s'établissent à 4900 tCO2eq en 2025."  # vraie valeur : 4820
    rapport = verifier_section("E1", 2025, texte, df_enrichi)
    assert rapport.statut == "a_corriger"


def test_valeur_zero_incidents_corruption_non_surinterpretee(df_enrichi):
    """Cas limite important : le KPI 'incidents de corruption' vaut 0 chaque
    année. Le texte ne doit citer que des chiffres réellement présents ;
    un texte qui invente '2 incidents' doit être flaggé."""
    texte = "L'entreprise a enregistré 2 incidents de corruption en 2025."
    rapport = verifier_section("G1", 2025, texte, df_enrichi)
    assert rapport.statut == "a_corriger"


def test_valeur_zero_incidents_corruption_texte_correct(df_enrichi):
    texte = "Aucun incident de corruption n'a été signalé en 2025 (0 incident)."
    rapport = verifier_section("G1", 2025, texte, df_enrichi)
    assert rapport.statut == "verifie"


# ----------------------------------------------------------------------
# cross_checker — faux positifs à éviter (libellés contenant des chiffres)
# ----------------------------------------------------------------------

def test_libelle_scope_1_2_3_non_flagge_a_tort(df_enrichi):
    """'Scope 1', 'Scope 2', 'Scope 3' apparaissent dans les noms d'indicateurs
    eux-mêmes : ces chiffres d'identification ne doivent pas être traités
    comme des valeurs mesurées à vérifier."""
    texte = (
        "L'indicateur « Émissions GES Scope 1 » s'établit à 4820 tCO2eq. "
        "L'indicateur « Émissions GES Scope 2 » s'établit à 2380 tCO2eq."
    )
    rapport = verifier_section("E1", 2025, texte, df_enrichi)
    assert rapport.statut == "verifie"
