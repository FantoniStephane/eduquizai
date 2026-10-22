import re

from django.core import mail
from django.test import TestCase
from django.urls import reverse

from .models import Role, Utilisateur

MOT_DE_PASSE = "Tableau-Noir-2026"


class ConnexionTests(TestCase):
    """Connexion, déconnexion et protection des pages (US2)."""

    def setUp(self):
        """Crée un enseignant avec un mot de passe."""
        self.enseignant = Utilisateur.objects.create_user(
            "anne.durand@eduquizai.local", MOT_DE_PASSE, nom="Durand", prenom="Anne"
        )

    def test_page_protegee_redirige_vers_la_connexion(self):
        """Un visiteur non connecté est renvoyé vers la page de connexion."""
        reponse = self.client.get(reverse("tableau_de_bord"))
        self.assertRedirects(reponse, f"{reverse('comptes:connexion')}?next=/")

    def test_connexion_reussie(self):
        """L'enseignant se connecte avec son e-mail, quelle que soit la casse."""
        reponse = self.client.post(
            reverse("comptes:connexion"),
            {"username": "Anne.Durand@EduQuizAI.local", "password": MOT_DE_PASSE},
        )
        self.assertRedirects(reponse, reverse("tableau_de_bord"))
        self.assertContains(self.client.get(reverse("tableau_de_bord")), "Bonjour Anne")

    def test_administrateur_arrive_dans_l_administration(self):
        """Même page de connexion, mais l'administrateur arrive dans l'admin."""
        Utilisateur.objects.create_superuser("admin@eduquizai.local", MOT_DE_PASSE)
        reponse = self.client.post(
            reverse("comptes:connexion"),
            {"username": "admin@eduquizai.local", "password": MOT_DE_PASSE},
        )
        self.assertRedirects(reponse, reverse("admin:index"))

    def test_administrateur_dans_l_administration_meme_depuis_l_accueil(self):
        """Arrivé par la page d'accueil (« next=/ »), l'admin va dans l'admin."""
        Utilisateur.objects.create_superuser("admin@eduquizai.local", MOT_DE_PASSE)
        reponse = self.client.post(
            reverse("comptes:connexion") + "?next=/",
            {"username": "admin@eduquizai.local", "password": MOT_DE_PASSE},
        )
        self.assertRedirects(reponse, reverse("admin:index"))

    def test_connexion_refusee_avec_un_mauvais_mot_de_passe(self):
        """Un mauvais mot de passe affiche un message général."""
        reponse = self.client.post(
            reverse("comptes:connexion"),
            {"username": "anne.durand@eduquizai.local", "password": "faux"},
        )
        self.assertContains(reponse, "Adresse e-mail ou mot de passe incorrect.")

    def test_connexion_refusee_pour_un_compte_desactive(self):
        """Un compte désactivé par l'administrateur ne peut plus se connecter."""
        self.enseignant.is_active = False
        self.enseignant.save()
        reponse = self.client.post(
            reverse("comptes:connexion"),
            {"username": "anne.durand@eduquizai.local", "password": MOT_DE_PASSE},
        )
        self.assertEqual(reponse.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_deconnexion_uniquement_en_post(self):
        """La déconnexion refuse le GET (protection CSRF) et accepte le POST."""
        self.client.force_login(self.enseignant)
        self.assertEqual(
            self.client.get(reverse("comptes:deconnexion")).status_code, 405
        )
        reponse = self.client.post(reverse("comptes:deconnexion"))
        self.assertRedirects(reponse, reverse("comptes:connexion"))
        self.assertNotIn("_auth_user_id", self.client.session)


class InvitationTests(TestCase):
    """Création d'un compte par l'administrateur et activation (US1)."""

    def setUp(self):
        """Connecte un administrateur."""
        admin = Utilisateur.objects.create_superuser(
            "admin@eduquizai.local", MOT_DE_PASSE, nom="Admin", prenom="Chef"
        )
        self.client.force_login(admin)

    def _creer_enseignant(self):
        """Crée un compte depuis l'admin et renvoie le chemin du lien d'invitation."""
        self.client.post(
            reverse("admin:comptes_utilisateur_add"),
            {
                "email": "marie.martin@eduquizai.local",
                "nom": "Martin",
                "prenom": "Marie",
                "role": Role.ENSEIGNANT,
            },
        )
        self.client.logout()
        return re.search(r"http://testserver(\S+)", mail.outbox[-1].body).group(1)

    def test_compte_cree_sans_mot_de_passe(self):
        """Le compte créé n'a pas de mot de passe et reçoit une invitation."""
        self._creer_enseignant()
        compte = Utilisateur.objects.get(email="marie.martin@eduquizai.local")
        self.assertFalse(compte.has_usable_password())
        self.assertEqual(mail.outbox[0].to, ["marie.martin@eduquizai.local"])

    def test_administrateur_ne_peut_pas_definir_le_mot_de_passe(self):
        """La page de l'admin qui changerait un mot de passe est interdite."""
        self._creer_enseignant()
        admin = Utilisateur.objects.get(email="admin@eduquizai.local")
        compte = Utilisateur.objects.get(email="marie.martin@eduquizai.local")
        self.client.force_login(admin)
        url = reverse("admin:auth_user_password_change", args=[compte.pk])
        self.assertEqual(self.client.get(url).status_code, 403)

    def test_parcours_complet_et_lien_a_usage_unique(self):
        """Invitation, mot de passe choisi, connexion ; le lien sert une seule fois."""
        lien = self._creer_enseignant()
        page = self.client.get(lien, follow=True)
        self.assertContains(page, "marie.martin@eduquizai.local")
        nouveau = {
            "new_password1": "Craie-Bleue-4821",
            "new_password2": "Craie-Bleue-4821",
        }
        reponse = self.client.post(page.redirect_chain[-1][0], nouveau)
        self.assertRedirects(reponse, reverse("comptes:mot_de_passe_defini"))
        self.assertTrue(
            self.client.login(
                username="marie.martin@eduquizai.local", password="Craie-Bleue-4821"
            )
        )
        self.client.logout()
        self.assertContains(self.client.get(lien, follow=True), "Lien invalide")

    def test_renvoyer_l_invitation_aux_seuls_comptes_non_actives(self):
        """L'action de l'admin ne renvoie le lien qu'aux comptes sans mot de passe."""
        en_attente = Utilisateur.objects.create_user(
            "marie.martin@eduquizai.local", None, nom="Martin", prenom="Marie"
        )
        active = Utilisateur.objects.create_user(
            "anne.durand@eduquizai.local", MOT_DE_PASSE, nom="Durand", prenom="Anne"
        )
        reponse = self.client.post(
            reverse("admin:comptes_utilisateur_changelist"),
            {
                "action": "renvoyer_invitation",
                "_selected_action": [en_attente.pk, active.pk],
            },
            follow=True,
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["marie.martin@eduquizai.local"])
        self.assertContains(reponse, "1 invitation(s) envoyée(s).")


class MotDePasseOublieTests(TestCase):
    """Réinitialisation du mot de passe."""

    def setUp(self):
        """Crée un enseignant dont le compte est activé."""
        Utilisateur.objects.create_user(
            "anne.durand@eduquizai.local", MOT_DE_PASSE, nom="Durand", prenom="Anne"
        )

    def test_message_neutre_et_envoi_uniquement_si_le_compte_existe(self):
        """Même réponse si l'adresse est inconnue ; e-mail envoyé au seul compte."""
        url = reverse("comptes:mot_de_passe_oublie")
        reponse = self.client.post(url, {"email": "inconnu@eduquizai.local"})
        self.assertRedirects(reponse, reverse("comptes:email_envoye"))
        self.assertEqual(len(mail.outbox), 0)
        self.client.post(url, {"email": "anne.durand@eduquizai.local"})
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("/comptes/mot-de-passe/definir/", mail.outbox[0].body)
