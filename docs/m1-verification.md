# Verification M1 - 16 novembre 2026

**M1 valide par execution reelle.** Le script `scripts/Test-M1.ps1` termine avec
le code de sortie 0. Les services restent demarres et healthy apres le test.

## Environnement

Docker Desktop installe par utilisateur dans `%LOCALAPPDATA%\Programs\DockerDesktop`.
Docker 29.9.3, Compose v5.7.0, moteur 29.9.3, backend WSL 2.
Le blocage initial (Docker absent) est resolu. L'acces au moteur depuis la sandbox
necessitait une execution hors sandbox ; ses permissions n'ont pas ete modifiees.

## Resultats observes

| Controle | Resultat |
|---|---|
| Lecture pages 4 et 5 du PDF | OK |
| docker compose config --quiet | Code 0 |
| Builds | PostgreSQL telecharge ; images MinIO et helper construites |
| Schema, contraintes, index et triggers PostgreSQL | Execution reussie |
| Clients / produits / commandes / lignes / paiements | 10 / 5 / **20** / 40 / 20 |
| Montants paiements / sommes des lignes | Coherents |
| Bucket shoppulse-raw | Cree et accessible via S3 HeadBucket |
| Seed rejoue deux fois | Effectifs et empreintes SHA-256 identiques |
| down puis up sans suppression des volumes | Reussite |
| Cinq tables apres recreation | Identiques, timestamps compris |
| Objet _m1/persistence.txt | Contenu conserve apres recreation |
| Etat final | PostgreSQL et MinIO healthy, ports sur 127.0.0.1 |
| .env | Cree avec mots de passe aleatoires et ignore par Git |

Sortie finale reelle :

```text
PASS: orders=20; bucket=shoppulse-raw; all five tables identical; MinIO object retained
```

Requete PostgreSQL executee directement apres le test :

```sql
SELECT count(*) AS orders_count FROM shop.orders;
```

```text
 orders_count
--------------
           20
(1 row)
```

Les empreintes avant recreation sont dans `.local/m1-before.json`, ignore par Git.
Aucun seed n'est rejoue entre la recreation et la comparaison finale : la perte
potentielle de donnees ne peut pas etre masquee par un rechargement.

Le script PowerShell a ete corrige pour transmettre les options via `@args` :
la declaration de parametre initiale interceptait l'option Docker `-d`.
Les analyses statiques YAML, SQL (15 instructions), Python et PowerShell passent.
Les outils d'analyse locaux sont dans `.tools/`, ignore par Git.

## Limite

Ce test valide la fixture et les volumes locaux, pas une sauvegarde contre la
perte du disque. L'ingestion incrementale releve de M2. Le bucket contient
uniquement l'objet technique de verification ; aucune extraction metier M2.
