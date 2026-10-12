# Journal de veille — EduQuizAI

Veille technologique et réglementaire menée pendant le projet. Chaque entrée indique la **source consultée**, ce qui en a été **retenu** et l'**impact** sur EduQuizAI. Dernière consultation des sources : **12/10/2026**.

## Méthode

- **Automatique, à chaque push** : `pip-audit` dans la CI (job « Qualité ») sur les dépendances web et IA ; échec du pipeline si une vulnérabilité connue est détectée.
- **Manuelle, ponctuelle** : lecture des avis de sécurité Django, des avis GitHub (GHSA) des bibliothèques JavaScript embarquées, des référentiels OWASP, des publications de la CNIL et des conditions du fournisseur d'IA.
- **Constats de terrain** : les changements rencontrés pendant le projet (ex. Coolify) sont consignés ici.
- **Règle** : une entrée n'est inscrite que si la source a été lue ; l'impact est évalué sur le code réel du projet.

## Synthèse

| # | Axe | Sujet | Impact sur EduQuizAI | Suite |
|---|---|---|---|---|
| 1 | Sécurité | Correctifs Django 5.2.13 (avril 2026) | Faible (admin, ASGI non utilisé) ; DoS multipart concerne l'import | Rester sur la dernière 5.2.x |
| 2 | Sécurité | Correctifs Django 5.2.17 (août 2026) | Nul à faible (GIS, `URLField`, `set_language` non utilisés) | Idem |
| 3 | Sécurité | OWASP Top 10 pour LLM 2025 — LLM01 injection de prompt | Mesures déjà en place, test réalisé (tâche 34) | Décrit en partie 8 |
| 4 | Sécurité | DOMPurify dans Trix (GHSA-gvmj-g25r-r7wr) | Risque résiduel accepté | Mettre à jour dès qu'un Trix embarque DOMPurify ≥ 3.4.8 |
| 5 | Déploiement | Coolify 4.4 : le webhook de déploiement passe en POST | Job CI corrigé | Documenté dans `docs/DEPLOIEMENT.md` |
| 6 | IA / RGPD | Offre gratuite Mistral : requêtes utilisables pour l'entraînement | Leçons d'exemple uniquement | Offre payante ou refus de l'entraînement en vraie mise en service |
| 7 | IA / RGPD | Recommandations CNIL sur les systèmes d'IA (juillet 2025) | Cadre de la partie 8 (RGPD) | À relire avant une vraie mise en service |
| 8 | Réglementation | AI Act : calendrier (report des systèmes à haut risque au 02/12/2027) | Pas d'obligation de haut risque identifiée à ce stade | À reconfirmer avant une mise en service réelle |
| 9 | Accessibilité | RGAA 4.1.2 → RGAA 5 (WCAG 2.2) annoncé | Vérification actuelle faite en RGAA 4.1 | Contrôler focus et taille des cibles (WCAG 2.2) |

## Entrées détaillées

### 1. Django 5.2.13 — correctifs de sécurité du 07/04/2026

