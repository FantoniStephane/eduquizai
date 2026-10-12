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

Le microservice `ia` utilise **par défaut l'API Mistral** (`IA_FOURNISSEUR=mistral`) : sur une vraie leçon, le modèle local de 3 milliards de paramètres produisait des QCM refusés par le contrôle (choix en double), alors que Mistral génère un quiz valide en 3,5 s (jeu d'essai du 12/10/2026). Le modèle local d'Ollama reste disponible par réglage, pour le développement et le fonctionnement hors ligne. Modèles locaux comparés :

```
docker compose exec ollama ollama pull qwen2.5:3b
docker compose exec ollama ollama pull llama3.2:1b
docker compose exec ia python manage.py mesure_generation llama3.2:3b qwen2.5:3b llama3.2:1b
docker compose exec ollama ollama ps
```

`ollama ps` doit afficher `100% GPU` dans la colonne PROCESSOR : le contexte est limité à 2 048 jetons pour que le modèle tienne entièrement dans les 4 Go de la carte graphique.

**Fournisseur par défaut : API Mistral.** Créer une clé sur la console de Mistral AI, puis la renseigner dans `.env` (jamais dans le code ni dans Git) :

```
IA_FOURNISSEUR=mistral
MISTRAL_API_KEY=<clé personnelle>
```

puis `docker compose up -d --force-recreate web ia`. Pour travailler avec le modèle local : `IA_FOURNISSEUR=ollama`, même commande.

**Confidentialité** : avec l'offre gratuite de Mistral, les requêtes peuvent servir à entraîner leurs modèles ; on n'y envoie que des leçons d'exemple. Une mise en production avec de vraies leçons demande une offre qui exclut les données de l'entraînement (à vérifier dans les conditions de Mistral AI). Mesure : `docker compose exec ia python manage.py mesure_generation --fournisseur mistral ministral-3b-2512`.

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

## Avant une démo

- Démo avec le fournisseur par défaut (Mistral) : vérifier `IA_FOURNISSEUR=mistral` et `MISTRAL_API_KEY` dans `.env`, puis une génération d'essai : `docker compose exec ia python manage.py essai_generation --nombre 3` (environ 3 s). Connexion Internet indispensable.
- Avec le modèle local (`IA_FOURNISSEUR=ollama`) : après un démarrage de Docker ou une longue inactivité, le modèle n'est plus en mémoire (`docker compose exec ollama ollama ps` vide) et la première génération peut dépasser le délai de 60 s ; lancer d'abord une génération de 3 questions (« chauffe »), puis vérifier `ollama ps` : `llama3.2:3b … 100% GPU`. Le petit modèle échoue sur certaines leçons (QCM aux choix en double, refusés par le contrôle) : il n'est pas utilisé pour la démo.

## Export d'un quiz en PDF (tâche 40)

