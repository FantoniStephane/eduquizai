"""Lanceur de tests du microservice IA.

Il rend la sortie des tests lisible : les refus et les pannes simulés
(réponse invalide du modèle, IA indisponible, délai dépassé) sont journalisés
par le service et les vues, et ces journaux ne sont plus affichés dans la
console. Les tests qui les vérifient (assertLogs) les reçoivent toujours.
"""

import logging

from django.test.runner import DiscoverRunner


class IaTestRunner(DiscoverRunner):
    """Journaux masqués pendant les tests."""

    def setup_test_environment(self, **kwargs):
        """Masque les journaux pendant les tests.

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
