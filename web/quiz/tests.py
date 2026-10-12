import jwt
from django.conf import settings
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase
from pymongo.errors import WriteError

from comptes.models import Utilisateur

from .jeton_ia import DESTINATAIRE, EMETTEUR, creer_jeton_ia
from .mongo import get_db
from .repository import QuizRepository
from .schema import NOM_COLLECTION
from .validation import QuizInvalideError, valider_quiz


def questions_valides():
    """Une question de chaque type, conforme aux règles."""
    return [
        {
            "type_question": "qcm",
            "texte": "En quelle année commence la Révolution française ?",
            "explication": "La prise de la Bastille a lieu le 14 juillet 1789.",
            "choix": [
                {"texte": "1789", "est_correct": True},
                {"texte": "1792", "est_correct": False},
                {"texte": "1815", "est_correct": False},
            ],
        },
        {
            "type_question": "vrai_faux",
            "texte": "Louis XVI convoque les états généraux en 1789.",
            "explication": "Ils s'ouvrent le 5 mai 1789 à Versailles.",
            "choix": [
                {"texte": "Vrai", "est_correct": True},
                {"texte": "Faux", "est_correct": False},
            ],
        },
        {
            "type_question": "ouverte",
            "texte": "Citez une cause de la Révolution française.",
            "explication": "Plusieurs réponses sont possibles.",
            "reponse_attendue": "La crise financière du royaume.",
            "choix": [],
        },
    ]


def creer_quiz(repository, id_utilisateur=1, id_lecon=1, **champs):
    """Enregistre un quiz valide ; chaque champ peut être remplacé."""
    valeurs = {
        "titre": "La Révolution française",
        "difficulte": "moyen",
        "questions": questions_valides(),
    }
    valeurs.update(champs)
    return repository.creer(id_utilisateur=id_utilisateur, id_lecon=id_lecon, **valeurs)


def document_valide(**champs):
    """Document complet, tel qu'il est enregistré dans MongoDB."""
    document = {
        "titre": "Quiz",
        "description": "",
        "difficulte": "facile",
        "statut": "brouillon",
        "id_lecon": 1,
        "id_utilisateur": 1,
        "questions": questions_valides(),
    }
    document.update(champs)
    return document


class ValidationTests(SimpleTestCase):
    """Contrôle du quiz avant écriture (règles du MCD par type de question)."""

    def erreurs(self, document):
        """Erreurs détectées sur le document (liste vide s'il est valide)."""
        try:
            valider_quiz(document)
        except QuizInvalideError as exc:
            return exc.erreurs
        return []

    def test_quiz_valide(self):
        """Un quiz avec une question de chaque type est accepté."""
        self.assertEqual(self.erreurs(document_valide()), [])

    def test_champs_du_quiz(self):
        """Titre, difficulté, statut et identifiants sont contrôlés."""
        cas = {
            "titre vide": {"titre": "  "},
            "titre trop long": {"titre": "x" * 201},
            "difficulté inconnue": {"difficulte": "extrême"},
            "statut inconnu": {"statut": "publié"},
            "identifiant booléen": {"id_lecon": True},
            "identifiant texte": {"id_utilisateur": "1"},
        }
        for nom, champs in cas.items():
            with self.subTest(nom):
                self.assertTrue(self.erreurs(document_valide(**champs)))

    def test_nombre_de_questions(self):
        """Un quiz contient de 1 à 20 questions."""
        for questions in ([], questions_valides() * 7, None):
            with self.subTest(nombre=len(questions or [])):
                self.assertTrue(self.erreurs(document_valide(questions=questions)))

    def test_regles_par_type_de_question(self):
        """Règles propres à chaque type de question.

        QCM : une seule bonne réponse ; vrai/faux : « Vrai » et « Faux » ;
        question ouverte : pas de choix mais une réponse attendue.
        """
        qcm, vrai_faux, ouverte = questions_valides()
        cas = {
            "QCM à deux bonnes réponses": {
                **qcm,
                "choix": [{**c, "est_correct": True} for c in qcm["choix"]],
            },
            "QCM à deux choix": {**qcm, "choix": qcm["choix"][:2]},
            "vrai/faux mal libellé": {
                **vrai_faux,
                "choix": [
                    {"texte": "Oui", "est_correct": True},
                    {"texte": "Non", "est_correct": False},
                ],
            },
            "ouverte avec des choix": {**ouverte, "choix": qcm["choix"]},
            "ouverte sans réponse attendue": {**ouverte, "reponse_attendue": ""},
            "type inconnu": {**qcm, "type_question": "dessin"},
            "explication vide": {**qcm, "explication": ""},
            "choix mal formé": {**qcm, "choix": [{"texte": "1789"}]},
            "question qui n'est pas un objet": "Quelle année ?",
        }
        for nom, question in cas.items():
            with self.subTest(nom):
                self.assertTrue(self.erreurs(document_valide(questions=[question])))


