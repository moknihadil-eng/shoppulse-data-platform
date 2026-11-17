# Runbook Windows / PowerShell

## Demarrer et executer toute la plateforme

Ouvrir Docker Desktop, attendre **Engine running**, puis depuis ce dossier :

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Start-ShopPulse.ps1
```

La commande configure les secrets manquants dans `.env`, construit les images,
initialise M1 sans effacer les donnees, execute ingestion / chargement bronze /
fraicheur / dbt / tests, puis demarre Dagster, Metabase et la documentation.
La compilation MinIO est longue au premier lancement ; les suivants utilisent
le cache. Le script arrete son execution des qu'une commande echoue.

Une fois les images construites, ajouter `-SkipBuild`. Pour travailler sans BI
et consommer moins de memoire, ajouter `-SkipBI` ; Metabase peut etre demarre plus
tard. Ne pas lancer plusieurs tests de demonstration simultanement.

| Interface | URL | Identification |
|---|---|---|
| Dagster | http://localhost:3000 | Locale, sans compte |
| Metabase | http://localhost:3001 | METABASE_ADMIN_EMAIL / METABASE_ADMIN_PASSWORD du .env |
| MinIO | http://localhost:9001 | MINIO_ROOT_USER / MINIO_ROOT_PASSWORD du .env |
| dbt docs / lineage | http://localhost:8081 | Locale, sans compte |

Les ports Windows PostgreSQL sont 5432 (source) et 5433 (warehouse). Le reseau
Docker utilise respectivement `postgres:5432` et `warehouse:5432`.
La base de configuration de Metabase n'expose pas de port Windows.

## Executer et observer

```powershell
docker compose ps
docker compose run --rm platform run
docker compose logs --tail 100 dagster
docker compose run --rm --entrypoint python ingestion status.py
```

Dans Dagster, ouvrir **Runs** pour voir les etapes, logs, retries et echecs.
Le job `shoppulse_pipeline` est planifie toutes les heures a la minute 0 UTC.
Le daemon est inclus dans `dagster dev` : Docker Desktop et le conteneur Dagster
doivent rester actifs. Le stockage des runs est persistant dans `dagster_data`.
Le deployement local utilise le serveur de developpement Dagster ; une production
exigerait des services daemon/webserver distincts, une base de metadonnees partagee,
authentification et gestion de secrets externe.

Les executants manuels et planifies utilisent un verrou PostgreSQL de session
sur le warehouse. Les jobs dbt ne s'executent pas simultanement. Le verrou source
M2 reste distinct et protege le checkpoint d'ingestion.

Les rapports sont dans `.local/reports` : `quality-report.json`, `verification.json`,
rapports dbt, logs, preuves de rejet qualite et `customer_features.csv`.
Les rapports qualite reussis sont aussi deposes dans MinIO sous
`_metadata/platform/quality/`. Dagster reste la reference pour les runs echoues.

Le chemin de lancement par la file et le daemon peut etre verifie separement,
avec les interfaces deja demarrees :

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Test-Deployment.ps1
```

Ce test soumet le job via l'API GraphQL Dagster, attend son execution par le daemon,
puis controle les endpoints Metabase, MinIO et documentation. Il conserve les
etats observes et l'ID du run dans `.local/reports/deployment.json`.

## Demonstration avec une nouvelle commande

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Demo-NewOrder.ps1
```

La commande synthetique 9001 ajoute une vente payee de 20 EUR. Son identifiant est
fixe : rejouer la demo ne la duplique pas. La source et les faits passent de 20 a
21 commandes, les lignes de 40 a 41, les paiements de 20 a 21. Le chiffre d'affaires
paye passe de 1520 a 1540 EUR. Les revisions historiques clients restent conservees.
Actualiser le dashboard Metabase apres le run. La demo conserve cette nouvelle
commande ; elle ne la supprime pas, puisque les suppressions ne sont pas ingerees.

## Backfill sur une plage de dates

```powershell
docker compose run --rm platform backfill --start 2027-01-02 --end 2027-01-03
```

Les bornes sont inclusives. Le job rejoue une partition Dagster par jour et
recalcule uniquement les agregats `daily_sales` de cette date par delete+insert.
Il charge d'abord les revisions raw connues. Ce backfill s'appuie sur l'historique
deja conserve ; il ne fabrique pas d'etats source perdus avant le debut du projet.
Les dates de janvier 2027 sont des partitions statiques pour la simulation, afin
de pouvoir les rejouer meme si l'horloge Windows est encore en 2026.

## Verifier la plateforme et demontrer une erreur

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Test-Platform.ps1
```