- Adresse : `/quiz/<id>/exporter/` (bouton « Exporter » du détail d'un quiz validé). Version élève uniquement, sans les réponses.
- Bibliothèque `reportlab` (installe aussi `pillow`) : après changement de `requirements.txt`, `pip install -r web/requirements.txt` (venv) et `docker compose up -d --build web`.
- Tests : `docker compose exec web python manage.py test quiz.tests_export`.

## Sécurité de l'environnement (tâche 33)

### Compte MongoDB de l'application

L'application ne se connecte pas avec le compte root de MongoDB : elle utilise un compte dédié, limité à la base `eduquizai` et à la base de test `test_eduquizai`. À ajouter dans `.env` :

```
MONGO_APP_USER=eduquizai_app
MONGO_APP_PASSWORD=<mot de passe généré>
```

Mot de passe : `python -c "import secrets; print(secrets.token_urlsafe(32))"`.

- **Nouvelle installation** (volume `mongo_data` vide) : le compte est créé automatiquement au premier démarrage par `docker/mongo/initdb/01_utilisateur_app.js`.
- **Base existante** : lancer une fois le script avec le compte root (il crée ou met à jour le compte, sans toucher aux données) :

```powershell
docker compose up -d --force-recreate mongo web
docker compose exec mongo sh -c 'mongosh --quiet -u $MONGO_INITDB_ROOT_USERNAME -p $MONGO_INITDB_ROOT_PASSWORD --authenticationDatabase admin /docker-entrypoint-initdb.d/01_utilisateur_app.js'
docker compose exec web python manage.py init_mongo
```

### Variables par conteneur

`docker-compose.yml` n'utilise plus `env_file` : chaque service liste les seules variables qu'il reçoit (un nom seul reprend la valeur de `.env`). Après l'ajout d'une variable dans `settings.py`, il faut aussi l'ajouter au service concerné dans `docker-compose.yml`. Vérification :

```powershell
docker compose exec ia env | Select-String "POSTGRES|MONGO|DJANGO"   # rien ne doit s'afficher
docker compose exec web env | Select-String "ROOT|MISTRAL"           # rien ne doit s'afficher
```

### Limitation des essais de connexion

Après 5 échecs (même adresse et même IP) ou 20 échecs (même IP), la connexion est bloquée 15 minutes. En développement, pour débloquer tout de suite : `docker compose restart web` (le cache est en mémoire).

## Données de test, démonstration, sauvegarde (tâche 35)

### Bases de test

Les tests ne touchent jamais aux données de développement : Django crée une base PostgreSQL `test_eduquizai` et le lanceur `config/test_runner.py` une base MongoDB `test_eduquizai`, toutes deux supprimées à la fin.

### Données de démonstration

```powershell
# Première fois (le compte n'existe pas) : le mot de passe est contrôlé par les validateurs
docker compose exec web python manage.py donnees_demo --mot-de-passe "<mot de passe>"
# Remettre la démo à neuf (supprime les leçons et quiz de l'enseignante de démo uniquement)
docker compose exec web python manage.py donnees_demo --reinitialiser
```

Contenu : l'enseignante anne.durand@eduquizai.local, 4 leçons (histoire, SVT, mathématiques, anglais) et 3 quiz (1 validé, 2 brouillons). La leçon d'anglais n'a pas de quiz (génération et suppression de leçon) ; la Révolution française en a un (suppression bloquée). La commande refuse d'écraser des données sans `--reinitialiser`.

### Sauvegarde et restauration

```powershell
.\scripts\sauvegarde.ps1                                    # crée sauvegardes\<date_heure>\
.\scripts\restauration.ps1 sauvegardes\2026-10-11_13-36-47   # demande de taper OUI
```

- Sauvegarde : `pg_dump -Fc` (→ `postgres.dump`) et `mongodump --gzip` avec le compte applicatif (→ `mongo.archive.gz`), faits dans les conteneurs puis copiés par `docker compose cp`.
- Restauration : arrêt de `web`, `pg_restore --clean --single-transaction`, `mongorestore --drop` limité à la base de l'application, redémarrage de `web` (même en cas d'erreur).
- `sauvegardes/` est ignoré par Git : il contient des données personnelles. Copier les sauvegardes hors du poste (clé USB, OneDrive) pour qu'elles survivent à une panne du disque.
- Essai du 11/10/2026 : sauvegarde, suppression d'une leçon et d'un quiz, restauration → tout est revenu.

## Éco-conception : police allégée (tâche 37)

`web/static/fonts/InterVariable.woff2` est une version réduite de la police Inter (licence SIL OFL 1.1, qui autorise cette modification ; voir `LICENSE_Inter.txt`) : seuls les caractères latins, les accents français, la ponctuation et quelques symboles sont conservés, avec les deux axes variables (graisse `wght`, taille optique `opsz`). Poids : 352 Ko → 102 Ko.

Pour la refaire à partir du fichier d'origine (`InterVariable.woff2` de la distribution officielle d'Inter) :

```powershell
pip install fonttools brotli
pyftsubset InterVariable.woff2 --unicodes="U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+2000-206F,U+2074,U+20AC,U+2122,U+2190-2199,U+2212,U+2215,U+2261,U+2713-2714" --layout-features="*" --flavor=woff2 --output-file=web/static/fonts/InterVariable.woff2
```

Un caractère absent de la police réduite (alphabet non latin, par exemple) s'affiche quand même, avec la police de secours du système.

## Intégration continue (tâche 41)

- Fichier `.github/workflows/ci.yml`, lancé à chaque push sur `develop` / `main` et à chaque pull request vers `main` : job « Qualité » (pip-audit, Ruff, `manage.py check`), puis en parallèle « Tests IA » et « Tests web » (PostgreSQL 17 et MongoDB 8 en services, compte MongoDB applicatif créé par `docker/mongo/initdb/01_utilisateur_app.js`).
- Résultats : onglet **Actions** du dépôt ; les tableaux de couverture sont dans le résumé du run, les rapports HTML dans « Artifacts » (14 jours).
- Couverture en local, depuis `web/` (venv) : `python -m coverage run manage.py test` puis `python -m coverage report` (réglages dans `web/.coveragerc` ; le rapport échoue sous 95 %).
- Aucun vrai secret dans le workflow : valeurs de test uniquement.
