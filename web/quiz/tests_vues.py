"""Tests de la liste des quiz (tâche 28.5, maquette 06)."""

from unittest import mock

from django.test import TestCase
from django.urls import reverse
from pymongo.errors import PyMongoError

from lecons.tests import creer_enseignant, creer_lecon

from .repository import QuizRepository
from .tests import creer_quiz


class QuizListeTests(TestCase):
    """Liste des quiz : propriétaire, filtres, pagination, panne MongoDB."""

    def setUp(self):
        """Deux enseignants, une leçon chacun, un dépôt vidé après chaque test."""
        self.anne = creer_enseignant()
        self.paul = creer_enseignant("paul.martin@eduquizai.local", prenom="Paul")
        self.lecon_anne = creer_lecon(self.anne, titre="Les fractions")
        self.lecon_paul = creer_lecon(self.paul, titre="La photosynthèse")
        self.repository = QuizRepository()
        self.addCleanup(self.repository.collection.delete_many, {})
        self.client.force_login(self.anne)
        self.url = reverse("quiz:liste")

    def quiz_d_anne(self, titre, **champs):
        """Crée un quiz d'Anne sur sa leçon."""
        return creer_quiz(
            self.repository,
            id_utilisateur=self.anne.pk,
            id_lecon=self.lecon_anne.pk,
            titre=titre,
            **champs,
        )

    def test_page_reservee_aux_enseignants_connectes(self):
        """Sans connexion, la liste redirige vers la connexion."""
        self.client.logout()
        reponse = self.client.get(self.url)
        self.assertRedirects(
            reponse,
            f"{reverse('comptes:connexion')}?next={self.url}",
            fetch_redirect_response=False,
        )

    def test_liste_vide(self):
        """Sans quiz, la page l'explique."""
        self.assertContains(self.client.get(self.url), "pas encore de quiz")

    def test_uniquement_les_quiz_du_proprietaire(self):
        """Faille IDOR : les quiz de Paul n'apparaissent pas chez Anne."""
        self.quiz_d_anne("Quiz d'Anne")
        creer_quiz(
            self.repository,
            id_utilisateur=self.paul.pk,
            id_lecon=self.lecon_paul.pk,
            titre="Quiz de Paul",
        )
        reponse = self.client.get(self.url)
        self.assertContains(reponse, "Quiz d&#x27;Anne")
        self.assertNotContains(reponse, "Quiz de Paul")
        self.assertContains(reponse, "1 quiz · 1 à valider")

    def test_ligne_du_tableau(self):
        """Titre de la leçon, nombre de questions, difficulté et statut."""
        self.quiz_d_anne("Les dates clés", difficulte="facile")
        reponse = self.client.get(self.url)
        self.assertContains(reponse, "Les fractions")
        self.assertContains(reponse, '<td data-l="Questions">3</td>', html=True)
        self.assertContains(reponse, "Facile")
        self.assertContains(reponse, "badge-brouillon")

    def test_filtre_statut(self):
        """Le filtre Statut garde les quiz validés ou les brouillons."""
        self.quiz_d_anne("Quiz brouillon")
        valide = self.quiz_d_anne("Quiz relu")
        self.repository.valider(valide, self.anne.pk)
        reponse = self.client.get(self.url, {"statut": "valide"})
        self.assertContains(reponse, "Quiz relu")
        self.assertNotContains(reponse, "Quiz brouillon")
        self.assertContains(reponse, "badge-valide")

    def test_filtre_lecon(self):
        """Le filtre Leçon garde les quiz de la leçon choisie."""
        autre = creer_lecon(self.anne, titre="Les verbes")
        self.quiz_d_anne("Quiz fractions")
        creer_quiz(
            self.repository,
            id_utilisateur=self.anne.pk,
            id_lecon=autre.pk,
            titre="Quiz verbes",
        )
        reponse = self.client.get(self.url, {"lecon": autre.pk})
        self.assertContains(reponse, "Quiz verbes")
        self.assertNotContains(reponse, "Quiz fractions")

    def test_filtre_sur_la_lecon_d_un_autre_enseignant_ignore(self):
        """Une leçon de Paul n'est pas un choix valide : aucun quiz de Paul."""
        creer_quiz(
            self.repository,
            id_utilisateur=self.paul.pk,
            id_lecon=self.lecon_paul.pk,
            titre="Quiz de Paul",
        )
        self.quiz_d_anne("Quiz d'Anne")
        reponse = self.client.get(self.url, {"lecon": self.lecon_paul.pk})
        self.assertNotContains(reponse, "Quiz de Paul")

    def test_recherche_par_titre_sans_tenir_compte_de_la_casse(self):
        """La recherche porte sur le titre."""
        self.quiz_d_anne("Les fractions décimales")
        self.quiz_d_anne("Les verbes")
        reponse = self.client.get(self.url, {"q": "FRACTIONS"})
        self.assertContains(reponse, "Les fractions décimales")
        self.assertNotContains(reponse, "Les verbes")

    def test_recherche_avec_caracteres_speciaux_cherchee_telle_quelle(self):
        """Injection NoSQL : « . » et « $ne » ne sont pas des expressions."""
        self.quiz_d_anne("Les verbes")
        for texte in (".*", ".", "$ne", "{'$ne': ''}"):
            with self.subTest(texte=texte):
                reponse = self.client.get(self.url, {"q": texte})
                self.assertNotContains(reponse, "Les verbes")
                self.assertContains(reponse, "Aucun quiz ne correspond")

    def test_pagination_par_six(self):
        """Huit quiz : six sur la première page, deux sur la seconde."""
        for numero in range(1, 9):
            self.quiz_d_anne(f"Quiz numéro {numero:02d}")
        premiere = self.client.get(self.url)
        self.assertEqual(len(premiere.context["quiz_liste"]), 6)
        self.assertContains(premiere, "Quiz 1 à 6 sur 8")
        seconde = self.client.get(self.url, {"page": 2})
        self.assertEqual(len(seconde.context["quiz_liste"]), 2)
        self.assertContains(seconde, "Quiz 7 à 8 sur 8")
        self.assertEqual(self.client.get(self.url, {"page": 3}).status_code, 404)

    def test_pagination_garde_les_filtres(self):
        """Les liens de page reprennent la recherche en cours."""
        for numero in range(1, 9):
            self.quiz_d_anne(f"Fractions {numero}")
        reponse = self.client.get(self.url, {"q": "Fractions"})
        self.assertContains(reponse, "?q=Fractions&amp;page=2")

    def test_bouton_generer_desactive(self):
        """Le bouton est visible mais désactivé jusqu'à la tâche 29."""
        reponse = self.client.get(self.url)
        self.assertContains(reponse, "✦ Générer un quiz")
        self.assertContains(reponse, "disabled")

    def test_mongodb_indisponible(self):
        """Sans MongoDB, la page répond avec un message, pas une erreur 500."""
        with (
            mock.patch.object(QuizRepository, "lister", side_effect=PyMongoError),
            self.assertLogs("quiz.views", level="ERROR"),
        ):
            reponse = self.client.get(self.url)
        self.assertEqual(reponse.status_code, 200)
        self.assertContains(reponse, "momentanément indisponibles")
        self.assertNotContains(reponse, "pas encore de quiz")
