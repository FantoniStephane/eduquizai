"""Fournisseur « mistral » : API de Mistral AI (alternative au modèle local).

Le cahier des charges autorise un service externe ou un modèle local. L'API
Mistral sert d'alternative quand le poste n'est pas assez puissant pour
respecter le temps de génération : entreprise française, hébergement en
Europe. Contrepartie : le contenu des leçons est envoyé à Mistral, et une clé
d'API secrète est nécessaire (variable MISTRAL_API_KEY du fichier .env).
"""

import requests
from django.conf import settings

from .erreurs import DelaiDepasseError, IAIndisponibleError

DELAI_CONNEXION = 5


def _detail(reponse):
    """Message d'erreur renvoyé par l'API, pour comprendre un refus."""
    try:
        detail = reponse.json().get("message")
    except (ValueError, AttributeError):
        detail = None
    return f" ({str(detail)[:200]})" if detail else ""


def appeler_mistral(messages, schema, modele=None):
    """Envoie les messages à l'API Mistral et retourne le texte de sa réponse.

    Args:
        messages: consignes et demande (voir prompt.construire_messages).
        schema: schéma JSON imposé à la réponse (« structured outputs »).
        modele: nom du modèle ; par défaut, celui des réglages.

    Returns:
        Le texte produit par le modèle (normalement du JSON).

    Raises:
        IAIndisponibleError: clé absente ou refusée, quota dépassé, erreur de
            l'API ou connexion impossible.
        DelaiDepasseError: pas de réponse dans le délai maximum.
    """
    reglages = settings.MISTRAL
    if not reglages["CLE"]:
        raise IAIndisponibleError("Aucune clé d'API Mistral n'est configurée.")
    try:
        reponse = requests.post(
            f"{reglages['URL']}/v1/chat/completions",
            headers={"Authorization": f"Bearer {reglages['CLE']}"},
            json={
                "model": modele or reglages["MODELE"],
                "messages": messages,
                "temperature": 0.2,
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {"name": "quiz", "schema": schema, "strict": True},
                },
            },
            timeout=(DELAI_CONNEXION, reglages["DELAI"]),
        )
    except requests.ConnectionError as exc:
        raise IAIndisponibleError("Le service d'IA ne répond pas.") from exc
    except requests.Timeout as exc:
        raise DelaiDepasseError("La génération a dépassé le délai maximum.") from exc

    if reponse.status_code in (401, 403):
        raise IAIndisponibleError(
            f"La clé d'API Mistral est refusée{_detail(reponse)}."
        )
    if reponse.status_code == 429:
        raise IAIndisponibleError(
            f"Limite d'utilisation de l'API Mistral atteinte{_detail(reponse)}."
        )
    if reponse.status_code != 200:
        raise IAIndisponibleError(
            f"Le service d'IA a renvoyé une erreur ({reponse.status_code})"
            f"{_detail(reponse)}."
        )
    try:
        return reponse.json()["choices"][0]["message"]["content"]
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        raise IAIndisponibleError("Réponse inattendue du service d'IA.") from exc
