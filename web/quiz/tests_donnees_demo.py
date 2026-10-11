"""Tests de la commande donnees_demo (jeu de démonstration)."""

from io import StringIO

from django.core.management import CommandError, call_command
from django.test import TestCase

from comptes.models import Utilisateur
from lecons.models import Lecon

from .demo import ENSEIGNANTE, LECONS, QUIZ
from .repository import QuizRepository
from .tests import creer_quiz

MOT_DE_PASSE = "Craie-Bleue-4821"


def charger(**options):
    """Lance la commande sans afficher sa sortie."""
    call_command("donnees_demo", stdout=StringIO(), **options)


class DonneesDemoTests(TestCase):
    """Création, protection contre l'écrasement et réinitialisation."""

    def setUp(self):
        """Base des quiz vide avant et après chaque test."""
        self.repository = QuizRepository()
        self.repository.collection.delete_many({})
        self.addCleanup(self.repository.collection.delete_many, {})

    def test_compte_absent_sans_mot_de_passe_refuse(self):
        """Sans mot de passe, le compte n'est pas créé."""
        with self.assertRaises(CommandError):
            charger()
        self.assertFalse(Utilisateur.objects.exists())

    def test_mot_de_passe_faible_refuse(self):
        """Le mot de passe passe par les validateurs de Django."""
        with self.assertRaises(CommandError):
            charger(mot_de_passe="12345678")
        self.assertFalse(Utilisateur.objects.exists())

    def test_chargement_complet(self):
        """Compte utilisable, 4 leçons, 3 quiz dont un validé, tous valides."""
        charger(mot_de_passe=MOT_DE_PASSE)
        anne = Utilisateur.objects.get(email=ENSEIGNANTE["email"])
        self.assertTrue(anne.check_password(MOT_DE_PASSE))
        self.assertEqual(Lecon.objects.filter(utilisateur=anne).count(), len(LECONS))
        self.assertEqual(self.repository.compter(anne.pk), len(QUIZ))
        self.assertEqual(self.repository.compter(anne.pk, "valide"), 1)

    def test_refuse_d_ecraser_des_donnees(self):
        """Une enseignante qui a déjà des leçons n'est pas modifiée."""
        charger(mot_de_passe=MOT_DE_PASSE)
        with self.assertRaises(CommandError):
            charger()
        self.assertEqual(Lecon.objects.count(), len(LECONS))

    def test_reinitialiser_ne_touche_qu_a_l_enseignante_de_demo(self):
        """Les essais de l'enseignante sont remplacés ; un collègue est intact."""
        charger(mot_de_passe=MOT_DE_PASSE)
        anne = Utilisateur.objects.get(email=ENSEIGNANTE["email"])
        Lecon.objects.create(
            utilisateur=anne, titre="Essai", matiere="svt",
            niveau_scolaire="5e", contenu="Texte d'essai",
        )  # fmt: skip
        creer_quiz(self.repository, id_utilisateur=anne.pk, titre="Quiz d'essai")
        collegue = Utilisateur.objects.create_user(
            "marie.martin@eduquizai.local", MOT_DE_PASSE
        )
        Lecon.objects.create(
            utilisateur=collegue, titre="Sa leçon", matiere="svt",
            niveau_scolaire="5e", contenu="Texte",
        )  # fmt: skip
        creer_quiz(self.repository, id_utilisateur=collegue.pk)

        charger(reinitialiser=True, mot_de_passe="Autre-Mot-De-Passe-77")

        self.assertFalse(Lecon.objects.filter(titre="Essai").exists())
        self.assertEqual(Lecon.objects.filter(utilisateur=anne).count(), len(LECONS))
        self.assertEqual(self.repository.compter(anne.pk), len(QUIZ))
        self.assertEqual(Lecon.objects.filter(utilisateur=collegue).count(), 1)
        self.assertEqual(self.repository.compter(collegue.pk), 1)
        anne.refresh_from_db()
        self.assertTrue(anne.check_password(MOT_DE_PASSE))
