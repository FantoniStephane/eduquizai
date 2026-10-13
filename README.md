# EduQuizAI by SchoolUp

[![CI](https://github.com/FantoniStephane/eduquizai/actions/workflows/ci.yml/badge.svg?branch=develop)](https://github.com/FantoniStephane/eduquizai/actions/workflows/ci.yml)

Générateur de quiz pédagogiques pour enseignants, piloté par une intelligence artificielle (API Mistral, ou modèle local avec Ollama).

**En ligne : https://eduquizai.duckdns.org** — déploiement automatique depuis `main` (voir `docs/DEPLOIEMENT.md`).

Projet fil rouge du titre professionnel **Concepteur Développeur d'Applications (CDA)** — Metz Numeric School, session 2026.

## Fonctionnalités

- Espace enseignant sécurisé (comptes créés par l'administrateur)
- Rédaction de leçons dans un éditeur mis en forme, ou import d'un fichier (.docx, .txt)
- Génération automatique de quiz par IA : QCM, vrai/faux, questions ouvertes
- Relecture, modification et validation manuelle des quiz
- Export d'un quiz validé en PDF, version élève (sans les réponses)

## Stack technique

| Couche | Technologie |
|---|---|
| Application | Python · Django (templates) |
| Microservice IA | Django REST Framework · JWT · API Mistral (par défaut) ou Ollama (modèle local) |
| Bases de données | PostgreSQL (utilisateurs, leçons) · MongoDB (quiz) |
| DevOps | Docker · Docker Compose · GitHub Actions |
| Qualité | Ruff · pre-commit · tests Django · coverage |

## Architecture

Application en couches (présentation → métier → accès aux données) et microservice IA séparé, dans 5 conteneurs Docker.
Voir `docs/conception/diagrammes/architecture.png`.

## Structure du dépôt

```
web/                     Application Django (templates) : comptes, lecons, quiz, config
ia/                      Microservice IA (Django REST Framework, JWT, Mistral / Ollama)
docker/mongo/            Initialisation de MongoDB (compte applicatif aux droits limités)
docs/                    Documentation : environnement, plan de tests, déploiement, veille
docs/conception/         Diagrammes (UML, MCD, architecture), script SQL, charte graphique, maquettes
scripts/                 Sauvegarde et restauration des bases (PowerShell)
.github/workflows/       Intégration continue et déploiement (GitHub Actions)
docker-compose.yml       Environnement de développement (5 conteneurs)
docker-compose.prod.yml  Environnement de production (4 conteneurs)
```

## Installation (développement)

Prérequis : Docker Desktop et Git.

```
git clone https://github.com/FantoniStephane/eduquizai.git
cd eduquizai
cp .env.example .env        # puis remplacer chaque « a_changer » par un secret
docker compose up -d --build
docker compose exec web python manage.py createsuperuser
```

L'application est alors disponible sur http://127.0.0.1:8000. Pour générer des quiz, renseigner `MISTRAL_API_KEY` dans `.env`, ou choisir le modèle local avec `IA_FOURNISSEUR=ollama`. Pour charger des données de démonstration : `docker compose exec web python manage.py donnees_demo --mot-de-passe "<mot de passe>"`.

Le détail (variables, IA, sauvegardes) est dans `docs/ENVIRONNEMENT.md`.

## Tests

284 tests automatiques (253 pour l'application web, 31 pour le microservice IA) :

```
docker compose exec web python manage.py test
docker compose exec ia python manage.py test
```

Voir `docs/PLAN_DE_TESTS.md`.

## Conventions

Voir [CONTRIBUTING.md](CONTRIBUTING.md).

## Auteur

Stéphane Fantoni — [github.com/FantoniStephane](https://github.com/FantoniStephane)

## Licence

Projet distribué sous licence MIT (voir le fichier `LICENSE`).
