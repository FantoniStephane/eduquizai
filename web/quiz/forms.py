"""Formulaires de l'application quiz."""

from django import forms

from lecons.models import Lecon

from .validation import STATUTS

LIBELLES_STATUT = {"brouillon": "Brouillon", "valide": "Validé"}


class QuizFiltreForm(forms.Form):
    """Recherche et filtres de la liste des quiz (maquette 06).

    Les valeurs arrivent par l'URL (méthode GET). La liste des leçons proposée
    est celle de l'enseignant connecté : l'identifiant d'une leçon qui n'est
    pas la sienne est refusé, donc ignoré.
    """

    q = forms.CharField(label="Rechercher", max_length=100, required=False)
    lecon = forms.ChoiceField(label="Leçon", required=False)
    statut = forms.ChoiceField(
        label="Statut",
        choices=[
            ("", "Tous les statuts"),
            *((statut, LIBELLES_STATUT[statut]) for statut in STATUTS),
        ],
        required=False,
    )

    def __init__(self, *args, utilisateur, **kwargs):
        """Remplit la liste des leçons avec celles de l'enseignant."""
        super().__init__(*args, **kwargs)
        lecons = Lecon.objects.filter(utilisateur=utilisateur).order_by("titre")
        self.fields["lecon"].choices = [
            ("", "Toutes les leçons"),
            *((str(lecon.pk), lecon.titre) for lecon in lecons),
        ]
