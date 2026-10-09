from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)
from pymongo.errors import PyMongoError

from quiz.repository import QuizRepository

from .forms import LeconFiltreForm, LeconForm
from .models import Lecon


class LeconListView(ListView):
    """Leçons de l'enseignant connecté (maquette 03).

    Recherche par titre, filtres matière et niveau, pagination par 6. La colonne
    Quiz et les actions (voir, modifier, supprimer) viendront avec leurs pages.
    """

    template_name = "lecons/lecon_liste.html"
    context_object_name = "lecons"
    paginate_by = 6

    def get_queryset(self):
        """Uniquement les leçons de l'utilisateur connecté, puis les filtres valides."""
        lecons = Lecon.objects.filter(utilisateur=self.request.user)
        self.filtres = LeconFiltreForm(self.request.GET)
        if self.filtres.is_valid():
            recherche = self.filtres.cleaned_data["q"]
            matiere = self.filtres.cleaned_data["matiere"]
            niveau = self.filtres.cleaned_data["niveau"]
            if recherche:
                lecons = lecons.filter(titre__icontains=recherche)
            if matiere:
                lecons = lecons.filter(matiere=matiere)
            if niveau:
                lecons = lecons.filter(niveau_scolaire=niveau)
        return lecons

    def get_context_data(self, **kwargs):
        """Ajoute les filtres et les paramètres à conserver dans la pagination."""
        contexte = super().get_context_data(**kwargs)
        parametres = self.request.GET.copy()
        parametres.pop("page", None)
        contexte["filtres"] = self.filtres
        contexte["parametres"] = parametres.urlencode()
        contexte["filtre_actif"] = any(
            self.request.GET.get(nom) for nom in ("q", "matiere", "niveau")
        )
        return contexte


class LeconCreateView(SuccessMessageMixin, CreateView):
    """Création d'une leçon (maquettes 04 et 04b)."""

    model = Lecon
    form_class = LeconForm
    template_name = "lecons/lecon_form.html"
    success_url = reverse_lazy("lecons:liste")
    success_message = "La leçon « %(titre)s » a été enregistrée."

    def form_valid(self, form):
        """Rattache la leçon à l'enseignant connecté avant l'enregistrement."""
        form.instance.utilisateur = self.request.user
        return super().form_valid(form)


class LeconDetailView(DetailView):
    """Détail d'une leçon (maquette 05).

    La leçon est cherchée uniquement parmi celles de l'utilisateur connecté :
    l'identifiant d'une leçon d'un autre enseignant donne une erreur 404
    (protection contre l'accès direct par l'URL, faille IDOR).
    """

    template_name = "lecons/lecon_detail.html"
    context_object_name = "lecon"

    def get_queryset(self):
        """Uniquement les leçons de l'utilisateur connecté."""
        return Lecon.objects.filter(utilisateur=self.request.user)


class LeconUpdateView(SuccessMessageMixin, UpdateView):
    """Modification d'une leçon (maquette 04, même formulaire que la création).

    Comme pour le détail, la leçon est cherchée parmi celles de l'utilisateur
    connecté : impossible de modifier la leçon d'un autre enseignant (404).
    """

    form_class = LeconForm
    template_name = "lecons/lecon_form.html"
    context_object_name = "lecon"
    success_message = "Les modifications ont été enregistrées."

    def get_queryset(self):
        """Uniquement les leçons de l'utilisateur connecté."""
        return Lecon.objects.filter(utilisateur=self.request.user)

    def get_success_url(self):
        """Retour au détail de la leçon modifiée."""
        return reverse("lecons:detail", args=[self.object.pk])


class LeconDeleteView(SuccessMessageMixin, DeleteView):
    """Suppression d'une leçon, après confirmation (maquette 10).

    L'affichage (GET) montre la demande de confirmation ; seule la validation
    du formulaire (POST, protégé par le jeton CSRF) supprime la leçon.
    Une leçon qui a servi à générer des quiz ne peut pas être supprimée : ses
    quiz (dans MongoDB, sans clé étrangère vers PostgreSQL) doivent d'abord
    être supprimés. Si MongoDB ne répond pas, la suppression est refusée.
    """

    template_name = "lecons/lecon_confirmation_suppression.html"
    context_object_name = "lecon"
    success_url = reverse_lazy("lecons:liste")

    def get_queryset(self):
        """Uniquement les leçons de l'utilisateur connecté."""
        return Lecon.objects.filter(utilisateur=self.request.user)

    def nombre_de_quiz(self):
        """Nombre de quiz issus de la leçon (None si MongoDB ne répond pas)."""
        try:
            return QuizRepository().compter_par_lecon(
                self.object.pk, self.request.user.pk
            )
        except PyMongoError:
            return None

    def get_context_data(self, **kwargs):
        """Ajoute le nombre de quiz : la fenêtre change s'il y en a."""
        contexte = super().get_context_data(**kwargs)
        contexte["nb_quiz"] = self.nombre_de_quiz()
        return contexte

    def form_valid(self, form):
        """Supprime la leçon seulement si aucun quiz n'en dépend."""
        nb_quiz = self.nombre_de_quiz()
        if nb_quiz == 0:
            return super().form_valid(form)
        if nb_quiz is None:
            messages.error(
                self.request,
                "Impossible de vérifier les quiz de cette leçon pour le moment. "
                "Réessayez plus tard.",
            )
        else:
            messages.error(
                self.request,
                f"Cette leçon a servi à générer {nb_quiz} quiz : supprimez-les "
                "avant de supprimer la leçon.",
            )
        return redirect("lecons:detail", pk=self.object.pk)

    def get_success_message(self, cleaned_data):
        """Message affiché sur la liste après la suppression."""
        return f"La leçon « {self.object.titre} » a été supprimée."
