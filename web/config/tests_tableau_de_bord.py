"""Tests du tableau de bord de l'enseignant (tâche 31.3, maquette 02)."""

from unittest import mock

from django.test import TestCase
from django.urls import reverse
from pymongo.errors import PyMongoError

from lecons.tests import creer_enseignant, creer_lecon
from quiz.repository import QuizRepository
from quiz.tests import creer_quiz


class TableauDeBordTests(TestCase):
    """Chiffres, listes limitées, isolation entre enseignants, cas vides, panne."""

    def setUp(self):
        """Deux enseignants ; Anne est connectée."""
        self.anne = creer_enseignant()
        self.paul = creer_enseignant("paul.martin@eduquizai.local", prenom="Paul")
        self.repository = QuizRepository()
        self.addCleanup(self.repository.collection.delete_many, {})
        self.client.force_login(self.anne)
        self.url = reverse("tableau_de_bord")

    def quiz(self, enseignant, lecon, titre, valide=False):
        """Crée un quiz (brouillon ou validé) pour un enseignant."""
        id_quiz = creer_quiz(
            self.repository,
            id_utilisateur=enseignant.pk,
            id_lecon=lecon.pk,
            titre=titre,
        )
        if valide:
            self.repository.valider(id_quiz, enseignant.pk)
        return id_quiz

    def test_anonyme_redirige_vers_la_connexion(self):
        """Sans connexion, retour à la page de connexion."""
        self.client.logout()
        self.assertEqual(self.client.get(self.url).status_code, 302)

    def test_cas_vides(self):
        """Sans leçon ni quiz : zéros et liens pour commencer."""
        reponse = self.client.get(self.url)
        self.assertContains(reponse, "Bonjour Anne")
        self.assertContains(reponse, "Aucun quiz à valider")
        self.assertContains(reponse, "Aucune leçon pour le moment")
        self.assertEqual(reponse.context["nb_lecons"], 0)
        self.assertEqual(reponse.context["nb_valides"], 0)
        self.assertEqual(reponse.context["nb_a_valider"], 0)

    def test_chiffres_cles(self):
        """Les trois chiffres comptent les éléments de l'enseignant seulement."""
        lecon = creer_lecon(self.anne)
        creer_lecon(self.anne, titre="Les fractions")
        self.quiz(self.anne, lecon, "Brouillon 1")
        self.quiz(self.anne, lecon, "Brouillon 2")
        self.quiz(self.anne, lecon, "Validé 1", valide=True)
        lecon_paul = creer_lecon(self.paul)
        self.quiz(self.paul, lecon_paul, "Quiz de Paul")
        contexte = self.client.get(self.url).context
        self.assertEqual(contexte["nb_lecons"], 2)
        self.assertEqual(contexte["nb_valides"], 1)
        self.assertEqual(contexte["nb_a_valider"], 2)

    def test_quiz_a_valider_limites_et_recents(self):
        """Seuls les 3 brouillons les plus récents sont listés ; validés exclus."""
        lecon = creer_lecon(self.anne)
        for numero in range(1, 5):
            self.quiz(self.anne, lecon, f"Brouillon {numero}")
        self.quiz(self.anne, lecon, "Déjà validé", valide=True)
        reponse = self.client.get(self.url)
        titres = [quiz["titre"] for quiz in reponse.context["quiz_a_valider"]]
        self.assertEqual(titres, ["Brouillon 4", "Brouillon 3", "Brouillon 2"])
        self.assertNotContains(reponse, "Déjà validé")
        self.assertEqual(reponse.context["nb_a_valider"], 4)

    def test_dernieres_lecons_limitees_a_quatre(self):
        """Les 4 leçons les plus récentes sont listées, la plus récente d'abord."""
        for numero in range(1, 6):
            creer_lecon(self.anne, titre=f"Leçon {numero}")
        titres = [
            lecon.titre
            for lecon in self.client.get(self.url).context["dernieres_lecons"]
        ]
        self.assertEqual(titres, ["Leçon 5", "Leçon 4", "Leçon 3", "Leçon 2"])

    def test_rien_d_un_autre_enseignant(self):
        """Faille IDOR : ni leçon ni quiz de Paul chez Anne."""
        lecon_paul = creer_lecon(self.paul, titre="Leçon secrète de Paul")
        self.quiz(self.paul, lecon_paul, "Quiz secret de Paul")
        reponse = self.client.get(self.url)
        self.assertNotContains(reponse, "secrète")
        self.assertNotContains(reponse, "Quiz secret")

    def test_liens_vers_les_pages(self):
        """Les éléments renvoient vers le quiz et vers la leçon."""
        lecon = creer_lecon(self.anne)
        id_quiz = self.quiz(self.anne, lecon, "Quiz à relire")
        reponse = self.client.get(self.url)
        self.assertContains(reponse, reverse("quiz:detail", args=[id_quiz]))
        self.assertContains(reponse, reverse("lecons:detail", args=[lecon.pk]))
        self.assertContains(reponse, reverse("lecons:creer"))

    def test_textes_echappes(self):
        """Un titre contenant du HTML est échappé (XSS)."""
        creer_lecon(self.anne, titre="<script>alert(1)</script>")
        reponse = self.client.get(self.url)
        self.assertNotContains(reponse, "<script>alert(1)</script>")
        self.assertContains(reponse, "&lt;script&gt;alert(1)&lt;/script&gt;")

    def test_mongodb_indisponible(self):
        """Panne MongoDB : message, chiffres des quiz masqués, leçons affichées."""
        creer_lecon(self.anne, titre="Leçon visible")
        with mock.patch.object(
            QuizRepository, "compter", side_effect=PyMongoError("x")
        ):
            reponse = self.client.get(self.url)
        self.assertEqual(reponse.status_code, 200)
        self.assertContains(reponse, "momentanément indisponibles")
        self.assertContains(reponse, "Leçon visible")
        self.assertNotContains(reponse, "Quiz à valider")
        self.assertNotContains(reponse, "PyMongoError")
