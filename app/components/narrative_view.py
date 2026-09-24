"""Composant Streamlit : affichage du texte narratif généré par section, avec le
badge de vérification anti-hallucination et le détail des chiffres contrôlés."""

import streamlit as st

from .verification_badge import afficher_badge_verification


def afficher_section_narrative(section: dict):
    col_titre, col_badge = st.columns([4, 1])
    with col_titre:
        st.markdown(f"### {section['esrs_section']}")
    with col_badge:
        afficher_badge_verification(section["statut_final"])

    st.write(section["texte_final"])

    rapport_verif = section.get("rapport_verification", {})
    nb_detectes = rapport_verif.get("nb_chiffres_detectes", 0)
    nb_verifies = rapport_verif.get("nb_chiffres_verifies", 0)

    with st.expander(f"🔍 Détail de la vérification ({nb_verifies}/{nb_detectes} chiffres vérifiés, "
                      f"{section['nb_tentatives']} tentative(s) de génération)"):
        if section["statut_final"] == "verifie":
            st.success(f"Les {nb_detectes} chiffre(s) cité(s) dans ce paragraphe correspondent "
                       f"tous à une valeur du dataset source.")
        else:
            chiffres_rejetes = rapport_verif.get("chiffres_non_verifies", [])
            st.warning(
                "Après plusieurs tentatives de génération, certains chiffres cités ne "
                "correspondent à aucune valeur du dataset source. Ce paragraphe nécessite "
                "une revue humaine avant publication."
            )
            if chiffres_rejetes:
                st.write("Chiffre(s) non vérifié(s) :")
                for c in chiffres_rejetes:
                    st.markdown(f"- `{c['valeur_brute']}`")

        if len(section.get("historique_tentatives", [])) > 1:
            st.markdown("**Historique des tentatives de génération :**")
            for h in section["historique_tentatives"]:
                icone = "✅" if h["statut"] == "verifie" else "⚠️"
                st.markdown(f"{icone} Tentative {h['tentative']} — statut : `{h['statut']}`"
                            + (f" — chiffres rejetés : {h['chiffres_non_verifies']}"
                               if h["chiffres_non_verifies"] else ""))
