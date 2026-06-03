# Résultats de la pipeline hybride par familles de graphes

Ce dossier contient les sorties de l'expérience récente de la pipeline hybride complète appliquée sur des graphes de taille $n=4$ par famille.

## Objectif

L'objectif est de vérifier si les familles de graphes qui sont favorables au mapping géométrique restent aussi favorables après la pipeline complète :
- préparation Pulser,
- extraction des corrélations,
- résolution SDP,
- rounding produit,
- sélection finale hybride (`ratio_hybrid = max(ratio_pulser, ratio_product)`).

## Commande de reproduction

```bash
python scripts/run_graph_family_full_pipeline.py --n 4 --num-instances 100 --seed 123
```

## Contenu principal

- `summary_by_family.csv` : résumé statistique par famille de graphes.
- `all_instances_results.csv` : données détaillées instance par instance.
- `ratio_hybrid_by_graph_family.png` : ratio hybride moyen par famille.
- `gain_by_graph_family.png` : gain moyen de la sélection hybride par rapport à Pulser.
- `pulser_vs_hybrid_by_family.png` : comparaison Pulser vs Hybrid par famille.
- `mapping_error_by_family_full_pipeline.png` : erreur de mapping moyenne par famille.
- `ratio_vs_mapping_error_by_family.png` : relation ratio / erreur de mapping par famille.

## Notes

- Les données sont issues de 100 instances par famille pour $n=4$.
- L'analyse reste exploratoire et ne doit pas être considérée comme une preuve définitive pour des tailles plus larges.
