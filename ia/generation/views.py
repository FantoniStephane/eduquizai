"""API de génération de quiz, réservée à l'application web."""

import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .erreurs import DelaiDepasseError, IAIndisponibleError
from .service import generer_quiz
from .validation import ParametresInvalidesError, ReponseInvalideError

logger = logging.getLogger(__name__)


def _erreur(message, code):
    """Réponse d'erreur au format JSON {"detail": ...}."""
    return Response({"detail": message}, status=code)


class GenererQuizView(APIView):
    """POST /api/generer-quiz/ : génère les questions d'un quiz.

    Corps JSON attendu : contenu, difficulte, types, nombre. Un jeton JWT
    valide est obligatoire (en-tête « Authorization: Bearer … »).

    Les messages d'erreur renvoyés sont volontairement génériques : le détail
    technique (adresse du service d'IA, réponse brute du modèle) reste dans
    les journaux du service et n'est jamais transmis à l'appelant.
    """

    def post(self, request):
        """Génère le quiz demandé ou renvoie une erreur adaptée."""
        donnees = request.data if isinstance(request.data, dict) else {}
        try:
            questions = generer_quiz(
                donnees.get("contenu"),
                difficulte=donnees.get("difficulte"),
                types=donnees.get("types"),
                nombre=donnees.get("nombre"),
            )
        except ParametresInvalidesError as erreur:
            return _erreur(str(erreur), status.HTTP_400_BAD_REQUEST)
        except DelaiDepasseError:
            logger.warning("Génération : délai dépassé", exc_info=True)
            return _erreur(
                "L'IA n'a pas répondu à temps.", status.HTTP_504_GATEWAY_TIMEOUT
            )
        except IAIndisponibleError:
            logger.warning("Génération : IA indisponible", exc_info=True)
            return _erreur(
                "L'IA est indisponible.", status.HTTP_503_SERVICE_UNAVAILABLE
            )
        except ReponseInvalideError:
            logger.warning("Génération : réponse invalide", exc_info=True)
            return _erreur(
                "L'IA n'a pas produit de quiz valide.", status.HTTP_502_BAD_GATEWAY
            )
        return Response({"questions": questions})