Le test ajoute une revision du client synthetique 1 et conserve ce changement.
Il verifie les faits, le chiffre d'affaires, l'idempotence, la SCD2, le backfill,
une erreur transitoire avec retry reussi, un paiement negatif rejete et une
source volontairement vieillie de 48 heures. Les donnees invalides temporaires
et la fausse fraicheur sont nettoyees avant le run final sain.

Pour montrer uniquement l'echec attendu dans Dagster :

```powershell
docker compose run --rm platform quality-demo
```

Cette commande **doit retourner 1** et le job `quality_failure_demo` doit apparaitre
en echec : c'est la preuve du rejet, pas une panne inattendue. Un paiement -5 EUR
avec une commande inexistante est injecte dans bronze, car les contraintes de la
base operationnelle interdiraient deja cette ligne. Le test `positive_payments`
et les relations dbt le detectent. Le nettoyage a lieu dans `finally`, sans
modifier les sources ni les objets raw MinIO. Ne pas interrompre volontairement
ce test ; en cas d'arret brutal, nettoyer la cle `_quality_demo/negative_payment`
dans bronze avant de relancer le pipeline. Le test integral verifie le nettoyage.

```powershell
docker compose run --rm platform retry-demo
docker compose run --rm platform run
```

La premiere commande doit reussir apres un seul retry intentionnel. La seconde
restaure les artefacts dbt et le rapport qualite de la chaine normale.

## Metabase

Le bootstrap cree un dashboard a six questions et execute chacune via l'API pour
verifier que les requetes fonctionnent. Il est rejouable : un dashboard existant
n'est pas duplique. La connexion utilise `metabase_reader`, autorise seulement a
lire le schema `marts`. Les tables bronze et la source ne sont pas exposees.

```powershell
docker compose run --rm platform metabase
```

Ouvrir le dashboard indique dans `.local/reports/metabase.json`. Les deux cartes
KPI affichent le nombre de commandes et le chiffre d'affaires effectivement paye ;
les autres montrent les ventes quotidiennes, produits, paiements et features.
La table de features est une demonstration a date de reference **2027-01-04** :
elle ne contient ni label cible ni modele ML entraine. Ne pas prendre une date
future comme reference en production ; passer explicitement la date d'observation.

## Arret, persistance et incidents

```powershell
docker compose stop
docker compose up -d --wait postgres minio warehouse source-api dagster metabase dbt-docs
```

Les cinq volumes nommes conservent source, raw, warehouse, runs Dagster et
configuration Metabase. `docker compose down` conserve aussi ces volumes.
**Ne pas utiliser `down -v` sur le PC pour un arret normal** : cela les supprime.
Le workflow CI utilise cette commande seulement pour ses donnees ephemeres.
Les volumes ne sont pas des sauvegardes contre une panne disque.

Si le moteur ne repond pas, ouvrir Docker Desktop. Si un port est occupe, changer
le port correspondant dans `.env` puis recreer le service ; le port docs 8081 est
fixe dans Compose. Les liens affiches par le script utilisent les ports par defaut.
Si Metabase manque de memoire, stopper temporairement les services BI et consulter
`docker compose logs --tail 100 metabase`. Le heap Java est limite a 384 Mo et
deux processeurs, avec des limites memoire Compose pour Metabase, Dagster et les
jobs. Sur ce PC de 8 Go, le script arrete temporairement les interfaces pendant
la construction et les transformations, puis les relance. Les tests complets
utilisent la meme precaution pour eviter les pics de consommation simultanes.
La premiere installation peut demander plusieurs Go de disque et de la patience.

Un echec d'ingestion conserve le checkpoint precedent. Rejouer `platform run`
reutilise les objets deja deposes. Un echec de build dbt peut avoir reconstruit
certains modeles : le dashboard peut momentanement lire une version partielle.
Le projet local ne fournit pas de publication atomique de tous les marts ; une
production utiliserait un schema de publication et un basculement apres validation.
