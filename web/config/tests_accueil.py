"""Tests de la page d'accueil publique (tâche 56, maquette 00)."""

from django.test import TestCase
from django.urls import reverse

from comptes.models import Utilisateur
from lecons.tests import creer_enseignant

MOT_DE_PASSE = "Tableau-Noir-2026"


class AccueilTests(TestCase):
    """Première page du site : publique pour les visiteurs, absente des connectés."""

    def setUp(self):
        """Adresse de la page d'accueil."""
        self.url = reverse("accueil")

    def test_adresses(self):
        """L'accueil est à la racine, le tableau de bord a sa propre adresse."""
        self.assertEqual(self.url, "/")
        self.assertEqual(reverse("tableau_de_bord"), "/tableau-de-bord/")

    def test_visiteur_voit_la_presentation_sans_connexion(self):
        """Un visiteur non connecté lit la page : pas de redirection."""
        reponse = self.client.get(self.url)
        self.assertEqual(reponse.status_code, 200)
        self.assertTemplateUsed(reponse, "accueil.html")
        self.assertContains(reponse, "Transformez vos leçons en quiz")
        for etape in ("Créez une leçon", "Générez un quiz", "Relisez et validez"):
            self.assertContains(reponse, etape)

    def test_liens_vers_la_connexion_et_les_donnees_personnelles(self):
        """Deux accès à la connexion et le lien RGPD, accessibles sans compte."""
        reponse = self.client.get(self.url)
        self.assertContains(reponse, f'href="{reverse("comptes:connexion")}"', count=2)
        self.assertContains(reponse, f'href="{reverse("donnees_personnelles")}"')
        self.assertEqual(self.client.get(reverse("comptes:connexion")).status_code, 200)

    def test_page_sans_donnee_personnelle(self):
        """Aucune information de compte n'apparaît sur la page publique."""
        reponse = self.client.get(self.url)
        self.assertNotContains(reponse, "Déconnexion")
        self.assertNotContains(reponse, "csrfmiddlewaretoken")

    def test_enseignant_connecte_renvoye_vers_son_tableau_de_bord(self):
        """Un enseignant déjà connecté n'a pas besoin de la présentation."""
        self.client.force_login(creer_enseignant())
        reponse = self.client.get(self.url)
        self.assertRedirects(
            reponse, reverse("tableau_de_bord"), fetch_redirect_response=False
        )

    def test_administrateur_connecte_renvoye_vers_l_administration(self):
        """L'administrateur n'a rien à faire côté enseignant."""
        admin = Utilisateur.objects.create_superuser(
            "admin@eduquizai.local", MOT_DE_PASSE
        )
        self.client.force_login(admin)
        reponse = self.client.get(self.url)
        self.assertRedirects(
            reponse, reverse("admin:index"), fetch_redirect_response=False
        )

    def test_tableau_de_bord_toujours_protege(self):
        """Le tableau de bord reste réservé aux personnes connectées."""
        reponse = self.client.get(reverse("tableau_de_bord"))
        self.assertRedirects(
            reponse,
            f"{reverse('comptes:connexion')}?next={reverse('tableau_de_bord')}",
        )

    def test_en_tetes_de_securite_presents(self):
        """La page publique garde la politique de sécurité du contenu."""
        reponse = self.client.get(self.url)
        self.assertIn("Content-Security-Policy", reponse.headers)
