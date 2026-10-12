"""Tests de la validation d'un quiz par l'enseignant (tâche 31, éthique du CDC)."""

from unittest import mock

from django.contrib.messages import get_messages
from django.test import Client, TestCase
from django.urls import reverse
from pymongo.errors import PyMongoError

from lecons.tests import creer_enseignant, creer_lecon

from .repository import QuizRepository
from .tests import creer_quiz


class QuizValidationTests(TestCase):
    """Validation : POST + CSRF, propriétaire, déjà validé, panne MongoDB."""

    def setUp(self):
        """Deux enseignants avec un quiz en brouillon chacun."""
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
        self.url = reverse("quiz:valider", args=[self.id_quiz])
        self.detail = reverse("quiz:detail", args=[self.id_quiz])

    def quiz(self, id_quiz, id_utilisateur):
        """Quiz relu en base."""
        return self.repository.obtenir(id_quiz, id_utilisateur)

    def textes_messages(self, reponse):
        """Messages affichés à l'enseignant après la requête."""
        return [str(m) for m in get_messages(reponse.wsgi_request)]

    def test_validation_reussie(self):
        """Le brouillon devient « valide », avec sa date de validation."""
        reponse = self.client.post(self.url)
        self.assertRedirects(reponse, self.detail, fetch_redirect_response=False)
        quiz = self.quiz(self.id_quiz, self.anne.pk)
        self.assertEqual(quiz["statut"], "valide")
        self.assertIsNotNone(quiz["date_validation"])
        self.assertIn("a été validé", self.textes_messages(reponse)[0])

    def test_methode_get_refusee(self):
        """Un simple lien ne valide jamais un quiz."""
        self.assertEqual(self.client.get(self.url).status_code, 405)
        self.assertEqual(self.quiz(self.id_quiz, self.anne.pk)["statut"], "brouillon")

    def test_jeton_csrf_exige(self):
        """Sans jeton CSRF, la validation est refusée."""
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.anne)
        self.assertEqual(client.post(self.url).status_code, 403)
        self.assertEqual(self.quiz(self.id_quiz, self.anne.pk)["statut"], "brouillon")

    def test_acces_reserve_aux_connectes(self):
        """Sans connexion, redirection vers la connexion et rien n'est validé."""
        self.client.logout()
        reponse = self.client.post(self.url)
        self.assertEqual(reponse.status_code, 302)
        self.assertIn(reverse("comptes:connexion"), reponse["Location"])
        self.assertEqual(self.quiz(self.id_quiz, self.anne.pk)["statut"], "brouillon")

    def test_quiz_d_un_autre_enseignant_intouchable(self):
        """Faille IDOR : Anne ne peut pas valider le quiz de Paul."""
        reponse = self.client.post(reverse("quiz:valider", args=[self.id_quiz_paul]))
        self.assertEqual(reponse.status_code, 404)
        self.assertEqual(
            self.quiz(self.id_quiz_paul, self.paul.pk)["statut"], "brouillon"
        )

    def test_identifiant_invalide(self):
        """Un identifiant mal formé ou inconnu donne une 404."""
        for identifiant in ("abc", "0" * 24):
            with self.subTest(identifiant=identifiant):
                reponse = self.client.post(reverse("quiz:valider", args=[identifiant]))
                self.assertEqual(reponse.status_code, 404)

    def test_deja_valide_inchange(self):
        """Valider deux fois ne change pas la date de validation."""
        self.client.post(self.url)
        premiere = self.quiz(self.id_quiz, self.anne.pk)["date_validation"]
        reponse = self.client.post(self.url)
        self.assertEqual(
            self.quiz(self.id_quiz, self.anne.pk)["date_validation"], premiere
        )
        self.assertEqual(self.textes_messages(reponse)[-1], "Ce quiz est déjà validé.")

    def test_mongodb_indisponible(self):
        """Sans MongoDB, un message d'erreur est affiché, pas une erreur 500."""
        with (
            mock.patch.object(
                QuizRepository, "obtenir", side_effect=PyMongoError("hors service")
            ),
            self.assertLogs("quiz.views", level="ERROR"),
        ):
            reponse = self.client.post(self.url)
        self.assertRedirects(reponse, self.detail, fetch_redirect_response=False)
        self.assertIn("n'a pas pu être validé", self.textes_messages(reponse)[0])
        self.assertEqual(self.quiz(self.id_quiz, self.anne.pk)["statut"], "brouillon")

    def test_detail_brouillon_propose_la_validation(self):
        """Un brouillon affiche le bouton, la fenêtre de confirmation et le script."""
        reponse = self.client.get(self.detail)
        self.assertContains(reponse, 'id="form-validation"')
        self.assertContains(reponse, reverse("quiz:valider", args=[self.id_quiz]))
        self.assertContains(reponse, "relu les questions et les réponses")
        self.assertContains(reponse, "js/validation.js")

    def test_detail_valide_sans_bouton(self):
        """Un quiz validé n'a plus de bouton ; la date de validation est indiquée."""
        self.client.post(self.url)
        reponse = self.client.get(self.detail)
        self.assertNotContains(reponse, 'id="form-validation"')
        self.assertNotContains(reponse, "relu les questions et les réponses")
        self.assertContains(reponse, ", validé le ")
