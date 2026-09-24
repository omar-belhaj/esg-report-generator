# Étude de cas — Limites observées du contrôle anti-hallucination

Ce document consigne un test réel effectué avec `LLM_MODE=ollama` et le modèle
`llama3.2:3b` sur le rapport 2025. Les 3 sections ont été marquées **✅ Vérifié**
par le système, mais une relecture manuelle a révélé 3 erreurs factuelles que
le contrôle actuel ne détecte pas. Ce cas est conservé tel quel comme preuve
que le système a été testé en conditions réelles (pas seulement en mode démo)
et que ses limites sont connues, comprises et assumées — pas découvertes après
coup.

## Les 3 erreurs identifiées

| # | Texte généré par Llama | Donnée réelle (source) | Pourquoi le contrôle actuel ne l'attrape pas |
|---|---|---|---|
| 1 | « en 2024, l'effectif comptait **2010** personnes » | 2024 = **1920** ; 2010 est la valeur de **2025** | Le contrôle vérifie qu'un chiffre existe *quelque part* dans les valeurs autorisées de la section (toutes années confondues), pas qu'il est associé à la bonne année dans la phrase. `2010` est une valeur légitime du dataset (celle de 2025) → validé à tort pour 2024. |
| 2 | taux de gravité « 0,29 jours perdus/**million d'heures** travaillées » | unité réelle : « jours perdus/**1000h** travaillées » | Le contrôle (`number_extractor.py` + `cross_checker.py`) ne compare que des **valeurs numériques**, jamais les **unités** qui les accompagnent. Le chiffre 0,29 est correct, l'unité est fausse — non détecté. |
| 3 | « le dispositif d'alerte interne... mis en place en **2025** » | Le contexte source indique **2022** | Le contrôle **exclut délibérément** les années isolées (2023/2024/2025) de la vérification (`exclure_annees_isolees()`), pour éviter de flaguer à tort des phrases légitimes du type « en 2025, la valeur était X ». Cette exclusion, utile pour réduire les faux positifs, laisse ici passer une vraie date erronée dans le contexte qualitatif. |

## Ce que ça confirme

Le contrôle actuel répond bien à sa mission déclarée : **vérifier que chaque
valeur numérique de KPI citée correspond à une donnée source** — et sur ce
plan précis, il n'a laissé passer aucune erreur dans ce test (tous les
chiffres de KPI cités, ex. 25800 MWh, 4820 tCO2eq, 8,3 accidents/million
d'heures, 96%, etc., étaient exacts).

Ce qu'il ne couvre pas, et qui reste donc à la charge d'une revue humaine :
- L'**association correcte** entre une valeur et l'année à laquelle elle se
  rapporte quand plusieurs années sont mentionnées dans la même phrase.
- La **cohérence des unités** entourant un chiffre.
- Les faits/dates mentionnés dans le **contexte qualitatif en texte libre**
  (par opposition aux valeurs structurées du tableau de KPIs), qui ne sont
  pas dans le périmètre du dataset numérique contrôlé.

## Pistes d'amélioration identifiées (non implémentées)

1. **Vérification d'unité** : extraire l'unité présente à proximité de
   chaque chiffre et la comparer à l'unité source attendue pour ce KPI.
2. **Vérification année-valeur appariée** : quand le texte associe
   explicitement un chiffre à une année (« en 2024, X = ... »), vérifier que
   cette paire *(année, valeur)* correspond à la ligne source de cette année
   précise, plutôt que d'accepter toute valeur présente ailleurs dans la
   section.
3. La détection de dates erronées dans le contexte qualitatif en texte libre
   nécessiterait une extraction d'entités plus poussée (NER) et sort du
   périmètre d'un contrôle purement numérique — laissée comme limite assumée.

Voir aussi `README.md` (section "Limites connues et pistes d'amélioration")
et `verification/cross_checker.py` (section "Limite assumée" du README
principal du projet). La sortie brute complète de ce test est conservée dans
`docs/exemples/sortie_ollama_llama3.2-3b_2025.txt`, avec les 3 erreurs
annotées directement dans le texte.
