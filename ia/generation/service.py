"""Génération d'un quiz à partir d'une leçon.

Enchaîne les étapes : contrôle de la demande, construction du prompt, appel
du fournisseur d'IA choisi dans les réglages (modèle local Ollama ou API
Mistral) et vérification de sa réponse. Si la réponse est invalide, une
seule nouvelle tentative est faite avant d'abandonner.
"""

from django.conf import settings

from .mistral import appeler_mistral
from .ollama import appeler_ollama
from .prompt import construire_messages, schema_reponse
from .validation import ReponseInvalideError, valider_reponse, verifier_parametres

TENTATIVES = 2

# Un fournisseur = une fonction (messages, schéma, modèle) -> texte JSON.
# Ajouter un fournisseur ne change rien au reste de l'application.
FOURNISSEURS = {
    "ollama": appeler_ollama,
    "mistral": appeler_mistral,
}


def generer_quiz(contenu, *, difficulte, types, nombre, fournisseur=None, modele=None):
    """Génère les questions d'un quiz à partir du contenu d'une leçon.

    Args:
        contenu: texte de la leçon (Markdown).
        difficulte: « facile », « moyen » ou « difficile ».
        types: liste des types autorisés (« qcm », « vrai_faux », « ouverte »).
        nombre: nombre de questions (3 à 20).
        fournisseur: « ollama » ou « mistral » ; par défaut, celui des réglages.
        modele: nom du modèle ; par défaut, celui du fournisseur.

    Returns:
        La liste des questions vérifiées.

    Raises:
        ParametresInvalidesError: demande incorrecte.
        IAIndisponibleError, DelaiDepasseError: problème technique avec l'IA.
        ReponseInvalideError: réponse toujours invalide après deux tentatives.
    """
    verifier_parametres(contenu, difficulte, types, nombre)
    appeler = FOURNISSEURS[fournisseur or settings.IA_FOURNISSEUR]
    messages = construire_messages(contenu, difficulte, types, nombre)
    schema = schema_reponse(types, nombre)
    for tentative in range(1, TENTATIVES + 1):
        brut = appeler(messages, schema, modele)
        try:
            return valider_reponse(brut, types, nombre)
        except ReponseInvalideError:
            if tentative == TENTATIVES:
                raise
