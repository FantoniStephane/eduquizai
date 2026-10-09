"""Tests des pages d'erreur : message clair, aucun détail technique visible."""

from unittest import mock

from django.core.exceptions import PermissionDenied
from django.test import Client, TestCase
from django.urls import reverse

from lecons.tests import creer_enseignant
from quiz.repository import QuizRepository

DETAILS_TECHNIQUES = ("Traceback", "urlpatterns", "Not Found", "Server Error", "DEBUG")


class PagesErreurTests(TestCase):
    """404, 403, formulaire expiré et 500 : pages personnalisées et sobres."""

    def setUp(self):
        """Un enseignant connecté."""
        self.anne = creer_enseignant()
        self.client.force_login(self.anne)

    def verifier_sobre(self, reponse):
        """Aucun détail technique n'est montré à l'utilisateur."""
        contenu = reponse.content.decode()
        for texte in DETAILS_TECHNIQUES:
            self.assertNotIn(texte, contenu)
        self.assertIn("Retour à l'accueil", contenu)

    def test_page_introuvable(self):
        """Une adresse inconnue affiche un message clair, sans code."""
        reponse = self.client.get("/page-qui-n-existe-pas/")
        self.assertEqual(reponse.status_code, 404)
        self.assertContains(reponse, "Cette page est introuvable", status_code=404)
        self.verifier_sobre(reponse)

    def test_quiz_inconnu(self):
        """Un quiz introuvable (ou d'un autre enseignant) donne la même page."""
        reponse = self.client.get(reverse("quiz:detail", args=["0" * 24]))
        self.assertEqual(reponse.status_code, 404)
        self.assertContains(reponse, "Cette page est introuvable", status_code=404)
        self.verifier_sobre(reponse)

    def test_acces_refuse(self):
        """Un accès refusé affiche la page dédiée."""
        with mock.patch.object(QuizRepository, "obtenir", side_effect=PermissionDenied):
            reponse = self.client.get(reverse("quiz:detail", args=["0" * 24]))
        self.assertEqual(reponse.status_code, 403)
        self.assertContains(reponse, "pas accès à cette page", status_code=403)
        self.verifier_sobre(reponse)

    def test_formulaire_expire(self):
        """Un jeton CSRF absent affiche un message clair."""
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.anne)
        reponse = client.post(
            reverse("quiz:annuler_generation"), {"id_generation": "x"}
        )
        self.assertEqual(reponse.status_code, 403)
        self.assertContains(reponse, "plus valide", status_code=403)
        self.verifier_sobre(reponse)

    def test_erreur_serveur(self):
        """Une erreur interne affiche un message sobre, sans le détail de l'erreur."""
        self.client.raise_request_exception = False
        with (
            mock.patch.object(
                QuizRepository, "obtenir", side_effect=RuntimeError("secret interne")
            ),
            self.assertLogs("django.request", level="ERROR"),
        ):
            reponse = self.client.get(reverse("quiz:detail", args=["0" * 24]))
        self.assertEqual(reponse.status_code, 500)
        self.assertContains(reponse, "Une erreur est survenue", status_code=500)
        self.assertNotContains(reponse, "secret interne", status_code=500)
        self.verifier_sobre(reponse)
