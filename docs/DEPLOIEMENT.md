# Déploiement en production — EduQuizAI

Application en ligne : **https://eduquizai.duckdns.org**

## Vue d'ensemble

```
développeur ──push──> develop ──pull request──> main
                                                  │
                                    GitHub Actions (ci.yml)
                          Qualité → Tests IA + Tests web → Images Docker
                                                  │ tout est vert
                                         job « Déploiement »
                                                  │ POST webhook + jeton
                                                  ▼
                       VPS OVH ── Coolify ── git clone main ── docker compose
                       (docker-compose.prod.yml) : web, ia, postgres, mongo,
                       sauvegarde_postgres, sauvegarde_mongo
                                                  │
                       Traefik (proxy de Coolify) ── HTTPS Let's Encrypt
                                                  ▼
                                   https://eduquizai.duckdns.org
```

- **Seule la branche `main` est déployée**, et seulement si tous les contrôles de la CI passent (`needs`). Le travail se fait sur `develop` ; une pull request vers `main` déclenche la mise en production.
- **Coolify** (installé sur le VPS) récupère le code de `main`, reconstruit les images avec `docker-compose.prod.yml` et remplace les conteneurs. Son proxy **Traefik** reçoit le HTTPS (certificat Let's Encrypt renouvelé automatiquement) et le transmet au conteneur `web` sur le réseau Docker : aucun port de l'application n'est ouvert sur Internet.
- **IA** : API Mistral (le serveur n'a pas de carte graphique, pas d'Ollama en production).

## Ce qui change entre développement et production

| | Développement (`docker-compose.yml`) | Production (`docker-compose.prod.yml`) |
|---|---|---|
| Serveur d'application | `runserver` (rechargement du code) | **Gunicorn** (3 processus web, 2 pour l'IA) |
| Interrupteur | `DJANGO_PRODUCTION=False` | `DJANGO_PRODUCTION=True` |
| HTTPS | non | redirection HTTPS, HSTS 1 an, cookies `Secure` |
| Cache (limitation des connexions, annulations) | mémoire | table PostgreSQL partagée entre processus |
| IP du visiteur | `REMOTE_ADDR` | dernière adresse de `X-Forwarded-For` (ajoutée par Traefik) |
| Fichiers statiques | WhiteNoise, fichiers sources | WhiteNoise, fichiers compressés et versionnés (`collectstatic`) |
| Fournisseur d'IA | au choix (Ollama ou Mistral) | Mistral |
| Ports publiés | `127.0.0.1` uniquement | aucun |
| Secrets | `.env` local (ignoré par Git) | variables d'environnement de Coolify |
| E-mails | console | SMTP (relais Brevo) |
| Sauvegarde des bases | scripts `sauvegarde.ps1` / `restauration.ps1` (à la main) | automatique, toutes les 24 h, 7 jours conservés |

Contrôle : `python manage.py check --deploy` sans avertissement en mode production (W021, préchargement HSTS, désactivé volontairement : réservé au propriétaire du domaine `duckdns.org`).

## Démarrage d'un conteneur (`lancement.sh`)

En production, le conteneur `web` enchaîne : `migrate` → `createcachetable` → `init_mongo` → `collectstatic` → Gunicorn. Le conteneur `ia` lance directement Gunicorn. En développement, les deux lancent `runserver`.

## Mise en place (une seule fois)

