"""
Recipe 02 — Calcul des variations YoY et des écarts par rapport aux objectifs
==============================================================================
Correspond, dans le flow Dataiku, à un recipe "Window" (pour le décalage
année N-1 par kpi_id) suivi d'un recipe "Formula" (pour variation_pct et
statut_vs_objectif). Regroupé ici en un seul recipe Python pour la lisibilité
du portfolio.

Entrée  : data/processed/kpis_clean.csv
Sortie  : data/processed/kpis_yoy.csv

Colonnes ajoutées :
  - valeur_n1          : valeur de l'année précédente pour le même kpi_id
  - variation_pct       : variation relative (%) vs année précédente
  - ecart_objectif_pct  : écart relatif (%) vs objectif_seuil
  - statut_vs_objectif  : "atteint" / "au-dessus" / "en-deça"
                           (la sémantique dépend de sens_amelioration)
"""

import numpy as np
import pandas as pd
from common import read_local, write_local


def calculer_yoy(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values(["kpi_id", "annee"]).copy()

    # Décalage N-1 par kpi_id (équivalent d'un recipe "Window" avec partition=kpi_id, order=annee)
    df["valeur_n1"] = df.groupby("kpi_id")["valeur"].shift(1)

    # Variation YoY en %
    df["variation_pct"] = np.where(
        df["valeur_n1"].notna() & (df["valeur_n1"] != 0),
        ((df["valeur"] - df["valeur_n1"]) / df["valeur_n1"]) * 100,
        np.nan,
    )
    df["variation_pct"] = df["variation_pct"].round(2)

    # Écart par rapport à l'objectif
    df["ecart_objectif_pct"] = np.where(
        df["objectif_seuil"] != 0,
        ((df["valeur"] - df["objectif_seuil"]) / df["objectif_seuil"]) * 100,
        np.nan,
    )
    df["ecart_objectif_pct"] = df["ecart_objectif_pct"].round(2)

    df["statut_vs_objectif"] = df.apply(_statut_vs_objectif, axis=1)

    return df.reset_index(drop=True)


def _statut_vs_objectif(row) -> str:
    """
    Détermine le statut par rapport à l'objectif, en tenant compte du sens
    d'amélioration (ex : pour les émissions, une valeur plus BASSE est meilleure ;
    pour la part de femmes au board, une valeur plus HAUTE est meilleure).
    """
    valeur = row["valeur"]
    objectif = row["objectif_seuil"]
    sens = row["sens_amelioration"]

    if pd.isna(valeur) or pd.isna(objectif):
        return "non_evaluable"

    if sens == "baisse":
        if valeur <= objectif:
            return "atteint"
        return "au-dessus"
    else:  # sens == "hausse"
        if valeur >= objectif:
            return "atteint"
        return "en-deça"


def main():
    from common import DATA_PROCESSED
    df_clean = read_local("kpis_clean.csv", folder=DATA_PROCESSED)
    df_yoy = calculer_yoy(df_clean)
    out_path = write_local(df_yoy, "kpis_yoy.csv")

    n_atteints = (df_yoy["statut_vs_objectif"] == "atteint").sum()
    print(f"[OK] YoY calculé pour {len(df_yoy)} lignes. {n_atteints} indicateur(s) au statut 'atteint'.")
    print(f"[OK] Fichier écrit : {out_path}")


if __name__ == "__main__":
    main()
