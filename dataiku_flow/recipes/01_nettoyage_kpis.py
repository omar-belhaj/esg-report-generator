"""
Recipe 01 — Nettoyage et structuration des KPIs bruts
======================================================
Correspond, dans le flow Dataiku, à un recipe "Prepare" (visual) suivi
d'un recipe Python pour les contrôles de cohérence qui sont plus simples
à exprimer en code qu'avec des steps visuels.

Entrée  : data/raw/kpis_esg.csv
Sortie  : data/processed/kpis_clean.csv

Étapes :
  1. Typage strict des colonnes (numérique, catégoriel)
  2. Suppression des doublons (kpi_id + annee)
  3. Contrôle des valeurs manquantes -> rejet avec log explicite
  4. Contrôle de cohérence des valeurs de `sens_amelioration` et `pilier`
  5. Normalisation des unités (trim, casse)

Dans le flow Dataiku réel, les steps 1/4/5 sont modélisés comme des steps
"Prepare" visuels (Change type, Filter, Find/Replace) ; les steps 2/3 sont
un recipe Python car ils nécessitent une logique de validation.
"""

import sys
import pandas as pd
from common import read_local, write_local

REQUIRED_COLUMNS = [
    "kpi_id", "pilier", "esrs_datapoint", "nom_indicateur",
    "annee", "valeur", "unite", "objectif_seuil", "sens_amelioration", "perimetre",
]
VALID_PILIERS = {"E1", "S1", "G1"}
VALID_SENS = {"hausse", "baisse"}


def nettoyer_kpis(df: pd.DataFrame) -> pd.DataFrame:
    # 1. Vérification du schéma
    missing_cols = set(REQUIRED_COLUMNS) - set(df.columns)
    if missing_cols:
        raise ValueError(f"Colonnes manquantes dans le dataset source : {missing_cols}")

    df = df[REQUIRED_COLUMNS].copy()

    # 2. Typage strict
    df["annee"] = pd.to_numeric(df["annee"], errors="coerce").astype("Int64")
    df["valeur"] = pd.to_numeric(df["valeur"], errors="coerce")
    df["objectif_seuil"] = pd.to_numeric(df["objectif_seuil"], errors="coerce")
    for col in ["kpi_id", "pilier", "esrs_datapoint", "nom_indicateur", "unite", "sens_amelioration", "perimetre"]:
        df[col] = df[col].astype(str).str.strip()

    # 3. Valeurs manquantes -> on rejette et on logue (pas de silent drop)
    n_before = len(df)
    lignes_invalides = df[df["valeur"].isna() | df["annee"].isna()]
    if len(lignes_invalides) > 0:
        print(f"[WARN] {len(lignes_invalides)} ligne(s) rejetée(s) pour valeur/année manquante :")
        print(lignes_invalides[["kpi_id", "annee"]].to_string(index=False))
    df = df.dropna(subset=["valeur", "annee"])

    # 4. Doublons (kpi_id, annee) : on garde la dernière occurrence
    n_dupes = df.duplicated(subset=["kpi_id", "annee"], keep="last").sum()
    if n_dupes > 0:
        print(f"[WARN] {n_dupes} doublon(s) (kpi_id, annee) détecté(s) — dernière valeur conservée.")
    df = df.drop_duplicates(subset=["kpi_id", "annee"], keep="last")

    # 5. Contrôle de cohérence référentielle
    piliers_invalides = set(df["pilier"].unique()) - VALID_PILIERS
    if piliers_invalides:
        raise ValueError(f"Pilier(s) ESRS invalide(s) détecté(s) : {piliers_invalides}")

    sens_invalides = set(df["sens_amelioration"].unique()) - VALID_SENS
    if sens_invalides:
        raise ValueError(f"Valeur(s) invalide(s) pour 'sens_amelioration' : {sens_invalides}")

    df["annee"] = df["annee"].astype(int)
    df = df.sort_values(["pilier", "kpi_id", "annee"]).reset_index(drop=True)

    print(f"[OK] Nettoyage terminé : {n_before} lignes en entrée -> {len(df)} lignes valides en sortie.")
    return df


def main():
    df_raw = read_local("kpis_esg.csv")
    df_clean = nettoyer_kpis(df_raw)
    out_path = write_local(df_clean, "kpis_clean.csv")
    print(f"[OK] Fichier écrit : {out_path}")


if __name__ == "__main__":
    main()
