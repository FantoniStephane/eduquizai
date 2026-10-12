"""Tests de sécurité transverses (tâche 34).

Ils complètent les tests de chaque fonctionnalité (IDOR, CSRF, injections,
fichiers importés, JWT…) avec les attaques qui touchent toute l'application :
redirection ouverte, fixation de session, mot de passe faible, accès à
l'administration et XSS stocké vu à travers les pages.

La page de connexion de l'administration est aussi vérifiée : elle renvoie vers
celle de l'application, seule porte d'entrée (point relevé lors du scan OWASP
ZAP, tâche 45).
"""

from django.contrib import admin
from django.contrib.auth.tokens import default_token_generator
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from comptes.models import Utilisateur
from lecons.models import Lecon

MOT_DE_PASSE = "Tableau-Noir-2026"
ADRESSE = "anne.durand@eduquizai.local"
SCRIPT = '<script>alert("xss")</script>'


def creer_enseignant():
    """Crée l'enseignante de test."""
    return Utilisateur.objects.create_user(
        ADRESSE, MOT_DE_PASSE, nom="Durand", prenom="Anne"
    )


class AuthentificationSecuriteTests(TestCase):
    """Connexion : redirection, session et cookie."""

    def setUp(self):
        """Crée l'enseignante et vide les compteurs d'échecs."""
        cache.clear()
        self.addCleanup(cache.clear)
        creer_enseignant()

    def _connexion(self, suivant=None):
        """Se connecte, avec un paramètre « next » éventuel."""
        url = reverse("comptes:connexion")
        if suivant is not None:
            url = f"{url}?next={suivant}"
        return self.client.post(url, {"username": ADRESSE, "password": MOT_DE_PASSE})

    def test_pas_de_redirection_vers_un_autre_site(self):
        """Redirection ouverte : un « next » extérieur est ignoré."""
        for suivant in (
            "https://site-pirate.fr/",
            "//site-pirate.fr/",
            "/\\site-pirate.fr/",
        ):
            with self.subTest(suivant=suivant):
                reponse = self._connexion(suivant)
                self.assertRedirects(
                    reponse,
                    reverse("tableau_de_bord"),
                    fetch_redirect_response=False,
                )
                self.client.logout()

    def test_redirection_interne_conservee(self):
        """Un « next » interne au site est bien suivi."""
        reponse = self._connexion(reverse("lecons:liste"))
        self.assertRedirects(
            reponse, reverse("lecons:liste"), fetch_redirect_response=False
        )

    def test_nouvel_identifiant_de_session_a_la_connexion(self):
        """Fixation de session : l'identifiant change à la connexion."""
        session = self.client.session
        session["visite"] = True
        session.save()
        avant = self.client.session.session_key
        self._connexion()
        self.assertIn("_auth_user_id", self.client.session)
        self.assertNotEqual(self.client.session.session_key, avant)

    def test_cookie_de_session_protege(self):
        """Cookie illisible par JavaScript, limité au site, valable 8 heures."""
        cookie = self._connexion().cookies["sessionid"]
        self.assertTrue(cookie["httponly"])
        self.assertEqual(cookie["samesite"], "Lax")
        self.assertEqual(cookie["max-age"], 8 * 60 * 60)


class MotDePasseFaibleTests(TestCase):
    """Le mot de passe choisi depuis le lien d'invitation est contrôlé."""

    def test_mots_de_passe_faibles_refuses(self):
        """Trop court, courant, numérique ou proche de l'adresse : refusé."""
        compte = Utilisateur.objects.create_user(
            "marie.martin@eduquizai.local", None, nom="Martin", prenom="Marie"
        )
        lien = reverse(
            "comptes:definir_mot_de_passe",
            args=[
                urlsafe_base64_encode(force_bytes(compte.pk)),
                default_token_generator.make_token(compte),
            ],
        )
        formulaire = self.client.get(lien, follow=True).redirect_chain[-1][0]
        for faible in ("Ab1!", "password123", "48201937", "eduquizai"):
            with self.subTest(mot_de_passe=faible):
                reponse = self.client.post(
                    formulaire, {"new_password1": faible, "new_password2": faible}
                )
                self.assertEqual(reponse.status_code, 200)
                compte.refresh_from_db()
                self.assertFalse(compte.has_usable_password())


class AdministrationSecuriteTests(TestCase):
    """L'administration est réservée et ne montre pas le contenu pédagogique."""

    def test_enseignant_refuse_dans_l_administration(self):
        """Une enseignante connectée est renvoyée vers la connexion de l'admin."""
        self.client.force_login(creer_enseignant())
        for url in (
            reverse("admin:index"),
            reverse("admin:comptes_utilisateur_changelist"),
        ):
            with self.subTest(url=url):
                reponse = self.client.get(url)
                self.assertEqual(reponse.status_code, 302)
                self.assertIn(reverse("admin:login"), reponse["Location"])

    def test_connexion_de_l_admin_renvoyee_vers_l_application(self):
        """/admin/login/ n'affiche rien : il renvoie à la page de connexion."""
        reponse = self.client.get(reverse("admin:login") + "?next=/admin/")
        self.assertRedirects(
            reponse,
            reverse("comptes:connexion") + "?next=/admin/",
            fetch_redirect_response=False,
        )

    def test_enseignant_sur_l_admin_retrouve_son_tableau_de_bord(self):
        """Pas de boucle de redirections : l'enseignant revient chez lui."""
        self.client.force_login(creer_enseignant())
        reponse = self.client.get(reverse("admin:index"), follow=True)
        self.assertEqual(reponse.status_code, 200)
        self.assertEqual(reponse.redirect_chain[-1][0], reverse("tableau_de_bord"))

    def test_ni_lecons_ni_quiz_dans_l_administration(self):
        """L'administrateur ne peut pas lire le contenu des enseignants."""
        applications = {modele._meta.app_label for modele in admin.site._registry}
        self.assertNotIn("lecons", applications)
        self.assertNotIn("quiz", applications)


class XssStockeTests(TestCase):
    """Un texte piégé enregistré en base reste inoffensif sur chaque page."""

    def setUp(self):
        """Leçon dont le titre et le contenu contiennent du code."""
        self.anne = creer_enseignant()
        self.client.force_login(self.anne)
        self.lecon = Lecon.objects.create(
            utilisateur=self.anne,
            titre=SCRIPT,
            matiere="histoire",
            niveau_scolaire="4e",
            # Écrit directement en base, sans passer par le formulaire
            contenu=f"Texte {SCRIPT} <img src=x onerror=alert(1)> fin",
        )

    def test_titre_echappe_sur_toutes_les_pages(self):
        """Le titre s'affiche en texte (&lt;script&gt;), jamais comme du code."""
        pages = (
            reverse("tableau_de_bord"),
            reverse("lecons:liste"),
            reverse("lecons:detail", args=[self.lecon.pk]),
            reverse("lecons:modifier", args=[self.lecon.pk]),
            reverse("quiz:generer"),
        )
        for url in pages:
            with self.subTest(url=url):
                reponse = self.client.get(url)
                self.assertEqual(reponse.status_code, 200)
                self.assertNotContains(reponse, SCRIPT)

    def test_contenu_nettoye_a_l_affichage(self):
        """Même écrit en base sans contrôle, le contenu affiché est nettoyé."""
        reponse = self.client.get(reverse("lecons:detail", args=[self.lecon.pk]))
        self.assertNotContains(reponse, "<script>alert")
        self.assertNotContains(reponse, "onerror")
