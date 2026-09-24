"""
number_extractor.py
=====================
Extraction DÉTERMINISTE (regex, sans LLM) de tous les nombres présents dans
un texte généré : entiers, décimaux (point ou virgule), pourcentages.

C'est volontairement la première ligne de défense du contrôle anti-hallucination :
un juge non-déterministe (un LLM qui "relit" le texte) pourrait lui-même se
tromper ou halluciner sur ce qu'il a "vu". La détection des nombres doit être
100% reproductible.

Un second passage optionnel (LLM "extracteur strict", voir cross_checker.py)
peut compléter cette extraction pour capter les formulations non strictement
numériques, mais le verdict final de correspondance reste calculé en Python
pur sur les nombres extraits par regex.
"""

import re
from dataclasses import dataclass


@dataclass
class NombreExtrait:
    valeur_brute: str      # tel qu'il apparaît dans le texte, ex. "4 820" ou "9,74%"
    valeur_normalisee: float  # ex. 4820.0 ou 9.74
    est_pourcentage: bool
    position: int          # index de caractère dans le texte, pour le report


# Capture les nombres avec espaces insécables/normaux comme séparateurs de milliers,
# virgule ou point comme séparateur décimal, et un éventuel signe %.
# Exemples capturés : "4820", "4 820", "4,820.5", "9,74%", "-13.45%", "0.29"
#
# IMPORTANT : l'alternative "avec séparateur de milliers" est placée EN PREMIER
# et rendue OBLIGATOIRE (+ et non *) pour qu'elle ne s'applique que lorsqu'un
# vrai séparateur d'espace est présent (ex. "25 800"). Sinon, l'alternation
# regex s'arrêterait au premier alternative qui "réussit" même partiellement
# (ex. "258" sur "25800"), ce qui tronquerait les grands nombres sans espace.
NUMBER_PATTERN = re.compile(
    r"(?<![\w.])([+-]?\d{1,3}(?:[ \u00A0]\d{3})+(?:[.,]\d+)?|[+-]?\d+(?:[.,]\d+)?)\s*(%)?"
)


def _normaliser(valeur_brute: str) -> float:
    """Convertit '4 820', '4,820', '9,74' etc. en float, en gérant les ambiguïtés
    virgule décimale (français) vs séparateur de milliers."""
    v = valeur_brute.replace("\u00A0", " ").strip()
    v = v.replace(" ", "")  # séparateur de milliers "4 820" -> "4820"

    if "," in v and "." in v:
        # ex "4,820.5" (rare, format US avec virgule milliers) -> retire les virgules
        v = v.replace(",", "")
    elif "," in v:
        # Ambiguïté FR : "9,74" = décimal ; "4,820" pourrait être un séparateur de
        # milliers mal formé. On applique la convention française par défaut :
        # la virgule est TOUJOURS un séparateur décimal.
        v = v.replace(",", ".")

    return float(v)


def extraire_nombres(texte: str) -> list:
    """Retourne la liste de tous les NombreExtrait détectés dans le texte,
    en excluant les faux positifs évidents (ex. années à 4 chiffres type "2025"
    utilisées seules sans contexte de mesure ne sont PAS exclues automatiquement
    ici : le cross-checker gère leur cas séparément car une année peut aussi être
    une donnée légitime, ex. 'objectif 2027')."""
    resultats = []
    for match in NUMBER_PATTERN.finditer(texte):
        brut_nombre, pct = match.group(1), match.group(2)
        try:
            val = _normaliser(brut_nombre)
        except ValueError:
            continue
        resultats.append(
            NombreExtrait(
                valeur_brute=match.group(0).strip(),
                valeur_normalisee=val,
                est_pourcentage=bool(pct),
                position=match.start(),
            )
        )
    return resultats


def exclure_annees_isolees(nombres: list, annees_valides: set) -> list:
    """Filtre les occurrences qui correspondent probablement à une année de
    reporting citée en texte (ex. 'en 2025', 'depuis 2023') plutôt qu'à une
    vraie valeur de KPI, pour éviter des faux positifs de vérification.
    Ne s'applique qu'aux entiers à 4 chiffres, non-pourcentage, présents dans
    l'ensemble des années valides du dataset."""
    filtres = []
    for n in nombres:
        est_annee_plausible = (
            not n.est_pourcentage
            and n.valeur_normalisee.is_integer()
            and int(n.valeur_normalisee) in annees_valides
        )
        if not est_annee_plausible:
            filtres.append(n)
    return filtres
