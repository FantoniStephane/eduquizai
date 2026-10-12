from django.contrib.auth.models import AnonymousUser
from django.template.loader import render_to_string
from django.test import RequestFactory, SimpleTestCase

from comptes.models import Utilisateur


class GabaritsTests(SimpleTestCase):
    """Vérifie le rendu des gabarits de base (tâche 19)."""

    def setUp(self):
        """Prépare une requête HTTP factice."""
        self.requete = RequestFactory().get("/")

    def test_gabarit_connexion(self):
        """La page hors connexion affiche le logo et la mise en page centrée."""
        self.requete.user = AnonymousUser()
        html = render_to_string("base_connexion.html", request=self.requete)
        self.assertIn('lang="fr"', html)
        self.assertIn('class="page-connexion"', html)
        self.assertIn("img/logo.svg", html)

    def test_gabarit_connecte(self):
        """L'espace enseignant affiche la navigation et l'utilisateur connecté."""
        self.requete.user = Utilisateur(nom="Durand", prenom="Marie")
        html = render_to_string("base_connecte.html", request=self.requete)
        self.assertIn('href="#contenu"', html)
        self.assertIn('aria-label="Navigation principale"', html)
        self.assertIn(">MD<", html)
        self.assertIn("Marie Durand", html)
        self.assertIn('name="csrfmiddlewaretoken"', html)
        self.assertIn('method="post"', html)
        self.assertIn("js/menu.js", html)
