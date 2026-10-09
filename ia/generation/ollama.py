"""Appel au modèle de langage local (API HTTP d'Ollama).

Chaque problème technique est traduit en une erreur explicite, que
l'application transforme en message compréhensible pour l'enseignant.
"""

import requests
from django.conf import settings

# Délai pour établir la connexion avec Ollama (secondes)
DELAI_CONNEXION = 3


class ErreurIAError(Exception):
    """Erreur commune à tous les problèmes de génération."""


class IAIndisponibleError(ErreurIAError):
    """Ollama ne répond pas ou refuse la demande (service arrêté, modèle absent)."""


class DelaiDepasseError(ErreurIAError):
    """Ollama n'a pas répondu dans le délai maximum."""


def appeler_ollama(messages, schema):
    """Envoie les messages au modèle et retourne le texte de sa réponse.

    Args:
        messages: consignes et demande (voir prompt.construire_messages).
        schema: schéma JSON imposé à la réponse.

    Returns:
        Le texte produit par le modèle (normalement du JSON).

    Raises:
        IAIndisponibleError: connexion impossible ou erreur renvoyée par Ollama.
        DelaiDepasseError: pas de réponse dans le délai maximum.
    """
    reglages = settings.OLLAMA
    try:
        reponse = requests.post(
            f"{reglages['URL']}/api/chat",
            json={
                "model": reglages["MODELE"],
                "messages": messages,
                "format": schema,
                "stream": False,
                # Peu de hasard : des réponses plus régulières et plus fiables
                "options": {"temperature": 0.2},
            },
            timeout=(DELAI_CONNEXION, reglages["DELAI"]),
        )
    except requests.ConnectionError as exc:
        raise IAIndisponibleError("Le service d'IA ne répond pas.") from exc
    except requests.Timeout as exc:
        raise DelaiDepasseError("La génération a dépassé le délai maximum.") from exc

    if reponse.status_code != 200:
        raise IAIndisponibleError(
            f"Le service d'IA a renvoyé une erreur ({reponse.status_code})."
        )
    try:
        return reponse.json()["message"]["content"]
    except (ValueError, KeyError, TypeError) as exc:
        raise IAIndisponibleError("Réponse inattendue du service d'IA.") from exc
