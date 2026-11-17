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

La premiere publication utilise un depot prive. La validation distante et la
release seront referencees ici apres leur execution effective.
