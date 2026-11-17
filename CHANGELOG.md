# Historique des versions

## 1.0.0 — 17 novembre 2026

- Fondations locales Compose, PostgreSQL et MinIO avec donnees synthetiques.
- Ingestion incrementale base/API/CSV, checkpoints et reprises idempotentes.
- Warehouse separe, 18 modeles dbt et dimension client SCD Type 2.
- Orchestration Dagster, planning horaire, retries et backfill par dates.
- 62 tests dbt, fraicheur, rapports et demonstrations d'erreurs controlees.
- Dashboard Metabase a six questions et features clients exportables.
- Scripts PowerShell, documentation, lineage et workflow GitHub Actions.

La CI GitHub Actions du 17 novembre 2026 a reussi : 62 tests et six questions
Metabase valides, avec execution du pipeline par le daemon Dagster. La preuve
distante et la reference exacte du commit teste figurent dans `docs/release.md`.
