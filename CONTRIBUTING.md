# Conventions du projet

## Branches

```
main                 version stable, toujours fonctionnelle
 └── develop         version en cours de développement
      ├── feature/<nom>   une branche par fonctionnalité (ex. feature/lecon-crud)
      └── fix/<nom>       une branche par correction (ex. fix/titre-vide)
```

- On ne travaille jamais directement sur `main`.
- Une fonctionnalité terminée et testée est fusionnée dans `develop`.
- En fin de sprint, `develop` est fusionnée dans `main`.

## Messages de commit

Format [Conventional Commits](https://www.conventionalcommits.org/fr/) : `<type>(<module>): <description en français> (tâche N)`

- `<module>` (facultatif) : la partie du projet concernée, par exemple `quiz`, `lecons`, `ia`, `dashboard`.
- `(tâche N)` (facultatif) : le numéro de la tâche du backlog, en fin de message.
- Exemple complet : `feat(quiz): modification et suppression d'un quiz (tâches 31.1 et 31.2)`.

| Type | Utilisation | Exemple |
|---|---|---|
| `feat` | nouvelle fonctionnalité | `feat: formulaire de création de leçon` |
| `fix` | correction de bug | `fix: erreur 500 si le titre est vide` |
| `docs` | documentation, dossier | `docs: section 5.2 architecture` |
| `test` | ajout ou modification de tests | `test: tests unitaires du service leçon` |
| `refactor` | amélioration du code sans changement de comportement | `refactor: extraction du client IA` |
| `chore` | configuration, outils, dépendances | `chore: ajout de Docker Compose` |

## Règles de nommage du code

- Python : `snake_case` pour les variables et fonctions, `PascalCase` pour les classes (PEP 8, vérifié par Ruff).
- Base de données : tables au singulier, en minuscules et snake_case ; clés primaires `id_<table>`.
- Pas d'accents dans les noms de fichiers, de variables ou de tables.

## Sécurité

- Aucun secret (mot de passe, clé, jeton) dans le code : tout passe par le fichier `.env`, jamais versionné.
- Les documents confidentiels (`dossiers_officiels/`) ne sont jamais versionnés.
