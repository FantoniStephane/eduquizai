"""Tests de l'export PDF d'un quiz, version élève (tâche 40)."""

from unittest import mock

from django.test import SimpleTestCase

from .export import generer_pdf_eleve, nom_fichier, version_eleve
from .tests import questions_valides


def quiz_stocke(**champs):
    """Quiz tel que le renvoie le repository (questions numérotées)."""
    questions = questions_valides()
    for ordre, question in enumerate(questions, start=1):
        question["ordre"] = ordre
    quiz = {
        "titre": "La Révolution française",
        "statut": "valide",
        "questions": questions,
    }
    quiz.update(champs)
    return quiz


def texte_du_pdf(quiz, **champs):
    """PDF produit sans compression, lu comme du texte pour vérifier son contenu."""
    with mock.patch("reportlab.rl_config.pageCompression", 0):
        return generer_pdf_eleve(quiz, **champs).decode("latin-1")


class VersionEleveTests(SimpleTestCase):
    """Le contenu remis à l'élève ne contient aucune réponse."""

    def test_aucune_reponse_ni_explication(self):
        """Ni bonne réponse, ni explication, ni réponse attendue."""
        eleve = version_eleve(quiz_stocke())
        for question in eleve["questions"]:
            self.assertEqual(
                set(question), {"numero", "type_question", "texte", "choix"}
            )
            for choix in question["choix"]:
                self.assertIsInstance(choix, str)

    def test_libelles_des_choix_conserves(self):
        """Les choix gardent leur libellé et leur ordre."""
        eleve = version_eleve(quiz_stocke())
        self.assertEqual(eleve["questions"][0]["choix"], ["1789", "1792", "1815"])
        self.assertEqual(eleve["questions"][1]["choix"], ["Vrai", "Faux"])
        self.assertEqual(eleve["questions"][2]["choix"], [])

    def test_questions_rangees_et_renumerotees(self):
        """Les questions suivent leur ordre et sont numérotées à partir de 1."""
        quiz = quiz_stocke()
        quiz["questions"][0]["ordre"], quiz["questions"][2]["ordre"] = 3, 1
        eleve = version_eleve(quiz)
        self.assertEqual([q["numero"] for q in eleve["questions"]], [1, 2, 3])
        self.assertEqual(eleve["questions"][0]["type_question"], "ouverte")
        self.assertEqual(eleve["questions"][2]["type_question"], "qcm")


class NomFichierTests(SimpleTestCase):
    """Nom du fichier téléchargé."""

    def test_nom_sans_accent_ni_espace(self):
        """Le titre devient un nom de fichier simple."""
        self.assertEqual(
            nom_fichier({"titre": "La Révolution française !"}),
            "quiz-la-revolution-francaise.pdf",
        )

    def test_titre_sans_caractere_utilisable(self):
        """Un titre fait seulement de symboles donne quand même un nom."""
        self.assertEqual(nom_fichier({"titre": "???"}), "quiz-eleve.pdf")


class PdfEleveTests(SimpleTestCase):
    """Fichier PDF produit pour les élèves."""

    def setUp(self):
        """Quiz dont l'explication et la réponse attendue sont repérables."""
        self.quiz = quiz_stocke()
        self.quiz["questions"][0]["explication"] = "EXPLICATION SECRETE"
        self.quiz["questions"][2]["reponse_attendue"] = "REPONSE ATTENDUE SECRETE"
        self.contenu = generer_pdf_eleve(self.quiz, matiere="Histoire", niveau="4e")
        self.texte = texte_du_pdf(self.quiz, matiere="Histoire", niveau="4e")

    def test_fichier_pdf(self):
        """Le fichier est bien un PDF."""
        self.assertTrue(self.contenu.startswith(b"%PDF-"))

    def test_questions_et_choix_presents(self):
        """Titre, questions, choix et cadre d'identité figurent dans le PDF."""
        for attendu in ("Histoire", "1792", "Vrai", "Faux", "Nom", "Classe"):
            self.assertIn(attendu, self.texte)

    def test_accents(self):
        """Les accents sont écrits correctement (encodage du PDF)."""
        self.assertIn("R\\351volution fran\\347aise", self.texte)

    def test_corrige_absent(self):
        """Explications et réponse attendue n'apparaissent jamais."""
        self.assertNotIn("SECRETE", self.texte)
        self.assertNotIn("Bonne r", self.texte)

    def test_balises_echappees(self):
        """Un « < » dans une question est affiché tel quel, sans erreur."""
        self.quiz["questions"][0]["texte"] = "Que vaut 2 < 3 ? <b>gras</b>"
        texte = texte_du_pdf(self.quiz)
        # Le texte est écrit tel quel, balise comprise (aucun passage en gras)
        self.assertIn("(/b)", texte)
        self.assertIn("(gras)", texte)