- **Source** : annonce officielle Django du 7 avril 2026 (versions 6.0.4, 5.2.13, 4.2.30) ; la branche 4.2 y atteint la fin de son support.
- **Retenu** : 5 CVE — CVE-2026-33033 (modérée, `MultiPartParser` : envois multipart en base64 avec beaucoup d'espaces → déni de service) ; CVE-2026-3902 et CVE-2026-33034 (faibles, ASGI) ; CVE-2026-4277 et CVE-2026-4292 (faibles, admin : permissions d'ajout via POST forgés).
- **Impact** : EduQuizAI tourne sous Gunicorn (WSGI) : les deux CVE ASGI ne s'appliquent pas. L'admin ne sert qu'aux comptes. Le déni de service multipart concerne l'**import de fichier** (5 Mo contrôlés par l'application) : la limite de taille côté serveur web reste un point listé dans les limites du déploiement.
- **Action** : `Django>=5.2,<5.3` accepte les correctifs à chaque reconstruction de l'image ; `pip-audit` signale tout retard.

### 2. Django 5.2.17 — correctifs de sécurité du 04/08/2026

- **Source** : notes de version Django 5.2.17.
- **Retenu** : CVE-2026-15307 (élevée, GIS : lookups spatiaux, `GDALRaster`), CVE-2026-15830 (modérée, GIS : `GEOSGeometry`), CVE-2026-15920 (modérée, admin : `URLField` rendu en lien cliquable), CVE-2026-15337 (faible, i18n : `check_for_language`, vue `set_language` non active par défaut).
- **Impact** : une recherche dans le code (12/10) ne trouve ni `django.contrib.gis`, ni `URLField`, ni `set_language` : **aucune des quatre failles n'est atteignable**. La mise à jour reste recommandée.
- **Version en production** : Django **5.2.18** (relevée le 12/10/2026), donc postérieure à la 5.2.17 : les correctifs ci-dessus sont inclus.

### 3. OWASP Top 10 pour les applications LLM (2025) — LLM01 injection de prompt

- **Source** : fiche OWASP GenAI « LLM01:2025 Prompt Injection ».
- **Retenu** : injection directe (le texte de l'utilisateur modifie le comportement du modèle) et indirecte (contenu externe). L'OWASP indique qu'aucune prévention n'est infaillible ; les mesures visent à **limiter l'impact** : définir et **valider le format de sortie par du code déterministe**, moindre privilège, **approbation humaine** pour les actions à risque, tests d'intrusion en traitant le modèle comme non fiable.
- **Impact** : EduQuizAI applique déjà ces mesures — schéma JSON par type de question et contrôles Python sur la sortie du modèle (microservice IA), microservice sans accès à la base de données, jeton JWT de 2 minutes, **quiz toujours créé en brouillon puis validé par l'enseignant**. Un essai d'injection a été joué avec le vrai modèle (tâche 34).
- **Limite assumée** : un contenu faux mais bien formé n'est pas détecté automatiquement → validation humaine.

### 4. DOMPurify embarqué dans Trix — GHSA-gvmj-g25r-r7wr

- **Source** : base d'avis GitLab (publié le 15/06/2026, mis à jour le 23/07/2026) ; registre npm de Trix.
- **Retenu** : gravité **moyenne** (CVSS 3.1 : 5.4, CWE-79). Versions de DOMPurify concernées : de 3.0.0 à avant 3.4.8 ; corrigé en **3.4.8**. Le contournement de `SAFE_FOR_TEMPLATES` ne joue qu'avec les modes de sortie DOM (`RETURN_DOM`, `RETURN_DOM_FRAGMENT`, `IN_PLACE`). Trix 2.1.19 (dernière version) déclare `dompurify ^3.2.5` ; la copie livrée dans le fichier JavaScript du projet est en 3.4.2.
- **Impact** : DOMPurify ne nettoie que le texte collé dans l'éditeur ; le contenu est de toute façon nettoyé par le serveur (`nh3`) à l'enregistrement et à l'affichage, et la CSP bloque les scripts injectés.
- **Décision (Stéphane, 12/10)** : risque résiduel **accepté et surveillé**, sans recompiler Trix. **Seuil de mise à jour** : une version de Trix qui embarque DOMPurify ≥ 3.4.8.

### 5. Coolify 4.4 — l'appel de déploiement passe en POST

- **Source** : constat direct, tâche 46 (12/10/2026) — pas de source externe consultée.
- **Retenu** : l'appel `GET` du webhook de déploiement répond **405** « This endpoint has changed to a POST request ». Le job de déploiement de la CI affiche maintenant la réponse de Coolify (sans secret) et utilise `curl --request POST`.
- **Impact / suite** : à surveiller à chaque montée de version de Coolify ; procédure dans `docs/DEPLOIEMENT.md`.

### 6. Mistral — données de l'offre gratuite

- **Source** : centre d'aide Mistral, article « How can I try the API for free with the Experiment plan ? » : « API requests made under the Experiment plan may be used to train Mistral's models ». Un autre article décrit un réglage « Anonymous improvement data » (panneau d'administration, menu Privacy) pour refuser l'utilisation des appels API ; il ne précise pas le réglage par défaut selon l'offre.
- **Impact** : le fournisseur par défaut est Mistral depuis le 12/10 → **uniquement des leçons d'exemple** tant que l'offre est gratuite. Pour une vraie mise en service : offre payante et/ou refus de l'entraînement, à vérifier dans les conditions en vigueur.

### 7. CNIL — recommandations sur le développement des systèmes d'IA

- **Source** : page CNIL « IA : la CNIL finalise ses recommandations sur le développement des systèmes d'IA » (22/07/2025).
- **Retenu** : le RGPD s'applique dans de nombreux cas aux modèles entraînés sur des données personnelles ; fiches sur l'annotation, la sécurité du développement et une liste de points à vérifier ; deux FAQ sur l'IA dans l'éducation déjà publiées.
- **Impact** : EduQuizAI n'entraîne aucun modèle ; il envoie des textes de leçons à un fournisseur. Les points à retenir sont la minimisation (aucune donnée d'élève), l'information de l'enseignant et le choix du fournisseur (entrée 6). Voir la partie 8 (RGPD). Les FAQ « éducation » sont à lire avant une mise en service.

### 8. AI Act — calendrier

- **Source** : page de synthèse donneespersonnelles.fr (mise à jour le 13/09/2026) — source secondaire, à confirmer sur EUR-Lex avant toute décision.
- **Retenu** : le règlement dit « omnibus » (UE 2026/1744, en vigueur le 27/07/2026) repousse les obligations des systèmes à haut risque de l'annexe III au **02/12/2027**. Date générale d'application inchangée : 02/08/2026 (dont les obligations de transparence).
- **Impact** : EduQuizAI sert à **préparer des supports** relus par l'enseignant ; il n'évalue ni ne classe automatiquement les élèves. Aucune obligation de haut risque n'est identifiée à ce stade (analyse du candidat, pas un avis juridique). Les obligations de transparence sont à relire si le produit devient public.

### 9. Accessibilité — RGAA 4.1.2 vers RGAA 5

- **Source** : article binclusive.io sur le RGAA 5 — source secondaire : annonce de la DINUM du 02/03/2026, publication prévue avant fin 2026, fondée sur WCAG 2.2.
- **Retenu** : WCAG 2.2 ajoute neuf critères A/AA (visibilité du focus, taille minimale des cibles, alternatives au glisser-déposer, aide cohérente, saisie redondante, authentification accessible).
- **Impact** : l'audit du projet est fait en RGAA 4.1 (Lighthouse 100 sur trois pages). **À contrôler** : taille des cibles et visibilité du focus sur les boutons d'action des listes.

## Sources consultées (12/10/2026)

- Django — annonce du 07/04/2026 et notes de la version 5.2.17 (docs.djangoproject.com).
- OWASP GenAI — LLM01:2025 Prompt Injection (genai.owasp.org).
- GitLab Advisory Database — GHSA-gvmj-g25r-r7wr ; registre npm — trix.
- Mistral — centre d'aide, articles 455206 et 455207 (help.mistral.ai).
- CNIL — recommandations IA (cnil.fr).
- donneespersonnelles.fr — calendrier de l'AI Act ; binclusive.io — RGAA 5.
