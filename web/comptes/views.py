"""Vues des comptes : une seule page de connexion pour tous les utilisateurs."""

from django.contrib.auth.views import LoginView
from django.urls import reverse

from .forms import ConnexionForm


class ConnexionView(LoginView):
    """Connexion des enseignants et de l'administrateur (maquette 01).

    C'est la seule porte d'entrée de l'application : la page de connexion de
    l'administration Django redirige ici (voir ``config/urls.py``). La
    limitation des essais (``ConnexionForm``) protège donc aussi le compte
    administrateur. Après la connexion, chacun arrive de son côté :
    l'administrateur dans l'administration, l'enseignant sur son tableau de bord.
    """

    template_name = "comptes/connexion.html"
    authentication_form = ConnexionForm
    redirect_authenticated_user = True

    def get_default_redirect_url(self):
        """Page d'arrivée par défaut, selon le rôle de l'utilisateur connecté."""
        if self.request.user.is_staff:
            return reverse("admin:index")
        return super().get_default_redirect_url()

    def get_redirect_url(self):
        """Page demandée (« next »), sauf l'administration pour un enseignant.

        Un enseignant connecté qui ouvre /admin/ est renvoyé ici par Django ;
        sans ce filtre, il serait aussitôt redirigé vers /admin/, puis ici, et
        ainsi de suite. Il retrouve simplement son tableau de bord.
        """
        url = super().get_redirect_url()
        utilisateur = self.request.user
        if (
            url.startswith(reverse("admin:index"))
            and utilisateur.is_authenticated
            and not utilisateur.is_staff
        ):
            return ""
        return url
