"""Tests de la modification d'un quiz (tâche 31.1, maquette 09)."""

from unittest import mock

from django.contrib.messages import get_messages
from django.test import Client, TestCase
from django.urls import reverse
from pymongo.errors import PyMongoError

from lecons.tests import creer_enseignant, creer_lecon

from .repository import QuizRepository
from .tests import creer_quiz


class QuizModificationTests(TestCase):
    """Formulaire prérempli, contrôles, propriétaire, brouillon, panne MongoDB."""

    def setUp(self):
        """Deux enseignants ; Anne a un quiz (QCM, Vrai/Faux, question ouverte)."""
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
        self.url = reverse("quiz:modifier", args=[self.id_quiz])
        self.detail = reverse("quiz:detail", args=[self.id_quiz])

    def donnees(self, **changements):
        """Saisie valide, identique au quiz enregistré ; chaque champ peut changer."""
        donnees = {
            "titre": "Quiz d'Anne",
            "difficulte": "moyen",
            "q0-texte": "En quelle année commence la Révolution française ?",
            "q0-explication": "La prise de la Bastille a lieu le 14 juillet 1789.",
            "q0-correct": "0",
            "q0-choix0": "1789",
            "q0-choix1": "1792",
            "q0-choix2": "1815",
            "q1-texte": "Louis XVI convoque les états généraux en 1789.",
            "q1-explication": "Ils s'ouvrent le 5 mai 1789 à Versailles.",
            "q1-correct": "0",
            "q2-texte": "Citez une cause de la Révolution française.",
            "q2-reponse": "La crise financière du royaume.",
        }
        donnees.update(changements)
        return donnees

    def quiz(self):
        """Quiz d'Anne relu en base."""
        return self.repository.obtenir(self.id_quiz, self.anne.pk)

    def textes_messages(self, reponse):
        """Messages affichés à l'enseignant après la requête."""
        return [str(m) for m in get_messages(reponse.wsgi_request)]

    def test_formulaire_prerempli(self):
        """Le formulaire reprend le titre, la difficulté et les questions."""
        reponse = self.client.get(self.url)
        self.assertEqual(reponse.status_code, 200)
        self.assertContains(reponse, "Quiz d&#x27;Anne")
        self.assertContains(reponse, "En quelle année commence")
        self.assertContains(reponse, 'name="q2-reponse"')
        self.assertContains(reponse, "Enregistrer les modifications")

    def test_anonyme_redirige_vers_la_connexion(self):
        """Sans connexion, retour à la page de connexion."""
        reponse = Client().get(self.url)
        self.assertEqual(reponse.status_code, 302)
        self.assertIn("connexion", reponse["Location"])

    def test_quiz_d_un_autre_enseignant_introuvable(self):
        """Faille IDOR : GET et POST sur le quiz de Paul donnent 404."""
        url = reverse("quiz:modifier", args=[self.id_quiz_paul])
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.post(url, self.donnees()).status_code, 404)
        self.assertEqual(
            self.repository.obtenir(self.id_quiz_paul, self.paul.pk)["titre"],
            "Quiz de Paul",
        )

    def test_identifiant_invalide_introuvable(self):
        """Un identifiant qui n'est pas un ObjectId donne aussi 404."""
        url = reverse("quiz:modifier", args=["{'$ne': 1}"])
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_modification_reussie(self):
        """Titre, difficulté et textes sont enregistrés, puis retour au détail."""
        reponse = self.client.post(
            self.url,
            self.donnees(
                titre="Titre relu",
                difficulte="difficile",
                **{"q0-texte": "Quelle année ?", "q0-correct": "1"},
            ),
        )
        self.assertRedirects(reponse, self.detail, fetch_redirect_response=False)
        quiz = self.quiz()
        self.assertEqual(quiz["titre"], "Titre relu")
        self.assertEqual(quiz["difficulte"], "difficile")
        self.assertEqual(quiz["questions"][0]["texte"], "Quelle année ?")
        self.assertEqual(
            [c["est_correct"] for c in quiz["questions"][0]["choix"]],
            [False, True, False],
        )
        self.assertIn("a été modifié", self.textes_messages(reponse)[0])

    def test_quiz_valide_repasse_en_brouillon(self):
        """Modifier un quiz validé le remet en brouillon, avec un message."""
        self.repository.valider(self.id_quiz, self.anne.pk)
        reponse = self.client.post(self.url, self.donnees(titre="Autre titre"))
        quiz = self.quiz()
        self.assertEqual(quiz["statut"], "brouillon")
        self.assertIsNone(quiz["date_validation"])
        self.assertIn("repassé en brouillon", self.textes_messages(reponse)[-1])

    def test_suppression_d_une_question(self):
        """Une question marquée « supprimer » n'est pas enregistrée."""
        self.client.post(self.url, self.donnees(**{"q1-supprimer": "1"}))
        types = [q["type_question"] for q in self.quiz()["questions"]]
        self.assertEqual(types, ["qcm", "ouverte"])

    def test_au_moins_une_question(self):
        """Supprimer toutes les questions est refusé, le quiz reste intact."""
        reponse = self.client.post(
            self.url,
            self.donnees(
                **{"q0-supprimer": "1", "q1-supprimer": "1", "q2-supprimer": "1"}
            ),
        )
        self.assertEqual(reponse.status_code, 200)
        self.assertContains(reponse, "au moins une question")
        self.assertEqual(len(self.quiz()["questions"]), 3)

    def test_erreurs_de_saisie(self):
        """Champs vides ou trop longs : page réaffichée avec les messages."""
        cas = {
            "Le titre est obligatoire": {"titre": "  "},
            "ne doit pas dépasser 100": {"titre": "x" * 101},
            "Choisissez une difficulté": {"difficulte": "extrême"},
            "L&#x27;énoncé est obligatoire": {"q0-texte": ""},
            "L&#x27;explication est obligatoire": {"q1-explication": ""},
            "Le choix 2 est vide": {"q0-choix1": ""},
            "Choisissez la bonne réponse": {"q0-correct": "9"},
            "La réponse attendue est obligatoire": {"q2-reponse": ""},
            "L&#x27;énoncé ne doit pas dépasser 1000": {"q0-texte": "x" * 1001},
        }
        for attendu, changement in cas.items():
            with self.subTest(attendu):
                reponse = self.client.post(self.url, self.donnees(**changement))
                self.assertEqual(reponse.status_code, 200)
                self.assertContains(reponse, attendu)
                self.assertEqual(self.quiz()["titre"], "Quiz d'Anne")

    def test_saisie_conservee_en_cas_d_erreur(self):
        """Après une erreur, ce que l'enseignant a tapé est réaffiché."""
        reponse = self.client.post(
            self.url, self.donnees(titre="Mon titre", **{"q0-explication": ""})
        )
        self.assertContains(reponse, 'value="Mon titre"')

    def test_type_et_choix_non_modifiables(self):
        """Le type, le nombre de choix et Vrai/Faux viennent du quiz enregistré."""
        self.client.post(
            self.url,
            self.donnees(
                **{
                    "q1-type_question": "ouverte",
                    "q1-choix0": "Peut-être",
                    "q1-choix5": "Intrus",
                    "q0-choix9": "Intrus",
                }
            ),
        )
        questions = self.quiz()["questions"]
        self.assertEqual(questions[1]["type_question"], "vrai_faux")
        self.assertEqual([c["texte"] for c in questions[1]["choix"]], ["Vrai", "Faux"])
        self.assertEqual(len(questions[0]["choix"]), 3)

    def test_champs_inconnus_ignores(self):
        """Une saisie truquée (statut, propriétaire) ne change pas le quiz."""
        self.client.post(
            self.url,
            self.donnees(statut="valide", id_utilisateur="999", id_lecon="999"),
        )
        quiz = self.quiz()
        self.assertEqual(quiz["statut"], "brouillon")
        self.assertEqual(quiz["id_utilisateur"], self.anne.pk)

    def test_jeton_csrf_exige(self):
        """Sans jeton CSRF, la modification est refusée."""
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.anne)
        reponse = client.post(self.url, self.donnees(titre="Piraté"))
        self.assertEqual(reponse.status_code, 403)
        self.assertEqual(self.quiz()["titre"], "Quiz d'Anne")

    def test_texte_html_echappe(self):
        """Un texte contenant du HTML est échappé dans le formulaire (XSS)."""
        self.client.post(
            self.url, self.donnees(**{"q0-texte": "<script>alert(1)</script>"})
        )
        reponse = self.client.get(self.url)
        self.assertNotContains(reponse, "<script>alert(1)</script>")
        self.assertContains(reponse, "&lt;script&gt;alert(1)&lt;/script&gt;")

    def test_mongodb_indisponible_en_lecture(self):
        """Panne MongoDB à l'affichage : page 503 avec message, sans détail."""
        with mock.patch.object(
            QuizRepository, "obtenir", side_effect=PyMongoError("x")
        ):
            reponse = self.client.get(self.url)
        self.assertEqual(reponse.status_code, 503)
        self.assertContains(reponse, "momentanément indisponible", status_code=503)

    def test_mongodb_indisponible_a_l_enregistrement(self):
        """Panne MongoDB à l'enregistrement : saisie conservée, message d'erreur."""
        with mock.patch.object(
            QuizRepository, "modifier", side_effect=PyMongoError("x")
        ):
            reponse = self.client.post(self.url, self.donnees(titre="Mon titre"))
        self.assertEqual(reponse.status_code, 200)
        self.assertContains(reponse, "n&#x27;a pas pu être enregistré")
        self.assertContains(reponse, 'value="Mon titre"')
        self.assertNotContains(reponse, "PyMongoError")
