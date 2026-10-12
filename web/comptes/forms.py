from django import forms
from django.contrib.auth.forms import AuthenticationForm

from .limitation import (
    MESSAGE_BLOCAGE,
    adresse_ip,
    effacer_echecs,
    enregistrer_echec,
    est_bloque,
)
from .models import Utilisateur


class UtilisateurCreationForm(forms.ModelForm):
    """Création d'un compte par l'administrateur, sans mot de passe.

    L'utilisateur choisit lui-même son mot de passe grâce au lien d'invitation :
    l'administrateur ne le connaît jamais.
    """

    class Meta:
        model = Utilisateur
        fields = ("email", "nom", "prenom", "role")

    def clean_email(self):
        """Enregistre l'adresse en minuscules pour éviter les doublons."""
        return self.cleaned_data["email"].lower()

    def save(self, commit=True):
        """Crée le compte avec un mot de passe inutilisable."""
        utilisateur = super().save(commit=False)
        utilisateur.set_unusable_password()
        if commit:
            utilisateur.save()
        return utilisateur


class UtilisateurChangeForm(forms.ModelForm):
    """Modification d'un compte par l'administrateur (sans accès au mot de passe)."""

    class Meta:
        model = Utilisateur
        fields = ("email", "nom", "prenom", "role", "is_active")

    def clean_email(self):
        """Enregistre l'adresse en minuscules pour éviter les doublons."""
        return self.cleaned_data["email"].lower()


class ConnexionForm(AuthenticationForm):
    """Formulaire de connexion par adresse e-mail et mot de passe.

    Le message d'erreur reste volontairement général : il ne précise pas si
    c'est l'adresse ou le mot de passe qui est faux. Les essais sont limités
    (voir ``limitation.py``) : après trop d'échecs, la connexion est refusée
    sans même vérifier le mot de passe, avec le même message que le compte
    existe ou non.
    """

    error_messages = {
        "invalid_login": "Adresse e-mail ou mot de passe incorrect.",
        "inactive": "Ce compte est désactivé.",
    }

    def clean_username(self):
        """Compare l'adresse en minuscules, comme elle est enregistrée."""
        return self.cleaned_data["username"].lower()

    def clean(self):
        """Refuse si trop d'échecs, sinon vérifie et compte le résultat."""
        adresse = self.cleaned_data.get("username", "")
        ip = adresse_ip(self.request)
        if est_bloque(adresse, ip):
            raise forms.ValidationError(MESSAGE_BLOCAGE, code="trop_de_tentatives")
        try:
            donnees = super().clean()
        except forms.ValidationError:
            enregistrer_echec(adresse, ip)
            raise
        if self.get_user() is not None:
            effacer_echecs(adresse, ip)
        return donnees
