"""Client du microservice IA : demande la génération des questions d'un quiz.

Seul point de contact de l'application web avec le microservice. L'appel est
authentifié par un jeton JWT de courte durée et limité dans le temps. Toute
erreur est ramenée à une seule exception dont le message peut être montré à
l'enseignant : le détail technique reste dans les journaux.
"""

import logging

import requests
from django.conf import settings

from .jeton_ia import creer_jeton_ia

logger = logging.getLogger(__name__)

# Délai pour établir la connexion avec le microservice (secondes)
DELAI_CONNEXION = 3

MESSAGE_GENERIQUE = "La génération a échoué. Réessayez dans quelques instants."
MESSAGES = {
    400: "Les réglages de génération sont invalides. Vérifiez-les et réessayez.",
    502: "L'IA n'a pas produit de quiz valide. Réessayez, ou demandez moins de "
    "questions.",
    503: "L'IA est indisponible pour le moment. Réessayez dans quelques instants.",
    504: "L'IA n'a pas répondu à temps. Réessayez, ou demandez moins de questions.",
}


class GenerationIAError(Exception):
    """La génération a échoué ; le message est destiné à l'enseignant."""


def generer_questions(id_utilisateur, contenu, difficulte, types, nombre):
    """Demande au microservice IA les questions d'un quiz.

    Args:
        id_utilisateur: enseignant qui demande la génération (trace du jeton).
        contenu: texte de la leçon (Markdown).
        difficulte: « facile », « moyen » ou « difficile ».
        types: types de questions voulus (« qcm », « vrai_faux », « ouverte »).
        nombre: nombre de questions voulu.

    Returns:
        La liste des questions, au format de l'application (choix avec
        « est_correct »).

    Raises:
        GenerationIAError: service injoignable, trop lent ou réponse refusée.
    """
    reglages = settings.IA
    try:
        reponse = requests.post(
            f"{reglages['URL']}/api/generer-quiz/",
            json={
                "contenu": contenu,
                "difficulte": difficulte,
                "types": list(types),
                "nombre": nombre,
            },
            headers={"Authorization": f"Bearer {creer_jeton_ia(id_utilisateur)}"},
            timeout=(DELAI_CONNEXION, reglages["DELAI"]),
        )
    except requests.ConnectionError as exc:
        logger.warning("Service IA injoignable", exc_info=True)
        raise GenerationIAError(MESSAGES[503]) from exc
    except requests.Timeout as exc:
        logger.warning("Service IA : délai dépassé", exc_info=True)
        raise GenerationIAError(MESSAGES[504]) from exc
    except requests.RequestException as exc:
        logger.warning("Service IA : erreur d'appel", exc_info=True)
        raise GenerationIAError(MESSAGE_GENERIQUE) from exc

    if reponse.status_code != 200:
        # 401 : jeton refusé, donc secret partagé incorrect (erreur de réglage)
        logger.error("Service IA : réponse %s", reponse.status_code)
        raise GenerationIAError(MESSAGES.get(reponse.status_code, MESSAGE_GENERIQUE))
    try:
        questions = reponse.json()["questions"]
    except (ValueError, KeyError, TypeError) as exc:
        logger.error("Service IA : réponse illisible", exc_info=True)
        raise GenerationIAError(MESSAGE_GENERIQUE) from exc
    if not isinstance(questions, list) or not questions:
        logger.error("Service IA : aucune question reçue")
        raise GenerationIAError(MESSAGE_GENERIQUE)
    return questions
