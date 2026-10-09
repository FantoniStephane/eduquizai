"""Connexion à MongoDB, la base des quiz.

Un seul client PyMongo est créé pour tout le processus, au premier besoin :
il gère lui-même un groupe de connexions réutilisées d'une requête à l'autre.
"""

from functools import cache

from django.conf import settings
from pymongo import MongoClient

# Délai au-delà duquel MongoDB est considérée comme indisponible (millisecondes)
DELAI_CONNEXION_MS = 3000


@cache
def get_client():
    """Retourne le client MongoDB unique (créé au premier appel)."""
    reglages = settings.MONGO
    return MongoClient(
        host=reglages["HOST"],
        port=reglages["PORT"],
        username=reglages["USER"],
        password=reglages["PASSWORD"],
        authSource="admin",
        serverSelectionTimeoutMS=DELAI_CONNEXION_MS,
        tz_aware=True,
    )


def get_db():
    """Retourne la base MongoDB de l'application (nom lu dans les réglages)."""
    return get_client()[settings.MONGO["NAME"]]
