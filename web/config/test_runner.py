"""Lanceur de tests : une base MongoDB de test, comme pour PostgreSQL.

Django crée automatiquement une base PostgreSQL « test_… » avant les tests et
la supprime après. Ce lanceur fait de même pour MongoDB : les tests
n'écrivent jamais dans la base de développement.

Il rend aussi la sortie des tests lisible : les pannes simulées (MongoDB ou
IA indisponibles) sont journalisées par les vues, et ces journaux ne sont plus
affichés dans la console. Les tests qui les vérifient (assertLogs) les
reçoivent toujours.
"""

import logging

from django.conf import settings
from django.test.runner import DiscoverRunner

from quiz.mongo import get_client, get_db
from quiz.schema import initialiser_collection


class EduQuizTestRunner(DiscoverRunner):
    """Ajoute la base MongoDB de test et masque les journaux pendant les tests."""

    def setup_test_environment(self, **kwargs):
        """Prépare l'environnement de test, sans affichage des journaux.

        Un gestionnaire « vide » sur le journal racine remplace l'affichage par
        défaut de Python (messages et traces sur la sortie d'erreur).
        """
        super().setup_test_environment(**kwargs)
        self._journal_muet = logging.NullHandler()
        logging.getLogger().addHandler(self._journal_muet)

    def teardown_test_environment(self, **kwargs):
        """Rétablit l'affichage des journaux, puis l'environnement normal."""
        logging.getLogger().removeHandler(self._journal_muet)
        super().teardown_test_environment(**kwargs)

    def setup_databases(self, **kwargs):
        """Crée les bases de test (PostgreSQL par Django, puis MongoDB)."""
        anciennes_bases = super().setup_databases(**kwargs)
        settings.MONGO = {**settings.MONGO, "NAME": f"test_{settings.MONGO['NAME']}"}
        get_client().drop_database(settings.MONGO["NAME"])
        initialiser_collection(get_db())
        return anciennes_bases

    def teardown_databases(self, old_config, **kwargs):
        """Supprime la base MongoDB de test, puis celles de PostgreSQL."""
        get_client().drop_database(settings.MONGO["NAME"])
        super().teardown_databases(old_config, **kwargs)