class QuizRepositoryTests(SimpleTestCase):
    """Accès aux quiz dans la base MongoDB de test."""

    def setUp(self):
        """Repository sur la base de test, vidée après chaque test."""
        self.repository = QuizRepository()
        self.addCleanup(self.repository.collection.delete_many, {})

    @staticmethod
    def ids(liste):
        """Identifiants d'une liste de quiz, dans l'ordre."""
        return [quiz["id"] for quiz in liste]

    def test_creer_un_quiz_en_brouillon(self):
        """Un quiz généré est toujours créé en brouillon, questions numérotées."""
        id_quiz = creer_quiz(self.repository)
        quiz = self.repository.obtenir(id_quiz, 1)
        self.assertEqual(quiz["id"], id_quiz)
        self.assertEqual(quiz["statut"], "brouillon")
        self.assertIsNone(quiz["date_validation"])
        self.assertEqual([q["ordre"] for q in quiz["questions"]], [1, 2, 3])

    def test_creer_un_quiz_invalide_n_ecrit_rien(self):
        """Un quiz invalide est refusé avant d'atteindre la base."""
        with self.assertRaises(QuizInvalideError):
            creer_quiz(self.repository, questions=[])
        self.assertEqual(self.repository.collection.count_documents({}), 0)

    def test_quiz_d_un_autre_enseignant_introuvable(self):
        """Faille IDOR : le quiz d'un collègue est traité comme inexistant."""
        id_quiz = creer_quiz(self.repository, id_utilisateur=1)
        self.assertIsNone(self.repository.obtenir(id_quiz, 2))
        self.assertFalse(self.repository.valider(id_quiz, 2))
        self.assertFalse(self.repository.supprimer(id_quiz, 2))
        self.assertFalse(
            self.repository.modifier(
                id_quiz,
                2,
                titre="Piraté",
                description="",
                questions=questions_valides(),
            )
        )
        self.assertEqual(
            self.repository.obtenir(id_quiz, 1)["titre"], "La Révolution française"
        )

    def test_identifiants_invalides(self):
        """Identifiant mal formé : quiz introuvable ; opérateur MongoDB : refusé."""
        self.assertIsNone(self.repository.obtenir("pas-un-identifiant", 1))
        self.assertFalse(self.repository.supprimer("123", 1))
        self.assertFalse(self.repository.valider("123", 1))
        id_quiz = creer_quiz(self.repository)
        with self.assertRaises(TypeError):
            self.repository.obtenir(id_quiz, {"$ne": None})

    def test_lister_avec_filtres(self):
        """Liste du plus récent au plus ancien, filtres statut, leçon, recherche."""
        ancien = creer_quiz(self.repository, titre="Les volcans", id_lecon=2)
        recent = creer_quiz(self.repository, titre="La Révolution")
        creer_quiz(self.repository, id_utilisateur=2, titre="Quiz de Paul")
        self.repository.valider(ancien, 1)
        self.assertEqual(self.ids(self.repository.lister(1)), [recent, ancien])
        self.assertEqual(self.ids(self.repository.lister(1, statut="valide")), [ancien])
        self.assertEqual(self.ids(self.repository.lister(1, id_lecon=2)), [ancien])
        self.assertEqual(
            self.ids(self.repository.lister(1, recherche="RÉVOL")), [recent]
        )
        # Caractères spéciaux cherchés tels quels (pas d'expression régulière)
        self.assertEqual(self.repository.lister(1, recherche=".*"), [])

    def test_compter_par_lecon(self):
        """Seuls les quiz de la leçon et de l'enseignant sont comptés."""
        creer_quiz(self.repository, id_lecon=1)
        creer_quiz(self.repository, id_lecon=1)
        creer_quiz(self.repository, id_lecon=2)
        creer_quiz(self.repository, id_utilisateur=2, id_lecon=1)
        self.assertEqual(self.repository.compter_par_lecon(1, 1), 2)

    def test_modifier(self):
        """La modification est contrôlée comme la création."""
        id_quiz = creer_quiz(self.repository)
        questions = questions_valides()[:1]
        self.assertTrue(
            self.repository.modifier(
                id_quiz,
                1,
                titre="Nouveau titre",
                description="Relu",
                questions=questions,
            )
        )
        quiz = self.repository.obtenir(id_quiz, 1)
        self.assertEqual(quiz["titre"], "Nouveau titre")
        self.assertEqual(len(quiz["questions"]), 1)
        with self.assertRaises(QuizInvalideError):
            self.repository.modifier(
                id_quiz, 1, titre="", description="", questions=questions
            )

    def test_modifier_repasse_en_brouillon(self):
        """Un quiz validé puis modifié redevient brouillon, sans date de validation."""
        id_quiz = creer_quiz(self.repository)
        self.repository.valider(id_quiz, 1)
        self.repository.modifier(
            id_quiz,
            1,
            titre="Relu",
            description="",
            questions=questions_valides(),
            difficulte="difficile",
        )
        quiz = self.repository.obtenir(id_quiz, 1)
        self.assertEqual(quiz["statut"], "brouillon")
        self.assertIsNone(quiz["date_validation"])
        self.assertEqual(quiz["difficulte"], "difficile")

    def test_valider(self):
        """Un brouillon passe à « valide » une seule fois, avec sa date."""
        id_quiz = creer_quiz(self.repository)
        self.assertTrue(self.repository.valider(id_quiz, 1))
        quiz = self.repository.obtenir(id_quiz, 1)
        self.assertEqual(quiz["statut"], "valide")
        self.assertIsNotNone(quiz["date_validation"])
        self.assertFalse(self.repository.valider(id_quiz, 1))

    def test_supprimer(self):
        """L'enseignant supprime son quiz."""
        id_quiz = creer_quiz(self.repository)
        self.assertTrue(self.repository.supprimer(id_quiz, 1))
        self.assertIsNone(self.repository.obtenir(id_quiz, 1))

    def test_la_base_refuse_un_document_mal_forme(self):
        """Seconde barrière : la règle $jsonSchema est appliquée par MongoDB.

        Un document qui contourne le repository est refusé par la base.
        """
        with self.assertRaises(WriteError):
            self.repository.collection.insert_one({"titre": "Sans questions"})


