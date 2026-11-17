# Livraison 1.0.0

Le projet local couvre les jalons M1 a M7 de la roadmap.

## Contenu du depot

- Code source, Docker Compose et exemples de configuration.
- Fixtures synthetiques, modeles dbt et definitions Dagster.
- Questions Metabase et configuration automatique du dashboard.
- Scripts de demarrage, demonstrations et tests d'integration.
- Runbook, diagramme d'architecture, explications d'entretien et rapports documentes.
- Workflow GitHub Actions reproduisant les controles sur une machine Linux isolee.

Le `.env`, les volumes Docker, `.tools` et les rapports locaux `.local` sont exclus
du depot. Les secrets CI sont generes sur le runner pour chaque execution.

## Publication distante

Depot prepare : https://github.com/moknihadil-eng/shoppulse-data-platform

La premiere publication utilise un depot prive.

## Validation distante reussie

- Workflow : [ShopPulse CI, run 44076721749](https://github.com/moknihadil-eng/shoppulse-data-platform/actions/runs/44076721749).
- Commit de code teste : `324dae46e4a6b47e0b8ebade03d8c7de769b05f2`.
- Execution du 17 novembre 2026, de 12:44:44 a 12:52:25 (UTC+1).
- Job `integration` : success ; toutes ses etapes ont reussi.
- Artefact `shoppulse-validation` : 1 083 308 octets, telecharge et inspecte.
- dbt : 62 tests passes, aucun echec, fraicheur valide.
- Metabase : six questions executees avec succes.
- Lancement Dagster distant : `f5c32ba7-1166-442f-a0cc-d15c2cac0132`, etats
  QUEUED, STARTING, STARTED, SUCCESS.
- Persistance M1, idempotence M2, SCD2, retries, backfill et rejets qualite verifies.
- Nettoyage des volumes du runner ephemere : success.

Les modifications de documentation posterieures enregistrent ces preuves sans
modifier le code valide. Le tag `v1.0.0` reference cette livraison documentee.

Release : https://github.com/moknihadil-eng/shoppulse-data-platform/releases/tag/v1.0.0

## Perimetre final

M1-M7 sont livres pour le portfolio local, avec depot Git, publication distante,
CI reussie et release versionnee. Les services de la CI sont ephemeres : cette
publication ne constitue pas un hebergement permanent de Metabase ou de Dagster.
Le deploiement cloud, Terraform et Kafka restent optionnels dans la roadmap.
