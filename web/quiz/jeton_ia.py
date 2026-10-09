"""Jeton JWT pour appeler le microservice IA.

L'application web signe elle-même un jeton de courte durée avec le secret
qu'elle partage avec le service IA. Le service n'enregistre aucun utilisateur :
il se contente de vérifier la signature, la date d'expiration, l'émetteur et le
destinataire du jeton.
"""

import time
import uuid

import jwt
from django.conf import settings

EMETTEUR = "eduquizai-web"
DESTINATAIRE = "eduquizai-ia"


def creer_jeton_ia(id_utilisateur):
    """Crée un jeton d'accès pour un appel à l'API du service IA.

    Args:
        id_utilisateur: identifiant de l'enseignant qui demande la génération
            (il sert de trace dans le jeton, pas de droit d'accès).

    Returns:
        Le jeton signé (HS256), à envoyer dans l'en-tête
        ``Authorization: Bearer <jeton>``.
    """
    maintenant = int(time.time())
    contenu = {
        "token_type": "access",
        "user_id": id_utilisateur,
        "jti": uuid.uuid4().hex,
        "iat": maintenant,
        "exp": maintenant + settings.IA["JWT_DUREE"],
        "iss": EMETTEUR,
        "aud": DESTINATAIRE,
    }
    return jwt.encode(contenu, settings.IA["JWT_SECRET"], algorithm="HS256")
