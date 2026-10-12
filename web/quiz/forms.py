"""Formulaires de l'application quiz."""

from django import forms
from django.core.validators import RegexValidator

from lecons.models import Lecon

from .validation import STATUTS

LIBELLES_STATUT = {"brouillon": "Brouillon", "valide": "Validé"}


# Identifiant tiré par le navigateur pour pouvoir annuler une génération
ID_GENERATION = forms.CharField(
    required=False,
    max_length=64,
    validators=[RegexValidator(r"^[A-Za-z0-9-]+$", "Identifiant invalide.")],
)


class QuizAnnulationForm(forms.Form):
    """Annulation d'une génération en cours : seul l'identifiant est reçu."""

    id_generation = forms.CharField(
        max_length=64,
        validators=[RegexValidator(r"^[A-Za-z0-9-]+$", "Identifiant invalide.")],
    )


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


DIFFICULTES = [("facile", "Facile"), ("moyen", "Moyen"), ("difficile", "Difficile")]
TYPES_QUESTION = [
    ("qcm", "QCM"),
    ("vrai_faux", "Vrai / Faux"),
    ("ouverte", "Question ouverte"),
]
NOMBRE_MIN = 3
NOMBRE_MAX = 20
MESSAGE_NOMBRE = (
    f"Le nombre de questions doit être compris entre {NOMBRE_MIN} et {NOMBRE_MAX}."
)


class QuizGenerationForm(forms.Form):
    """Réglages de la génération d'un quiz (maquette 07).

    La leçon est choisie uniquement parmi celles de l'enseignant connecté :
    l'identifiant d'une leçon d'un autre enseignant est refusé. Le contenu de
    la leçon n'est jamais envoyé par le navigateur, la vue le lit en base.
    """

    lecon = forms.ModelChoiceField(
        label="Leçon",
        queryset=Lecon.objects.none(),
        error_messages={
            "required": "Choisissez une leçon.",
            "invalid_choice": "Cette leçon n'existe pas.",
        },
    )
    titre = forms.CharField(
        label="Titre du quiz",
        max_length=100,
        error_messages={"required": "Le titre est obligatoire."},
    )
    difficulte = forms.ChoiceField(
        label="Difficulté",
        choices=DIFFICULTES,
        initial="moyen",
        error_messages={
            "required": "Choisissez une difficulté.",
            "invalid_choice": "Difficulté inconnue.",
        },
    )
    types = forms.MultipleChoiceField(
        label="Types de questions",
        choices=TYPES_QUESTION,
        initial=["qcm", "vrai_faux"],
        error_messages={
            "required": "Choisissez au moins un type de question.",
            "invalid_choice": "Type de question inconnu.",
        },
    )
    nombre = forms.IntegerField(
        label="Nombre de questions",
        min_value=NOMBRE_MIN,
        max_value=NOMBRE_MAX,
        initial=10,
        error_messages={
            "required": "Indiquez le nombre de questions.",
            "invalid": MESSAGE_NOMBRE,
            "min_value": MESSAGE_NOMBRE,
            "max_value": MESSAGE_NOMBRE,
        },
    )

    id_generation = ID_GENERATION

    def __init__(self, *args, utilisateur, **kwargs):
        """Limite le choix aux leçons de l'enseignant."""
        super().__init__(*args, **kwargs)
        self.fields["lecon"].queryset = Lecon.objects.filter(
            utilisateur=utilisateur
        ).order_by("titre")

    def clean_titre(self):
        """Refuse un titre fait uniquement d'espaces."""
        titre = self.cleaned_data["titre"].strip()
        if not titre:
            raise forms.ValidationError("Le titre est obligatoire.")
        return titre
