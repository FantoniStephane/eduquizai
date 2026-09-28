from django import forms

from .models import Lecon, Matiere, Niveau

CONTENU_MAX = 20_000


class LeconForm(forms.ModelForm):
    """Création et modification d'une leçon (maquettes 04 et 04b).

    L'enseignant propriétaire n'est pas un champ du formulaire : la vue le
    prend dans la session (request.user), pour qu'on ne puisse pas créer une
    leçon au nom d'un autre utilisateur.
    """

    contenu = forms.CharField(
        label="Contenu de la leçon",
        max_length=CONTENU_MAX,
        widget=forms.Textarea,
    )

    class Meta:
        model = Lecon
        fields = ("titre", "matiere", "niveau_scolaire", "contenu")
        error_messages = {
            "titre": {"required": "Le titre est obligatoire."},
            "matiere": {"required": "Choisissez une matière."},
            "niveau_scolaire": {"required": "Choisissez un niveau scolaire."},
        }

    def __init__(self, *args, **kwargs):
        """Libellés des listes vides, repris des maquettes."""
        super().__init__(*args, **kwargs)
        self.fields["matiere"].choices = [("", "Choisir une matière")] + list(
            self.fields["matiere"].choices
        )[1:]
        self.fields["niveau_scolaire"].choices = [("", "Choisir un niveau")] + list(
            self.fields["niveau_scolaire"].choices
        )[1:]
        self.fields["contenu"].error_messages["required"] = (
            "Le contenu de la leçon est obligatoire."
        )


class LeconFiltreForm(forms.Form):
    """Recherche et filtres de la liste des leçons (maquette 03).

    Les valeurs arrivent par l'URL (méthode GET) : le formulaire les valide,
    une valeur inconnue est simplement ignorée.
    """

    q = forms.CharField(label="Rechercher", max_length=100, required=False)
    matiere = forms.ChoiceField(
        label="Matière",
        choices=[("", "Toutes les matières"), *Matiere.choices],
        required=False,
    )
    niveau = forms.ChoiceField(
        label="Niveau",
        choices=[("", "Tous les niveaux"), *Niveau.choices],
        required=False,
    )
