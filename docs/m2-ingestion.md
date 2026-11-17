# M2 - Ingestion locale vers raw

Le pipeline charge les cinq tables PostgreSQL, une API locale d'evenements clients
et un CSV de livraisons dans MinIO. L'API et le CSV sont des sources synthetiques
de demonstration, pas des services tiers ni des livraisons reelles.

## Executer depuis PowerShell

M1 doit avoir ete initialise, avec le bucket `shoppulse-raw` existant.
Depuis la racine du projet, avec Docker Desktop ouvert :

```powershell
# Seulement si docker est introuvable dans le terminal courant :
$env:PATH = "$env:LOCALAPPDATA\Programs\DockerDesktop\resources\bin;" + $env:PATH
docker compose up -d --wait postgres minio
docker compose build source-api ingestion
docker compose up -d --wait source-api
docker compose run --rm ingestion
docker compose run --rm --entrypoint python ingestion status.py
```

Controler `$LASTEXITCODE` apres chaque commande : il doit etre 0. `ingestion` est
un job ponctuel qui se termine ; `source-api`, PostgreSQL et MinIO restent actifs.
L'API ecoute uniquement dans le reseau Docker, sans port publie sur Windows.
Les secrets proviennent du `.env` existant.

## Organisation du bucket

```text
shoppulse-raw/
  raw/postgres/<table>/date=.../id=.../<sha256>.json
  raw/api/events/date=.../id=.../<sha256>.json
  raw/file/shipping/date=.../id=.../<sha256>.json
  raw/file/original/<sha256>/shipping.csv
  _metadata/m2/checkpoint.json
  _metadata/m2/runs/<run_id>.json
  _m1/persistence.txt
```

Dans la console MinIO, cliquer sur **Refresh**, puis explorer `raw` et `_metadata`.
Le JSON d'une ligne conserve ses champs source. Le CSV original est aussi archive
octet pour octet. Un nom de source, une date, un identifiant et une empreinte du
contenu forment la cle objet. Une nouvelle version cree un nouvel objet ; relire
le meme contenu reutilise la meme cle. Les manifestes de runs sont distincts a
chaque execution : ce sont des traces d'audit, pas des doublons metier.

## Fonctionnement a expliquer en entretien

1. Un verrou consultatif PostgreSQL assure un seul ecrivain pour le checkpoint M2.
2. Le job lit le dernier point de reprise dans MinIO.
3. PostgreSQL fournit les lignes dont `updated_at` est superieur ou egal au dernier
   maximum moins cinq minutes. L'extraction des cinq tables utilise un snapshot
   transactionnel coherent en lecture seule. Le tri utilise timestamp puis ID.
4. L'API applique le meme filtre temporel et renvoie deux evenements par page ; le
   client suit `next_page` jusqu'a la fin. Le CSV est compare par SHA-256 : un
   fichier identique est ignore, un fichier modifie est relu et archive.
5. Les donnees sont ecrites vers des cles deterministes. La recherche des objets
   existants evite de recreer les memes versions lors du chevauchement temporel.
6. Le manifeste de run enregistre ID, debut/fin, statut, sources, bornes temporelles,
   lignes lues, objets crees/reutilises, cles et empreinte du fichier.
7. Le checkpoint est enregistre seulement apres toutes les ecritures et le
   manifeste de succes. En cas d'echec, les objets deja ecrits restent reutilisables
   et le checkpoint n'avance pas. Le manifeste prend le statut `failed`.

Le chevauchement evite de perdre des lignes qui partagent le meme timestamp.
Les dates de la fixture sont tres proches et situees en janvier 2027 : certaines
petites tables peuvent etre entierement relues dans la fenetre de cinq minutes.
Cela ne reecrit pas toutes les donnees. Le test distingue lignes relues et objets
nouvellement crees, plutot que de confondre lecture et chargement.

## Test d'integration

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Test-M2.ps1
```

Ce test, reserve a la fixture, effectue un chargement, une relance, une mutation
reelle du pays du client synthetique 1, puis une mutation du client 2 et un echec
injecte apres la lecture des commandes. Les deux pays sont bascules entre FR et BE
et restent dans leur nouvel etat ; `updated_at` avance automatiquement.
Chaque relance du test ajoute donc deux revisions historiques legitimes.
Les nombres de clients et commandes ne changent pas.

Les assertions controlent : aucun objet brut supplementaire au rejeu, exactement
une nouvelle revision pour une mutation, CSV inchange ignore, checkpoint inchange
apres l'echec, objets partiels reutilises a la reprise et manifeste final reussi.
Le premier test observe 104 objets raw : 95 lignes PostgreSQL initiales, trois
evenements, trois livraisons, un CSV original et deux revisions client.
Ce total augmente avec les mutations ulterieures ; ce n'est pas un nombre fixe
d'enregistrements metier courants. M3 devra selectionner les dernieres versions
par source et identifiant avant de construire ses modeles.

## Limites explicites

Ce M2 est une fondation pedagogique : un objet par revision simplifie la preuve
d'idempotence mais serait remplace par des lots JSONL/Parquet a plus grande echelle.
Les donnees sont lues en memoire pour les petits jeux locaux. Les suppressions
physiques et les transactions qui se terminent avec un retard de plus de cinq
minutes exigent CDC/tombstones ou une reconciliation ; elles ne sont pas couvertes.
L'API de demo est statique pendant la pagination, sans contrat de snapshot pour une
API externe mutable. Le checkpoint et le manifeste sont deux objets distincts :
il n'existe pas de transaction distribuee entre eux. `checkpoint.last_run_id`
identifie le dernier run effectivement valide ; un crash entre les deux ecritures
peut laisser un manifeste de succes non reference, rejouable sans doublons raw.
Apres un arret brutal, un manifeste peut rester `running` ; M4 apportera la
supervision et les retries, M5 les controles qualite approfondis.

La modification d'une fixture API impose de mettre a jour `updated_at` pour que
la nouvelle version soit prise par le filtre incremental. M2 n'inclut pas encore
de warehouse, dbt ou dashboard : cela appartient aux jalons suivants.
