from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.core.exceptions import PermissionDenied

from .forms import UtilisateurChangeForm, UtilisateurCreationForm
from .models import Utilisateur
from .services import envoyer_invitation


@admin.register(Utilisateur)
class UtilisateurAdmin(UserAdmin):
    """Gestion des comptes enseignants par l'administrateur (US1, US8).

    L'administrateur n'a jamais accès aux mots de passe : chaque utilisateur
    choisit le sien grâce au lien d'invitation envoyé par e-mail.
    """

    add_form = UtilisateurCreationForm
    form = UtilisateurChangeForm
    list_display = ("email", "nom", "prenom", "role", "is_active", "date_creation")
    list_filter = ("role", "is_active")
    search_fields = ("email", "nom", "prenom")
    ordering = ("nom", "prenom")
    readonly_fields = ("date_creation", "last_login")
    filter_horizontal = ()
    actions = ["renvoyer_invitation"]
    fieldsets = (
        (None, {"fields": ("email",)}),
        ("Identité", {"fields": ("nom", "prenom")}),
        ("Droits", {"fields": ("role", "is_active")}),
        ("Dates", {"fields": ("date_creation", "last_login")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "nom", "prenom", "role"),
            },
        ),
    )

    def save_model(self, request, obj, form, change):
        """Enregistre le compte et, à la création, envoie l'invitation."""
        super().save_model(request, obj, form, change)
        if not change:
            envoyer_invitation(obj, request)
            messages.success(request, f"Invitation envoyée à {obj.email}.")

    @admin.action(description="Renvoyer l'invitation")
    def renvoyer_invitation(self, request, queryset):
        """Renvoie le lien d'activation aux comptes pas encore activés."""
        envoyees = 0
        for utilisateur in queryset:
            if not utilisateur.has_usable_password():
                envoyer_invitation(utilisateur, request)
                envoyees += 1
        self.message_user(
            request,
            f"{envoyees} invitation(s) envoyée(s). Les comptes déjà activés "
            "ont été ignorés.",
        )

    def user_change_password(self, request, id, form_url=""):
        """Interdit à l'administrateur de définir le mot de passe d'un utilisateur."""
        raise PermissionDenied
