"""Tests de la page « Données personnelles » (RGPD)."""

from django.test import TestCase
from django.urls import reverse

from comptes.models import Utilisateur

URL = reverse("donnees_personnelles")


class DonneesPersonnellesTests(TestCase):
    """Page lisible par tous, liée depuis la connexion et les pages connectées."""

    def test_page_publique(self):
        """Lisible sans être connecté, depuis la page de connexion."""
        reponse = self.client.get(URL)
        self.assertEqual(reponse.status_code, 200)
        self.assertContains(reponse, "Données personnelles</h1>")
        self.assertContains(reponse, "Vos droits")
        self.assertContains(self.client.get(reverse("comptes:connexion")), URL)

    def test_page_dans_l_application(self):
        """Connecté : même page, avec la navigation et le lien en pied de page."""
        enseignant = Utilisateur.objects.create_user(
            "anne.durand@eduquizai.local", "Tableau-Noir-2026"
        )
        self.client.force_login(enseignant)
        reponse = self.client.get(URL)
        self.assertEqual(reponse.status_code, 200)
        self.assertContains(reponse, "Navigation principale")
        self.assertContains(
            self.client.get(reverse("lecons:liste")),
            f'<footer class="pied"><a href="{URL}">Données personnelles</a></footer>',
            html=True,
        )
