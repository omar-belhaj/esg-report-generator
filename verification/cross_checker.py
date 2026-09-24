"""
cross_checker.py
==================
Cœur du contrôle anti-hallucination : compare chaque chiffre extrait d'un
texte généré (via number_extractor) à l'ensemble des valeurs "autorisées"
pour la section concernée (issues de data/processed/kpis_enrichis.csv).

Le verdict est calculé en Python pur, sans appel LLM : c'est ce qui garantit
la reproductibilité du contrôle (même texte -> même verdict, toujours).

Valeurs considérées comme "autorisées" pour un pilier/année donnés :
  - valeur (valeur courante du KPI)
  - valeur_n1 (valeur année précédente)
  - variation_pct (en valeur signée ET en valeur absolue, car le texte peut
    dire "en baisse de 9.74%" sans le signe négatif)
  - objectif_seuil
  - ecart_objectif_pct (signée et absolue)

Un nombre extrait est considéré comme "vérifié" s'il correspond, à une
tolérance près (défaut 0.05 en absolu, ou 0.5% en relatif pour les grandes
valeurs), à au moins une valeur autorisée.
"""

import re
from dataclasses import dataclass, field

import pandas as pd

from number_extractor import extraire_nombres, exclure_annees_isolees, NombreExtrait

TOLERANCE_ABSOLUE = 0.05
TOLERANCE_RELATIVE = 0.005  # 0.5%


@dataclass
class VerdictNombre:
    nombre: NombreExtrait
    verifie: bool
    kpi_correspondant: str = None
    champ_correspondant: str = None


@dataclass
class RapportVerification:
    pilier: str
    annee: int
    texte: str
    verdicts: list = field(default_factory=list)
    statut: str = "verifie"  # "verifie" ou "a_corriger"
    nombres_non_verifies: list = field(default_factory=list)

    def to_dict(self):
        return {
            "pilier": self.pilier,
            "annee": self.annee,
            "statut": self.statut,
            "nb_chiffres_detectes": len(self.verdicts),
            "nb_chiffres_verifies": sum(1 for v in self.verdicts if v.verifie),
            "chiffres_non_verifies": [
                {"valeur_brute": v.nombre.valeur_brute, "position": v.nombre.position}
                for v in self.verdicts if not v.verifie
            ],
        }


def _construire_valeurs_autorisees(df_pilier: pd.DataFrame) -> dict:
    """Construit un dict {valeur_arrondie: (kpi_id, champ)} de toutes les
    valeurs sources autorisées pour ce pilier/année."""
    autorisees = {}

    def ajouter(val, kpi_id, champ):
        if pd.isna(val):
            return
        for v in {val, abs(val)}:  # on autorise la valeur signée ET sa valeur absolue
            key = round(float(v), 2)
            autorisees.setdefault(key, (kpi_id, champ))

    for _, row in df_pilier.iterrows():
        ajouter(row.get("valeur"), row["kpi_id"], "valeur")
        ajouter(row.get("valeur_n1"), row["kpi_id"], "valeur_n1")
        ajouter(row.get("variation_pct"), row["kpi_id"], "variation_pct")
        ajouter(row.get("objectif_seuil"), row["kpi_id"], "objectif_seuil")
        ajouter(row.get("ecart_objectif_pct"), row["kpi_id"], "ecart_objectif_pct")

    return autorisees


def _chercher_correspondance(valeur: float, valeurs_autorisees: dict):
    """Cherche une correspondance à tolérance près (absolue OU relative)."""
    for val_ref, (kpi_id, champ) in valeurs_autorisees.items():
        if abs(valeur - val_ref) <= TOLERANCE_ABSOLUE:
            return kpi_id, champ
        if val_ref != 0 and abs(valeur - val_ref) / abs(val_ref) <= TOLERANCE_RELATIVE:
            return kpi_id, champ
    return None, None


def _masquer_chiffres_des_libelles(texte: str, df_pilier: pd.DataFrame) -> str:
    """Neutralise les chiffres qui font partie du NOM d'un indicateur plutôt
    que de sa valeur (ex. « Émissions GES Scope 1 » contient le chiffre "1",
    qui n'est pas une valeur mesurée mais un identifiant de périmètre).
    On remplace chaque occurrence du libellé par une version où les chiffres
    sont neutralisés, en conservant la longueur de la chaîne pour ne pas
    décaler les positions des autres nombres dans le texte."""
    texte_masque = texte
    identifiants_scope = set()

    for nom in df_pilier["nom_indicateur"].dropna().unique():
        nom_neutralise = re.sub(r"\d", "#", nom)
        texte_masque = texte_masque.replace(nom, nom_neutralise)
        # Version entre guillemets français, utilisée par le mode mock et par
        # plusieurs LLMs qui citent le nom de l'indicateur entre « » ou "".
        texte_masque = texte_masque.replace(f"« {nom} »", f"« {nom_neutralise} »")
        # Identifiants de périmètre type "Scope 1/2/3" : le LLM peut reformuler
        # librement autour ("du Scope 1", "le scope 2 a...") sans reprendre le
        # libellé exact. On collecte ces identifiants pour les neutraliser
        # partout dans le texte, pas seulement dans le libellé complet.
        identifiants_scope.update(re.findall(r"[Ss]cope\s*\d+", nom))

    for identifiant in identifiants_scope:
        texte_masque = re.sub(
            re.escape(identifiant), lambda m: re.sub(r"\d", "#", m.group(0)), texte_masque
        )

    return texte_masque


def verifier_section(pilier: str, annee: int, texte: str, df_enrichi: pd.DataFrame) -> RapportVerification:
    df_pilier = df_enrichi[(df_enrichi["pilier"] == pilier) & (df_enrichi["annee"] == annee)]
    annees_valides = set(df_enrichi["annee"].unique().tolist())

    valeurs_autorisees = _construire_valeurs_autorisees(df_pilier)

    texte_pour_extraction = _masquer_chiffres_des_libelles(texte, df_pilier)
    nombres = extraire_nombres(texte_pour_extraction)
    nombres = exclure_annees_isolees(nombres, annees_valides)

    rapport = RapportVerification(pilier=pilier, annee=annee, texte=texte)

    for n in nombres:
        kpi_id, champ = _chercher_correspondance(n.valeur_normalisee, valeurs_autorisees)
        verdict = VerdictNombre(
            nombre=n,
            verifie=kpi_id is not None,
            kpi_correspondant=kpi_id,
            champ_correspondant=champ,
        )
        rapport.verdicts.append(verdict)
        if not verdict.verifie:
            rapport.nombres_non_verifies.append(n)

    rapport.statut = "a_corriger" if rapport.nombres_non_verifies else "verifie"
    return rapport
