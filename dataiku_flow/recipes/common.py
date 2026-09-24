"""
common.py
---------
Petite couche d'abstraction pour que les recipes du flow puissent tourner :
  - soit DANS Dataiku (comme un recipe Python classique, via dataiku.Dataset)
  - soit EN LOCAL (hors Dataiku), pour la démo/portfolio, via des fichiers CSV

Cela permet de committer un code de recipe qui est un copier-coller fidèle
de ce qui tourne réellement dans le flow visuel Dataiku, tout en gardant
le projet exécutable sans instance Dataiku pour un reviewer externe.

Dans Dataiku, on remplacerait simplement les appels `read_local` / `write_local`
par :
    import dataiku
    df = dataiku.Dataset("nom_du_dataset").get_dataframe()
    dataiku.Dataset("nom_du_dataset_sortie").write_with_schema(df)
"""

import os
import pandas as pd

# Racine du projet (2 niveaux au-dessus de dataiku_flow/recipes/)
PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)
DATA_RAW = os.path.join(PROJECT_ROOT, "data", "raw")
DATA_PROCESSED = os.path.join(PROJECT_ROOT, "data", "processed")


def read_local(filename: str, folder: str = DATA_RAW) -> pd.DataFrame:
    """Lit un CSV du dossier data/raw ou data/processed."""
    path = os.path.join(folder, filename)
    return pd.read_csv(path)


def write_local(df: pd.DataFrame, filename: str, folder: str = DATA_PROCESSED) -> str:
    """Écrit un CSV dans data/processed (équivalent d'un dataset de sortie Dataiku)."""
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, filename)
    df.to_csv(path, index=False)
    return path


def running_in_dataiku() -> bool:
    """Détecte si on tourne dans un environnement Dataiku (package dataiku dispo)."""
    try:
        import dataiku  # noqa: F401
        return True
    except ImportError:
        return False