class InitMongoTests(SimpleTestCase):
    """Commande init_mongo : collection, règle de validation et index."""

    def test_commande_relancable(self):
        """La commande peut être lancée plusieurs fois sans erreur."""
        call_command("init_mongo", verbosity=0)
        call_command("init_mongo", verbosity=0)
        collection = get_db()[NOM_COLLECTION]
        self.assertIn("proprietaire_date", collection.index_information())
        self.assertIn("lecon", collection.index_information())
        options = collection.options()
        self.assertIn("$jsonSchema", options["validator"])


class SuppressionCompteTests(TestCase):
    """Cohérence entre les deux bases à la suppression d'un compte (RGPD)."""

    def test_supprimer_un_enseignant_supprime_ses_quiz(self):
        """Les quiz MongoDB de l'enseignant supprimé disparaissent aussi."""
        repository = QuizRepository()
        self.addCleanup(repository.collection.delete_many, {})
        anne = Utilisateur.objects.create_user(
            "anne.durand@eduquizai.local",
            "Tableau-Noir-2026",
            nom="Durand",
            prenom="Anne",
        )
        creer_quiz(repository, id_utilisateur=anne.pk)
        creer_quiz(repository, id_utilisateur=anne.pk + 1)
        anne.delete()
        self.assertEqual(
            repository.collection.count_documents({"id_utilisateur": anne.pk}), 0
        )
        self.assertEqual(repository.collection.count_documents({}), 1)


class JetonIATests(SimpleTestCase):
    """Le jeton signé par le web doit être accepté par le service IA."""

    def decoder(self, jeton, cle=None):
        """Décode le jeton comme le fait le service IA (signature, émetteur…)."""
        return jwt.decode(
            jeton,
            cle or settings.IA["JWT_SECRET"],
            algorithms=["HS256"],
            audience=DESTINATAIRE,
            issuer=EMETTEUR,
        )

    def test_contenu_du_jeton(self):
        """Les informations attendues par le service IA sont présentes."""
        contenu = self.decoder(creer_jeton_ia(7))
        self.assertEqual(contenu["token_type"], "access")
        self.assertEqual(contenu["user_id"], 7)
        self.assertEqual(contenu["exp"] - contenu["iat"], settings.IA["JWT_DUREE"])

    def test_jetons_distincts(self):
        """Chaque jeton a son propre identifiant."""
        self.assertNotEqual(
            self.decoder(creer_jeton_ia(7))["jti"],
            self.decoder(creer_jeton_ia(7))["jti"],
        )

    def test_mauvais_secret_refuse(self):
        """Un jeton ne se vérifie qu'avec le secret partagé."""
        with self.assertRaises(jwt.InvalidSignatureError):
            self.decoder(creer_jeton_ia(7), cle="x" * 48)