1. **DNS** : sous-domaine `eduquizai.duckdns.org` pointant vers l'IP du VPS.
2. **Coolify** : nouvelle ressource « Private Repository (with Deploy Key) », dépôt `git@github.com:FantoniStephane/eduquizai.git`, branche `main`, *build pack* **Docker Compose**, fichier `/docker-compose.prod.yml`.
   - **Clé de déploiement** : une clé ED25519 générée dans Coolify (*Keys & Tokens*), dont la partie publique est ajoutée au dépôt GitHub (*Settings → Deploy keys*, lecture seule). Une clé de déploiement GitHub ne sert qu'à un seul dépôt. *Le dépôt est public ; Coolify continue d'utiliser cette clé en lecture seule.*
   - **Preserve repository during deployment** : coché. Sinon Coolify supprime le dépôt après la construction et le dossier `docker/mongo/initdb` monté dans MongoDB est vide (le compte applicatif n'est pas créé).
   - **Auto deploy** : « Manual deployments only » (le déploiement est commandé par la CI, après les tests).
   - **Domaine** : `https://eduquizai.duckdns.org`, service `web`, port `8000`.
3. **Variables d'environnement** (Coolify, jamais dans le dépôt) : `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS=eduquizai.duckdns.org`, `DJANGO_CSRF_TRUSTED_ORIGINS=https://eduquizai.duckdns.org`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `MONGO_INITDB_ROOT_USERNAME`, `MONGO_INITDB_ROOT_PASSWORD`, `MONGO_DB`, `MONGO_APP_USER`, `MONGO_APP_PASSWORD`, `IA_SECRET_KEY`, `IA_JWT_SECRET`, `MISTRAL_API_KEY`, et pour les e-mails (relais SMTP Brevo, compte gratuit) : `DJANGO_EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend`, `DJANGO_DEFAULT_FROM_EMAIL` (adresse validée comme expéditeur dans Brevo), `EMAIL_HOST_USER` (identifiant SMTP Brevo), `EMAIL_HOST_PASSWORD` (clé SMTP Brevo). Secrets générés avec `python -c "import secrets; print(secrets.token_urlsafe(50))"`, tous différents de ceux du développement.
4. **GitHub** (*Settings → Secrets and variables → Actions*) :
   - `COOLIFY_WEBHOOK` : `https://<coolify>/api/v1/deploy?uuid=<uuid de la ressource>&force=false` ;
   - `COOLIFY_TOKEN` : jeton d'API Coolify avec la seule permission `deploy`.
5. **Premier déploiement** (bouton *Deploy* de Coolify), puis compte administrateur : *Terminal* de Coolify → conteneur `web` → `python manage.py createsuperuser`.

## Déployer une nouvelle version

1. Travailler sur `develop`, pousser, vérifier la CI.
2. Pull request `develop` → `main`, attendre la CI, fusionner.
3. La CI de `main` se termine par le job « Déploiement » : `Réponse de Coolify : HTTP 200`. Coolify reconstruit et redémarre l'application (environ 1 minute).
4. Vérifier https://eduquizai.duckdns.org (connexion, génération d'un quiz).

En cas d'échec du job, il affiche le code et le message de Coolify (jamais l'URL ni le jeton). Coolify n'accepte que `POST` sur cette route (version 4.4) : un `GET` renvoie 405.

## Incidents rencontrés lors de la mise en place

| Symptôme | Cause | Correction |
|---|---|---|
| Conteneur `web` qui redémarre en boucle, « Authentication failed » (MongoDB) | Dépôt supprimé après la construction : script `initdb` absent, compte `eduquizai_app` jamais créé | « Preserve repository » coché, puis script lancé une fois à la main dans le conteneur `mongo` (il est relançable) |
| Administrateur envoyé sur le tableau de bord | Arrivé par `/`, la connexion reçoit `next=/` | Un `next` n'est suivi que s'il correspond au côté de l'utilisateur (test ajouté) |
| Job « Déploiement » en échec, HTTP 405 | Route de Coolify passée en `POST` | `curl --request POST` |

## Exploitation

- **Journaux** : Coolify → ressource → *Runtime Logs* (requêtes Gunicorn, erreurs Django, résultat des sauvegardes).
- **Commandes** : Coolify → *Terminal* → conteneur `web` (ex. `python manage.py donnees_demo`).
- **Retour arrière** : Coolify → *Rollback* (redéploie une version précédente).
- **Sauvegardes** : les conteneurs `sauvegarde_postgres` et `sauvegarde_mongo` sauvegardent les deux bases au démarrage puis toutes les 24 h dans le volume `sauvegardes_data` (`postgres_AAAA-MM-JJ.dump`, `mongo_AAAA-MM-JJ.archive.gz`) ; les fichiers de plus de 7 jours sont supprimés. Liste : *Terminal* → conteneur `sauvegarde_postgres` → `ls -l /sauvegardes`.
- **Restauration** (écrase les données actuelles) :
  - PostgreSQL : *Terminal* → `sauvegarde_postgres` → `pg_restore --clean --if-exists -d "$PGDATABASE" /sauvegardes/postgres_AAAA-MM-JJ.dump` ;
  - MongoDB : *Terminal* → `sauvegarde_mongo` → `mongorestore --host mongo --username "$MONGO_APP_USER" --password "$MONGO_APP_PASSWORD" --authenticationDatabase "$MONGO_DB" --nsInclude="$MONGO_DB.*" --drop --archive=/sauvegardes/mongo_AAAA-MM-JJ.archive.gz --gzip`.
- **Pistes d'amélioration** : copie des sauvegardes hors du VPS (stockage S3 par exemple ; aujourd'hui elles protègent d'une erreur de manipulation, pas de la perte du serveur), limite de taille des envois au niveau du proxy.
