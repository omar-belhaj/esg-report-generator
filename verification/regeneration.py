"""
regeneration.py
=================
Si le cross-checker détecte un ou plusieurs chiffres non vérifiés dans une
section générée, ce module relance la génération en renforçant le prompt
avec :
  - un rappel explicite de la liste des chiffres autorisés
  - la liste des valeurs qui ont été rejetées au tour précédent (pour que le
    LLM comprenne concrètement ce qu'il doit éviter)

Après MAX_TENTATIVES échecs consécutifs, la section est marquée
"a_corriger" définitivement et transmise telle quelle au dashboard, avec le
détail des chiffres en cause, pour une revue humaine (le principe du garde-fou
est de ne JAMAIS publier silencieusement un texte non vérifié comme vérifié).
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "generation"))
sys.path.insert(0, os.path.dirname(__file__))

from cross_checker import verifier_section
from generate_sections import (
    construire_prompt_utilisateur,
    charger_prompt_template,
    LABELS_PILIER,
)

MAX_TENTATIVES = 3


def _construire_prompt_correction(prompt_original: str, chiffres_rejetes: list) -> str:
    if not chiffres_rejetes:
        return prompt_original

    liste_rejets = ", ".join(f"« {v.valeur_brute} »" for v in chiffres_rejetes)
    correction = (
        f"\n\nATTENTION — CORRECTION REQUISE : ta réponse précédente contenait "
        f"le(s) chiffre(s) suivant(s), qui NE CORRESPONDENT À AUCUNE VALEUR DU "
        f"TABLEAU SOURCE ci-dessus : {liste_rejets}. Ces valeurs sont soit "
        f"inventées, soit mal recopiées (unité/arrondi différent). Réécris "
        f"entièrement le paragraphe en utilisant UNIQUEMENT les valeurs "
        f"listées dans le tableau, recopiées à l'identique."
    )
    return prompt_original + correction


def generer_section_avec_verification(pilier: str, annee: int, df_enrichi, llm_client) -> dict:
    """Génère une section et la vérifie, en régénérant jusqu'à MAX_TENTATIVES
    fois si des chiffres non vérifiés sont détectés."""
    df_pilier = df_enrichi[(df_enrichi["pilier"] == pilier) & (df_enrichi["annee"] == annee)].copy()
    if df_pilier.empty:
        raise ValueError(f"Aucune donnée pour {pilier}/{annee}")

    system_prompt = charger_prompt_template("system_prompt.txt")
    user_prompt = construire_prompt_utilisateur(pilier, annee, df_pilier)

    historique_tentatives = []
    prompt_courant = user_prompt

    for tentative in range(1, MAX_TENTATIVES + 1):
        texte = llm_client.complete(system_prompt, prompt_courant)
        rapport = verifier_section(pilier, annee, texte, df_enrichi)

        historique_tentatives.append({
            "tentative": tentative,
            "texte": texte,
            "statut": rapport.statut,
            "chiffres_non_verifies": [v.valeur_brute for v in rapport.nombres_non_verifies],
        })

        if rapport.statut == "verifie":
            return {
                "pilier": pilier,
                "esrs_section": LABELS_PILIER[pilier],
                "annee": annee,
                "texte_final": texte,
                "statut_final": "verifie",
                "nb_tentatives": tentative,
                "historique_tentatives": historique_tentatives,
                "rapport_verification": rapport.to_dict(),
                "kpis_utilises": df_pilier.to_dict(orient="records"),
            }

        # Échec -> on prépare le prompt de correction pour la prochaine tentative
        prompt_courant = _construire_prompt_correction(user_prompt, rapport.nombres_non_verifies)
        print(f"[FLAG] {pilier}/{annee} — tentative {tentative} : "
              f"{len(rapport.nombres_non_verifies)} chiffre(s) non vérifié(s). Régénération...")

    # Toutes les tentatives ont échoué -> flag pour revue humaine, texte conservé tel quel
    dernier = historique_tentatives[-1]
    print(f"[ECHEC] {pilier}/{annee} — échec après {MAX_TENTATIVES} tentatives. Marqué 'a_corriger' pour revue humaine.")
    return {
        "pilier": pilier,
        "esrs_section": LABELS_PILIER[pilier],
        "annee": annee,
        "texte_final": dernier["texte"],
        "statut_final": "a_corriger",
        "nb_tentatives": MAX_TENTATIVES,
        "historique_tentatives": historique_tentatives,
        "rapport_verification": verifier_section(pilier, annee, dernier["texte"], df_enrichi).to_dict(),
        "kpis_utilises": df_pilier.to_dict(orient="records"),
    }
