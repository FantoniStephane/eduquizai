from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView

from .forms import LeconForm
from .models import Lecon


class LeconListView(ListView):
    """Leçons de l'enseignant connecté (maquette 03, version minimale).

    La tâche 21 ajoutera les filtres, la recherche et la pagination.
    """

    template_name = "lecons/lecon_liste.html"
    context_object_name = "lecons"

    def get_queryset(self):
        """Uniquement les leçons de l'utilisateur connecté."""
        return Lecon.objects.filter(utilisateur=self.request.user)


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
