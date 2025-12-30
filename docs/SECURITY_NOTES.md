# Notes de Sécurité - JobMatch

Ce document recense les alertes de sécurité identifiées par les outils d'analyse statique (Bandit, etc.) et explique pourquoi elles sont acceptables dans notre contexte.

---

## Alertes Bandit - SQL Injection (B608)

### Fichier concerné
`app/gui/services/offers_db.py`

### Alertes signalées

| Ligne | Sévérité | Confiance | Description |
|-------|----------|-----------|-------------|
| 109 | Medium | Medium | SQLite - `WHERE o.id IN ({placeholders})` |
| 254 | Medium | Low | BigQuery - f-string avec `project_id` et `dataset` |
| 289 | Medium | Low | BigQuery - f-string avec `project_id` et `dataset` |
| 323 | Medium | Low | BigQuery - f-string avec `project_id` et `dataset` |
| 330 | Medium | Low | BigQuery - f-string avec `project_id` et `dataset` |

### Analyse et justification

#### 1. SQLite - Ligne 109 (Confiance Medium)

```python
placeholders = ",".join("?" * len(offer_ids))
cursor.execute(
    f"""
    SELECT ... WHERE o.id IN ({placeholders})
    """,
    offer_ids,
)
```

**Pourquoi c'est sûr :**
- Les `placeholders` sont générés dynamiquement mais contiennent uniquement des `?`
- Les valeurs réelles (`offer_ids`) sont passées en paramètres séparés
- SQLite effectue l'échappement automatique des paramètres
- Aucune donnée utilisateur n'est interpolée directement dans la requête

**Pattern standard** : C'est le pattern recommandé pour les clauses `IN` avec un nombre variable de paramètres en SQLite.

#### 2. BigQuery - Lignes 254, 289, 323, 330 (Confiance Low)

```python
query = f"""
    SELECT ...
    FROM `{self.project_id}.{self.dataset}.offers` o
    WHERE o.id IN UNNEST(@offer_ids)
"""
```

**Pourquoi c'est sûr :**
- `self.project_id` et `self.dataset` proviennent de variables d'environnement serveur
- Ces valeurs sont définies au déploiement, jamais par l'utilisateur
- Les paramètres utilisateur (`offer_ids`, `offer_id`) utilisent les paramètres nommés BigQuery (`@param`)
- BigQuery effectue l'échappement automatique des paramètres nommés

**Sources des valeurs :**
```python
project_id = os.environ.get("GCP_PROJECT_ID", "job-match-v0")
dataset = os.environ.get("BIGQUERY_GOLD_DATASET", "gold")
```

### Décision

Ces alertes sont des **faux positifs** dans notre contexte :
- Les données utilisateur sont toujours passées via des paramètres préparés
- Les f-strings ne contiennent que des identifiants de configuration serveur
- Le code suit les bonnes pratiques de prévention des injections SQL

### Comment supprimer ces alertes (optionnel)

Si nécessaire, on peut ajouter des commentaires `# nosec B608` pour ignorer ces lignes :

```python
query = f"""  # nosec B608 - project_id and dataset are server config, not user input
    SELECT ...
"""
```

Ou configurer `.bandit` pour exclure ce fichier/ces lignes.

---

## Bonnes pratiques appliquées

1. **Paramètres préparés** : Toutes les données utilisateur passent par des paramètres (`?` pour SQLite, `@param` pour BigQuery)

2. **Validation des entrées** : Les `offer_ids` proviennent de la base de données, pas directement de l'utilisateur

3. **Principe du moindre privilège** : Les credentials BigQuery ont uniquement accès aux datasets nécessaires

4. **Configuration serveur** : Les identifiants de projet/dataset sont des variables d'environnement, non modifiables par les utilisateurs

---

## Références

- [OWASP SQL Injection Prevention](https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html)
- [CWE-89: SQL Injection](https://cwe.mitre.org/data/definitions/89.html)
- [Bandit B608 Documentation](https://bandit.readthedocs.io/en/latest/plugins/b608_hardcoded_sql_expressions.html)
- [BigQuery Parameterized Queries](https://cloud.google.com/bigquery/docs/parameterized-queries)
