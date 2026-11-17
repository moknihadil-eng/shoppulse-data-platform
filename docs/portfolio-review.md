# Revue du portfolio GitHub — 17 novembre 2026

## Vue recruteur

Le profil [moknihadil-eng](https://github.com/moknihadil-eng) presente maintenant
deux projets complementaires dans un README public de profil :

| Projet | Objectif | Acces au moment de la revue |
|---|---|---|
| Revenue & Retention Analytics | Analyse de revenus, cohortes et segmentation RFM sur des transactions reelles | Public |
| ShopPulse — Modern Data Platform | Ingestion, warehouse, orchestration, qualite et BI sur des donnees synthetiques | Prive, acces sur invitation |

La page ne presente pas les donnees synthetiques de ShopPulse comme des resultats
de production. Elle distingue aussi les resultats descriptifs de l'analyse retail
d'une prevision ou d'un impact business mesure.

## Ameliorations publiees

- README de profil avec projets, objectifs, stack, preuves et liens directs.
- Descriptions About et topics coherents sur les deux depots.
- Analytics : apercu du dashboard et indicateurs avant les instructions techniques.
  Les details d'execution et d'analyse sont repliables ; les blocs de resultats
  generes sont conserves sans modification de leur contenu.
- ShopPulse : vue en 30 secondes, preuves liees au code, schema Mermaid et guide
  des dossiers avant les commandes de demarrage.

Les chemins et programmes n'ont pas ete renommes : l'organisation technique
existante et les commandes restent compatibles. Seules la documentation et les
metadonnees de presentation ont ete modifiees.

## Verifications

- Controle du profil public dans Edge headless avec un profil temporaire sans connexion.
- Verification des README apres publication par l'API GitHub.
- Verification de l'integrite des resultats Analytics et des liens locaux ShopPulse.
- Confirmation de la presence du fichier dashboard.png utilise pour l'apercu.
- Captures de controle conservees dans `.local/portfolio/screenshots`, exclu de Git.

## Points restant a regler dans le profil

La bio actuelle contient du Markdown qui s'affiche comme du texte brut. La
modification via l'API `/user` a retourne 404 avec l'acces disponible ; elle n'a
donc pas ete appliquee. Dans **Edit profile**, utiliser une bio simple, par exemple :

> Software engineering student | Data Engineering & Analytics | Python, SQL, dbt, Dagster | Reproducible data projects.

Aucun depot n'etait epingle lors de la revue. Utiliser **Customize your pins**
pour mettre Revenue & Retention en avant, puis ShopPulse lorsqu'il sera public.
Les instructions sont dans la [documentation GitHub](https://docs.github.com/en/account-and-profile/how-tos/profile-customization/pinning-items-to-your-profile).

ShopPulse reste prive : les visiteurs non invites ne peuvent pas lire son code.
Son passage en public est une decision de visibilite distincte de cette revue.
