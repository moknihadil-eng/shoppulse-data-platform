# ShopPulse – Modern Data Platform

[![ShopPulse CI](https://github.com/moknihadil-eng/shoppulse-data-platform/actions/workflows/ci.yml/badge.svg)](https://github.com/moknihadil-eng/shoppulse-data-platform/actions/workflows/ci.yml)

Plateforme Data Engineering locale pour une boutique e-commerce, d'après les
pages 4 et 5 de la roadmap 2027. Les sept jalons sont implémentés ; les preuves
locales figurent dans les rapports de validation. Les sources sont synthétiques.

## Démarrer avec une commande PowerShell

Ouvrir Docker Desktop et attendre **Engine running**, puis dans ce dossier :

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Start-ShopPulse.ps1
```

Le premier démarrage construit les images, crée un `.env` avec des secrets locaux,
initialise PostgreSQL/MinIO, exécute le pipeline et crée le dashboard. Le `.env`
existant est conservé et complété si nécessaire. MinIO est compilé depuis une
version officielle fixe ; cette première construction peut prendre plusieurs minutes.
Aucune installation Python, dbt ou Dagster sur Windows n'est nécessaire.

Pour les démarrages suivants, ajouter `-SkipBuild`. Pour travailler sans Metabase,
ajouter `-SkipBI`. Les commandes détaillées sont dans le [runbook](docs/runbook.md).

## Ouvrir les interfaces

| Outil | URL | Identifiants |
|---|---|---|
| Metabase | http://localhost:3001/dashboard/2 | METABASE_ADMIN_EMAIL / METABASE_ADMIN_PASSWORD du .env |
| Dagster | http://localhost:3000 | Pas de compte pour cette instance locale |
| MinIO | http://localhost:9001 | MINIO_ROOT_USER / MINIO_ROOT_PASSWORD du .env |
| Documentation et lineage dbt | http://localhost:8081 | Pas de compte |

L'identifiant du dashboard peut changer sur une installation neuve : son URL exacte
est enregistrée dans `.local/reports/metabase.json`. Les ports Windows sont limités
à `127.0.0.1`. La source PostgreSQL écoute sur 5432, le warehouse sur 5433.

## Jalons livrés

| Jalon | Livraison |
|---|---|
| M1 | Compose, source PostgreSQL, MinIO, données reproductibles et volumes persistants |
| M2 | Ingestion incrémentale PostgreSQL + API paginée + CSV, manifestes et checkpoints |
| M3 | 18 modèles dbt staging/intermediate/marts, étoile, dimension client SCD Type 2 |
| M4 | Dagster horaire, runs persistants, retries, backfill par plage de dates |
| M5 | 62 tests dbt, fraîcheur, rapport qualité, démonstrations de rejet et de reprise |
| M6 | Dashboard Metabase à six questions, compte BI en lecture seule, features clients exportables |
| M7 | Workflow GitHub Actions, scripts PowerShell, diagramme, lineage, démo et runbook |

Le workflow CI est prêt pour les pull requests et la branche principale. Les
vérifications ont été exécutées localement ; aucune exécution GitHub ni aucun
déploiement cloud n'est revendiqué avant publication dans un dépôt distant.
Le workflow inclut un déploiement local éphémère et un test des interfaces.

## Ce que fait le pipeline

1. Extraire les changements des cinq tables PostgreSQL et de l'API, comparer le CSV.
2. Déposer des versions brutes immuables dans MinIO, avec clés déterministes.
3. Charger uniquement les versions non encore connues dans le warehouse bronze.
4. Contrôler la fraîcheur, typer/dédupliquer en staging et calculer les intermédiaires.
5. Construire les dimensions/faits/marts et exécuter les tests dbt.
6. Publier les rapports qualité, la documentation et le CSV de features.

Dagster lance cette chaîne toutes les heures à la minute 0 UTC. La base opérationnelle
et le warehouse sont séparés. Metabase lit seulement le schéma `marts` du warehouse.
MinIO conserve les extractions brutes, leur historique et les métadonnées de runs.

La fixture M1 comprend 10 clients, 5 produits, 20 commandes, 40 lignes et 20 paiements.
La démo ajoute la commande stable 9001 : après son exécution, la boutique contient
21 commandes, 41 lignes et 21 paiements. Les versions SCD2 supplémentaires sont de
l'historique, pas des doublons de clients. Les dates métier de janvier 2027 sont fictives.
La fraîcheur mesure les extractions réellement réussies ; les features utilisent une
date de référence explicite du 4 janvier 2027, avec une fenêtre de 30 jours antérieurs.

## Vérifier et démontrer

```powershell
# Exécution normale
 docker compose run --rm platform run

# Suite complète : rejeu, SCD2, backfill, retry, erreur qualité, source périmée
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Test-Platform.ps1

# Nouvelle commande : rejouable, une seule commande supplémentaire
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Demo-NewOrder.ps1

# Recalcul des agrégats journaliers depuis l'historique retenu
 docker compose run --rm platform backfill --start 2027-01-02 --end 2027-01-03

# Démonstration d'un rejet : le code de sortie 1 est attendu
 docker compose run --rm platform quality-demo

# Voir l'état des services
 docker compose ps

# Vérifier le lancement par le daemon Dagster et les interfaces
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Test-Deployment.ps1
```

Le test de qualité temporaire nettoie la mauvaise ligne. Après une démonstration
isolée, relancer `platform run` pour régénérer les rapports du chemin sain.
Les tests complets modifient le pays d'un client synthétique pour prouver la SCD2.

Les résultats sont dans `.local/reports` : `quality-report.json`, `verification.json`,
rapports dbt, preuves des rejets, logs, documentation et `customer_features.csv`.
Ce dossier et le `.env` sont exclus de Git. Le dépôt contient seulement `.env.example`.
Les dépendances de la plateforme sont verrouillées dans `platform/requirements.lock.txt`.

## Documentation

- [Architecture et grains des tables](docs/architecture.md)
- [Runbook PowerShell et incidents](docs/runbook.md)
- [Explications pour l'entretien](docs/interview.md)
- [Résultats de validation M1–M7](docs/platform-verification.md)
- [Détails de l'ingestion M2](docs/m2-ingestion.md)
- [Validation historique M1](docs/m1-verification.md) et [M2](docs/m2-verification.md)
- [Références techniques](docs/references.md)

## Limites de cette version portfolio

Les suppressions et les transactions source très tardives demanderaient du CDC ou
une réconciliation. Les objets par révision et les chargements en mémoire conviennent
à la petite démo. Le backfill rejoue l'historique déjà retenu, sans reconstituer des
états jamais extraits. La SCD2 ne connaît que les changements effectivement observés.
Les marts ne sont pas publiés par une transaction globale ; un échec dbt peut laisser
une publication partielle jusqu'au rejeu. Dagster utilise son serveur de développement
local et Metabase n'est exposé que sur le PC. Cette livraison n'est pas un déploiement
production. Kafka, Terraform et le warehouse cloud sont des extensions optionnelles.

Pour arrêter sans perdre les données : `docker compose stop` ou `docker compose down`.
Ne pas ajouter `-v` : cette option supprime les volumes et leurs données.
