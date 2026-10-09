"""Lanceur de tests : une base MongoDB de test, comme pour PostgreSQL.

Django crée automatiquement une base PostgreSQL « test_… » avant les tests et
la supprime après. Ce lanceur fait de même pour MongoDB : les tests
n'écrivent jamais dans la base de développement.
"""

from django.conf import settings
from django.test.runner import DiscoverRunner

from quiz.mongo import get_client, get_db
from quiz.schema import initialiser_collection


class EduQuizTestRunner(DiscoverRunner):
    """Ajoute la création et la suppression de la base MongoDB de test."""

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
