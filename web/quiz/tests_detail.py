"""Tests de la page de détail d'un quiz (tâche 30, maquette 08)."""

from unittest import mock

from django.test import TestCase
from django.urls import reverse
from pymongo.errors import PyMongoError

from lecons.tests import creer_enseignant, creer_lecon

from .repository import QuizRepository
from .tests import creer_quiz, questions_valides


class QuizDetailTests(TestCase):
    """Détail : propriétaire, affichage par type, récapitulatif, panne MongoDB."""

    def setUp(self):
        """Deux enseignants avec une leçon chacun et un quiz d'Anne."""
        self.anne = creer_enseignant()
        self.paul = creer_enseignant("paul.martin@eduquizai.local", prenom="Paul")
        self.lecon_anne = creer_lecon(self.anne, titre="Les fractions")
        self.lecon_paul = creer_lecon(self.paul, titre="La photosynthèse")
        self.repository = QuizRepository()
        self.addCleanup(self.repository.collection.delete_many, {})
        self.id_quiz = creer_quiz(
            self.repository,
            id_utilisateur=self.anne.pk,
            id_lecon=self.lecon_anne.pk,
            titre="Quiz d'Anne",
        )
        self.client.force_login(self.anne)
        self.url = reverse("quiz:detail", args=[self.id_quiz])

    def test_page_reservee_aux_enseignants_connectes(self):
        """Sans connexion, la page redirige vers la connexion."""
        self.client.logout()
        self.assertRedirects(
            self.client.get(self.url),
            f"{reverse('comptes:connexion')}?next={self.url}",
            fetch_redirect_response=False,
        )

    def test_affichage_du_quiz(self):
        """Titre, statut, leçon d'origine et difficulté sont affichés."""
        reponse = self.client.get(self.url)
        self.assertContains(reponse, "Quiz d&#x27;Anne")
        self.assertContains(reponse, "Brouillon")
        self.assertContains(reponse, "Moyen")
        self.assertContains(reponse, "Histoire")
        self.assertContains(
            reponse, reverse("lecons:detail", args=[self.lecon_anne.pk])
        )

    def test_questions_de_chaque_type(self):
        """QCM, vrai/faux et question ouverte sont présentés comme la maquette."""
        reponse = self.client.get(self.url)
        self.assertContains(reponse, "En quelle année commence la Révolution")
        self.assertContains(reponse, "✓ Bonne réponse", count=2)
        self.assertContains(reponse, "Vrai / Faux")
        self.assertContains(reponse, "Réponse attendue :")
        self.assertContains(reponse, "La crise financière du royaume.")
        self.assertContains(reponse, "Explication :")

    def test_recapitulatif(self):
        """Le récapitulatif compte les questions par type."""
        recap = self.client.get(self.url).context["recap"]
        self.assertEqual(recap, {"total": 3, "qcm": 1, "vrai_faux": 1, "ouverte": 1})

    def test_alerte_a_relire_seulement_en_brouillon(self):
        """L'alerte « À relire » disparaît pour un quiz validé."""
        self.assertContains(self.client.get(self.url), "À relire avant validation")
        self.repository.collection.update_many({}, {"$set": {"statut": "valide"}})
        reponse = self.client.get(self.url)
        self.assertContains(reponse, "Validé")
        self.assertNotContains(reponse, "À relire avant validation")

    def test_boutons_non_disponibles_desactives(self):
        """Modifier, supprimer, exporter et valider sont désactivés pour l'instant."""
        self.assertContains(self.client.get(self.url), "disabled", count=4)

    def test_quiz_d_un_autre_enseignant_introuvable(self):
        """Faille IDOR : le quiz de Paul donne une 404 chez Anne."""
        autre = creer_quiz(
            self.repository,
            id_utilisateur=self.paul.pk,
            id_lecon=self.lecon_paul.pk,
            titre="Quiz de Paul",
        )
        reponse = self.client.get(reverse("quiz:detail", args=[autre]))
        self.assertEqual(reponse.status_code, 404)
        self.assertNotContains(reponse, "Quiz de Paul", status_code=404)

    def test_identifiants_invalides_ou_inconnus(self):
        """Identifiant mal formé, inconnu ou piégé : même 404."""
        for identifiant in ("abc", "0" * 24, "%7B%22$ne%22:1%7D", "x" * 200):
            with self.subTest(identifiant=identifiant):
                reponse = self.client.get(f"/quiz/{identifiant}/")
                self.assertEqual(reponse.status_code, 404)

    def test_lecon_d_un_autre_non_montree(self):
        """Si la leçon source n'est pas à l'enseignant, rien n'est affiché."""
        self.repository.collection.update_many(
            {}, {"$set": {"id_lecon": self.lecon_paul.pk}}
        )
        reponse = self.client.get(self.url)
        self.assertEqual(reponse.status_code, 200)
        self.assertNotContains(reponse, "La photosynthèse")
        self.assertIsNone(reponse.context["lecon"])

    def test_textes_de_l_ia_echappes(self):
        """Faille XSS : un texte contenant du HTML est affiché tel quel, pas exécuté."""
        questions = questions_valides()
        questions[0]["texte"] = "<script>alert(1)</script> ?"
        identifiant = creer_quiz(
            self.repository,
            id_utilisateur=self.anne.pk,
            id_lecon=self.lecon_anne.pk,
            questions=questions,
        )
        reponse = self.client.get(reverse("quiz:detail", args=[identifiant]))
        self.assertNotContains(reponse, "<script>alert(1)</script>")
        self.assertContains(reponse, "&lt;script&gt;alert(1)&lt;/script&gt;")

    def test_mongodb_indisponible(self):
        """Sans MongoDB, la page répond 503 avec un message, pas une erreur 500."""
        with (
            mock.patch.object(
                QuizRepository, "obtenir", side_effect=PyMongoError("hors service")
            ),
            self.assertLogs("quiz.views", level="ERROR"),
        ):
            reponse = self.client.get(self.url)
        self.assertEqual(reponse.status_code, 503)
        self.assertContains(reponse, "momentanément indisponible", status_code=503)

    def test_titre_de_la_liste_mene_au_detail(self):
        """Dans la liste, le titre du quiz est un lien vers son détail."""
        reponse = self.client.get(reverse("quiz:liste"))
        self.assertContains(reponse, f'href="{self.url}">Quiz d&#x27;Anne</a>')
