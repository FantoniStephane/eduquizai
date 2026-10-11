# EduQuizAI by SchoolUp

[![CI](https://github.com/FantoniStephane/eduquizai/actions/workflows/ci.yml/badge.svg?branch=develop)](https://github.com/FantoniStephane/eduquizai/actions/workflows/ci.yml)

Générateur de quiz pédagogiques pour enseignants, piloté par une intelligence artificielle **locale**.

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
| Microservice IA | Django REST Framework · JWT · Ollama (modèle local) |
| Bases de données | PostgreSQL (utilisateurs, leçons) · MongoDB (quiz) |
| DevOps | Docker · Docker Compose · GitHub Actions |
| Qualité | Ruff · pre-commit · tests Django · coverage |

## Architecture

Application en couches (présentation → métier → accès aux données) et microservice IA séparé, dans 5 conteneurs Docker.
Voir `docs/conception/diagrammes/architecture.png`.

## Structure du dépôt

```
docs/                    Documentation technique (environnement)
docs/conception/         Diagrammes (UML, MCD, architecture), charte graphique, maquettes
```

*(la structure sera complétée au fil du développement)*

## Installation

*(à venir — sprint 1)*

## Conventions

Voir [CONTRIBUTING.md](CONTRIBUTING.md).

## Auteur

Stéphane Fantoni — [github.com/FantoniStephane](https://github.com/FantoniStephane)
