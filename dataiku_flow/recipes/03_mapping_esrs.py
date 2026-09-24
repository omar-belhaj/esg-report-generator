"""
Recipe 03 — Mapping ESRS + jointure du contexte qualitatif
=============================================================
Correspond, dans le flow Dataiku, à deux recipes "Join" visuels :
  (a) kpis_yoy x mapping_esrs   sur esrs_datapoint
  (b) résultat x contexte_qualitatif   sur (kpi_id, annee)

Entrées :
  - data/processed/kpis_yoy.csv
  - data/raw/mapping_esrs.csv
  - data/raw/contexte_qualitatif.csv

Sortie :
  - data/processed/kpis_enrichis.csv   <- dataset final consommé par le
    module de génération LLM et par le dashboard Streamlit.
"""

import pandas as pd
from common import read_local, write_local, DATA_PROCESSED


def enrichir(df_yoy: pd.DataFrame, df_mapping: pd.DataFrame, df_contexte: pd.DataFrame) -> pd.DataFrame:
    # (a) Jointure avec le référentiel ESRS -> ajoute esrs_section, description_officielle, type_obligation
    df = df_yoy.merge(df_mapping, on="esrs_datapoint", how="left")

    n_non_mappes = df["esrs_section"].isna().sum()
    if n_non_mappes > 0:
        codes_non_mappes = df[df["esrs_section"].isna()]["esrs_datapoint"].unique()
        print(f"[WARN] {n_non_mappes} ligne(s) sans mapping ESRS trouvé. Codes concernés : {list(codes_non_mappes)}")

    # (b) Jointure avec le contexte qualitatif (texte libre), clé (kpi_id, annee)
    df = df.merge(
        df_contexte[["kpi_id", "annee", "texte_contexte", "source_interne"]],
        on=["kpi_id", "annee"],
        how="left",
    )

    n_sans_contexte = df["texte_contexte"].isna().sum()
    if n_sans_contexte > 0:
        print(f"[INFO] {n_sans_contexte} ligne(s) sans contexte qualitatif associé (normal pour les années "
              f"non couvertes par le contexte, ex. historique 2023/2024).")

    # Réordonnancement des colonnes pour lisibilité
    colonnes_ordre = [
        "pilier", "esrs_datapoint", "esrs_section", "kpi_id", "nom_indicateur",
        "annee", "valeur", "valeur_n1", "variation_pct", "unite",
        "objectif_seuil", "ecart_objectif_pct", "statut_vs_objectif", "sens_amelioration",
        "perimetre", "type_obligation", "description_officielle",
        "texte_contexte", "source_interne",
    ]
    colonnes_ordre = [c for c in colonnes_ordre if c in df.columns]
    df = df[colonnes_ordre].sort_values(["pilier", "kpi_id", "annee"]).reset_index(drop=True)
    return df


def main():
    df_yoy = read_local("kpis_yoy.csv", folder=DATA_PROCESSED)
    df_mapping = read_local("mapping_esrs.csv")
    df_contexte = read_local("contexte_qualitatif.csv")

    df_final = enrichir(df_yoy, df_mapping, df_contexte)
    out_path = write_local(df_final, "kpis_enrichis.csv")

    print(f"[OK] Dataset final enrichi : {len(df_final)} lignes, {df_final['pilier'].nunique()} piliers ESRS.")
    print(f"[OK] Fichier écrit : {out_path}")


if __name__ == "__main__":
    main()
