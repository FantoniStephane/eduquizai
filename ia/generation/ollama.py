"""Fournisseur « ollama » : modèle de langage local (API HTTP d'Ollama).

Choix par défaut : les leçons ne quittent pas l'infrastructure.
"""

import requests
from django.conf import settings

from .erreurs import DelaiDepasseError, IAIndisponibleError

# Délai pour établir la connexion avec Ollama (secondes)
DELAI_CONNEXION = 3
# Contexte de 2 048 jetons : assez pour la plus longue leçon (20 000
# caractères) et assez petit pour que tout le modèle tienne dans les 4 Go de
# la carte graphique (avec 4 096, 20 % du calcul passait par le processeur).
CONTEXTE = 2048
# Le modèle reste chargé 30 minutes après le dernier appel (5 par défaut) :
# on évite de le recharger à chaque génération.
GARDER_EN_MEMOIRE = "30m"


def appeler_ollama(messages, schema, modele=None):
    """Envoie les messages au modèle local et retourne le texte de sa réponse.

    Args:
        messages: consignes et demande (voir prompt.construire_messages).
        schema: schéma JSON imposé à la réponse (sorties structurées).
        modele: nom du modèle ; par défaut, celui des réglages.

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
                "model": modele or reglages["MODELE"],
                "messages": messages,
                "format": schema,
                "stream": False,
                "keep_alive": GARDER_EN_MEMOIRE,
                # Peu de hasard : des réponses plus régulières et plus fiables
                "options": {"temperature": 0.2, "num_ctx": CONTEXTE},
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
