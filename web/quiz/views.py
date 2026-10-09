"""Vues des quiz : liste (tâche 28.5), puis génération et détail (tâches 29 à 31)."""

import logging

from django.views.generic import ListView
from pymongo.errors import PyMongoError

from lecons.models import Lecon

from .forms import QuizFiltreForm
from .repository import QuizRepository

logger = logging.getLogger(__name__)


class QuizListView(ListView):
    """Quiz de l'enseignant connecté (maquette 06).

    Recherche par titre, filtres leçon et statut, pagination par 6. Les quiz
    sont lus par le repository, qui filtre toujours sur le propriétaire.
    """

    template_name = "quiz/quiz_liste.html"
    context_object_name = "quiz_liste"
    paginate_by = 6

    def get_queryset(self):
        """Quiz de l'utilisateur connecté, puis les filtres valides.

        Si MongoDB ne répond pas, la liste est vide et la page l'explique.
        """
        self.mongo_indisponible = False
        self.filtres = QuizFiltreForm(self.request.GET, utilisateur=self.request.user)
        criteres = {}
        if self.filtres.is_valid():
            criteres = {
                "recherche": self.filtres.cleaned_data["q"],
                "id_lecon": self.filtres.cleaned_data["lecon"],
                "statut": self.filtres.cleaned_data["statut"],
            }
        try:
            return QuizRepository().lister(self.request.user.pk, **criteres)
        except PyMongoError:
            logger.exception("MongoDB indisponible : liste des quiz")
            self.mongo_indisponible = True
            return []

    def get_context_data(self, **kwargs):
        """Ajoute filtres, titres des leçons, nombre à valider et paramètres d'URL."""
        contexte = super().get_context_data(**kwargs)
        # Un seul accès à PostgreSQL pour les titres des leçons de la page
        identifiants = {quiz["id_lecon"] for quiz in contexte["quiz_liste"]}
        titres = dict(
            Lecon.objects.filter(
                utilisateur=self.request.user, pk__in=identifiants
            ).values_list("pk", "titre")
        )
        for quiz in contexte["quiz_liste"]:
            quiz["lecon_titre"] = titres.get(quiz["id_lecon"], "—")
        parametres = self.request.GET.copy()
        parametres.pop("page", None)
        contexte["filtres"] = self.filtres
        contexte["parametres"] = parametres.urlencode()
        contexte["filtre_actif"] = any(
            self.request.GET.get(nom) for nom in ("q", "lecon", "statut")
        )
        contexte["nb_a_valider"] = sum(
            1 for quiz in self.object_list if quiz["statut"] == "brouillon"
        )
        contexte["mongo_indisponible"] = self.mongo_indisponible
        return contexte
