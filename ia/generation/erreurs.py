"""Erreurs de génération, communes à tous les fournisseurs d'IA.

Qu'il s'agisse du modèle local (Ollama) ou de l'API Mistral, chaque problème
technique est traduit dans l'une de ces erreurs : le reste de l'application
n'a pas à savoir quel fournisseur est utilisé.
"""


class ErreurIAError(Exception):
    """Erreur commune à tous les problèmes de génération."""


class IAIndisponibleError(ErreurIAError):
    """Le service d'IA ne répond pas ou refuse la demande."""


class DelaiDepasseError(ErreurIAError):
    """Le service d'IA n'a pas répondu dans le délai maximum."""
