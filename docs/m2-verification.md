# Verification M2 - 16 novembre 2026

**M2 valide sur les sources locales synthetiques.**

- Configuration Compose officielle : valide.
- PostgreSQL, MinIO et API source : healthy pendant les tests.
- Test d'integration execute deux fois : code de sortie 0.
- Rejeu sans mutation : aucun nouvel objet raw.
- Une mutation client : exactement une nouvelle revision raw.
- Echec injecte apres les commandes : checkpoint conserve.
- Reprise : objets deja ecrits reutilises, aucun doublon ajoute.
- CSV inchange : ignore par empreinte SHA-256.
- API : trois evenements charges, endpoint pagine a deux lignes par page.
- Ingestion normale finale : success, zero nouvelle version a ecrire.
- Syntaxe des quatre fichiers Python et du script PowerShell : valide.

Dernier run normal : `afaa0f5f-cc9c-4204-be66-9dcbdac026cc`.

| Prefixe raw | Objets observes |
|---|---:|
| postgres/customers | 14 |
| postgres/products | 5 |
| postgres/orders | 20 |
| postgres/order_items | 40 |
| postgres/payments | 20 |
| api/events | 3 |
| file/shipping | 3 |
| file/original | 1 |
| Total | 106 |

Les 14 objets clients representent 10 clients et quatre revisions historiques
ajoutees par les deux passages du test ; ce ne sont pas 14 clients distincts.
Les deux clients modifies sont revenus a FR apres deux bascules, mais leurs
timestamps ont avance. L'historique reste intentionnellement conserve dans raw.
Les autres tables PostgreSQL conservent leurs nombres de lignes M1.

Les manifestes et le checkpoint sont accessibles sous `_metadata/m2/` dans MinIO.
La sortie du dernier run est aussi conservee dans `.local/m2-last-run.json`, ignore
par Git. Les limites (retard de transactions, suppressions, fichiers de petite
taille et absence de transaction distribuee) figurent dans `m2-ingestion.md`.
