# Flow Dataiku — `esg-report-generator`

Ce dossier documente le **flow visuel Dataiku** dont ce projet est une
transposition exécutable hors Dataiku (pour permettre à un reviewer externe,
sans instance Dataiku, de lancer le pipeline).

## Vue d'ensemble du flow

```
[kpis_esg (CSV)] ──┐
                    ├──> (Prepare) ──> (Python: contrôles) ──> [kpis_clean]
                    │
[mapping_esrs (CSV)]│
                    │
[contexte_qualitatif]
        │
        ▼
  kpis_clean ──> (Window: shift N-1 par kpi_id) ──> (Formula: variation_pct,
                  ecart_objectif_pct, statut_vs_objectif) ──> [kpis_yoy]

  kpis_yoy ──(Join sur esrs_datapoint)──> mapping_esrs
           ──(Join sur kpi_id+annee)──> contexte_qualitatif
           ──> [kpis_enrichis]   <-- dataset final consommé par la génération LLM
```

## Recipes du flow (correspondance avec `recipes/`)

| Recipe Dataiku (visuel) | Type | Fichier équivalent | Rôle |
|---|---|---|---|
| `nettoyage_kpis` | Prepare + Python | `01_nettoyage_kpis.py` | Typage, dédoublonnage, contrôle de cohérence référentielle (piliers ESRS valides, sens d'amélioration valide) |
| `calcul_yoy` | Window | `02_calcul_yoy_et_ecarts.py` (partie 1) | Décalage N-1 par `kpi_id`, trié par `annee` |
| `calcul_ecarts` | Formula | `02_calcul_yoy_et_ecarts.py` (partie 2) | `variation_pct`, `ecart_objectif_pct`, `statut_vs_objectif` |
| `mapping_esrs` | Join | `03_mapping_esrs.py` (partie 1) | Jointure sur `esrs_datapoint` avec le référentiel |
| `jointure_contexte` | Join | `03_mapping_esrs.py` (partie 2) | Jointure sur `(kpi_id, annee)` avec le contexte qualitatif |

Dans le vrai projet Dataiku, `01` correspond à un recipe **Prepare** (steps
visuels : Change type, Remove duplicate rows, Filter rows) complété par un
recipe **Python** pour les contrôles de cohérence trop spécifiques pour des
steps visuels standards (ex. validation des valeurs autorisées de
`sens_amelioration`). Les recipes `02` et `03` combinent respectivement un
**Window recipe** + un **Formula recipe**, et deux **Join recipes**, regroupés
ici en un seul fichier Python par souci de lisibilité pour la review du code.

## Pourquoi ce choix d'architecture

- **Window recipe pour le YoY** plutôt qu'un Self-Join : plus lisible dans le
  flow visuel, et évite un recipe supplémentaire.
- **Deux Join recipes séparés** (mapping ESRS, puis contexte qualitatif)
  plutôt qu'une jointure unique multi-clés : chaque recipe reste responsable
  d'une seule source de vérité, ce qui facilite le debug visuel dans
  Dataiku (on peut inspecter le résultat intermédiaire après chaque Join).
- **Sortie unique `kpis_enrichis`** : c'est le seul point de contact entre le
  flow de préparation de données et le module de génération LLM — toute
  logique de dérivation de KPI doit être ajoutée en amont de ce dataset, pas
  dans le code de génération.

## Reproduire le flow dans une instance Dataiku Free Edition

1. Créer un projet, importer les 3 CSV de `data/raw/` comme datasets.
2. Recréer les recipes ci-dessus dans l'ordre du tableau (Prepare → Window →
   Formula → Join × 2), en s'appuyant sur la logique documentée dans les
   fichiers `.py` correspondants (chaque fichier contient les règles exactes
   à reproduire visuellement, avec commentaires).
3. Brancher le dataset de sortie `kpis_enrichis` sur un recipe Python (ou un
   notebook) qui appelle `generation/generate_sections.py` avec
   `LLM_MODE=dataiku`, après avoir configuré une connexion LLM Mesh dans le
   projet et renseigné `DATAIKU_LLM_ID`.

## Export du projet

`project_export/` est l'emplacement prévu pour le fichier `.zip` d'export du
projet Dataiku réel (Project > Export), si vous souhaitez le partager tel
quel. Il n'est pas fourni dans cette version portfolio afin de ne pas lier le
repo à une instance Dataiku spécifique ; la logique équivalente est
entièrement reproductible via les scripts Python de ce dossier.
