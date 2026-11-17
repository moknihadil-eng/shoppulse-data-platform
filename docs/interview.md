# Expliquer ShopPulse en entretien

## Presentation en une minute

« ShopPulse simule la plateforme data d'une boutique. J'extrais les changements
d'une base PostgreSQL, une API paginee et des fichiers vers un stockage objet
compatible S3. Je conserve les versions brutes et les traces d'execution pour
pouvoir rejouer les traitements. Un warehouse PostgreSQL separe heberge les
couches dbt et un modele dimensionnel. Dagster orchestre les etapes, les retries
et les backfills. Les tests bloquent les erreurs de qualite, et Metabase expose
les indicateurs. Une table de features illustre la consommation ML. »

## M1 : fondation

Compose decrit les services et leur reseau. Les volumes nommes vivent au-dela des
conteneurs. Les healthchecks evitent de lancer un job avant que PostgreSQL ou
MinIO soit pret. Les secrets sont injectes par environnement, pas commites.
Les donnees synthetiques ont des cles et des dates fixes pour reproduire la demo.

## M2 : ingestion

Un watermark reduit la lecture aux modifications recentes ; une fenetre de
chevauchement limite le risque de manquer des timestamps identiques ou arrives
avec un petit retard. Des cles objet basees sur le contenu rendent le depot
idempotent. Le checkpoint est ecrit a la fin ; un echec peut laisser des objets
partiels, mais une reprise les reutilise. Je ne promets pas exactement-once :
c'est une lecture potentiellement repetee avec deduplication des revisions.
La detection des suppressions et des longues transactions exigerait du CDC ou
une reconciliation periodique.

## M3 : modele

Je distingue le grain commande du grain ligne et paiement, ce qui evite de
multiplier le chiffre d'affaires lors des jointures. Les dimensions decrivent
clients, produits et dates. La SCD2 conserve les versions observees du client
avec des intervalles de validite. Les faits pointent vers la version valable au
moment de la commande. Un prix produit actuel ne remplace pas le prix achete.
Staging type et deduplique ; intermediate applique les calculs partages ; marts
presente des tables directement utilisables.

## M4 : exploitation

Le DAG exprime l'ordre ingestion, chargement, fraicheur, transformation et
publication. Un retry traite une panne transitoire ; il ne remplace pas la
correction d'une mauvaise donnee. Le backfill rejoue des partitions de dates
depuis l'historique retenu. Les runs, logs et erreurs persistent dans Dagster.
Pour le portfolio, `dagster dev` regroupe webserver et daemon localement ; je
separerais ces composants et leur stockage en production.

## M5 : qualite

Je teste unicite, valeurs nulles, relations, montants, reconciliations et
intervalles SCD2. La fraicheur mesure la derniere extraction reussie, pas la date
metier fictive de janvier 2027. La demo injecte un paiement negatif dans bronze :
les tests le rejettent et le run apparait en echec. Une source vieillie de
48 heures declenche aussi un echec. Les fixtures temporaires sont nettoyees.

## M6 : consommation

Le dashboard distingue valeur commandee et paiements effectivement reussis.
Le compte BI n'a que SELECT sur les marts. Les features sont calculees sur les
30 jours avant une date de reference, sans observations futures, label ou
pretention d'avoir entraine un modele. La table peut etre exportee en CSV.

## M7 : reproductibilite et limites

Le script PowerShell demarre et execute la demo. La CI reproduit les tests dans
des conteneurs ephemeres et conserve les artefacts. La documentation decrit les
grains, lineage et procedures de reprise. Une demo avec une nouvelle commande
montre la chaine complete jusqu'au dashboard. Le workflow est fourni pour GitHub
mais une execution distante exige que le depot y soit publie.

Les volumes locaux ne sont pas une sauvegarde. Les revisions par petits objets
conviennent a cette demo, pas a des milliards de lignes. Une mise en production
demanderait au minimum secrets externes, droits plus fins pour les jobs, TLS,
sauvegardes/restaurations testees, observabilite et publication atomique des marts.
Kafka/Redpanda, Terraform et un warehouse cloud sont des extensions optionnelles
de la roadmap, pas des composants de cette livraison locale.

## Demonstration en entretien

1. Lancer `scripts/Start-ShopPulse.ps1 -SkipBuild` et ouvrir Dagster/Metabase.
2. Montrer le bucket raw, un manifeste et le checkpoint.
3. Lancer `scripts/Demo-NewOrder.ps1`, puis actualiser le dashboard.
4. Montrer les relations dbt et les intervalles de dim_customer.
5. Executer `platform quality-demo`, constater son echec attendu, puis montrer
   `quality-rejected-run_results.json` et le dernier run sain.
6. Rejouer le backfill des 2 et 3 janvier 2027 et montrer les montants inchanges.
