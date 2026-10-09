"""Vues générales : tableau de bord de l'enseignant (maquette 02)."""

import logging

from django.views.generic import TemplateView
from pymongo.errors import PyMongoError

from lecons.models import Lecon
from quiz.repository import QuizRepository

logger = logging.getLogger(__name__)

NB_QUIZ_A_VALIDER = 3
NB_DERNIERES_LECONS = 4


class TableauDeBordView(TemplateView):
    """Page d'accueil de l'enseignant : chiffres clés et derniers éléments.

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
