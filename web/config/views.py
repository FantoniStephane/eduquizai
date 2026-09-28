from django.views.generic import TemplateView


class TableauDeBordView(TemplateView):
    """Page d'accueil de l'enseignant connecté (version provisoire, maquette 2)."""

    template_name = "tableau_de_bord.html"
