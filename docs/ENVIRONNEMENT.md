# Environnement de développement — EduQuizAI

Installation réalisée le 27/09/2026 (tâche n°12, compétence C1 « Installer et configurer son environnement de travail en fonction du projet »).

## Poste de travail

| Élément | Détail |
|---|---|
| Système | Windows 11 Pro, virtualisation activée (WSL 2) |
| Carte graphique | NVIDIA GeForce RTX 3050 Laptop, 4 Go de VRAM (pilote 566.07, CUDA 12.7) |
| Disques | C: système (espace limité) ; E: projet et données Docker |

## Outils installés

| Outil | Version | Rôle |
|---|---|---|
| Git | 2.55 | Gestion de versions, repo `github.com/FantoniStephane/eduquizai` |
| Python | 3.12.10 | Linting, tests et exécution locale ; même version que les images Docker |
| Docker Desktop | Docker 29.8.0 (moteur WSL 2) | Exécution des 5 conteneurs : web, ia, postgres, mongo, ollama |
| VS Code | 1.139 | Éditeur de code |

Ollama n'est **pas** installé sous Windows : il tourne dans son propre conteneur Docker (image `ollama/ollama`). On évite ainsi un doublon d'installation et de modèles.

## Configuration de Docker

- **Stockage déplacé sur E:** (Settings → Resources → Advanced → Disk image location) : `E:\S_F\docker`. Les images, les volumes et les modèles d'IA ne saturent pas le disque C:.
- **Accès GPU** : les conteneurs lancés avec `--gpus all` utilisent la carte NVIDIA.
- **Volume `ollama_data`** : il conserve les modèles téléchargés d'un conteneur à l'autre.

## Test de l'IA locale (27/09/2026)

```
docker run -d --gpus all -v ollama_data:/root/.ollama -p 11434:11434 --name ollama-test ollama/ollama
docker exec ollama-test ollama pull llama3.2:3b
docker exec ollama-test ollama run llama3.2:3b "Donne une question de QCM sur la photosynthèse, en français."
docker exec ollama-test ollama ps
```

| Mesure | Résultat |
|---|---|
| Modèle testé | `llama3.2:3b` (2,0 Go téléchargés, 2,9 Go en mémoire) |
| Répartition | 80 % GPU / 20 % CPU |
| Réponse | QCM correct, obtenu en quelques secondes |

**Constats :**
- Avec 4 Go de VRAM, il faut un modèle de 3 à 4 milliards de paramètres pour rester majoritairement sur le GPU (Windows occupe déjà environ 0,5 Go de la carte pour l'affichage).
- Le petit modèle fait quelques fautes de français (« du chlorophylle »). Le modèle définitif sera choisi après des tests sur de vraies leçons, et la validation manuelle par l'enseignant (US6) reste indispensable.

## Modèles d'IA et fournisseur (sprint 2)

Le microservice `ia` utilise par défaut le modèle local d'Ollama. Modèles comparés :

```
docker compose exec ollama ollama pull qwen2.5:3b
docker compose exec ollama ollama pull llama3.2:1b
docker compose exec ia python manage.py mesure_generation llama3.2:3b qwen2.5:3b llama3.2:1b
docker compose exec ollama ollama ps
```

`ollama ps` doit afficher `100% GPU` dans la colonne PROCESSOR : le contexte est limité à 2 048 jetons pour que le modèle tienne entièrement dans les 4 Go de la carte graphique.

**Alternative : API Mistral.** Créer une clé sur la console de Mistral AI, puis la renseigner dans `.env` (jamais dans le code ni dans Git) :

```
IA_FOURNISSEUR=mistral
MISTRAL_API_KEY=<clé personnelle>
```

puis `docker compose up -d --force-recreate ia`. Mesure : `docker compose exec ia python manage.py mesure_generation --fournisseur mistral ministral-3b-2512`.

## Extensions VS Code

Elles sont listées dans `.vscode/extensions.json` : VS Code propose de les installer à l'ouverture du projet.

| Extension | Rôle |
|---|---|
| Python (`ms-python.python`) | Autocomplétion, débogage, lancement des tests |
| Ruff (`charliermarsh.ruff`) | Vérification et formatage du code (le même outil que dans la CI) |
| Django (`batisteo.vscode-django`) | Coloration des templates Django |
| Docker (`ms-azuretools.vscode-docker`) | Gestion des conteneurs |
| MongoDB (`mongodb.mongodb-vscode`) | Exploration des quiz enregistrés |
| GitHub Actions (`github.vscode-github-actions`) | Suivi de l'intégration continue |

## API du microservice IA et jeton JWT (sprint 2)

Le service `ia` n'accepte que les appels munis d'un jeton JWT signé par l'application web. Les deux conteneurs partagent un secret, `IA_JWT_SECRET`, à définir dans `.env` (32 caractères minimum, jamais dans Git) :

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Après l'ajout ou le changement du secret : `docker compose up -d --force-recreate web ia`. Tests : `docker compose exec ia python manage.py test` et `docker compose exec web python manage.py test quiz`.

## Génération d'un quiz depuis l'application web (tâche 29)

- Page : `/quiz/generer/` (bouton « Générer un quiz » de la liste). L'appel au service `ia` est synchrone.
- `IA_DELAI` (défaut 130 s) : attente maximale côté web, à garder supérieure au délai du modèle (60 s) pour laisser place à la nouvelle tentative.
- `IA_FOURNISSEUR` est aussi lu par le web, uniquement pour l'encart d'information (« IA locale » ou API Mistral).
- Le paquet `requests` est installé dans l'image `web` : après changement de `requirements.txt`, `docker compose up -d --build web`.
- Annulation : retenue dans le cache en mémoire de Django (un seul processus en développement).
