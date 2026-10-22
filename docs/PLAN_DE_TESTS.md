# Plan de tests — EduQuizAI

Ce document décrit comment l'application est testée : stratégie, outils, environnement, intégration continue, tests par fonctionnalité et recette des user stories.

**Lancer les tests** (conteneurs démarrés) :

```powershell
docker compose exec web python manage.py test   # application web
docker compose exec ia python manage.py test    # microservice IA
```

Couverture (venv activé, depuis `web/` ou `ia/`) : `python -m coverage run manage.py test` puis `python -m coverage report`.

## Stratégie de test

Chaque fonctionnalité est livrée avec ses tests, écrits en même temps que le code et lancés avant chaque commit puis par l'intégration continue. Pour chaque fonctionnalité, les tests couvrent quatre situations : le **cas nominal** (ce que l'enseignant attend), les **erreurs de saisie** (champ vide, valeur hors limites, fichier refusé), les **accès interdits** (non connecté, objet d'un collègue, mauvaise méthode, jeton CSRF absent) et les **pannes** (MongoDB ou IA indisponible, délai dépassé). Les tests portent un nom en français qui décrit la règle vérifiée (`test_suppression_bloquee_si_la_lecon_a_des_quiz`) : la liste des tests se lit comme la liste des règles de l'application.

Le plan suit les quatre niveaux de test classiques :

| Niveau | Ce qui est vérifié | Comment | Volume |
|---|---|---|---|
| Tests unitaires | Une fonction isolée, sans base de données ni réseau : conversion HTML ↔ Markdown, lecture d'un fichier importé, contrôle d'un quiz, construction du prompt, jeton JWT, PDF élève | `SimpleTestCase` de Django, doublures (`unittest.mock`) pour Ollama et Mistral | 65 tests (40 web, 25 microservice IA) |
| Tests d'intégration | Une page ou une API de bout en bout côté serveur : URL, vue, formulaire, gabarit, bases PostgreSQL et MongoDB de test, appel au microservice simulé | `TestCase` et client de test de Django, client de test de DRF pour l'API | 219 tests (213 web, 6 microservice IA) |
| Tests système | L'application complète dans ses conteneurs, avec le vrai modèle d'IA | Parcours manuel dans Chrome (ordinateur et mobile), console sans erreur CSP, Lighthouse, génération réelle (`essai_generation`, `mesure_generation`), essai d'injection de prompt, construction et démarrage des images Docker en CI | À chaque fonctionnalité terminée |
| Tests d'acceptation | Chaque user story, du point de vue de l'enseignant | Recette : critère d'acceptation vérifié à la main et couvert par des tests automatiques (tableau « Recette des user stories ») | 12 user stories |

## Outils de test

| Outil | Usage |
|---|---|
| Framework de test de Django (`unittest`) | Tests unitaires et d'intégration ; bases de test créées et supprimées à chaque lancement |
| `unittest.mock` | Doublures du microservice IA, d'Ollama, de l'API Mistral et des pannes de MongoDB |
| `coverage` | Mesure de la couverture du code, seuil minimal de 95 % |
| GitHub Actions | Relance de tous les contrôles à chaque push, sur une machine neuve |
| Ruff et `pip-audit` | Analyse statique du code et des dépendances avant les tests |
| Chrome (outils de développement), Lighthouse, script d'audit d'accessibilité | Rendu comparé aux maquettes, console (CSP), accessibilité |
| Commandes `essai_generation` et `mesure_generation` | Génération avec le vrai modèle, mesure du temps et de la validité des réponses |
| OWASP ZAP | Scan de l'application en fonctionnement, vue de l'extérieur comme par un attaquant (en-têtes, cookies, bibliothèques vulnérables, fuites d'informations) |

## Environnement de test

Les tests n'utilisent jamais les données de développement. À chaque lancement, Django crée une base PostgreSQL de test (`test_eduquizai`) et le lanceur de tests du projet (`config/test_runner.py`) crée de la même façon une base MongoDB de test, prépare sa règle de validation et ses index, puis supprime les deux bases à la fin. Chaque test part d'un état connu : les données qu'il crée sont annulées (transaction PostgreSQL) ou effacées (collection MongoDB) après lui.

Les services extérieurs sont remplacés par des **doublures** (`unittest.mock`) : le microservice IA, le modèle Ollama et l'API Mistral ne sont jamais appelés par les tests, ce qui les rend rapides, reproductibles et utilisables sans carte graphique. Pendant les tests seulement, les mots de passe sont hachés par un algorithme rapide : le hachage réel (PBKDF2, un million d'itérations) est volontairement lent pour freiner un attaquant, et il ralentissait chaque création de compte et chaque connexion des tests. Ce réglage n'existe que dans le lanceur de tests, la production n'est pas concernée : les 241 tests de l'application web passent de 53 s à 5 s. Les mêmes doublures simulent les pannes (MongoDB indisponible, IA injoignable, délai dépassé) pour vérifier les messages affichés.

## Données de démonstration

La commande `python manage.py donnees_demo` charge un jeu de données cohérent pour les démonstrations et les essais manuels : une enseignante, quatre leçons de collège (histoire, SVT, mathématiques, anglais) et trois quiz (un validé, deux en brouillon). Les situations utiles à la démonstration sont prévues : une leçon sans quiz (génération, suppression possible), une leçon avec quiz (suppression bloquée). Le mot de passe du compte n'est jamais écrit dans le code : il est passé en paramètre et contrôlé par les validateurs de Django. La commande refuse d'écraser des données existantes ; l'option `--reinitialiser` supprime d'abord les leçons et les quiz de cette seule enseignante, ce qui permet de remettre la démonstration à neuf sans toucher aux autres comptes. Cinq tests vérifient ce comportement.

## Intégration continue (GitHub Actions)

À chaque push sur `develop` ou `main`, et à chaque demande de fusion vers `main`, GitHub Actions vérifie le projet sur une machine neuve (`.github/workflows/ci.yml`). Les jobs s'enchaînent avec `needs` : si la qualité échoue, les tests ne sont pas lancés ; les images Docker ne sont construites, et plus tard déployées, qu'à partir d'un code qui passe tous les contrôles. Les images ne sont pas publiées sur un registre : au déploiement, la plateforme Coolify du serveur les reconstruit à partir du même code et des mêmes Dockerfiles ; la CI garantit que cette construction fonctionne.

| Job | Contrôles | Durée |
|---|---|---|
| Qualité | `pip-audit` (aucune dépendance avec une faille connue), Ruff (erreurs, style, mise en forme), `manage.py check` sur les deux projets Django | ~30 s |
| Tests du microservice IA | 31 tests, Ollama et Mistral remplacés par des doublures ; couverture | ~20 s |
| Tests de l'application web | 254 tests sur de vraies bases PostgreSQL 17 et MongoDB 7.0 (services GitHub ; MongoDB 8, utilisé en développement et en production, ne démarre pas sur le noyau Linux des machines GitHub depuis octobre 2026) ; couverture | ~1 min |
| Images Docker | Construction des images `web` et `ia` avec les Dockerfiles du projet, puis démarrage de l'application dans chaque image (`manage.py check`) ; taille des images dans le résumé du run (web : 220 Mo, ia : 157 Mo, sur une base `python:3.12-slim`). Lancé seulement si tous les tests passent | ~1 min |
| Déploiement | Seulement après un push sur `main` et si tout est vert : appel du webhook de Coolify (méthode POST, jeton d'API limité au déploiement) ; la réponse de Coolify est affichée, sans aucun secret | ~5 s, puis ~1 min de reconstruction sur le serveur |

- **Mêmes bases qu'en développement** : le compte MongoDB applicatif est créé par le script utilisé en local (`docker/mongo/initdb/01_utilisateur_app.js`), qui est ainsi vérifié lui aussi.
- **Aucun secret dans le dépôt** : les variables obligatoires reçoivent des valeurs de test, valables seulement sur la machine temporaire de GitHub ; le workflow n'a que le droit de lire le dépôt (`permissions: contents: read`).
- **Reproductibilité** : version de Python, de Ruff et système de la machine (`ubuntu-24.04`) fixés ; un nouveau push annule la vérification en cours sur la même branche. Le pipeline complet (4 jobs) dure environ 2 minutes.
- **Couverture** : mesurée par `coverage` sur le code applicatif seulement (tests, migrations et points d'entrée exclus, `.coveragerc`). Premier run : **97,6 %** pour l'application web (1 397 instructions) et **98,0 %** pour le microservice IA. Le tableau par fichier s'affiche dans le résumé du run, le rapport HTML est téléchargeable, et la CI **échoue sous 95 %** (`fail_under`) : la couverture ne peut pas baisser sans qu'on le voie.

## Tests par fonctionnalité

Au total, **284 tests automatiques** : 253 pour l'application web, 31 pour le microservice IA. Ils passent en 5 secondes en local et environ 2 minutes en CI (installation comprise).

| Fonctionnalité | Fichier de tests | Nb | Exemples de cas vérifiés |
|---|---|---|---|
| Comptes, invitation, connexion | `comptes/tests.py` | 11 | Compte créé sans mot de passe, administrateur envoyé dans l'administration (même arrivé par la page d'accueil), lien d'invitation à usage unique, compte désactivé refusé, déconnexion en POST seulement, message neutre « mot de passe oublié » |
| Limitation des essais de connexion | `comptes/tests_limitation.py` | 12 | Blocage au 6ᵉ échec même avec le bon mot de passe (compte administrateur compris), IP réelle lue derrière le proxy (IP inventée ignorée), blocage d'une IP qui essaie de nombreux comptes, autre IP non bloquée, même message pour un compte inexistant, aucune adresse en clair dans le cache |
| Leçons (modèle, éditeur, formulaire, pages) | `lecons/tests.py` | 45 | Conversion HTML → Markdown sans perte, script et image piégée supprimés, 20 000 caractères maximum, liste limitée à mes leçons, recherche et filtres, pagination, suppression bloquée si la leçon a des quiz, MongoDB en panne |
| Import d'un fichier texte | `lecons/tests_importation.py` | 20 | .txt (UTF-8 et Windows) et .docx, faux .docx, bombe ZIP, fichier trop gros, texte trop long refusé sans coupure |
| Accès aux quiz (MongoDB) | `quiz/tests.py` | 20 | Contrôle d'un quiz, quiz d'un collègue introuvable, identifiants invalides, règle de validation de la collection, suppression d'un compte → ses quiz supprimés, jeton JWT |
| Génération d'un quiz | `quiz/tests_generation.py` | 25 | Brouillon créé, appel authentifié au microservice, leçon d'un collègue refusée, nombre de questions hors limites, IA injoignable ou trop lente, réponse invalide de l'IA, annulation sans enregistrement |
| Visualisation d'un quiz | `quiz/tests_detail.py` | 12 | Questions, choix, bonne réponse et explication affichés ; alerte « À relire » pour un brouillon ; 404 identique pour un quiz d'autrui ou un identifiant invalide ; 503 si MongoDB est en panne |
| Validation | `quiz/tests_validation.py` | 10 | POST + CSRF uniquement, quiz d'autrui intouchable, quiz déjà validé inchangé, MongoDB en panne |
| Modification | `quiz/tests_modification.py` | 16 | Champs inconnus ignorés, type de question non modifiable, au moins une question, saisie conservée en cas d'erreur, quiz validé repassé en brouillon |
| Suppression | `quiz/tests_suppression.py` | 9 | Confirmation, POST + CSRF, quiz d'autrui introuvable |
| Liste des quiz | `quiz/tests_vues.py` | 13 | Liste limitée à mes quiz, filtre par leçon limité à mes leçons, colonnes lues dans MongoDB |
| Export PDF élève | `quiz/tests_export.py` | 20 | Aucune réponse ni explication dans la version élève, quiz brouillon refusé, quiz d'autrui introuvable, en-têtes de téléchargement, nom du fichier, textes échappés |
| Tableau de bord | `config/tests_tableau_de_bord.py` | 9 | Trois chiffres, derniers brouillons et dernières leçons de l'enseignant seulement, MongoDB en panne |
| Sécurité transverse | `config/tests_securite.py`, `config/tests_entetes.py` | 17 | Redirection ouverte, fixation de session, mots de passe faibles, administration (page de connexion unique, pas de boucle pour un enseignant), XSS stocké sur 5 pages, CSP et en-têtes ajoutés après le scan ZAP sur toutes les pages, cookie CSRF `HttpOnly`, fichiers statiques avec les en-têtes |
| Pages d'erreur, gabarits, données personnelles | `config/tests_erreurs.py`, `config/tests.py`, `config/tests_donnees_personnelles.py` | 9 | 404, 403, formulaire expiré et 500 sans détail technique ; page RGPD accessible sans connexion |
| Données de démonstration | `quiz/tests_donnees_demo.py` | 5 | Refus d'écraser des données, réinitialisation limitée à l'enseignante de démonstration |
| Microservice IA : génération | `ia/generation/tests.py` | 25 | Leçon encadrée dans le prompt, fausse balise neutralisée, schéma JSON par type, nouvelle tentative indiquant au modèle la règle non respectée puis abandon, refus journalisé sans le texte de la leçon, Ollama arrêté, délai dépassé, Mistral choisi par réglage, aucun appel sans clé |
| Microservice IA : API | `ia/generation/tests_api.py` | 6 | Jetons invalides et `alg: none` refusés (401), GET refusé (405), paramètres invalides, erreurs de l'IA transmises proprement |

## Recette des user stories

Chaque user story est acceptée quand son critère est vérifié à la main dans l'application et couvert par des tests automatiques.

| US | Critère d'acceptation | Tests automatiques | Vérification manuelle | Statut |
|---|---|---|---|---|
| US1 | L'administrateur crée un compte sans mot de passe ; l'enseignant choisit le sien par un lien d'invitation | `comptes/tests.py` (invitation) | Compte créé dans l'administration, lien lu dans les journaux, mot de passe choisi | Validée |
| US2 | Connexion et déconnexion ; pages protégées ; blocage après 5 échecs | `comptes/`, `config/tests_securite.py` | Connexion, déconnexion, blocage au 6ᵉ essai | Validée |
| US3 | Leçon créée avec titre, matière, niveau et contenu mis en forme | `lecons/tests.py` | Saisie avec gras, italique et puces dans l'éditeur | Validée |
| US4 | Quiz généré à partir d'une leçon selon le nombre et les types de questions choisis | `quiz/tests_generation.py`, `ia/` | Génération réelle avec le modèle local et avec Mistral, temps mesuré | Validée |
| US5 | Questions, choix, bonne réponse et explication affichés | `quiz/tests_detail.py` | Comparaison avec la maquette 08 (ordinateur et mobile) | Validée |
| US6 | Le quiz passe de « brouillon » à « validé » après confirmation | `quiz/tests_validation.py` | Fenêtre de confirmation, badge mis à jour | Validée |
| US7 | Listes de mes leçons et de mes quiz, avec recherche et filtres | `lecons/tests.py`, `quiz/tests_vues.py`, `config/tests_tableau_de_bord.py` | Listes et tableau de bord comparés aux maquettes 02, 03 et 06 | Validée |
| US8 | Un compte désactivé ne peut plus se connecter ; un compte supprimé emporte ses leçons et ses quiz | `comptes/tests.py`, `lecons/tests.py`, `quiz/tests.py` | Désactivation et suppression dans l'administration | Validée |
| US9 | Le microservice renvoie un quiz JSON conforme au schéma, ou une erreur claire | `ia/generation/` | Commande `essai_generation` avec le vrai modèle | Validée |
| US10 | Contenu d'un .txt ou d'un .docx repris dans l'éditeur ; fichiers dangereux refusés | `lecons/tests_importation.py` | Les 8 fichiers du dossier `docs/jeu_essai_import/` | Validée |
| US11 | PDF élève sans les réponses, pour un quiz validé uniquement | `quiz/tests_export.py` | PDF ouvert et relu ; bouton grisé pour un brouillon | Validée |
| US12 | Modification et suppression de mes leçons et de mes quiz, jamais de ceux d'un collègue | `lecons/tests.py`, `quiz/tests_modification.py`, `quiz/tests_suppression.py` | Parcours complet ; suppression d'une leçon avec quiz refusée (maquette 10b) | Validée |

## Limites des tests automatiques

- **Le JavaScript** (éditeur Trix, fenêtres de confirmation, écran d'attente, fenêtre d'import) n'est pas exécuté par les tests Django : il est vérifié à la main dans Chrome. Les tests vérifient en revanche ce que le serveur reçoit, y compris un texte envoyé sans JavaScript.
- **La qualité des réponses de l'IA** ne peut pas être prouvée par un test : les tests vérifient la structure du quiz, pas la justesse des questions. C'est la raison de la validation humaine obligatoire (US6).
- **Le rendu visuel** est comparé aux maquettes à la main, sur ordinateur et sur mobile.
- Amélioration possible : automatiser le parcours complet dans un vrai navigateur (Playwright) pour vérifier aussi le JavaScript à chaque push.
