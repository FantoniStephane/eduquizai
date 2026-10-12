"""Charge les données de démonstration d'EduQuizAI (leçons et quiz).

Utilisation :
    python manage.py donnees_demo --mot-de-passe "<mot de passe>"
    python manage.py donnees_demo --reinitialiser

Le compte de démonstration (enseignante) est créé s'il n'existe pas : son mot
de passe est alors demandé en paramètre et contrôlé par les validateurs de
Django ; il n'est jamais écrit dans le code. Un compte existant garde son mot
de passe.

Par sécurité, la commande refuse d'écraser des données : avec
``--reinitialiser``, elle supprime d'abord les leçons et les quiz de cette
seule enseignante (jamais ceux des autres comptes), puis recharge le jeu de
démonstration. C'est aussi la façon de nettoyer les essais avant une démo.
"""

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from pymongo.errors import PyMongoError

from comptes.models import Role, Utilisateur
from lecons.models import Lecon
from quiz.demo import ENSEIGNANTE, LECONS, QUIZ
from quiz.repository import QuizRepository


class Command(BaseCommand):
    """Crée l'enseignante de démonstration, ses leçons et ses quiz."""

    help = "Charge les leçons et les quiz de démonstration."

    def add_arguments(self, parser):
        """Mot de passe (création du compte) et réinitialisation."""
        parser.add_argument(
            "--mot-de-passe",
            help="Mot de passe du compte de démonstration, s'il faut le créer.",
        )
        parser.add_argument(
            "--reinitialiser",
            action="store_true",
            help="Supprime d'abord les leçons et quiz de l'enseignante de démo.",
        )

    def handle(self, *args, **options):
        """Charge le jeu de démonstration."""
        enseignante = self._enseignante(options["mot_de_passe"])
        repository = QuizRepository()
        try:
            self._preparer(enseignante, repository, options["reinitialiser"])
            with transaction.atomic():
                lecons = {
                    donnees["cle"]: Lecon.objects.create(
                        utilisateur=enseignante,
                        **{k: v for k, v in donnees.items() if k != "cle"},
                    )
                    for donnees in LECONS
                }
            for quiz in QUIZ:
                id_quiz = repository.creer(
                    id_utilisateur=enseignante.pk,
                    id_lecon=lecons[quiz["lecon"]].pk,
                    titre=quiz["titre"],
                    difficulte=quiz["difficulte"],
                    questions=quiz["questions"],
                )
                if quiz["valide"]:
                    repository.valider(id_quiz, enseignante.pk)
        except PyMongoError as erreur:
            raise CommandError("MongoDB ne répond pas : rien n'a été chargé.") from (
                erreur
            )
        self.stdout.write(
            self.style.SUCCESS(
                f"Démonstration prête pour {enseignante.email} : "
                f"{len(LECONS)} leçons, {len(QUIZ)} quiz."
            )
        )

    def _enseignante(self, mot_de_passe):
        """Retourne le compte de démo, créé si besoin (mot de passe contrôlé)."""
        compte = Utilisateur.objects.filter(email=ENSEIGNANTE["email"]).first()
        if compte is not None:
            if compte.role != Role.ENSEIGNANT:
                raise CommandError(f"{compte.email} n'est pas un compte enseignant.")
            if mot_de_passe:
                self.stdout.write("Compte existant : mot de passe inchangé.")
            return compte
        if not mot_de_passe:
            raise CommandError(
                f"Le compte {ENSEIGNANTE['email']} n'existe pas : "
                "indiquez --mot-de-passe pour le créer."
            )
        candidat = Utilisateur(**ENSEIGNANTE)
        try:
            validate_password(mot_de_passe, candidat)
        except ValidationError as erreur:
            raise CommandError(" ".join(erreur.messages)) from erreur
        return Utilisateur.objects.create_user(
            ENSEIGNANTE["email"],
            mot_de_passe,
            nom=ENSEIGNANTE["nom"],
            prenom=ENSEIGNANTE["prenom"],
        )

    def _preparer(self, enseignante, repository, reinitialiser):
        """Refuse d'écraser des données, sauf demande de réinitialisation."""
        lecons = Lecon.objects.filter(utilisateur=enseignante)
        if not reinitialiser:
            if lecons.exists() or repository.compter(enseignante.pk):
                raise CommandError(
                    f"{enseignante.email} a déjà des leçons ou des quiz : "
                    "relancez avec --reinitialiser pour les remplacer."
                )
            return
        nb_quiz = repository.supprimer_par_utilisateur(enseignante.pk)
        nb_lecons, _ = lecons.delete()
        self.stdout.write(f"Supprimé : {nb_lecons} leçon(s), {nb_quiz} quiz.")
