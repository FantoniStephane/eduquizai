"""Tests de la suppression d'un quiz (tâche 31.2, maquette 10)."""

from unittest import mock

from django.contrib.messages import get_messages
from django.test import Client, TestCase
from django.urls import reverse
from pymongo.errors import PyMongoError

from lecons.tests import creer_enseignant, creer_lecon

from .repository import QuizRepository
from .tests import creer_quiz


class QuizSuppressionTests(TestCase):
    """Confirmation (GET), suppression (POST + CSRF), propriétaire, panne MongoDB."""

    def setUp(self):
        """Deux enseignants avec un quiz chacun."""
        self.anne = creer_enseignant()
        self.paul = creer_enseignant("paul.martin@eduquizai.local", prenom="Paul")
        self.repository = QuizRepository()
        self.addCleanup(self.repository.collection.delete_many, {})
        self.id_quiz = creer_quiz(
            self.repository,
            id_utilisateur=self.anne.pk,
            id_lecon=creer_lecon(self.anne).pk,
            titre="Quiz d'Anne",
        )
        self.id_quiz_paul = creer_quiz(
            self.repository,
            id_utilisateur=self.paul.pk,
            id_lecon=creer_lecon(self.paul).pk,
            titre="Quiz de Paul",
        )
        self.client.force_login(self.anne)
        self.url = reverse("quiz:supprimer", args=[self.id_quiz])

    def textes_messages(self, reponse):
        """Messages affichés à l'enseignant après la requête."""
        return [str(m) for m in get_messages(reponse.wsgi_request)]

    def test_get_affiche_la_confirmation_sans_supprimer(self):
        """GET demande confirmation et ne supprime rien."""
        reponse = self.client.get(self.url)
        self.assertEqual(reponse.status_code, 200)
        self.assertContains(reponse, "Supprimer le quiz « Quiz d&#x27;Anne » ?")
        self.assertContains(reponse, "Supprimer définitivement")
        self.assertIsNotNone(self.repository.obtenir(self.id_quiz, self.anne.pk))

    def test_suppression_reussie(self):
        """POST supprime le quiz et retourne à la liste avec un message."""
        reponse = self.client.post(self.url)
        self.assertRedirects(
            reponse, reverse("quiz:liste"), fetch_redirect_response=False
        )
        self.assertIsNone(self.repository.obtenir(self.id_quiz, self.anne.pk))
        self.assertIn("a été supprimé", self.textes_messages(reponse)[0])

    def test_quiz_d_un_autre_enseignant_introuvable(self):
        """Faille IDOR : le quiz de Paul ne peut pas être supprimé par Anne."""
        url = reverse("quiz:supprimer", args=[self.id_quiz_paul])
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.post(url).status_code, 404)
        self.assertIsNotNone(self.repository.obtenir(self.id_quiz_paul, self.paul.pk))

    def test_identifiant_invalide_introuvable(self):
        """Un identifiant invalide donne 404 sans erreur serveur."""
        url = reverse("quiz:supprimer", args=["{'$ne': 1}"])
        self.assertEqual(self.client.post(url).status_code, 404)

    def test_deuxieme_suppression_introuvable(self):
        """Supprimer deux fois le même quiz : la seconde donne 404."""
        self.client.post(self.url)
        self.assertEqual(self.client.post(self.url).status_code, 404)

    def test_anonyme_redirige_vers_la_connexion(self):
        """Sans connexion, rien n'est supprimé."""
        reponse = Client().post(self.url)
        self.assertEqual(reponse.status_code, 302)
        self.assertIsNotNone(self.repository.obtenir(self.id_quiz, self.anne.pk))

    def test_jeton_csrf_exige(self):
        """Sans jeton CSRF, la suppression est refusée."""
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.anne)
        self.assertEqual(client.post(self.url).status_code, 403)
        self.assertIsNotNone(self.repository.obtenir(self.id_quiz, self.anne.pk))

    def test_mongodb_indisponible(self):
        """Panne MongoDB : message d'erreur, retour au détail, rien de perdu."""
        with mock.patch.object(
            QuizRepository, "obtenir", side_effect=PyMongoError("x")
        ):
            reponse = self.client.post(self.url)
        self.assertRedirects(
            reponse,
            reverse("quiz:detail", args=[self.id_quiz]),
            fetch_redirect_response=False,
        )
        self.assertIn("n'a pas pu être supprimé", self.textes_messages(reponse)[0])
        self.assertIsNotNone(self.repository.obtenir(self.id_quiz, self.anne.pk))

    def test_liste_propose_modifier_et_supprimer(self):
        """La liste affiche voir / modifier / supprimer pour chaque quiz."""
        reponse = self.client.get(reverse("quiz:liste"))
        self.assertContains(reponse, reverse("quiz:modifier", args=[self.id_quiz]))
        self.assertContains(reponse, reverse("quiz:supprimer", args=[self.id_quiz]))
        self.assertContains(reponse, "Supprimer le quiz Quiz d&#x27;Anne")
        self.assertNotContains(
            reponse, reverse("quiz:supprimer", args=[self.id_quiz_paul])
        )
