"""Génération d'un quiz à partir d'une leçon.

Enchaîne les étapes : contrôle de la demande, construction du prompt, appel
du modèle et vérification de sa réponse. Si la réponse est invalide, une
seule nouvelle tentative est faite avant d'abandonner.
"""

from .ollama import appeler_ollama
from .prompt import construire_messages, schema_reponse
from .validation import ReponseInvalideError, valider_reponse, verifier_parametres

TENTATIVES = 2


def generer_quiz(contenu, *, difficulte, types, nombre):
    """Génère les questions d'un quiz à partir du contenu d'une leçon.

    Args:
        contenu: texte de la leçon (Markdown).
        difficulte: « facile », « moyen » ou « difficile ».
        types: liste des types autorisés (« qcm », « vrai_faux », « ouverte »).
        nombre: nombre de questions (3 à 20).

    Returns:
        La liste des questions vérifiées.

    Raises:
        ParametresInvalidesError: demande incorrecte.
        IAIndisponibleError, DelaiDepasseError: problème technique avec Ollama.
        ReponseInvalideError: réponse toujours invalide après deux tentatives.
    """
    verifier_parametres(contenu, difficulte, types, nombre)
    messages = construire_messages(contenu, difficulte, types, nombre)
    schema = schema_reponse(types, nombre)
    for tentative in range(1, TENTATIVES + 1):
        brut = appeler_ollama(messages, schema)
        try:
            return valider_reponse(brut, types, nombre)
        except ReponseInvalideError:
            if tentative == TENTATIVES:
                raise
