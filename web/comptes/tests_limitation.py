"""Tests de la limitation des essais de connexion (force brute)."""

from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from .limitation import MAX_ECHECS_COMPTE, MAX_ECHECS_IP, MESSAGE_BLOCAGE, _cles
from .models import Utilisateur

ADRESSE = "anne.durand@eduquizai.local"
MOT_DE_PASSE = "Tableau-Noir-2026"


class LimitationConnexionTests(TestCase):
    """Blocage après trop d'échecs, par compte + IP et par IP seule."""

    def setUp(self):
        """Crée un enseignant et vide les compteurs (cache partagé entre tests)."""
        cache.clear()
        self.addCleanup(cache.clear)
        Utilisateur.objects.create_user(
            ADRESSE, MOT_DE_PASSE, nom="Durand", prenom="Anne"
        )

    def _connexion(self, adresse=ADRESSE, mot_de_passe="faux", ip="10.0.0.1"):
        """Tente une connexion depuis l'IP donnée."""
        return self.client.post(
            reverse("comptes:connexion"),
            {"username": adresse, "password": mot_de_passe},
            REMOTE_ADDR=ip,
        )

    def _echouer(self, fois, **kwargs):
        """Enchaîne des connexions ratées."""
        for _ in range(fois):
            self._connexion(**kwargs)

    def test_bloque_apres_trop_d_echecs_meme_avec_le_bon_mot_de_passe(self):
        """Au-delà de 5 échecs, même le bon mot de passe est refusé."""
        self._echouer(MAX_ECHECS_COMPTE)
        reponse = self._connexion(mot_de_passe=MOT_DE_PASSE)
        self.assertContains(reponse, MESSAGE_BLOCAGE)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_sous_la_limite_la_connexion_reste_possible(self):
        """4 échecs puis le bon mot de passe : connexion acceptée."""
        self._echouer(MAX_ECHECS_COMPTE - 1)
        reponse = self._connexion(mot_de_passe=MOT_DE_PASSE)
        self.assertRedirects(reponse, reverse("tableau_de_bord"))

    def test_connexion_reussie_remet_le_compteur_a_zero(self):
        """Après une connexion réussie, les anciens échecs ne comptent plus."""
        self._echouer(MAX_ECHECS_COMPTE - 1)
        self._connexion(mot_de_passe=MOT_DE_PASSE)
        self.client.post(reverse("comptes:deconnexion"))
        self._echouer(MAX_ECHECS_COMPTE - 1)
        reponse = self._connexion(mot_de_passe=MOT_DE_PASSE)
        self.assertRedirects(reponse, reverse("tableau_de_bord"))

    def test_une_autre_ip_n_est_pas_bloquee(self):
        """Le blocage d'un compte vaut pour l'IP de l'attaquant seulement."""
        self._echouer(MAX_ECHECS_COMPTE, ip="10.0.0.66")
        reponse = self._connexion(mot_de_passe=MOT_DE_PASSE, ip="10.0.0.1")
        self.assertRedirects(reponse, reverse("tableau_de_bord"))

    def test_ip_bloquee_apres_de_nombreux_comptes_essayes(self):
        """20 échecs sur des comptes différents bloquent l'IP pour tous."""
        for numero in range(MAX_ECHECS_IP):
            self._connexion(adresse=f"inconnu{numero}@exemple.fr", ip="10.0.0.66")
        reponse = self._connexion(mot_de_passe=MOT_DE_PASSE, ip="10.0.0.66")
        self.assertContains(reponse, MESSAGE_BLOCAGE)
        reponse = self._connexion(mot_de_passe=MOT_DE_PASSE, ip="10.0.0.1")
        self.assertRedirects(reponse, reverse("tableau_de_bord"))

    def test_meme_message_pour_un_compte_inexistant(self):
        """Le blocage ne révèle pas si l'adresse correspond à un compte."""
        self._echouer(MAX_ECHECS_COMPTE, adresse="personne@exemple.fr")
        reponse = self._connexion(adresse="personne@exemple.fr")
        self.assertContains(reponse, MESSAGE_BLOCAGE)

    def test_aucune_adresse_en_clair_dans_le_cache(self):
        """Les clés du cache sont des empreintes, sans e-mail ni IP lisibles."""
        for cle in _cles(ADRESSE, "10.0.0.1"):
            self.assertNotIn("anne", cle)
            self.assertNotIn("10.0.0.1", cle)
