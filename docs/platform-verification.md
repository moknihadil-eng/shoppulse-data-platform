# Validation locale M1-M7 - 16 novembre 2026

Les sept jalons sont implementes et la chaine a ete executee localement. Le
workflow GitHub Actions est fourni ; aucun run distant n'est revendique, car
ce dossier n'a pas ete publie sur GitHub dans cette session.

## Resultats fonctionnels observes

| Controle | Resultat |
|---|---|
| M1 : comptages source et bucket | Valides ; fixture initiale de 20 commandes |
| M1 : recréation des conteneurs | Cinq tables identiques et objet MinIO conserve |
| M2 : PostgreSQL / API / CSV | Charges dans raw, metadonnees et checkpoint disponibles |
| M2 : rejeu / echec partiel | Aucun doublon et checkpoint non avance sur echec |
| M3 : dbt | 18 modeles construits ; staging, intermediate et marts |
| M3 : dimension client SCD2 | 15 versions observees, 10 clients courants |
| M3 : mutation client | Exactement une nouvelle version, intervalles valides |
| M4 : planning | shoppulse_pipeline_schedule confirme RUNNING via GraphQL |
| M4 : daemon | Heartbeats SCHEDULER, BACKFILL et QUEUED_RUN_COORDINATOR observes |
| M4 : backfill | 2 et 3 janvier 2027 rejoues ; agregats identiques |
| M4 : retry | Une erreur transitoire suivie d'un retry reussi |
| M5 : qualite | 62 tests dbt passes, aucun echec sur le run sain |
| M5 : paiement negatif | Rejete par positive_payments ; run demo en echec attendu |
| M5 : source vieillie de 48h | Echec de fraicheur observe puis nettoyage |
| M5 : droits BI | SELECT autorise, INSERT refuse au compte metabase_reader |
| M6 : dashboard | Six questions creees et executees avec succes via l'API |
| M6 : features | 10 lignes a la date de reference 2027-01-04, CSV exporte |
| M7 : nouvelle commande 9001 | Ingestion jusqu'aux faits et au dashboard, puis rejeu sans doublon |
| M7 : dependances | 109 versions gelees ; build contraint et pip check reussis |
| M7 : secrets | Aucun mot de passe reel du .env dans les fichiers du depot |

La suite d'integration a produit `verification.json` avec statut PASS, dont un run
`quality_failure_demo` attendu en FAILURE. Un premier build avait trouve un alias
SQL reserve dans dim_date ; il a ete corrige et tous les tests ont ensuite passe.

## Donnees finales apres la demonstration

Requete executee directement sur le warehouse apres reprise :

```text
orders_count | payments_count | line_count | feature_rows | paid_revenue_eur
          21 |             21 |         41 |           10 |          1540.00
```

La fixture initiale reste documentee dans les rapports M1/M2. La commande 9001
ajoute une ligne achetee et un paiement reussi de 20 EUR. Elle est conservee dans
la source et dans raw ; la supprimer physiquement n'est pas un mecanisme de demo.
Les verifications de fondation acceptent ces nouvelles lignes tout en exigeant
au minimum la fixture initiale et des empreintes identiques au rejeu/redemarrage.

## Ressources et reprise Docker

Ce PC dispose de 8 Go de RAM. Pendant le dernier build avec toutes les interfaces
actives, Docker/WSL a cesse de repondre. Un redemarrage normal a echoue ; les
processus Docker puis uniquement la distribution docker-desktop ont ete arretes,
sans suppression de volume. Docker a ete relance et les donnees ont ete retrouvees.

La configuration limite maintenant les jobs a 768 Mo, Dagster a 1024 Mo et
Metabase a 1280 Mo, avec deux CPU. Le heap Java est de 384 Mo. Le script de
demarrage separe les pics : interfaces stoppees, build/pipeline, puis interfaces.
Le script de tests utilise la meme precaution. Aucun changement de configuration
globale Windows/WSL ni aucune suppression de volume n'a ete effectue.

Le pipeline apres reprise a reussi, avec les memes 62 tests et la fraicheur au vert.
La reconstruction des dependances verrouillees a aussi reussi. Les artefacts
locaux distinguent le lancement interrompu (`start-script.log`) de la reprise
(`start-recovery.log`), afin de ne pas masquer l'incident.

Le script `Start-ShopPulse.ps1 -SkipBuild` a ensuite termine avec le code 0 :
pipeline sain, interfaces relancees et dashboard a six questions toujours valide.
Les requetes du dashboard ont donc ete reverifiees apres le redemarrage Docker.

Le test du lancement par le daemon a egalement termine avec le code 0 : le run
`0a62ad36-b925-4c00-9131-f7acb2109de1` est passe par QUEUED, STARTING, STARTED,
puis SUCCESS. Les endpoints Metabase, MinIO et documentation ont repondu 200.
Cette verification utilise l'API GraphQL et le lanceur reel du daemon, distinct
des tests CLI executes en processus local.

Apres la pause, le moteur Docker etait arrete puis son demarrage WSL est reste
bloque. La relance ciblee a permis de remettre les services en route sans effacer
de volume. Le script de reprise a termine avec le code 0 ; le rapport du
16 novembre a 16:34 UTC confirme 62 tests passes et la fraicheur valide. Les six
questions Metabase ont ete executees avec succes et les services applicatifs
avec healthchecks sont healthy. La trace est dans `resume-recovery.log`.

## Artefacts consultables

- `.local/reports/verification.json` : assertions et IDs de runs Dagster.
- `.local/reports/quality-report.json` : dernier rapport sain.
- `.local/reports/quality-rejected-run_results.json` : preuve du paiement rejete.
- `.local/reports/stale-rejected-sources.json` : preuve de fraicheur en echec.
- `.local/reports/metabase.json` : URL du dashboard et six cartes verifiees.
- `.local/reports/scheduler.json` : planning RUNNING.
- `.local/reports/deployment.json` : execution par la file et interfaces verifiees.
- `.local/reports/customer_features.csv` : export de features.
- `.local/reports/dbt-docs/` : catalogue et lineage generes.

Les schemas marts ne sont pas publies par transaction globale et les volumes
ne sont pas des sauvegardes. Les limites de production sont decrites dans le
README et le runbook. Les composants Kafka/Redpanda, Terraform et cloud restent
optionnels dans la roadmap et ne font pas partie de cette version locale.
