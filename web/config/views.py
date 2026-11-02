"""Vues générales : accueil, tableau de bord (maquette 02), données personnelles."""

import logging

from django.contrib.auth.decorators import login_not_required
from django.shortcuts import redirect
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView
from pymongo.errors import PyMongoError

from lecons.models import Lecon
from quiz.repository import QuizRepository

logger = logging.getLogger(__name__)

NB_QUIZ_A_VALIDER = 3
NB_DERNIERES_LECONS = 4


@method_decorator(login_not_required, name="dispatch")
class AccueilView(TemplateView):
    """Première page du site, publique (maquette 00).

    Elle présente EduQuizAI avant la connexion. Une personne déjà connectée n'a
    pas besoin de cette présentation : elle est renvoyée de son côté, comme à la
    connexion (l'administrateur dans l'administration, l'enseignant sur son
    tableau de bord).
    """

    template_name = "accueil.html"

    def dispatch(self, request, *args, **kwargs):
        """Renvoie les personnes connectées vers leur espace."""
        if request.user.is_authenticated:
            destination = "admin:index" if request.user.is_staff else "tableau_de_bord"
            return redirect(destination)
        return super().dispatch(request, *args, **kwargs)


class TableauDeBordView(TemplateView):
    """Tableau de bord de l'enseignant : chiffres clés et derniers éléments.

    Tout est limité à l'enseignant connecté. Si MongoDB ne répond pas, les
    informations sur les quiz sont remplacées par un message et le reste de la
    page (leçons) s'affiche normalement.
    """

    template_name = "tableau_de_bord.html"

    def get_context_data(self, **kwargs):
        """Leçons (PostgreSQL) puis quiz (MongoDB)."""
        contexte = super().get_context_data(**kwargs)
        lecons = Lecon.objects.filter(utilisateur=self.request.user)
        contexte["nb_lecons"] = lecons.count()
        contexte["dernieres_lecons"] = lecons.order_by("-date_creation", "-pk")[
            :NB_DERNIERES_LECONS
        ]
        contexte["mongo_indisponible"] = False
        try:
            repository = QuizRepository()
            identifiant = self.request.user.pk
            contexte["nb_valides"] = repository.compter(identifiant, "valide")
            contexte["nb_a_valider"] = repository.compter(identifiant, "brouillon")
            a_valider = repository.lister(
                identifiant, statut="brouillon", limite=NB_QUIZ_A_VALIDER
            )
        except PyMongoError:
            logger.exception("MongoDB indisponible : tableau de bord")
            contexte["mongo_indisponible"] = True
            return contexte
        # Un seul accès à PostgreSQL pour les titres, matières et niveaux
        lecons_des_quiz = {
            lecon.pk: lecon
            for lecon in Lecon.objects.filter(
                utilisateur=self.request.user,
                pk__in={quiz["id_lecon"] for quiz in a_valider},
            )
        }
        for quiz in a_valider:
            quiz["lecon"] = lecons_des_quiz.get(quiz["id_lecon"])
        contexte["quiz_a_valider"] = a_valider
        return contexte


@method_decorator(login_not_required, name="dispatch")
class DonneesPersonnellesView(TemplateView):
    """Information des utilisateurs sur leurs données personnelles (RGPD).

    Page publique : elle doit pouvoir être lue avant la première connexion,
    depuis la page de connexion comme depuis toutes les pages de l'application.
    """

    template_name = "donnees_personnelles.html"
