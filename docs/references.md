# References techniques

- [Docker Desktop Windows / WSL 2](https://docs.docker.com/desktop/setup/install/windows-install/)
- [dbt et PostgreSQL](https://docs.getdbt.com/docs/local/connect-data-platform/postgres-setup)
- [Historisation et choix entre incremental / snapshots](https://docs.getdbt.com/best-practices/how-we-handle-cdc/2-choosing-incremental-or-snapshots)
- [Dagster schedules](https://docs.dagster.io/guides/automate/schedules)
- [Metabase API](https://www.metabase.com/docs/latest/api)
- [Automatiser la configuration Metabase](https://www.metabase.com/articles/set-up-metabase-from-code-with-the-api)

Le modele SCD2 de ce projet est calcule par SQL sur les revisions raw, sans
snapshot dbt : ce choix permet de conserver les versions deja observees avant le
premier lancement dbt. Les docs dbt expliquent le besoin d'historisation ; le SQL
et les tests du depot constituent la specification du comportement livre.
