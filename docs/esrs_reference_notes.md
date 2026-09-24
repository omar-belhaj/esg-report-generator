# Notes de référence — Taxonomie ESRS

## ⚠️ Avertissement important

Le mapping ESRS utilisé dans ce projet (`data/raw/mapping_esrs.csv`) est
**volontairement simplifié à des fins de démonstration**. Il illustre le
*principe* du mapping KPI → datapoint ESRS dans un pipeline de données, mais :

- Il ne couvre qu'un sous-ensemble restreint de datapoints (7 codes, contre
  plusieurs centaines dans le standard complet).
- Certains regroupements sont approximatifs (ex. la mixité au board et la
  mixité des effectifs sont toutes deux rattachées à `S1-9` par simplicité,
  alors qu'une application stricte du standard distinguerait plus finement
  les exigences de S1 et de G1 sur ce point).
- Les descriptions dans `description_officielle` sont des **paraphrases
  pédagogiques**, pas des citations du texte réglementaire.

**Ce projet ne doit pas être utilisé comme référence de conformité ESRS.**
Pour un usage réel, le mapping doit être validé avec :
- Le texte officiel des normes ESRS (règlement délégué UE 2023/2772 et ses
  annexes),
- Un expert conformité / CSRD,
- Les guides d'application publiés par l'EFRAG.

## Piliers couverts dans ce projet

| Pilier | Nom | Datapoints illustrés ici |
|---|---|---|
| E1 | Changement climatique | E1-5 (énergie), E1-6 (émissions GES) |
| S1 | Effectifs propres | S1-6 (effectifs), S1-9 (diversité), S1-13 (formation), S1-14 (santé/sécurité) |
| G1 | Conduite des affaires | G1-1 (gouvernance / anti-corruption) |

## Pourquoi ce périmètre volontairement restreint

L'objectif du projet est de démontrer un **pipeline de bout en bout**
(nettoyage → mapping → génération → vérification → publication), pas de
produire un outil de reporting CSRD exhaustif. Un périmètre de 15 KPIs sur 3
piliers permet de garder le dataset lisible pour la review tout en couvrant
des cas réalistes et variés (valeurs à la hausse et à la baisse, objectifs
atteints et non atteints, un KPI à valeur nulle constante pour tester les
cas limites du contrôle anti-hallucination).
