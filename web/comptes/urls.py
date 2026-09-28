from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from .forms import ConnexionForm

app_name = "comptes"

urlpatterns = [
    # Connexion et déconnexion
    path(
        "connexion/",
        auth_views.LoginView.as_view(
            template_name="comptes/connexion.html",
            authentication_form=ConnexionForm,
            redirect_authenticated_user=True,
        ),
        name="connexion",
    ),
    path("deconnexion/", auth_views.LogoutView.as_view(), name="deconnexion"),
    # Mot de passe oublié : demande du lien, puis confirmation d'envoi
    path(
        "mot-de-passe/oublie/",
        auth_views.PasswordResetView.as_view(
            template_name="comptes/mot_de_passe_oublie.html",
            email_template_name="comptes/emails/reinitialisation.txt",
            subject_template_name="comptes/emails/reinitialisation_sujet.txt",
            success_url=reverse_lazy("comptes:email_envoye"),
        ),
        name="mot_de_passe_oublie",
    ),
    path(
        "mot-de-passe/email-envoye/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="comptes/email_envoye.html",
        ),
        name="email_envoye",
    ),
    # Choix du mot de passe depuis le lien reçu (invitation ou mot de passe oublié)
    path(
        "mot-de-passe/definir/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="comptes/definir_mot_de_passe.html",
            success_url=reverse_lazy("comptes:mot_de_passe_defini"),
        ),
        name="definir_mot_de_passe",
    ),
    path(
        "mot-de-passe/defini/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="comptes/mot_de_passe_defini.html",
        ),
        name="mot_de_passe_defini",
    ),
]
