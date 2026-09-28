from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

app_name = "comptes"

urlpatterns = [
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
